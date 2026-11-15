"""Task management routes."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from datetime import datetime, timezone

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.task import AgentTask, AgentTaskStatus, TaskComplexity
from app.schemas.task import TaskCreate, TaskResponse, TaskUpdate

router = APIRouter()


@router.post("/", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    data: TaskCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new agent task."""
    task = AgentTask(
        user_id=current_user.id,
        conversation_id=data.conversation_id,
        project_id=data.project_id,
        description=data.description,
        complexity=data.complexity,
        priority=data.priority,
        model_used=data.model_override,
        agent_type=data.agent_type or "general",
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task


@router.get("/", response_model=list[TaskResponse])
async def list_tasks(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = 50,
    offset: int = 0,
    status_filter: str | None = None,
):
    """List user's tasks."""
    query = select(AgentTask).where(AgentTask.user_id == current_user.id)
    if status_filter:
        query = query.where(AgentTask.status == status_filter)
    query = query.order_by(AgentTask.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get task details."""
    result = await db.execute(
        select(AgentTask).where(AgentTask.id == task_id, AgentTask.user_id == current_user.id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.post("/{task_id}/pause", response_model=TaskResponse)
async def pause_task(
    task_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Pause a running task."""
    result = await db.execute(
        select(AgentTask).where(AgentTask.id == task_id, AgentTask.user_id == current_user.id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.status not in ("EXECUTING", "PLANNING", "VERIFYING"):
        raise HTTPException(status_code=400, detail=f"Cannot pause task in status: {task.status}")

    task.status = AgentTaskStatus.PAUSED
    await db.commit()
    await db.refresh(task)
    return task


@router.post("/{task_id}/resume", response_model=TaskResponse)
async def resume_task(
    task_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Resume a paused task."""
    result = await db.execute(
        select(AgentTask).where(AgentTask.id == task_id, AgentTask.user_id == current_user.id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.status != AgentTaskStatus.PAUSED:
        raise HTTPException(status_code=400, detail="Task is not paused")

    task.status = AgentTaskStatus.EXECUTING
    await db.commit()
    await db.refresh(task)
    return task


@router.post("/{task_id}/cancel", response_model=TaskResponse)
async def cancel_task(
    task_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Cancel a task."""
    result = await db.execute(
        select(AgentTask).where(AgentTask.id == task_id, AgentTask.user_id == current_user.id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.status in (AgentTaskStatus.COMPLETED, AgentTaskStatus.CANCELLED):
        raise HTTPException(status_code=400, detail=f"Task already {task.status.value.lower()}")

    task.status = AgentTaskStatus.CANCELLED
    task.completed_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(task)
    return task
