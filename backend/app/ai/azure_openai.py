from __future__ import annotations

import asyncio
import time

from app.models.criteria import AuditCriteria
from app.models.llm import LlmAuditEvaluation
from app.models.ticket import IncidentTicket
from app.utils.errors import ConfigurationError, InvalidModelOutput, TransientError
from app.utils.retry import with_retries


class AzureOpenAIAuditClient:
    """Calls Azure OpenAI for per-measure JSON. The scoring engine discards totals."""

    def __init__(self, *, endpoint: str, api_key: str, deployment: str, api_version: str) -> None:
        if not endpoint or not api_key or not deployment:
            raise ConfigurationError("Azure OpenAI endpoint, key, and deployment are required")
        self._endpoint = endpoint
        self._api_key = api_key
        self._deployment = deployment
        self._api_version = api_version

    async def evaluate(
        self,
        ticket: IncidentTicket,
        criteria: AuditCriteria,
        system_prompt: str,
        user_prompt: str,
    ) -> LlmAuditEvaluation:
        del ticket, criteria

        async def _call() -> LlmAuditEvaluation:
            try:
                return await asyncio.to_thread(self._complete, system_prompt, user_prompt)
            except (InvalidModelOutput, ConfigurationError):
                raise
            except Exception as exc:
                raise TransientError("Azure OpenAI request failed") from exc

        return await with_retries(_call)  # type: ignore[return-value]

    def _complete(self, system_prompt: str, user_prompt: str) -> LlmAuditEvaluation:
        try:
            from openai import AzureOpenAI
        except ImportError as exc:
            raise ConfigurationError("Install backend/requirements-azure.txt to call Azure OpenAI") from exc
        client = AzureOpenAI(
            azure_endpoint=self._endpoint,
            api_key=self._api_key,
            api_version=self._api_version,
        )
        schema = LlmAuditEvaluation.model_json_schema()
        started = time.perf_counter()
        try:
            response = client.chat.completions.create(
                model=self._deployment,
                temperature=0,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {"name": "incident_audit", "schema": schema, "strict": False},
                },
            )
        except Exception:
            response = client.chat.completions.create(
                model=self._deployment,
                temperature=0,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
            )
        latency_ms = int((time.perf_counter() - started) * 1000)
        content = response.choices[0].message.content or ""
        try:
            parsed = LlmAuditEvaluation.model_validate_json(content)
        except Exception as exc:
            raise InvalidModelOutput("Azure OpenAI returned JSON that does not match the audit schema") from exc
        usage = getattr(response, "usage", None)
        token_usage = None
        if usage is not None:
            token_usage = {
                "prompt_tokens": int(getattr(usage, "prompt_tokens", 0) or 0),
                "completion_tokens": int(getattr(usage, "completion_tokens", 0) or 0),
            }
        return parsed.model_copy(update={"latency_ms": latency_ms, "token_usage": token_usage})
