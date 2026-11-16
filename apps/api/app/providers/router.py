"""Multi-provider router with fallback and load/rate-limit recovery using LiteLLM."""
import logging
from typing import List, Dict, Any, Optional, AsyncGenerator
import time
import litellm
from app.providers.registry import MODEL_REGISTRY, ModelCapability

logger = logging.getLogger(__name__)

# Suppress excessively verbose logs from litellm in standard execution
litellm.suppress_debug_info = True


_FREE_HINTS = ("flash", "lite", "mini", "nano", "instant", "8b", "7b", "9b", "small", "free", "gemma", "haiku", "scout")
# Non-chat models that showing up in a provider's model list but must not be tried as a chat completion.
_NON_CHAT = ("tts", "embedding", "embed", "image", "imagen", "whisper", "audio", "live", "aqa", "veo", "vision-only", "rerank", "moderation", "guard")


def assemble_candidates(configured_providers, avail, discovered_ok, all_discovered, limit: int = 12):
    """Merge the curated registry with live-discovered models into a ranked candidate list.

    - Keep registry models for configured providers, but DROP any the provider's live
      list says it doesn't have (kills stale/blocked IDs automatically).
    - Append free-friendly discovered models the registry doesn't know about.
    Returns a list of {litellm_id, provider, model_id} dicts, best first.
    """
    known = []
    for cap in MODEL_REGISTRY.values():
        if cap.provider not in configured_providers:
            continue
        if cap.provider in discovered_ok and cap.model_id not in avail.get(cap.provider, set()):
            continue  # provider confirmed it doesn't offer this model
        known.append({
            "litellm_id": cap.litellm_id, "provider": cap.provider, "model_id": cap.model_id,
            "api_base": cap.api_base, "score": cap.coding_score + cap.reasoning_score,
        })
    known.sort(key=lambda d: -d["score"])
    known_lids = {d["litellm_id"] for d in known}

    extra = []
    seen = set(known_lids)
    for d in all_discovered:
        if d["litellm_id"] in seen:
            continue
        seen.add(d["litellm_id"])
        mid = d["model_id"].lower()
        if any(x in mid for x in _NON_CHAT):
            continue
        extra.append({**d, "score": 1 if any(h in mid for h in _FREE_HINTS) else 0})
    extra.sort(key=lambda d: -d["score"])

    merged = known + extra
    return [
        {"litellm_id": d["litellm_id"], "provider": d["provider"], "model_id": d["model_id"], "api_base": d.get("api_base")}
        for d in merged
    ][:limit]


class RouterPolicy:
    QUALITY = "quality"  # prioritize highest coding_score + reasoning_score
    SPEED = "speed"  # prioritize ULTRA_FAST models (Groq/Cerebras)
    LOCAL_ONLY = "local_only"  # only route to local Ollama
    FALLBACK = "fallback"  # sequential failover across active providers


# Round-robin cursor per provider so load spreads across a user's multiple keys.
_key_cursor: Dict[str, int] = {}


def _rotated_keys(provider: str, configured_keys: dict) -> List[str]:
    """Return this provider's keys, rotated so each request starts on a different key
    (load balancing) while still exposing the full list for 429 failover."""
    keys = configured_keys.get(provider) or configured_keys.get(provider.upper()) or []
    if isinstance(keys, str):
        keys = [keys]
    keys = [k for k in keys if k]
    if not keys:
        return []
    i = _key_cursor.get(provider, 0) % len(keys)
    _key_cursor[provider] = (i + 1) % len(keys)
    return keys[i:] + keys[:i]


def _is_rate_limit(exc) -> bool:
    s = str(exc).lower()
    return any(t in s for t in ("429", "rate limit", "ratelimit", "quota", "resource_exhausted", "too many requests"))


def _apply_prompt_cache(messages: List[Dict[str, Any]], provider: str) -> List[Dict[str, Any]]:
    """Mark the large, stable leading block as cacheable where the provider supports
    explicit cache breakpoints (Anthropic). Other providers cache a stable prefix
    automatically, which the caller enables by putting stable content first."""
    if provider and provider.upper() == "ANTHROPIC" and messages and isinstance(messages[0].get("content"), str):
        out = [dict(m) for m in messages]
        out[0]["content"] = [{"type": "text", "text": messages[0]["content"], "cache_control": {"type": "ephemeral"}}]
        return out
    return messages


