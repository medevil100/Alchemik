"""
Official OpenAI SDK adapter with Structured Outputs.

This is the production AI boundary. It uses the official ``openai`` SDK,
the Responses API (``client.responses.parse``) and strict Pydantic
``text_format`` so the provider response is returned already validated
as :class:`AIAnalysisResult` — no free-text JSON slicing.

Networking policy (Punkt 4):
  - ``max_retries=0`` — exactly one SDK attempt per application call.
  - explicit ``timeout`` — no unlimited waits.
  - no bespoke retry loop.

Secrets: only ``api_key`` is accepted here. It is used to build the client
and is never returned, logged, or placed in any output model.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Optional

from openai import OpenAI
from pydantic import BaseModel, Field


class AIAnalysisResult(BaseModel):
    """Strict schema returned by GPT-4o (Structured Output).

    Distinguishes facts grounded in the supplied instrument data from
    hypotheses, alternative explanations, risks, data limitations and the
    justification. ``refusal`` is set when the model refuses to produce an
    analysis; ``confidence`` is the model's declared certainty (0.0-1.0).
    """

    facts: list[str] = Field(default_factory=list)
    hypotheses: list[str] = Field(default_factory=list)
    alternatives: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    data_limitations: list[str] = Field(default_factory=list)
    justification: str = ""
    confidence: float = Field(ge=0.0, le=1.0)
    refusal: Optional[str] = None


@dataclass
class OpenAIProviderResult:
    """Validated result plus provider metadata (no secrets)."""

    result: Optional[AIAnalysisResult]
    response_id: str
    request_id: Optional[str] = None
    refusal: Optional[str] = None


class AIProviderError(Exception):
    """Raised when the OpenAI provider cannot produce a valid analysis."""


class OpenAIProvider:
    """Real GPT-4o adapter over the official OpenAI SDK.

    Args:
        api_key: OpenAI API key (used to build the client; never exposed).
        model: Model name. Must remain the approved GPT-4o variant.
        timeout: Request timeout in seconds.
        max_retries: SDK retry count. Must be 0 for controlled runs.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o",
        timeout: float = 30.0,
        max_retries: int = 0,
    ) -> None:
        self.model = model
        self.timeout = timeout
        self.max_retries = max_retries
        # OpenAI client raises here if api_key is missing/empty, which is the
        # intended fail-fast behaviour for a misconfigured production run.
        self._client = OpenAI(
            api_key=api_key,
            timeout=timeout,
            max_retries=max_retries,
        )

    def analyze(self, payload: dict) -> OpenAIProviderResult:
        """Send the instrument payload and return a validated analysis.

        Args:
            payload: Already-redacted instrument context. Must not contain
                secrets, cookies, crumb or foreign-symbol data.

        Returns:
            OpenAIProviderResult with the validated ``AIAnalysisResult``.

        Raises:
            AIProviderError: If the provider fails, refuses, or returns no
                structured output.
        """
        instructions = (
            "Jesteś końcową warstwą analityczną ALCHEMIK. Na podstawie "
            "wyłącznie dostarczonych danych dla jednego instrumentu rozdziel "
            "fakty wynikające z danych, hipotezy, alternatywne wyjaśnienia, "
            "ryzyka i ograniczenia danych. Nie wymyślaj brakujących danych "
            "rynkowych, nie generuj OHLCV, nie rozstrzygaj GPW/NC i nie "
            "działaj jako samodzielny generator BUY/SELL. Jeżeli danych jest "
            "za mało, wskaż to w ograniczeniach i obniż confidence."
        )

        # The Responses API ``input`` is a string or a ResponseInputParam.
        # Serialise the redacted instrument context to a single deterministic
        # JSON document so the model receives one clean, self-contained input
        # without us hand-building ResponseInputParam message items.
        parsed = self._client.responses.parse(
            model=self.model,
            instructions=instructions,
            input=json.dumps(payload, ensure_ascii=False, default=str),
            text_format=AIAnalysisResult,
        )

        result = parsed.output_parsed
        response_id = getattr(parsed, "id", "")
        request_id = getattr(parsed, "_request_id", None)

        if result is not None:
            return OpenAIProviderResult(
                result=result,
                response_id=response_id,
                request_id=request_id,
            )

        # No structured text output — check for an explicit refusal.
        refusal = self._extract_refusal(parsed)
        if refusal is not None:
            return OpenAIProviderResult(
                result=None,
                response_id=response_id,
                request_id=request_id,
                refusal=refusal,
            )

        raise AIProviderError("Model returned no structured output")

    @staticmethod
    def _extract_refusal(parsed) -> Optional[str]:
        """Return the model's refusal text, or None if there was none."""
        for item in getattr(parsed, "output", []) or []:
            if getattr(item, "type", None) == "refusal":
                text = getattr(item, "refusal", None)
                return text or "Model refused the request"
        return None