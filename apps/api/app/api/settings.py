"""User settings routes — currently the agent approval policy."""
from typing import Any, Dict

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.approval_policy import DEFAULT_POLICY, OP_CLASSES, normalize_policy
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.approval import ApprovalPolicy
from app.models.user import User

router = APIRouter()


class PolicyBody(BaseModel):
    modes: Dict[str, Any]


def _payload(modes: Dict[str, str]) -> Dict[str, Any]:
    return {"modes": modes, "classes": OP_CLASSES, "defaults": DEFAULT_POLICY}


@router.get("/approval-policy")
async def get_approval_policy(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the user's approval policy (safe defaults if none saved)."""
    row = (
        await db.execute(select(ApprovalPolicy).where(ApprovalPolicy.user_id == current_user.id))
    ).scalar_one_or_none()
    return _payload(normalize_policy(row.modes if row else None))


@router.put("/approval-policy")
async def update_approval_policy(
    body: PolicyBody,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upsert the user's approval policy. Input is normalized server-side, so an invalid
    mode can never weaken the gate below its safe default."""
    modes = normalize_policy(body.modes)
    row = (
        await db.execute(select(ApprovalPolicy).where(ApprovalPolicy.user_id == current_user.id))
    ).scalar_one_or_none()
    if row is None:
        row = ApprovalPolicy(user_id=current_user.id, modes=modes)
        db.add(row)
    else:
        row.modes = modes
    await db.commit()
    return _payload(modes)
