"""Rollout resume policy.

Decides whether a failed rollout should restart from the prompt, continue from
partial tokens after prefill replay, or be discarded and resampled.
"""

from __future__ import annotations

from enum import Enum
from typing import Any


class ResumeMode(str, Enum):
    """Supported rollout resume modes."""

    REPLAY_FROM_PROMPT = "replay_from_prompt"
    REPLAY_WITH_PARTIAL_PREFIX = "replay_with_partial_prefix"
    CONTINUE_FROM_KV_CACHE = "continue_from_kv_cache"
    FAIL = "fail"


class ResumePolicy:
    """Default conservative rollout resume strategy."""

    def __init__(self, max_attempts: int = 3, allow_kv_resume: bool = True) -> None:
        self.max_attempts = max_attempts
        self.allow_kv_resume = allow_kv_resume

    def choose(self, request: dict | Any) -> ResumeMode:
        """Return a resume mode for a failed request."""

        attempt = int(_request_value(request, "attempt", 0) or 0)
        if attempt >= self.max_attempts:
            return ResumeMode.FAIL

        partial_tokens = _request_value(request, "partial_tokens", []) or []
        kv_cache = _request_value(request, "kv_cache", None)
        if self.allow_kv_resume and kv_cache is not None and partial_tokens:
            return ResumeMode.CONTINUE_FROM_KV_CACHE
        if partial_tokens:
            return ResumeMode.REPLAY_WITH_PARTIAL_PREFIX
        return ResumeMode.REPLAY_FROM_PROMPT


def _request_value(request: dict | Any, key: str, default: Any = None) -> Any:
    if isinstance(request, dict):
        return request.get(key, default)
    return getattr(request, key, default)
