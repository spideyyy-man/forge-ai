"""Code intelligence routes — surface the local agent's codebase index over REST."""
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.tool_dispatcher import execute_remote_tool
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.device import Device
from app.models.user import User
from app.models.workspace import Workspace
from app.websocket.manager import connection_manager

logger = logging.getLogger(__name__)
router = APIRouter()


async def _resolve_device_workspace(user: User, db: AsyncSession):
    """Find the user's live agent device and active workspace path."""
    dev_res = await db.execute(
        select(Device).where(Device.user_id == user.id, Device.status == "ACTIVE")
    )
    device_id = None
    for d in dev_res.scalars().all():
        if connection_manager.is_device_connected(str(d.id)):
            device_id = str(d.id)
            break
    ws_res = await db.execute(
        select(Workspace).where(Workspace.user_id == user.id, Workspace.is_active == True)  # noqa: E712
    )
    ws = ws_res.scalars().first()
    return device_id, (ws.root_path if ws else None)


@router.get("/status")
async def index_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Current index stats from the connected agent (or connected=False if none)."""
    device_id, workspace_path = await _resolve_device_workspace(current_user, db)
    if not device_id:
        return {"connected": False, "workspace_path": workspace_path, "stats": None}
    try:
        stats = await execute_remote_tool(device_id, "index_stats", {}, user_id=str(current_user.id))
    except Exception as e:
        return {"connected": True, "workspace_path": workspace_path, "stats": None, "error": str(e)}
    return {"connected": True, "workspace_path": workspace_path, "stats": stats}


@router.post("/index")
async def reindex(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Run an incremental index of the active workspace on the connected agent."""
    device_id, workspace_path = await _resolve_device_workspace(current_user, db)
    if not device_id:
        raise HTTPException(status_code=400, detail="No connected local agent. Pair and connect an agent first.")
    if not workspace_path:
        raise HTTPException(status_code=400, detail="No active workspace selected.")
    try:
        return await execute_remote_tool(
            device_id, "index_workspace", {"root_path": workspace_path}, user_id=str(current_user.id)
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Indexing failed: {e}")


@router.get("/search")
async def search_symbols(
    q: str = Query(..., min_length=1),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Search the agent's symbol index."""
    device_id, _ = await _resolve_device_workspace(current_user, db)
    if not device_id:
        raise HTTPException(status_code=400, detail="No connected local agent.")
    try:
        results = await execute_remote_tool(
            device_id, "search_symbols", {"query": q, "limit": 50}, user_id=str(current_user.id)
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Search failed: {e}")
    return {"results": results}
