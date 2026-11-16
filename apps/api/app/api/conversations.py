"""Conversation management routes with background LangGraph autonomous execution."""
import asyncio
import logging
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID

from app.core.database import get_db, AsyncSessionLocal
from app.core.deps import get_current_user
from app.models.user import User
from app.models.device import Device
from app.models.conversation import Conversation, Message, MessageRole
from app.models.workspace import Workspace
from app.schemas.conversation import ConversationCreate, ConversationResponse, MessageCreate, MessageResponse
from app.agents.workflow import engineering_graph
from app.websocket.manager import connection_manager

logger = logging.getLogger(__name__)

router = APIRouter()


async def run_agent_workflow(
    conversation_id: str,
    user_id: str,
    prompt: str,
    project_id: str = None,
):
    """Background task to run LangGraph cycle and stream back to database and client."""
    import uuid as _uuid

    # IDs arrive as strings; the ORM columns are Uuid, so comparing a raw string
    # raises "'str' object has no attribute 'hex'". Coerce before any query.
    try:
        user_uuid = _uuid.UUID(str(user_id))
        conv_uuid = _uuid.UUID(str(conversation_id))
    except (ValueError, TypeError):
        logger.error("run_agent_workflow: invalid user/conversation id")
        return

    async with AsyncSessionLocal() as db:
        # Check active device for user
        # Use the agent only if it's actually connected over WebSocket. Pick the first
        # ACTIVE device whose agent is live; a stale "ACTIVE" row with no live agent
        # would otherwise stall the workflow on remote tool calls that never return.
        device_res = await db.execute(select(Device).where(Device.user_id == user_uuid, Device.status == "ACTIVE"))
        device_id = None
        for d in device_res.scalars().all():
            if connection_manager.is_device_connected(str(d.id)):
                device_id = str(d.id)
                break
        if device_id is None:
            logger.info("No connected agent; running task in sandbox mode")

        # Check workspace root
        workspace_res = await db.execute(select(Workspace).where(Workspace.user_id == user_uuid, Workspace.is_active == True))
        workspace = workspace_res.scalars().first()
        workspace_path = workspace.root_path if workspace else "."

        # Resolve the project's privacy mode. LOCAL_ONLY forbids any cloud contact
        # (including model discovery); it is enforced again in the router.
        privacy_mode = "CLOUD_ASSISTED"
        if project_id:
            try:
                from app.models.project import Project
                proj_res = await db.execute(select(Project).where(Project.id == _uuid.UUID(str(project_id))))
                proj = proj_res.scalar_one_or_none()
                if proj and proj.privacy_mode is not None:
                    privacy_mode = str(getattr(proj.privacy_mode, "value", proj.privacy_mode)).upper()
            except Exception as e:
                logger.warning("Could not load project privacy mode: %s", e)
        local_only = privacy_mode == "LOCAL_ONLY"

        # Load the user's BYOK provider keys (decrypted) so the agent can call their
        # models. The model registry names providers slightly differently from the
        # ProviderType enum, so map DB type -> registry provider name.
        DB_TO_REGISTRY = {"GOOGLE": "GEMINI", "NVIDIA": "NVIDIA_NIM"}
        configured_keys: dict = {}
        provider_metas = []  # (db_type, reg_name, key, base_url)
        try:
            from app.models.provider import ProviderAccount
            from app.core.security import decrypt_api_key
            prov_res = await db.execute(
                select(ProviderAccount).where(
                    ProviderAccount.user_id == user_uuid,
                    ProviderAccount.is_enabled == True,
                )
            )
            for p in prov_res.scalars().all():
                if not p.encrypted_api_key:
                    continue
                db_type = str(getattr(p.provider_type, "value", p.provider_type)).upper()
                reg_name = DB_TO_REGISTRY.get(db_type, db_type)
                try:
                    key = decrypt_api_key(p.encrypted_api_key)
                except Exception:
                    logger.warning("Could not decrypt key for provider %s", db_type)
                    continue
                configured_keys.setdefault(reg_name, []).append(key)  # multiple keys per provider → rotation
                provider_metas.append((db_type, reg_name, key, getattr(p, "base_url", None)))
        except Exception as e:
            logger.warning("Could not load provider keys: %s", e)

        # FORGE-as-router (Path B): ask each provider what models the key can actually
        # call, then rank registry ∩ live-available first, plus free-friendly extras.
        # Skipped entirely in Local-Only mode — discovery would contact cloud providers.
        model_candidates = []
        if not local_only:
          try:
            from app.providers.discovery import discover_models
            from app.providers.router import assemble_candidates
            results = await asyncio.gather(
                *[discover_models(dbt, key, burl) for (dbt, reg, key, burl) in provider_metas],
                return_exceptions=True,
            )
            avail, discovered_ok, all_discovered = {}, set(), []
            for (dbt, reg, key, burl), res in zip(provider_metas, results):
                if isinstance(res, Exception) or not res:
                    continue
                discovered_ok.add(reg)
                avail.setdefault(reg, set())
                for d in res:
                    avail[reg].add(d["model_id"])
                    all_discovered.append(d)
            model_candidates = assemble_candidates(set(configured_keys.keys()), avail, discovered_ok, all_discovered)
            logger.info("Model candidates for task: %s", [c["litellm_id"] for c in model_candidates])
          except Exception as e:
            logger.warning("Model discovery failed: %s", e)

        # Build a snapshot of the active workspace so the agent reasons about real code.
        repo_context = ""
        try:
            from app.agents.context import build_repo_context
            repo_context = await asyncio.to_thread(build_repo_context, workspace_path)
        except Exception as e:
            logger.warning("Could not build repo context: %s", e)

        # Initial state
        initial_state = {
            "task_id": str(conversation_id),
            "user_id": str(user_id),
            "device_id": device_id,
            "workspace_path": workspace_path,
            "configured_keys": configured_keys,
            "privacy_mode": privacy_mode,
            "repo_context": repo_context,
            "model_candidates": model_candidates,
            "description": prompt,
            "status": "PENDING",
            "plan": [],
            "current_step_index": 0,
            "messages": [],
            "modified_files": [],
            "executed_commands": [],
            "undo_buffer": [],
            "diagnostics": None,
            "error": None,
            "repair_context": None,
            "verification_passed": False,
            "retry_count": 0,
            "max_retries": 2,
        }

        # Run state graph
        try:
            final_state = await engineering_graph.ainvoke(initial_state)

            # Record final assistant message
            assistant_messages = [m for m in final_state.get("messages", []) if m.get("role") == "assistant"]
            reply_text = assistant_messages[-1]["content"] if assistant_messages else "Workflow completed."

            assistant_msg = Message(
                conversation_id=conv_uuid,
                role=MessageRole.ASSISTANT,
                content=reply_text,
            )
            db.add(assistant_msg)
            await db.commit()

            # Push notification to client over WebSocket if user is listening
            await connection_manager.send_to_user(str(user_id), {
                "type": "agent_event",
                "event_type": "completion",
                "conversation_id": str(conversation_id),
                "content": reply_text,
                "plan": final_state.get("plan"),
                "modified_files": final_state.get("modified_files", []),
                "executed_commands": final_state.get("executed_commands", []),
                "verification_passed": final_state.get("verification_passed"),
            })

        except Exception as e:
            err_msg = Message(
                conversation_id=conv_uuid,
                role=MessageRole.SYSTEM,
                content=f"Engineering agent error: {str(e)}",
            )
            db.add(err_msg)
            await db.commit()


