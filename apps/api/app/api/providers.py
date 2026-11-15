"""Provider management routes."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
import httpx
import time

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.security import encrypt_api_key, decrypt_api_key
from app.models.user import User
from app.models.provider import ProviderAccount, ModelEntry
from app.schemas.provider import ProviderCreate, ProviderResponse, ProviderUpdate, ModelEntryResponse, ProviderTestResult

router = APIRouter()


@router.post("/", response_model=ProviderResponse, status_code=status.HTTP_201_CREATED)
async def create_provider(
    data: ProviderCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add a model provider."""
    provider = ProviderAccount(
        user_id=current_user.id,
        provider_type=data.provider_type,
        display_name=data.display_name,
        encrypted_api_key=encrypt_api_key(data.api_key),
        base_url=data.base_url,
        settings=data.settings or {},
    )
    db.add(provider)
    await db.commit()
    await db.refresh(provider)
    return provider


@router.get("/", response_model=list[ProviderResponse])
async def list_providers(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List user's providers."""
    result = await db.execute(select(ProviderAccount).where(ProviderAccount.user_id == current_user.id))
    return result.scalars().all()


@router.get("/{provider_id}", response_model=ProviderResponse)
async def get_provider(
    provider_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get provider details."""
    result = await db.execute(
        select(ProviderAccount).where(
            ProviderAccount.id == provider_id,
            ProviderAccount.user_id == current_user.id,
        )
    )
    provider = result.scalar_one_or_none()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    return provider


@router.patch("/{provider_id}", response_model=ProviderResponse)
async def update_provider(
    provider_id: UUID,
    data: ProviderUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update provider."""
    result = await db.execute(
        select(ProviderAccount).where(
            ProviderAccount.id == provider_id,
            ProviderAccount.user_id == current_user.id,
        )
    )
    provider = result.scalar_one_or_none()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")

    update_data = data.model_dump(exclude_unset=True)
    if "api_key" in update_data and update_data["api_key"]:
        update_data["encrypted_api_key"] = encrypt_api_key(update_data.pop("api_key"))

    for field, value in update_data.items():
        setattr(provider, field, value)

    await db.commit()
    await db.refresh(provider)
    return provider


@router.delete("/{provider_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_provider(
    provider_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a provider."""
    result = await db.execute(
        select(ProviderAccount).where(
            ProviderAccount.id == provider_id,
            ProviderAccount.user_id == current_user.id,
        )
    )
    provider = result.scalar_one_or_none()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    await db.delete(provider)
    await db.commit()


@router.post("/{provider_id}/test", response_model=ProviderTestResult)
async def test_provider(
    provider_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Test provider connection with actual HTTP check."""
    result = await db.execute(
        select(ProviderAccount).where(
            ProviderAccount.id == provider_id,
            ProviderAccount.user_id == current_user.id,
        )
    )
    provider = result.scalar_one_or_none()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")

    try:
        start = time.time()
        api_key = decrypt_api_key(provider.encrypted_api_key) if provider.encrypted_api_key else ""
        ptype = provider.provider_type.lower()
        base_url = provider.base_url

        async with httpx.AsyncClient(timeout=10.0) as client:
            if "ollama" in ptype:
                url = base_url or "http://localhost:11434"
                resp = await client.get(f"{url}/api/tags")
                resp.raise_for_status()
                data = resp.json()
                models = data.get("models", [])
                latency = (time.time() - start) * 1000
                return ProviderTestResult(success=True, latency_ms=latency, models_found=len(models))

            elif "gemini" in ptype or "google" in ptype:
                url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
                resp = await client.get(url)
                resp.raise_for_status()
                data = resp.json()
                models = data.get("models", [])
                latency = (time.time() - start) * 1000
                return ProviderTestResult(success=True, latency_ms=latency, models_found=len(models))

            elif "groq" in ptype:
                headers = {"Authorization": f"Bearer {api_key}"}
                resp = await client.get("https://api.groq.com/openai/v1/models", headers=headers)
                resp.raise_for_status()
                data = resp.json()
                models = data.get("data", [])
                latency = (time.time() - start) * 1000
                return ProviderTestResult(success=True, latency_ms=latency, models_found=len(models))

            elif "openrouter" in ptype:
                headers = {"Authorization": f"Bearer {api_key}"}
                resp = await client.get("https://openrouter.ai/api/v1/models", headers=headers)
                resp.raise_for_status()
                data = resp.json()
                models = data.get("data", [])
                latency = (time.time() - start) * 1000
                return ProviderTestResult(success=True, latency_ms=latency, models_found=len(models))

            elif "nvidia" in ptype or "nim" in ptype:
                url = base_url or "https://integrate.api.nvidia.com/v1"
                headers = {"Authorization": f"Bearer {api_key}"}
                resp = await client.get(f"{url}/models", headers=headers)
                resp.raise_for_status()
                data = resp.json()
                models = data.get("data", [])
                latency = (time.time() - start) * 1000
                return ProviderTestResult(success=True, latency_ms=latency, models_found=len(models))

            elif "github" in ptype:
                # GitHub Models lists via a separate catalog path.
                headers = {"Authorization": f"Bearer {api_key}", "Accept": "application/json"}
                resp = await client.get("https://models.github.ai/catalog/models", headers=headers)
                resp.raise_for_status()
                data = resp.json()
                models = data if isinstance(data, list) else data.get("data", [])
                latency = (time.time() - start) * 1000
                return ProviderTestResult(success=True, latency_ms=latency, models_found=len(models))

            else:
                # Generic OpenAI-compatible endpoint test. Known fixed-URL providers
                # (that have no user-supplied base_url) are resolved here.
                _bases = {
                    "sambanova": "https://api.sambanova.ai/v1",
                    "cohere": "https://api.cohere.com/compatibility/v1",
                }
                url = base_url or _bases.get(ptype) or "https://api.openai.com/v1"
                headers = {"Authorization": f"Bearer {api_key}"}
                resp = await client.get(f"{url}/models", headers=headers)
                resp.raise_for_status()
                data = resp.json()
                models = data.get("data", [])
                latency = (time.time() - start) * 1000
                return ProviderTestResult(success=True, latency_ms=latency, models_found=len(models))

    except Exception as e:
        return ProviderTestResult(success=False, error=str(e))


@router.get("/{provider_id}/models", response_model=list[ModelEntryResponse])
async def list_provider_models(
    provider_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List models for a provider."""
    result = await db.execute(
        select(ModelEntry).where(ModelEntry.provider_id == provider_id)
    )
    return result.scalars().all()
