"""Shared trajectory buffer.

Stores completed or partial GRPO trajectories: prompt ID, group ID, response
tokens, rewards, logprobs, reference logprobs, advantage fields, model version,
and completion status.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from time import time
from typing import Any


class TrajectoryStatus(str, Enum):
    """Lifecycle status for a rollout trajectory."""

    PARTIAL = "PARTIAL"
    DONE = "DONE"
    FAILED = "FAILED"


@dataclass
class Trajectory:
    """Serializable rollout trajectory."""

    request_id: str
    model_version: int | None = None
    trajectory_id: str | None = None
    group_id: str | None = None
    prompt_tokens: list[int] = field(default_factory=list)
    response_tokens: list[int] = field(default_factory=list)
    logprobs: list[float] = field(default_factory=list)
    ref_logprobs: list[float] = field(default_factory=list)
    advantages: list[float] = field(default_factory=list)
    reward: float | None = None
    status: TrajectoryStatus = TrajectoryStatus.PARTIAL
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time)
    updated_at: float = field(default_factory=time)

    def __post_init__(self) -> None:
        if self.trajectory_id is None:
            self.trajectory_id = self.request_id

    def as_event_fields(self) -> dict[str, Any]:
        """Return JSON-serializable fields for event logs."""

        return {
            "trajectory_id": self.trajectory_id,
            "request_id": self.request_id,
            "group_id": self.group_id,
            "model_version": self.model_version,
            "prompt_tokens": len(self.prompt_tokens),
            "response_tokens": len(self.response_tokens),
            "reward": self.reward,
            "status": self.status.value,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class InMemoryTrajectoryStore:
    """Append-friendly in-memory trajectory store for first-stage experiments."""

    def __init__(self) -> None:
        self._items: dict[str, Trajectory] = {}

    def upsert_partial(
        self,
        request_id: str,
        *,
        trajectory_id: str | None = None,
        model_version: int | None = None,
        group_id: str | None = None,
        prompt_tokens: list[int] | None = None,
        response_tokens: list[int] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Trajectory:
        """Create or update a partial trajectory."""

        key = trajectory_id or request_id
        trajectory = self._items.get(key)
        if trajectory is None:
            trajectory = Trajectory(
                request_id=request_id,
                trajectory_id=key,
                model_version=model_version,
                group_id=group_id,
                prompt_tokens=list(prompt_tokens or []),
                response_tokens=list(response_tokens or []),
                metadata=dict(metadata or {}),
            )
            self._items[key] = trajectory
        else:
            if model_version is not None:
                trajectory.model_version = model_version
            if group_id is not None:
                trajectory.group_id = group_id
            if prompt_tokens is not None:
                trajectory.prompt_tokens = list(prompt_tokens)
            if response_tokens is not None:
                trajectory.response_tokens = list(response_tokens)
            if metadata:
                trajectory.metadata.update(metadata)
            trajectory.status = TrajectoryStatus.PARTIAL
            trajectory.updated_at = time()
        return trajectory

    def append_response_tokens(self, trajectory_id: str, token_ids: list[int]) -> Trajectory:
        """Append generated response tokens to a partial trajectory."""

        trajectory = self._require(trajectory_id)
        trajectory.response_tokens.extend(token_ids)
        trajectory.updated_at = time()
        return trajectory

    def mark_done(
        self,
        trajectory_id: str,
        *,
        reward: float | None = None,
        logprobs: list[float] | None = None,
        ref_logprobs: list[float] | None = None,
        advantages: list[float] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Trajectory:
        """Mark a trajectory as complete."""

        trajectory = self._require(trajectory_id)
        trajectory.status = TrajectoryStatus.DONE
        trajectory.reward = reward
        if logprobs is not None:
            trajectory.logprobs = list(logprobs)
        if ref_logprobs is not None:
            trajectory.ref_logprobs = list(ref_logprobs)
        if advantages is not None:
            trajectory.advantages = list(advantages)
        if metadata:
            trajectory.metadata.update(metadata)
        trajectory.updated_at = time()
        return trajectory

    def mark_failed(self, trajectory_id: str, *, error: str | None = None) -> Trajectory:
        """Mark a trajectory as failed while preserving partial data."""

        trajectory = self._require(trajectory_id)
        trajectory.status = TrajectoryStatus.FAILED
        if error is not None:
            trajectory.metadata["error"] = error
        trajectory.updated_at = time()
        return trajectory

    def get(self, trajectory_id: str) -> Trajectory | None:
        """Return a trajectory if present."""

        return self._items.get(trajectory_id)

    def all(self) -> list[Trajectory]:
        """Return all trajectories."""

        return list(self._items.values())

    def _require(self, trajectory_id: str) -> Trajectory:
        trajectory = self._items.get(trajectory_id)
        if trajectory is None:
            raise KeyError(f"unknown trajectory: {trajectory_id}")
        return trajectory