@router.post("/", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    data: ConversationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new conversation."""
    conversation = Conversation(
        user_id=current_user.id,
        project_id=data.project_id,
        title=data.title or "New Conversation",
        model_id=data.model_id,
        agent_type=data.agent_type or "planner",
    )
    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)
    return conversation


@router.get("/", response_model=list[ConversationResponse])
async def list_conversations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = 50,
    offset: int = 0,
):
    """List user's conversations."""
    result = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == current_user.id)
        .order_by(Conversation.updated_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return result.scalars().all()


@router.get("/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get conversation details."""
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id,
        )
    )
    conversation = result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@router.get("/{conversation_id}/messages", response_model=list[MessageResponse])
async def get_messages(
    conversation_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = 100,
    offset: int = 0,
):
    """Get conversation messages."""
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Conversation not found")

    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
        .limit(limit)
        .offset(offset)
    )
    return result.scalars().all()


@router.post("/{conversation_id}/messages", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def create_message(
    conversation_id: UUID,
    data: MessageCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Send a message and trigger LangGraph agent cycle."""
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id,
        )
    )
    conversation = result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    role_str = data.role.upper() if hasattr(data.role, "upper") else "USER"
    try:
        role_enum = MessageRole(role_str)
    except ValueError:
        role_enum = MessageRole.USER

    message = Message(
        conversation_id=conversation_id,
        role=role_enum,
        content=data.content,
        model_used=data.model_override,
    )
    db.add(message)
    await db.commit()
    await db.refresh(message)

    # Dispatch agent graph in background if message is from user
    if role_enum == MessageRole.USER:
        background_tasks.add_task(
            run_agent_workflow,
            str(conversation_id),
            str(current_user.id),
            data.content,
            str(conversation.project_id) if conversation.project_id else None,
        )

    return message


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a conversation."""
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id,
        )
    )
    conversation = result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    await db.delete(conversation)
    await db.commit()
