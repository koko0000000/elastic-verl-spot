"""Rollout request state and retry bookkeeping.

The first durable implementation can be backed by SQLite or Redis.  This module
keeps the interface small and provides an in-memory implementation for local
tests and the first verl hook integration.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from time import time
from typing import Any


class RequestStatus(str, Enum):
    """Lifecycle states for one rollout request."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    RETRYING = "RETRYING"
    DONE = "DONE"
    FAILED = "FAILED"


@dataclass
class RolloutRequest:
    """Serializable rollout request state."""

    request_id: str
    prompt: str | None = None
    model_version: int | None = None
    status: RequestStatus = RequestStatus.PENDING
    worker_id: str | None = None
    attempt: int = 0
    partial_tokens: list[int] = field(default_factory=list)
    response_tokens: list[int] = field(default_factory=list)
    error: str | None = None
    created_at: float = field(default_factory=time)
    updated_at: float = field(default_factory=time)

    @property
    def retried(self) -> bool:
        """Whether this request has been retried at least once."""

        return self.attempt > 1

    def as_event_fields(self) -> dict[str, Any]:
        """Return JSON-serializable fields for event logs."""

        return {
            "request_id": self.request_id,
            "status": self.status.value,
            "worker_id": self.worker_id,
            "attempt": self.attempt,
            "retried": self.retried,
            "partial_tokens": len(self.partial_tokens),
            "response_tokens": len(self.response_tokens),
            "error": self.error,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class InMemoryRequestStore:
    """Small request store used before the Redis/SQLite backend is wired in."""

    def __init__(self) -> None:
        self._requests: dict[str, RolloutRequest] = {}

    def submit(
        self,
        request_id: str,
        *,
        prompt: str | None = None,
        model_version: int | None = None,
    ) -> RolloutRequest:
        """Create or return a pending request."""

        request = self._requests.get(request_id)
        if request is None:
            request = RolloutRequest(request_id=request_id, prompt=prompt, model_version=model_version)
            self._requests[request_id] = request
        request.updated_at = time()
        return request

    def mark_running(self, request_id: str, worker_id: str) -> RolloutRequest:
        """Mark a request as assigned to a worker."""

        request = self._require(request_id)
        request.status = RequestStatus.RUNNING
        request.worker_id = worker_id
        request.attempt += 1
        request.error = None
        request.updated_at = time()
        return request

    def save_partial(self, request_id: str, token_ids: list[int]) -> RolloutRequest:
        """Persist partial generated tokens for retry or audit."""

        request = self._require(request_id)
        request.partial_tokens = list(token_ids)
        request.updated_at = time()
        return request

    def mark_retrying(self, request_id: str, *, error: str | None = None) -> RolloutRequest:
        """Put a failed in-flight request back into retry state."""

        request = self._require(request_id)
        request.status = RequestStatus.RETRYING
        request.worker_id = None
        request.error = error
        request.updated_at = time()
        return request

    def mark_done(self, request_id: str, token_ids: list[int] | None = None) -> RolloutRequest:
        """Mark a request as successfully completed."""

        request = self._require(request_id)
        request.status = RequestStatus.DONE
        request.response_tokens = list(token_ids or [])
        request.error = None
        request.updated_at = time()
        return request

    def mark_failed(self, request_id: str, *, error: str | None = None) -> RolloutRequest:
        """Mark a request as permanently failed."""

        request = self._require(request_id)
        request.status = RequestStatus.FAILED
        request.error = error
        request.updated_at = time()
        return request

    def get(self, request_id: str) -> RolloutRequest | None:
        """Return a request if present."""

        return self._requests.get(request_id)

    def all(self) -> list[RolloutRequest]:
        """Return all request records."""

        return list(self._requests.values())

    def _require(self, request_id: str) -> RolloutRequest:
        request = self._requests.get(request_id)
        if request is None:
            raise KeyError(f"unknown rollout request: {request_id}")
        return request

