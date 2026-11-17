"""FORGE AI - FastAPI Application"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging

from app.core.config import settings
from app.core.database import engine, Base, get_db
from app.core.security import verify_device_token
from app.models.device import Device, DeviceStatus
from app.api import auth, devices, workspaces, projects, providers, conversations, tasks, health
from app.websocket.manager import connection_manager
from app.websocket.handlers import handle_websocket_message

logger = logging.getLogger(__name__)

# Default local development account. Seeded only when DEBUG is on so the web app
# can sign in automatically and work out-of-the-box on a fresh machine.
DEV_USER_EMAIL = "dev@forge.local"
DEV_USER_NAME = "dev"
DEV_USER_PASSWORD = "forgedev123"


async def seed_dev_user() -> None:
    """Create the default local dev user if it does not already exist (DEBUG only)."""
    from sqlalchemy import select
    from app.core.database import AsyncSessionLocal
    from app.core.security import hash_password
    from app.models.user import User

    async with AsyncSessionLocal() as db:
        existing = await db.execute(select(User).where(User.email == DEV_USER_EMAIL))
        if existing.scalar_one_or_none():
            return
        db.add(
            User(
                email=DEV_USER_EMAIL,
                username=DEV_USER_NAME,
                hashed_password=hash_password(DEV_USER_PASSWORD),
                is_verified=True,
            )
        )
        await db.commit()
        logger.info("Seeded development user %s (password: %s)", DEV_USER_EMAIL, DEV_USER_PASSWORD)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    logger.info("FORGE AI Backend starting up...")
    # Create tables if they don't exist (dev mode)
    if settings.DEBUG:
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
        except Exception as e:
            logger.warning(f"Database initialization warning: {e}")
        try:
            await seed_dev_user()
        except Exception as e:
            logger.warning(f"Dev user seed warning: {e}")
    yield
    logger.info("FORGE AI Backend shutting down...")
    await engine.dispose()


app = FastAPI(
    title="FORGE AI",
    description="Multi-model autonomous AI software engineering platform",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS
cors_origins = (
    settings.CORS_ORIGINS
    if isinstance(settings.CORS_ORIGINS, list)
    else (settings.CORS_ORIGINS.split(",") if settings.CORS_ORIGINS else ["http://localhost:3000"])
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


# Include routers
app.include_router(health.router, prefix="/api", tags=["Health"])
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(devices.router, prefix="/api/devices", tags=["Devices"])
app.include_router(workspaces.router, prefix="/api/workspaces", tags=["Workspaces"])
app.include_router(projects.router, prefix="/api/projects", tags=["Projects"])
app.include_router(providers.router, prefix="/api/providers", tags=["Providers"])
app.include_router(conversations.router, prefix="/api/conversations", tags=["Conversations"])
app.include_router(tasks.router, prefix="/api/tasks", tags=["Tasks"])


# WebSocket endpoints
@app.websocket("/ws/user/{user_id}")
async def websocket_user(websocket: WebSocket, user_id: str):
    """WebSocket endpoint for frontend clients."""
    await connection_manager.connect_user(websocket, user_id)
    try:
        while True:
            data = await websocket.receive_json()
            await handle_websocket_message(data, user_id=user_id)
    except WebSocketDisconnect:
        connection_manager.disconnect_user(user_id)
    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {e}")
        connection_manager.disconnect_user(user_id)


@app.websocket("/ws/agent")
async def websocket_agent(websocket: WebSocket):
    """WebSocket endpoint for local workspace agents."""
    # Authenticate the agent connection
    await websocket.accept()
    device_id = None
    try:
        # First message should be authentication
        auth_msg = await websocket.receive_json()
        device_id = auth_msg.get("device_id")
        auth_token = auth_msg.get("auth_token")

        if not device_id or not auth_token:
            await websocket.send_json({"type": "auth_error", "message": "Missing credentials"})
            await websocket.close()
            return

        # The device_id arrives as a string; coerce it to UUID for the typed column.
        import uuid as _uuid
        try:
            device_uuid = _uuid.UUID(str(device_id))
        except (ValueError, TypeError):
            await websocket.send_json({"type": "auth_error", "message": "Invalid device id"})
            await websocket.close()
            return

        # Validate auth_token against stored hash using db session
        from app.core.database import AsyncSessionLocal
        from app.core.security import verify_device_token
        from app.models.device import Device, DeviceStatus
        from sqlalchemy import select

        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Device).where(Device.id == device_uuid))
            device = result.scalar_one_or_none()

        if not device:
            await websocket.send_json({"type": "auth_error", "message": "Device not found"})
            await websocket.close()
            return
        if device.status == DeviceStatus.REVOKED:
            await websocket.send_json({"type": "auth_error", "message": "Device revoked"})
            await websocket.close()
            return
        if not device.auth_token_hash or not verify_device_token(auth_token, device.auth_token_hash):
            await websocket.send_json({"type": "auth_error", "message": "Invalid auth token"})
            await websocket.close()
            return
        await connection_manager.connect_device(websocket, device_id)
        await websocket.send_json({"type": "auth_success", "message": "Connected"})

        while True:
            data = await websocket.receive_json()
            await handle_websocket_message(data, device_id=device_id)
    except WebSocketDisconnect:
        if device_id:
            await connection_manager.mark_device_disconnected(device_id)
    except Exception as e:
        logger.error(f"WebSocket error for agent: {e}")
        if device_id:
            await connection_manager.mark_device_disconnected(device_id)
