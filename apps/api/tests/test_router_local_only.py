"""Tests that Local-Only mode never routes to a cloud provider."""
import pytest

import app.providers.router as router_mod
from app.providers.router import ModelRouter
from app.providers.registry import ModelCapability


class FakeChoice:
    def __init__(self):
        self.message = type("M", (), {"content": "ok", "tool_calls": None})()


class FakeResponse:
    def __init__(self):
        self.choices = [FakeChoice()]


def _install_recording_acompletion(monkeypatch):
    """Record every model litellm is asked to call."""
    attempted = []

    async def fake_acompletion(**kwargs):
        attempted.append(kwargs["model"])
        return FakeResponse()

    monkeypatch.setattr(router_mod.litellm, "acompletion", fake_acompletion)
    return attempted


async def test_local_only_never_calls_cloud(monkeypatch):
    attempted = _install_recording_acompletion(monkeypatch)
    router = ModelRouter()
    cloud = ModelCapability(model_id="gpt", provider="OPENAI", litellm_id="openai/gpt-4o")

    res = await router.execute_completion(
        messages=[{"role": "user", "content": "hi"}],
        candidates=[cloud],               # only a cloud model offered…
        configured_keys={"OPENAI": ["sk-x"]},
        local_only=True,                  # …but local-only is on
    )
    assert res["success"] is True
    # The cloud model was stripped; only the registry's Ollama model was attempted.
    assert attempted, "a model should have been attempted"
    assert all(m.startswith("ollama/") for m in attempted), attempted


async def test_local_only_errors_when_no_local_model(monkeypatch):
    attempted = _install_recording_acompletion(monkeypatch)
    # Pretend the registry has no Ollama models available.
    monkeypatch.setattr(router_mod, "MODEL_REGISTRY", {
        k: v for k, v in router_mod.MODEL_REGISTRY.items() if v.provider != "OLLAMA"
    })
    router = ModelRouter()
    cloud = ModelCapability(model_id="gpt", provider="OPENAI", litellm_id="openai/gpt-4o")

    res = await router.execute_completion(
        messages=[{"role": "user", "content": "hi"}],
        candidates=[cloud],
        configured_keys={"OPENAI": ["sk-x"]},
        local_only=True,
    )
    assert res["success"] is False
    assert "local-only" in res["error"].lower()
    assert attempted == []  # never attempted any model, cloud included


async def test_cloud_mode_still_uses_cloud(monkeypatch):
    attempted = _install_recording_acompletion(monkeypatch)
    router = ModelRouter()
    cloud = ModelCapability(model_id="gpt", provider="OPENAI", litellm_id="openai/gpt-4o")

    res = await router.execute_completion(
        messages=[{"role": "user", "content": "hi"}],
        candidates=[cloud],
        configured_keys={"OPENAI": ["sk-x"]},
        local_only=False,
    )
    assert res["success"] is True
    assert attempted == ["openai/gpt-4o"]