class ModelRouter:
    """Intelligent Model Selection and Fallback Engine."""

    def __init__(self):
        self.fallback_history: List[Dict[str, Any]] = []

    def get_candidate_models(
        self,
        policy: str = RouterPolicy.QUALITY,
        requires_tools: bool = True,
        configured_providers: Optional[List[str]] = None,
    ) -> List[ModelCapability]:
        """Rank and return candidate models based on user constraints and active keys."""
        candidates = list(MODEL_REGISTRY.values())

        # Filter by tool requirements
        if requires_tools:
            candidates = [m for m in candidates if m.supports_tools]

        # Filter by configured provider accounts if provided
        if configured_providers:
            allowed = set(p.upper() for p in configured_providers)
            candidates = [m for m in candidates if m.provider.upper() in allowed]

        if policy == RouterPolicy.LOCAL_ONLY:
            return [m for m in candidates if m.provider == "OLLAMA"]

        if policy == RouterPolicy.SPEED:
            # Sort by speed priority
            order = {"ULTRA_FAST": 0, "FAST": 1, "BALANCED": 2, "DEEP_THINKING": 3}
            candidates.sort(key=lambda m: (order.get(m.speed_tier, 9), -m.coding_score))
        else:
            # Default to Quality prioritized
            candidates.sort(key=lambda m: (m.coding_score + m.reasoning_score), reverse=True)

        return candidates

    async def execute_completion(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        policy: str = RouterPolicy.QUALITY,
        configured_keys: Optional[Dict[str, str]] = None,
        stream: bool = False,
        candidates: Optional[List[Any]] = None,
        local_only: bool = False,
    ) -> Dict[str, Any]:
        """Execute model completion with automatic provider fallback on rate-limits or errors.

        When ``local_only`` is set, candidates are hard-restricted to local (Ollama) models
        and the router will NEVER fall back to a cloud provider — a Local-Only request that
        cannot be served locally fails with a clear error rather than leaking to the cloud.
        """
        configured_keys = configured_keys or {}
        active_providers = list(configured_keys.keys())

        # Prefer a caller-supplied (discovery-ranked) candidate list; else fall back to the registry.
        if not candidates:
            candidates = self.get_candidate_models(
                policy=RouterPolicy.LOCAL_ONLY if local_only else policy,
                requires_tools=bool(tools),
                configured_providers=active_providers if active_providers else None,
            )
        if not candidates:
            candidates = list(MODEL_REGISTRY.values())

        if local_only:
            # Enforce the privacy boundary here, in trusted code: strip every non-local model.
            candidates = [c for c in candidates if str(getattr(c, "provider", "")).upper() == "OLLAMA"]
            if not candidates:
                candidates = [m for m in MODEL_REGISTRY.values() if m.provider == "OLLAMA"]
            if not candidates:
                return {
                    "success": False,
                    "error": "Local-Only mode: no local (Ollama) model is available. Start Ollama and pull a model.",
                    "fallback_attempts": 0,
                }

        errors: List[str] = []

        for model in candidates:
            keys = _rotated_keys(model.provider, configured_keys) or [None]
            msgs = _apply_prompt_cache(messages, model.provider)
            for ki, api_key in enumerate(keys):
                kwargs: Dict[str, Any] = {"model": model.litellm_id, "messages": msgs, "stream": stream}
                if api_key:
                    kwargs["api_key"] = api_key
                if getattr(model, "api_base", None):
                    kwargs["api_base"] = model.api_base
                if tools and model.supports_tools:
                    kwargs["tools"] = tools
                    kwargs["tool_choice"] = "auto"
                try:
                    start_time = time.time()
                    logger.info(f"[ModelRouter] Attempting {model.litellm_id} (key {ki + 1}/{len(keys)})")
                    response = await litellm.acompletion(**kwargs)
                    return {
                        "success": True,
                        "response": response,
                        "model_used": model.litellm_id,
                        "provider": model.provider,
                        "latency_ms": (time.time() - start_time) * 1000,
                        "fallback_attempts": len(errors),
                    }
                except Exception as exc:
                    errors.append(f"{model.litellm_id} failed: {str(exc)}")
                    self.fallback_history.append({"timestamp": time.time(), "model": model.litellm_id, "error": str(exc)})
                    if _is_rate_limit(exc) and ki + 1 < len(keys):
                        logger.warning(f"[ModelRouter] {model.litellm_id} rate-limited; rotating to next key")
                        continue  # try the next key for this model
                    # non-rate-limit error, or no keys left: try remaining keys then next model
                    continue

        return {
            "success": False,
            "error": f"All candidate models failed in fallback chain: {'; '.join(errors)}",
            "fallback_attempts": len(errors),
        }

    async def stream_completion(
        self,
        messages: List[Dict[str, Any]],
        policy: str = RouterPolicy.QUALITY,
        configured_keys: Optional[Dict[str, str]] = None,
        on_delta=None,
        candidates: Optional[List[Any]] = None,
    ) -> Dict[str, Any]:
        """Like execute_completion but streams tokens. For each text chunk it awaits
        `on_delta(chunk)` (if given) and accumulates the full reply. Falls over to the
        next candidate model on error, same as the non-streaming path."""
        configured_keys = configured_keys or {}
        active_providers = list(configured_keys.keys())
        if not candidates:
            candidates = self.get_candidate_models(
                policy=policy,
                requires_tools=False,
                configured_providers=active_providers if active_providers else None,
            )
        if not candidates:
            candidates = list(MODEL_REGISTRY.values())

        errors: List[str] = []
        for model in candidates:
            keys = _rotated_keys(model.provider, configured_keys) or [None]
            msgs = _apply_prompt_cache(messages, model.provider)
            for ki, api_key in enumerate(keys):
                kwargs: Dict[str, Any] = {"model": model.litellm_id, "messages": msgs, "stream": True}
                if api_key:
                    kwargs["api_key"] = api_key
                if getattr(model, "api_base", None):
                    kwargs["api_base"] = model.api_base
                try:
                    start_time = time.time()
                    logger.info(f"[ModelRouter] Streaming {model.litellm_id} (key {ki + 1}/{len(keys)})")
                    response = await litellm.acompletion(**kwargs)
                    full = ""
                    async for chunk in response:
                        try:
                            delta = chunk.choices[0].delta.content or ""
                        except Exception:
                            delta = ""
                        if delta:
                            full += delta
                            if on_delta is not None:
                                await on_delta(delta)
                    return {
                        "success": True,
                        "text": full,
                        "model_used": model.litellm_id,
                        "provider": model.provider,
                        "latency_ms": (time.time() - start_time) * 1000,
                        "fallback_attempts": len(errors),
                    }
                except Exception as exc:
                    errors.append(f"{model.litellm_id} failed: {str(exc)}")
                    if _is_rate_limit(exc) and ki + 1 < len(keys):
                        logger.warning(f"[ModelRouter] {model.litellm_id} rate-limited; rotating key")
                        continue
                    continue

        return {
            "success": False,
            "error": f"All candidate models failed in fallback chain: {'; '.join(errors)}",
            "fallback_attempts": len(errors),
        }


# Global Singleton Router
model_router = ModelRouter()
