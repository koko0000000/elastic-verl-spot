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
class KVCacheMetadata:
    """CPU-side metadata for a saved rollout KV cache segment."""

    cache_key: str
    model_version: int | None = None
    token_count: int = 0
    worker_id: str | None = None
    location: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time)

    def as_event_fields(self) -> dict[str, Any]:
        """Return JSON-serializable fields for event logs."""

        return {
            "cache_key": self.cache_key,
            "model_version": self.model_version,
            "token_count": self.token_count,
            "worker_id": self.worker_id,
            "location": self.location,
            "extra": self.extra,
            "created_at": self.created_at,
        }


@dataclass
class RolloutRequest:
    """Serializable rollout request state."""

    request_id: str
    engine_request_ids: list[str] = field(default_factory=list)
    prompt: str | None = None
    prompt_tokens: list[int] = field(default_factory=list)
    sampling_params: dict[str, Any] = field(default_factory=dict)
    model_version: int | None = None
    status: RequestStatus = RequestStatus.PENDING
    worker_id: str | None = None
    attempt: int = 0
    partial_tokens: list[int] = field(default_factory=list)
    partial_token_count: int = 0
    partial_text: str | None = None
    response_tokens: list[int] = field(default_factory=list)
    response_token_count: int = 0
    response_text: str | None = None
    kv_cache: KVCacheMetadata | None = None
    trajectory_id: str | None = None
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
            "engine_request_ids": list(self.engine_request_ids),
            "partial_tokens": self.partial_token_count,
            "response_tokens": self.response_token_count,
            "has_kv_cache": self.kv_cache is not None,
            "kv_cache_tokens": self.kv_cache.token_count if self.kv_cache else 0,
            "trajectory_id": self.trajectory_id,
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
        prompt_tokens: list[int] | None = None,
        sampling_params: dict[str, Any] | None = None,
        model_version: int | None = None,
    ) -> RolloutRequest:
        """Create or return a pending request."""

        request = self._requests.get(request_id)
        if request is None:
            request = RolloutRequest(
                request_id=request_id,
                prompt=prompt,
                prompt_tokens=list(prompt_tokens or []),
                sampling_params=dict(sampling_params or {}),
                model_version=model_version,
            )
            self._requests[request_id] = request
        else:
            if prompt is not None:
                request.prompt = prompt
            if prompt_tokens is not None:
                request.prompt_tokens = list(prompt_tokens)
            if sampling_params is not None:
                request.sampling_params = dict(sampling_params)
            if model_version is not None:
                request.model_version = model_version
        request.updated_at = time()
        return request

    def mark_running(
        self,
        request_id: str,
        worker_id: str,
        *,
        engine_request_id: str | None = None,
    ) -> RolloutRequest:
        """Mark a request as assigned to a worker."""

        request = self._require(request_id)
        request.status = RequestStatus.RUNNING
        request.worker_id = worker_id
        request.attempt += 1
        request.error = None
        if engine_request_id is not None:
            request.engine_request_ids.append(engine_request_id)
        request.updated_at = time()
        return request

    def bind_engine_request(self, request_id: str, engine_request_id: str) -> RolloutRequest:
        """Bind an internal engine request id to the stable rollout request id."""

        request = self._require(request_id)
        if engine_request_id not in request.engine_request_ids:
            request.engine_request_ids.append(engine_request_id)
        request.updated_at = time()
        return request

    def save_partial(
        self,
        request_id: str,
        token_ids: list[int],
        *,
        text: str | None = None,
        token_count: int | None = None,
    ) -> RolloutRequest:
        """Persist partial generated tokens for retry or audit."""

        request = self._require(request_id)
        request.partial_tokens = list(token_ids)
        request.partial_token_count = len(token_ids) if token_count is None else token_count
        if text is not None:
            request.partial_text = text
        request.updated_at = time()
        return request

    def append_partial(
        self,
        request_id: str,
        token_ids: list[int],
        *,
        text_delta: str | None = None,
        token_count: int | None = None,
    ) -> RolloutRequest:
        """Append newly streamed partial tokens to a request."""

        request = self._require(request_id)
        request.partial_tokens.extend(token_ids)
        request.partial_token_count = (
            len(request.partial_tokens) if token_count is None else request.partial_token_count + token_count
        )
        if text_delta:
            request.partial_text = (request.partial_text or "") + text_delta
        request.updated_at = time()
        return request

    def save_kv_cache(
        self,
        request_id: str,
        *,
        cache_key: str,
        model_version: int | None = None,
        token_count: int = 0,
        worker_id: str | None = None,
        location: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> RolloutRequest:
        """Persist metadata for a replayable KV cache segment."""

        request = self._require(request_id)
        request.kv_cache = KVCacheMetadata(
            cache_key=cache_key,
            model_version=model_version if model_version is not None else request.model_version,
            token_count=token_count,
            worker_id=worker_id,
            location=location,
            extra=dict(extra or {}),
        )
        request.updated_at = time()
        return request

    def attach_trajectory(self, request_id: str, trajectory_id: str) -> RolloutRequest:
        """Associate a request with a trajectory record."""

        request = self._require(request_id)
        request.trajectory_id = trajectory_id
        request.updated_at = time()
        return request

    def mark_retrying(
        self,
        request_id: str,
        *,
        error: str | None = None,
        preserve_worker: bool = False,
    ) -> RolloutRequest:
        """Put a failed in-flight request back into retry state."""

        request = self._require(request_id)
        request.status = RequestStatus.RETRYING
        if not preserve_worker:
            request.worker_id = None
        request.error = error
        request.updated_at = time()
        return request

    def mark_done(
        self,
        request_id: str,
        token_ids: list[int] | None = None,
        *,
        text: str | None = None,
        token_count: int | None = None,
    ) -> RolloutRequest:
        """Mark a request as successfully completed."""

        request = self._require(request_id)
        request.status = RequestStatus.DONE
        request.response_tokens = list(token_ids or [])
        request.response_token_count = len(request.response_tokens) if token_count is None else token_count
        if text is not None:
            request.response_text = text
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
