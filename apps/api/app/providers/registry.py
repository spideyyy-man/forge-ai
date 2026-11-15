"""Multi-model provider abstraction layer and router."""
import logging
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
import time

logger = logging.getLogger(__name__)


class ModelCapability(BaseModel):
    model_id: str
    provider: str
    litellm_id: str
    context_window: int = 128000
    supports_tools: bool = True
    supports_streaming: bool = True
    supports_vision: bool = False
    coding_score: int = 85
    reasoning_score: int = 85
    speed_tier: str = "FAST"  # FAST, ULTRA_FAST, BALANCED, DEEP_THINKING
    cost_per_1m_input: float = 0.0
    cost_per_1m_output: float = 0.0
    api_base: Optional[str] = None  # for CUSTOM / self-hosted OpenAI-compatible endpoints


# Normalized catalog of default models across initial supported providers
MODEL_REGISTRY: Dict[str, ModelCapability] = {
    # Groq (Ultra-Fast)
    "groq/llama-3.3-70b-versatile": ModelCapability(
        model_id="llama-3.3-70b-versatile",
        provider="GROQ",
        litellm_id="groq/llama-3.3-70b-versatile",
        context_window=128000,
        supports_tools=True,
        supports_streaming=True,
        coding_score=88,
        reasoning_score=88,
        speed_tier="ULTRA_FAST",
    ),
    "groq/qwen-2.5-coder-32b": ModelCapability(
        model_id="llama-3.1-8b-instant",
        provider="GROQ",
        litellm_id="groq/llama-3.1-8b-instant",
        context_window=128000,
        supports_tools=True,
        supports_streaming=True,
        coding_score=92,
        reasoning_score=86,
        speed_tier="ULTRA_FAST",
    ),
    # Google Gemini
    "gemini/gemini-2.0-flash": ModelCapability(
        model_id="gemini-2.5-flash",
        provider="GEMINI",
        litellm_id="gemini/gemini-2.5-flash",
        context_window=1000000,
        supports_tools=True,
        supports_streaming=True,
        supports_vision=True,
        coding_score=98,
        reasoning_score=97,
        speed_tier="FAST",
    ),
    "gemini/gemini-2.5-pro": ModelCapability(
        model_id="gemini-2.5-pro",
        provider="GEMINI",
        litellm_id="gemini/gemini-2.5-pro",
        context_window=2000000,
        supports_tools=True,
        supports_streaming=True,
        supports_vision=True,
        coding_score=95,
        reasoning_score=96,
        speed_tier="BALANCED",
    ),
    # Gemini Flash-Lite — free, very fast; great cheap fallback / speed-tier pick.
    "gemini/gemini-2.5-flash-lite": ModelCapability(
        model_id="gemini-2.5-flash-lite",
        provider="GEMINI",
        litellm_id="gemini/gemini-2.5-flash-lite",
        context_window=1000000,
        supports_tools=True,
        supports_streaming=True,
        supports_vision=True,
        coding_score=90,
        reasoning_score=88,
        speed_tier="ULTRA_FAST",
    ),
    # NVIDIA NIM
    "nvidia/meta/llama-3.3-70b-instruct": ModelCapability(
        model_id="llama-3.3-70b-instruct",
        provider="NVIDIA_NIM",
        litellm_id="nvidia_nim/meta/llama-3.3-70b-instruct",
        context_window=128000,
        supports_tools=True,
        supports_streaming=True,
        coding_score=88,
        reasoning_score=88,
        speed_tier="FAST",
    ),
    "nvidia/deepseek-ai/deepseek-r1": ModelCapability(
        model_id="deepseek-r1",
        provider="NVIDIA_NIM",
        litellm_id="nvidia_nim/deepseek-ai/deepseek-r1",
        context_window=64000,
        supports_tools=True,
        supports_streaming=True,
        coding_score=96,
        reasoning_score=98,
        speed_tier="DEEP_THINKING",
    ),
    # DeepSeek direct
    "deepseek/deepseek-chat": ModelCapability(
        model_id="deepseek-chat",
        provider="DEEPSEEK",
        litellm_id="deepseek/deepseek-chat",
        context_window=64000,
        supports_tools=True,
        supports_streaming=True,
        coding_score=94,
        reasoning_score=93,
        speed_tier="FAST",
    ),
    "deepseek/deepseek-reasoner": ModelCapability(
        model_id="deepseek-reasoner",
        provider="DEEPSEEK",
        litellm_id="deepseek/deepseek-reasoner",
        context_window=64000,
        supports_tools=False,
        supports_streaming=True,
        coding_score=96,
        reasoning_score=98,
        speed_tier="DEEP_THINKING",
    ),
    # Cerebras
    "cerebras/llama3.1-70b": ModelCapability(
        model_id="llama3.1-70b",
        provider="CEREBRAS",
        litellm_id="cerebras/llama3.1-70b",
        context_window=8192,
        supports_tools=True,
        supports_streaming=True,
        coding_score=86,
        reasoning_score=85,
        speed_tier="ULTRA_FAST",
    ),
    # Mistral
    "mistral/codestral-latest": ModelCapability(
        model_id="codestral-latest",
        provider="MISTRAL",
        litellm_id="mistral/codestral-latest",
        context_window=256000,
        supports_tools=True,
        supports_streaming=True,
        coding_score=94,
        reasoning_score=91,
        speed_tier="FAST",
    ),
    # SambaNova (free, ultra-fast RDU inference)
    "sambanova/llama-3.3-70b": ModelCapability(
        model_id="Meta-Llama-3.3-70B-Instruct",
        provider="SAMBANOVA",
        litellm_id="sambanova/Meta-Llama-3.3-70B-Instruct",
        context_window=128000,
        coding_score=88,
        reasoning_score=88,
        speed_tier="ULTRA_FAST",
    ),
    "sambanova/llama-3.1-8b": ModelCapability(
        model_id="Meta-Llama-3.1-8B-Instruct",
        provider="SAMBANOVA",
        litellm_id="sambanova/Meta-Llama-3.1-8B-Instruct",
        context_window=16000,
        coding_score=82,
        reasoning_score=80,
        speed_tier="ULTRA_FAST",
    ),
    # GitHub Models (free with a GitHub token). Routed as OpenAI-compatible against the
    # current endpoint; litellm's native github/ provider points at a dead Azure host.
    # Model ids are publisher-namespaced, so litellm_id = openai/<publisher>/<model>.
    "github/gpt-4o-mini": ModelCapability(
        model_id="openai/gpt-4o-mini",
        provider="GITHUB",
        litellm_id="openai/openai/gpt-4o-mini",
        api_base="https://models.github.ai/inference",
        context_window=128000,
        supports_vision=True,
        coding_score=86,
        reasoning_score=85,
        speed_tier="FAST",
    ),
    "github/llama-3.3-70b": ModelCapability(
        model_id="meta/Llama-3.3-70B-Instruct",
        provider="GITHUB",
        litellm_id="openai/meta/Llama-3.3-70B-Instruct",
        api_base="https://models.github.ai/inference",
        context_window=128000,
        coding_score=85,
        reasoning_score=85,
        speed_tier="FAST",
    ),
    # Ollama (Local)
    "ollama/qwen2.5-coder:7b": ModelCapability(
        model_id="qwen2.5-coder:7b",
        provider="OLLAMA",
        litellm_id="ollama/qwen2.5-coder:7b",
        context_window=32000,
        supports_tools=True,
        supports_streaming=True,
        coding_score=84,
        reasoning_score=80,
        speed_tier="FAST",
    ),
}
