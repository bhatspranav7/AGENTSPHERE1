import json
import logging
import re
import time

import requests

from ..core.config import settings
from ..core.exceptions import LLMError
from . import LLMResponse

logger = logging.getLogger(__name__)

_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


def parse_json_object(text: str) -> dict:
    """Tolerates code fences and prose around the JSON object."""
    cleaned = _FENCE.sub("", text.strip())
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start == -1 or end <= start:
            raise LLMError("LLM response contained no JSON object")
        try:
            data = json.loads(cleaned[start:end + 1])
        except json.JSONDecodeError as e:
            raise LLMError(f"LLM returned invalid JSON: {e}") from e
    if not isinstance(data, dict):
        raise LLMError("LLM returned JSON that is not an object")
    return data


class OpenAICompatibleLLM:
    """Chat Completions client for OpenAI, Groq, OpenRouter, Together or Ollama (/v1)."""

    mode = "live"

    def __init__(self):
        self.model = settings.LLM_MODEL
        self.url = settings.LLM_BASE_URL.rstrip("/") + "/chat/completions"
        self.session = requests.Session()
        if settings.LLM_API_KEY:
            self.session.headers["Authorization"] = f"Bearer {settings.LLM_API_KEY}"

    def complete_json(self, task, system, user, sim) -> LLMResponse:
        payload = {
            "model": self.model,
            "temperature": settings.LLM_TEMPERATURE,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system + "\n\nRespond with a single JSON object only."},
                {"role": "user", "content": user},
            ],
        }

        started = time.perf_counter()
        body = self._post(payload)
        latency_ms = int((time.perf_counter() - started) * 1000)

        try:
            content = body["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError, TypeError) as e:
            raise LLMError(f"Unexpected LLM response shape: {e}") from e

        usage = body.get("usage") or {}
        return LLMResponse(
            data=parse_json_object(content),
            tokens=int(usage.get("total_tokens") or 0),
            latency_ms=latency_ms,
            model=body.get("model", self.model),
            raw=content,
        )

    def _post(self, payload: dict) -> dict:
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                resp = self.session.post(self.url, json=payload, timeout=settings.LLM_TIMEOUT_SECONDS)
            except requests.RequestException as e:
                last_error = e
            else:
                if resp.status_code == 400 and "response_format" in payload:
                    # Some providers/models reject JSON mode; the prompt already demands JSON
                    payload = {k: v for k, v in payload.items() if k != "response_format"}
                    continue
                if resp.status_code in (429, 500, 502, 503, 504):
                    last_error = LLMError(f"LLM HTTP {resp.status_code}")
                    time.sleep(min(2 ** attempt, 8))
                    continue
                if resp.status_code >= 400:
                    raise LLMError(f"LLM HTTP {resp.status_code}: {resp.text[:200]}")
                return resp.json()
            time.sleep(min(2 ** attempt, 8))

        raise LLMError(f"LLM unavailable: {last_error}")
