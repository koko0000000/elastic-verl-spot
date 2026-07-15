"""Replay elastic rollout event logs into rollout state stores."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from elastic_verl_spot.rollout.request_store import InMemoryRequestStore
from elastic_verl_spot.rollout.trajectory_store import InMemoryTrajectoryStore


class RolloutEventStateBuilder:
    """Build request and trajectory state from elastic rollout JSONL events."""

    def __init__(
        self,
        request_store: InMemoryRequestStore | None = None,
        trajectory_store: InMemoryTrajectoryStore | None = None,
    ) -> None:
        self.request_store = request_store or InMemoryRequestStore()
        self.trajectory_store = trajectory_store or InMemoryTrajectoryStore()

    def apply_event(self, event: dict[str, Any]) -> None:
        """Apply one elastic rollout event to the in-memory stores."""

        event_type = event.get("event_type")
        request_id = event.get("request_id")
        if not request_id:
            return

        if event_type == "request_submitted":
            self.request_store.submit(request_id, model_version=event.get("model_version"))
            self.trajectory_store.upsert_partial(
                request_id,
                trajectory_id=request_id,
                model_version=event.get("model_version"),
                metadata={"global_steps": event.get("global_steps")},
            )
            return

        if event_type in {"request_dispatched", "request_running"}:
            self._ensure_request(request_id)
            self.request_store.mark_running(
                request_id,
                worker_id=str(event.get("worker_id")),
                engine_request_id=event.get("engine_request_id"),
            )
            return

        if event_type == "request_engine_bound":
            self._ensure_request(request_id)
            engine_request_id = event.get("engine_request_id")
            if engine_request_id is not None:
                self.request_store.bind_engine_request(request_id, str(engine_request_id))
            return

        if event_type == "partial_response_saved":
            self._ensure_request(request_id)
            engine_request_id = event.get("engine_request_id")
            if engine_request_id is not None:
                self.request_store.bind_engine_request(request_id, str(engine_request_id))
            token_ids = list(event.get("token_ids") or [])
            token_count = int(event.get("partial_tokens", len(token_ids)) or 0)
            existing = self.request_store.get(request_id)
            should_update_partial = token_ids or token_count > (existing.partial_token_count if existing else 0)
            if should_update_partial:
                self.request_store.save_partial(request_id, token_ids, token_count=token_count)
            self.trajectory_store.upsert_partial(
                request_id,
                trajectory_id=request_id,
                response_tokens=token_ids if should_update_partial else None,
                metadata={
                    "partial_tokens": token_count,
                    "error": event.get("reason"),
                    "worker_id": event.get("worker_id"),
                    "engine_request_id": engine_request_id,
                    "finished": event.get("finished"),
                },
            )
            return

        if event_type == "request_retry_queued":
            self._ensure_request(request_id)
            self.request_store.mark_retrying(request_id, error=event.get("error"))
            return

        if event_type in {"request_retry_done", "request_done"}:
            self._ensure_request(request_id)
            engine_request_id = event.get("engine_request_id")
            if engine_request_id is not None:
                self.request_store.bind_engine_request(request_id, str(engine_request_id))
            token_ids = list(event.get("token_ids") or [])
            token_count = int(event.get("token_count", len(token_ids)) or 0)
            self.request_store.mark_done(request_id, token_ids, token_count=token_count)
            self.trajectory_store.upsert_partial(request_id, trajectory_id=request_id, response_tokens=token_ids)
            self.trajectory_store.mark_done(
                request_id,
                metadata={
                    "retried": event.get("retried", False),
                    "attempt": event.get("attempt"),
                    "worker_id": event.get("worker_id"),
                    "token_count": token_count,
                },
            )
            return

        if event_type == "request_retry_failed":
            self._ensure_request(request_id)
            engine_request_id = event.get("engine_request_id")
            if engine_request_id is not None:
                self.request_store.bind_engine_request(request_id, str(engine_request_id))
            self.request_store.mark_failed(request_id, error=event.get("error"))
            self.trajectory_store.upsert_partial(request_id, trajectory_id=request_id)
            self.trajectory_store.mark_failed(request_id, error=event.get("error"))

    def apply_events(self, events: Iterable[dict[str, Any]]) -> "RolloutEventStateBuilder":
        """Apply many events and return self for chaining."""

        for event in events:
            self.apply_event(event)
        return self

    @classmethod
    def from_jsonl(cls, path: str | Path) -> "RolloutEventStateBuilder":
        """Build stores from a JSONL event log."""

        builder = cls()
        with Path(path).open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    builder.apply_event(json.loads(line))
        return builder

    def _ensure_request(self, request_id: str) -> None:
        if self.request_store.get(request_id) is None:
            self.request_store.submit(request_id)
