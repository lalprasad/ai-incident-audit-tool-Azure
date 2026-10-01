from __future__ import annotations

import asyncio
import time

from app.ai.azure_credentials import openai_token_provider, require_azure_sdk
from app.models.criteria import AuditCriteria
from app.models.llm import LlmAuditEvaluation
from app.models.ticket import IncidentTicket
from app.utils.errors import ConfigurationError, InvalidModelOutput, TransientError
from app.utils.retry import with_retries


class AzureOpenAIAuditClient:
    """Calls Azure OpenAI / Azure AI Foundry for per-measure JSON.

    Ticket and criteria are already rendered into ``user_prompt`` by AuditEngine.
    The scoring engine owns totals, percentage, and classification.
    """

    def __init__(
        self,
        *,
        endpoint: str,
        deployment: str,
        api_version: str,
        api_key: str = "",
        use_managed_identity: bool = True,
    ) -> None:
        if not endpoint or not deployment:
            raise ConfigurationError("Azure OpenAI endpoint and deployment are required")
        if not api_key and not use_managed_identity:
            raise ConfigurationError(
                "Provide AZURE_OPENAI_API_KEY or enable AZURE_USE_MANAGED_IDENTITY"
            )
        self._endpoint = endpoint.rstrip("/")
        self._api_key = api_key
        self._deployment = deployment
        self._api_version = api_version
        self._use_managed_identity = use_managed_identity and not api_key

    async def evaluate(
        self,
        ticket: IncidentTicket,
        criteria: AuditCriteria,
        system_prompt: str,
        user_prompt: str,
    ) -> LlmAuditEvaluation:
        # Ticket/criteria are embedded in user_prompt by AuditEngine.
        del ticket, criteria

        async def _call() -> LlmAuditEvaluation:
            try:
                return await asyncio.to_thread(self._complete, system_prompt, user_prompt)
            except (InvalidModelOutput, ConfigurationError):
                raise
            except Exception as exc:
                raise TransientError("Azure OpenAI request failed") from exc

        return await with_retries(_call)  # type: ignore[return-value]

    def _client(self):
        require_azure_sdk("openai")
        from openai import AzureOpenAI

        if self._use_managed_identity:
            return AzureOpenAI(
                azure_endpoint=self._endpoint,
                azure_ad_token_provider=openai_token_provider(),
                api_version=self._api_version,
            )
        return AzureOpenAI(
            azure_endpoint=self._endpoint,
            api_key=self._api_key,
            api_version=self._api_version,
        )

    def _complete(self, system_prompt: str, user_prompt: str) -> LlmAuditEvaluation:
        client = self._client()
        schema = LlmAuditEvaluation.model_json_schema()
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        started = time.perf_counter()
        try:
            response = client.chat.completions.create(
                model=self._deployment,
                temperature=0,
                messages=messages,
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "incident_audit",
                        "schema": schema,
                        "strict": False,
                    },
                },
            )
        except Exception:
            response = client.chat.completions.create(
                model=self._deployment,
                temperature=0,
                messages=messages,
                response_format={"type": "json_object"},
            )
        latency_ms = int((time.perf_counter() - started) * 1000)
        content = response.choices[0].message.content or ""
        try:
            parsed = LlmAuditEvaluation.model_validate_json(content)
        except Exception as exc:
            raise InvalidModelOutput(
                "Azure OpenAI returned JSON that does not match the audit schema"
            ) from exc
        usage = getattr(response, "usage", None)
        token_usage = None
        if usage is not None:
            token_usage = {
                "prompt_tokens": int(getattr(usage, "prompt_tokens", 0) or 0),
                "completion_tokens": int(getattr(usage, "completion_tokens", 0) or 0),
            }
        return parsed.model_copy(update={"latency_ms": latency_ms, "token_usage": token_usage})
