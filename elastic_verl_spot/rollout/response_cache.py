"""Response cache for optional rollout reuse.

Caches completed responses keyed by prompt hash, model version, and sampling
configuration. This is an optimization and must not be required for correctness.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from time import time
from typing import Any


@dataclass(frozen=True)
class ResponseCacheKey:
    """Stable response-cache key."""

    prompt_hash: str
    model_version: int | None
    sampling_hash: str

    @classmethod
    def build(
        cls,
        *,
        prompt_tokens: list[int] | None = None,
        prompt: str | None = None,
        model_version: int | None = None,
        sampling_params: dict[str, Any] | None = None,
    ) -> "ResponseCacheKey":
        """Build a stable cache key from prompt and sampling metadata."""

        prompt_payload = {
            "prompt": prompt,
            "prompt_tokens": list(prompt_tokens or []),
        }
        sampling_payload = sampling_params or {}
        return cls(
            prompt_hash=_stable_hash(prompt_payload),
            model_version=model_version,
            sampling_hash=_stable_hash(sampling_payload),
        )


@dataclass
class CachedResponse:
    """Cached completed rollout response."""

    key: ResponseCacheKey
    response_tokens: list[int] = field(default_factory=list)
    response_text: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time)


def _stable_hash(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class ResponseCache:
    """In-memory response cache used as an optional rollout optimization."""

    def __init__(self) -> None:
        self._items: dict[ResponseCacheKey, CachedResponse] = {}

    def put(
        self,
        key: ResponseCacheKey,
        *,
        response_tokens: list[int],
        response_text: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> CachedResponse:
        """Store a completed response."""

        item = CachedResponse(
            key=key,
            response_tokens=list(response_tokens),
            response_text=response_text,
            metadata=dict(metadata or {}),
        )
        self._items[key] = item
        return item

    def get(self, key: ResponseCacheKey) -> CachedResponse | None:
        """Return a cached response if present."""

        return self._items.get(key)

    def contains(self, key: ResponseCacheKey) -> bool:
        """Return whether a key exists in the cache."""

        return key in self._items

    def clear(self) -> None:
        """Remove all cached responses."""

        self._items.clear()
