"""Custom / Ollama provider profile with configurable reasoning wire formats."""

import logging

from typing import Any
from urllib.parse import urlparse

from agent.reasoning_effort import OPENAI_COMPAT_WIRE_EFFORTS, clamp_effort
from providers import register_provider
from providers.base import ProviderProfile


logger = logging.getLogger(__name__)


def _looks_like_ollama_endpoint(base_url: str | None) -> bool:
    """True only for explicit Ollama signatures (port 11434 or an ``ollama`` host label).
    ``think`` is Ollama-native; strict hosts (Mistral, Groq) 422 on it, and
    arbitrary localhost may be llama.cpp / vLLM / LM Studio."""
    raw = (base_url or "").strip()
    if not raw:
        return False
    parsed = urlparse(raw if "://" in raw else f"//{raw}")
    try:  # urlparse raises ValueError on malformed ports ("host:99999"); treat as not-Ollama.
        if parsed.port == 11434:
            return True
    except ValueError:
        return False
    host = (parsed.hostname or "").lower().rstrip(".")
    return bool(host) and (host == "ollama.com" or host.endswith(".ollama.com") or "ollama" in host.split("."))


class CustomProfile(ProviderProfile):
    """Custom/Ollama local provider — think=false and num_ctx support."""

    @staticmethod
    def _resolve_reasoning_format(base_url: Any) -> str | None:
        if not isinstance(base_url, str) or not base_url:
            return None
        try:
            from hermes_cli.config_providers import get_custom_provider_reasoning_format

            return get_custom_provider_reasoning_format(base_url)
        except Exception:
            return None

    def build_api_kwargs_extras(
        self, *, reasoning_config: dict | None = None, ollama_num_ctx: int | None = None, **ctx: Any
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        extra_body: dict[str, Any] = {}
        top_level: dict[str, Any] = {}
        if ollama_num_ctx:
            extra_body["options"] = {"num_ctx": ollama_num_ctx}
        if reasoning_config and isinstance(reasoning_config, dict):
            effort = (reasoning_config.get("effort") or "").strip().lower()
            reasoning_format = self._resolve_reasoning_format(ctx.get("base_url"))
            if effort == "none" or reasoning_config.get("enabled", True) is False:
                if reasoning_format == "reasoning_object":
                    extra_body["reasoning"] = {"enabled": False}
                elif reasoning_format == "none":
                    logger.warning(
                        "reasoning_format='none' suppresses the explicit reasoning "
                        "disable request; the endpoint's server-side default applies"
                    )
                elif reasoning_format != "none":
                    top_level["reasoning_effort"] = "none"
                if reasoning_format != "none" and _looks_like_ollama_endpoint(ctx.get("base_url")):
                    extra_body["think"] = False
            elif effort:
                if reasoning_format == "reasoning_object":
                    extra_body["reasoning"] = {"enabled": True, "effort": effort}
                elif reasoning_format != "none":
                    top_level["reasoning_effort"] = clamp_effort(
                        effort, OPENAI_COMPAT_WIRE_EFFORTS)
        return extra_body, top_level

    def fetch_models(
        self, *, api_key: str | None = None, base_url: str | None = None, timeout: float = 8.0
    ) -> list[str] | None:
        """base_url is user-configured; fetch only if set."""
        if not (base_url or self.base_url):
            return None
        return super().fetch_models(api_key=api_key, base_url=base_url, timeout=timeout)


custom = CustomProfile(
    name="custom", aliases=("ollama", "local", "vllm", "llamacpp", "llama.cpp", "llama-cpp"),
    env_vars=(),  # No fixed key — custom endpoint
    base_url="",  # User-configured
    # Floor only (user model.max_tokens overrides); without it Ollama falls
    # back to num_predict=128 and truncates.
    # Without this, no max_tokens is sent and Ollama falls back to its internal num_predict=128, truncating
    # responses after a few tokens (#39281). This is only a floor used when the user hasn't set
    # model.max_tokens — they can override per-model — so we set it generously rather than lowballing it.
    default_max_tokens=65536,
)

register_provider(custom)
