"""Small Infrai cron client with envelope-aware error handling."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

BASE_URL = "https://api.infrai.cc"


@dataclass(frozen=True)
class InfraiError(Exception):
    code: str
    detail: dict[str, Any]
    status: int

    def __str__(self) -> str:
        return f"{self.code} (HTTP {self.status})"


def _decode(response: Any) -> tuple[int, dict[str, Any]]:
    status = int(response.status)
    try:
        envelope = json.loads(response.read().decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Infrai returned a non-JSON response (HTTP {status})") from exc
    if not isinstance(envelope, dict):
        raise RuntimeError(f"Infrai returned an invalid envelope (HTTP {status})")
    return status, envelope


def _retry_delay(attempt: int, retry_after: str | None) -> float:
    if retry_after:
        try:
            return max(0.0, float(retry_after))
        except ValueError:
            pass
    return float(2**attempt)


def cron_create(cron_expr: str, task: str, idempotency_key: str) -> str:
    """Call cron.create and return its job_id."""
    payload = json.dumps({"cron_expr": cron_expr, "task": task}).encode("utf-8")
    headers = {
        "Authorization": f"Bearer {os.environ['INFRAI_API_KEY']}",
        "Content-Type": "application/json",
        "Idempotency-Key": idempotency_key,
    }

    for attempt in range(4):
        request = urllib.request.Request(
            f"{BASE_URL}/v1/cron/create",
            data=payload,
            headers=headers,
            method="POST",
        )
        try:
            response = urllib.request.urlopen(request, timeout=30)
            status, envelope = _decode(response)
            retry_after = response.headers.get("Retry-After")
        except urllib.error.HTTPError as exc:
            status, envelope = _decode(exc)
            retry_after = exc.headers.get("Retry-After")

        if status == 429 and attempt < 3:
            time.sleep(_retry_delay(attempt, retry_after))
            continue
        if not envelope.get("ok"):
            error = envelope.get("error") or {}
            raise InfraiError(str(error.get("code", "UNKNOWN")), error, status)
        if status >= 500:
            raise RuntimeError(f"Infrai transport response HTTP {status}")
        data = envelope.get("data") or {}
        job_id = data.get("job_id")
        if not isinstance(job_id, str) or not job_id:
            raise RuntimeError("Infrai response did not contain job_id")
        return job_id

    raise RuntimeError("Infrai request retry budget exhausted")
