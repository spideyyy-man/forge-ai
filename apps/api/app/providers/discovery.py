"""Live model discovery — query each provider's real model list so the router uses
models the user's keys can actually call (no stale/blocked hardcoded IDs).

FORGE-as-its-own-router (Path B): instead of trusting a fixed registry, we ask each
configured provider "what models do I have?" and route to those. Results are cached
briefly so we don't hit the providers on every task.
"""
import time
import logging
import httpx

logger = logging.getLogger(__name__)

# DB ProviderType -> registry provider name (what ModelCapability.provider uses).
DB_TO_REGISTRY = {"GOOGLE": "GEMINI", "NVIDIA": "NVIDIA_NIM"}

# provider_type (DB, upper) -> how to list its models.
# style: "openai" (GET {url} Bearer -> {data:[{id}]}), "gemini" (key as query param),
#        "anthropic" (x-api-key header).  prefix is the litellm model prefix.
_PROVIDERS = {
    "GROQ":       {"url": "https://api.groq.com/openai/v1/models",            "style": "openai",    "prefix": "groq/"},
    "DEEPSEEK":   {"url": "https://api.deepseek.com/models",                  "style": "openai",    "prefix": "deepseek/"},
    "MISTRAL":    {"url": "https://api.mistral.ai/v1/models",                 "style": "openai",    "prefix": "mistral/"},
    "OPENROUTER": {"url": "https://openrouter.ai/api/v1/models",              "style": "openai",    "prefix": "openrouter/"},
    "CEREBRAS":   {"url": "https://api.cerebras.ai/v1/models",                "style": "openai",    "prefix": "cerebras/"},
    "NVIDIA":     {"url": "https://integrate.api.nvidia.com/v1/models",       "style": "openai",    "prefix": "nvidia_nim/"},
    "SAMBANOVA":  {"url": "https://api.sambanova.ai/v1/models",               "style": "openai",    "prefix": "sambanova/"},
    "GITHUB":     {"url": "https://models.github.ai/catalog/models", "style": "openai", "prefix": "openai/", "api_base": "https://models.github.ai/inference"},
    "OPENAI":     {"url": "https://api.openai.com/v1/models",                 "style": "openai",    "prefix": "openai/"},
    "ANTHROPIC":  {"url": "https://api.anthropic.com/v1/models",              "style": "anthropic", "prefix": "anthropic/"},
    "GOOGLE":     {"url": "https://generativelanguage.googleapis.com/v1beta/models", "style": "gemini", "prefix": "gemini/"},
}

_CACHE: dict = {}          # key -> (expires_at, result)
_TTL = 600                 # 10 minutes


async def discover_models(provider_type: str, api_key: str, base_url: str | None = None) -> list[dict]:
    """Return [{model_id, litellm_id, provider}] for models this key can call. [] on failure."""
    ptype = (provider_type or "").upper()
    cache_key = f"{ptype}:{hash(api_key)}:{base_url or ''}"
    hit = _CACHE.get(cache_key)
    if hit and hit[0] > time.time():
        return hit[1]

    cfg = _PROVIDERS.get(ptype)
    reg_provider = DB_TO_REGISTRY.get(ptype, ptype)

    # CUSTOM / unknown provider with a base_url: treat as OpenAI-compatible.
    if cfg is None:
        if not base_url:
            return []
        cfg = {"url": base_url.rstrip("/") + "/models", "style": "openai", "prefix": "openai/"}
        reg_provider = "CUSTOM"
    elif base_url and cfg["style"] == "openai":
        cfg = {**cfg, "url": base_url.rstrip("/") + "/models"}

    # Fixed api_base for providers whose litellm route needs an explicit endpoint
    # (e.g. GitHub Models, or a user's CUSTOM endpoint).
    ab = cfg.get("api_base") or base_url

    out: list[dict] = []
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            if cfg["style"] == "gemini":
                resp = await client.get(cfg["url"], params={"key": api_key})
                resp.raise_for_status()
                for m in resp.json().get("models", []):
                    if "generateContent" in m.get("supportedGenerationMethods", []):
                        mid = m["name"].split("/")[-1]
                        out.append({"model_id": mid, "litellm_id": cfg["prefix"] + mid, "provider": reg_provider, "api_base": ab})
            elif cfg["style"] == "anthropic":
                resp = await client.get(cfg["url"], headers={"x-api-key": api_key, "anthropic-version": "2023-06-01"})
                resp.raise_for_status()
                for m in resp.json().get("data", []):
                    mid = m.get("id")
                    if mid:
                        out.append({"model_id": mid, "litellm_id": cfg["prefix"] + mid, "provider": reg_provider, "api_base": ab})
            else:  # openai-compatible (tolerant: accepts {"data":[...]} or a bare list)
                resp = await client.get(cfg["url"], headers={"Authorization": f"Bearer {api_key}"})
                resp.raise_for_status()
                js = resp.json()
                items = js.get("data", js) if isinstance(js, dict) else js
                for m in (items or []):
                    mid = m.get("id") or m.get("name") if isinstance(m, dict) else None
                    if mid:
                        out.append({"model_id": mid, "litellm_id": cfg["prefix"] + mid, "provider": reg_provider, "api_base": ab})
    except Exception as e:
        logger.info("Model discovery failed for %s: %s", ptype, str(e)[:120])
        out = []

    _CACHE[cache_key] = (time.time() + _TTL, out)
    return out
