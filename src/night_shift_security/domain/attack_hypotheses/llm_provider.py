"""Swappable LLM provider abstraction for hypothesis expansion."""

from __future__ import annotations

import json
import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class LLMCompletionResult:
    """Outcome of a single LLM completion call."""

    content: str
    success: bool
    provider: str
    model: str
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    estimated_cost_usd: float | None = None
    error: str | None = None
    raw_response: dict[str, Any] = field(default_factory=dict)


class LLMProvider(ABC):
    """Provider interface — implement for each backend (LiteLLM, OpenAI, etc.)."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        ...

    @abstractmethod
    def complete(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        timeout_seconds: float = 30.0,
    ) -> LLMCompletionResult:
        ...


class MockLLMProvider(LLMProvider):
    """Deterministic provider for tests — returns preconfigured responses."""

    def __init__(
        self,
        responses: list[str] | None = None,
        *,
        model: str = "mock-model",
        fail: bool = False,
        error: str = "mock failure",
    ) -> None:
        self._responses = list(responses or [])
        self._model = model
        self._fail = fail
        self._error = error
        self._call_index = 0

    @property
    def provider_name(self) -> str:
        return "mock"

    def complete(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        timeout_seconds: float = 30.0,
    ) -> LLMCompletionResult:
        del messages, temperature, max_tokens, timeout_seconds
        if self._fail:
            return LLMCompletionResult(
                content="",
                success=False,
                provider=self.provider_name,
                model=self._model,
                error=self._error,
            )

        if self._call_index < len(self._responses):
            content = self._responses[self._call_index]
        elif self._responses:
            content = self._responses[-1]
        else:
            content = "[]"

        self._call_index += 1
        prompt_tokens = 120
        completion_tokens = max(1, len(content) // 4)
        return LLMCompletionResult(
            content=content,
            success=True,
            provider=self.provider_name,
            model=self._model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            estimated_cost_usd=0.0,
        )


class LiteLLMProvider(LLMProvider):
    """Production provider via LiteLLM (supports OpenAI, Anthropic, Grok, etc.)."""

    def __init__(
        self,
        model: str,
        *,
        api_key: str | None = None,
        api_base: str | None = None,
    ) -> None:
        self._model = model
        self._api_key = api_key
        self._api_base = api_base

    @property
    def provider_name(self) -> str:
        return "litellm"

    def complete(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        timeout_seconds: float = 30.0,
    ) -> LLMCompletionResult:
        try:
            import litellm
        except ImportError as exc:
            return LLMCompletionResult(
                content="",
                success=False,
                provider=self.provider_name,
                model=self._model,
                error=f"litellm not installed: {exc}",
            )

        kwargs: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "timeout": timeout_seconds,
        }
        if self._api_key:
            kwargs["api_key"] = self._api_key
        if self._api_base:
            kwargs["api_base"] = self._api_base

        try:
            response = litellm.completion(**kwargs)
        except Exception as exc:  # noqa: BLE001 — provider errors are untrusted input
            logger.warning("LLM completion failed: %s", exc)
            return LLMCompletionResult(
                content="",
                success=False,
                provider=self.provider_name,
                model=self._model,
                error=str(exc),
            )

        content = ""
        if response.choices:
            message = response.choices[0].message
            content = getattr(message, "content", None) or ""

        usage = getattr(response, "usage", None)
        prompt_tokens = getattr(usage, "prompt_tokens", None) if usage else None
        completion_tokens = getattr(usage, "completion_tokens", None) if usage else None
        total_tokens = getattr(usage, "total_tokens", None) if usage else None

        estimated_cost: float | None = None
        try:
            estimated_cost = float(litellm.completion_cost(completion_response=response))
        except Exception:  # noqa: BLE001
            estimated_cost = None

        return LLMCompletionResult(
            content=content,
            success=True,
            provider=self.provider_name,
            model=self._model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            estimated_cost_usd=estimated_cost,
            raw_response={"id": getattr(response, "id", None)},
        )


def create_llm_provider(config: dict[str, Any]) -> LLMProvider | None:
    """Factory for configured LLM providers. Returns None when misconfigured."""
    provider = str(config.get("provider", "litellm")).lower()
    model = str(config.get("model", "gpt-4o-mini"))

    if provider == "mock":
        return MockLLMProvider(model=model)

    if provider == "litellm":
        api_key_env = str(config.get("api_key_env", "OPENAI_API_KEY"))
        api_key = os.environ.get(api_key_env) or config.get("api_key")
        api_base = config.get("api_base")
        if not api_key and not api_base:
            logger.warning(
                "LLM provider litellm requires %s or api_base; skipping real LLM call",
                api_key_env,
            )
            return None
        return LiteLLMProvider(model=model, api_key=api_key, api_base=api_base)

    logger.warning("Unknown LLM provider %r; no provider created", provider)
    return None


def log_llm_outcome(result: LLMCompletionResult, *, context: str) -> None:
    """Basic observability for LLM calls."""
    if result.success:
        logger.info(
            "LLM call ok [%s] provider=%s model=%s tokens=%s cost_usd=%s",
            context,
            result.provider,
            result.model,
            result.total_tokens,
            result.estimated_cost_usd,
        )
    else:
        logger.warning(
            "LLM call failed [%s] provider=%s model=%s error=%s",
            context,
            result.provider,
            result.model,
            result.error,
        )


def extract_json_payload(text: str) -> Any:
    """Parse JSON from raw LLM text, tolerating fenced code blocks."""
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        stripped = "\n".join(lines).strip()
    return json.loads(stripped)