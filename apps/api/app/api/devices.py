"""Device management routes."""
import secrets
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.security import generate_device_token, hash_device_token, hash_password
from app.models.user import User
from app.models.device import Device
from app.schemas.device import DeviceRegister, DevicePair, DeviceResponse, DeviceStatusUpdate
from app.websocket.manager import connection_manager

router = APIRouter()


def _with_presence(device: Device) -> DeviceResponse:
    """Build a response and stamp the live connection state from the socket map."""
    resp = DeviceResponse.model_validate(device)
    resp.is_connected = connection_manager.is_device_connected(str(device.id))
    return resp


@router.post("/register", response_model=DeviceResponse, status_code=status.HTTP_201_CREATED)
async def register_device(
    data: DeviceRegister,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Register a new device and generate a pairing code."""
    pairing_code = secrets.token_hex(3).upper()[:6]

    device = Device(
        user_id=current_user.id,
        name=data.name,
        device_type=data.device_type,
        status="PENDING",
        pairing_code=pairing_code,
        pairing_code_expires_at=datetime.now(timezone.utc) + timedelta(minutes=15),
        os_info=data.os_info,
    )
    db.add(device)
    await db.commit()
    await db.refresh(device)
    return device


@router.post("/pair")
async def pair_device(
    data: DevicePair,
    db: AsyncSession = Depends(get_db),
):
    """Pair a device using a pairing code."""
    result = await db.execute(
        select(Device).where(
            Device.id == data.device_id,
            Device.pairing_code == data.pairing_code,
            Device.status == "PENDING",
        )
    )
    device = result.scalar_one_or_none()

    if not device:
        # Distinguish "already paired" from "bad code" so the user isn't stuck on a
        # confusing 404 after a successful first pair.
        existing = (
            await db.execute(select(Device).where(Device.id == data.device_id))
        ).scalar_one_or_none()
        if existing is not None and str(getattr(existing.status, "value", existing.status)).upper() == "ACTIVE":
            raise HTTPException(status_code=409, detail="Device is already paired. Reconnect with the saved credentials (run the agent with no --pair).")
        raise HTTPException(status_code=404, detail="Invalid or expired pairing code.")

    expires_at = device.pairing_code_expires_at
    if expires_at is not None:
        # SQLite returns naive datetimes even for tz-aware columns; normalize to UTC.
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) > expires_at:
            raise HTTPException(status_code=400, detail="Pairing code has expired")

    # Generate auth token
    auth_token = generate_device_token()
    device.auth_token_hash = hash_device_token(auth_token)
    device.status = "ACTIVE"
    device.pairing_code = None

    await db.commit()
    await db.refresh(device)

    return {"device_id": str(device.id), "auth_token": auth_token, "status": "paired"}


@router.get("/", response_model=list[DeviceResponse])
async def list_devices(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List user's devices."""
    result = await db.execute(select(Device).where(Device.user_id == current_user.id))
    return [_with_presence(d) for d in result.scalars().all()]


@router.get("/{device_id}", response_model=DeviceResponse)
async def get_device(
    device_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get device details."""
    result = await db.execute(
        select(Device).where(Device.id == device_id, Device.user_id == current_user.id)
    )
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return _with_presence(device)


@router.patch("/{device_id}", response_model=DeviceResponse)
async def update_device(
    device_id: UUID,
    data: DeviceStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update device status."""
    result = await db.execute(
        select(Device).where(Device.id == device_id, Device.user_id == current_user.id)
    )
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(device, field, value)

    await db.commit()
    await db.refresh(device)
    return device


@router.delete("/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_device(
    device_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Revoke a device."""
    result = await db.execute(
        select(Device).where(Device.id == device_id, Device.user_id == current_user.id)
    )
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    device.status = "REVOKED"
    await db.commit()
