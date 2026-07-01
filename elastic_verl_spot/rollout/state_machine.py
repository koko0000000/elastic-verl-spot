"""Rollout replica state machine.

This module is the system-level owner of rollout replica lifecycle state.  The
vendored verl patches should call into this module instead of embedding policy
decisions directly in trainer hooks.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from time import time
from typing import Any


class RolloutReplicaState(str, Enum):
    """Lifecycle states for one rollout worker / rollout replica."""

    ALIVE = "ALIVE"
    DRAINING = "DRAINING"
    DEAD = "DEAD"
    REMOVED = "REMOVED"
    REBUILDING = "REBUILDING"


_ALLOWED_TRANSITIONS: dict[RolloutReplicaState, set[RolloutReplicaState]] = {
    RolloutReplicaState.ALIVE: {
        RolloutReplicaState.DRAINING,
        RolloutReplicaState.DEAD,
        RolloutReplicaState.REBUILDING,
    },
    RolloutReplicaState.DRAINING: {
        RolloutReplicaState.DEAD,
        RolloutReplicaState.REMOVED,
    },
    RolloutReplicaState.DEAD: {
        RolloutReplicaState.REMOVED,
        RolloutReplicaState.REBUILDING,
    },
    RolloutReplicaState.REMOVED: {
        RolloutReplicaState.REBUILDING,
    },
    RolloutReplicaState.REBUILDING: {
        RolloutReplicaState.ALIVE,
        RolloutReplicaState.DEAD,
    },
}


@dataclass
class RolloutReplica:
    """State record for a rollout replica."""

    replica_id: str
    server_id: str | None = None
    state: RolloutReplicaState = RolloutReplicaState.ALIVE
    active_requests: int = 0
    last_error: str | None = None
    updated_at: float = field(default_factory=time)

    @property
    def schedulable(self) -> bool:
        """Whether load balancer may assign new requests to this replica."""

        return self.state == RolloutReplicaState.ALIVE

    @property
    def checkpoint_participant(self) -> bool:
        """Whether checkpoint manager may sleep/wake/update this replica."""

        return self.state == RolloutReplicaState.ALIVE

    def transition(
        self,
        target: RolloutReplicaState,
        *,
        error: str | None = None,
        allow_idempotent: bool = True,
    ) -> None:
        """Move this replica to a target state."""

        if self.state == target and allow_idempotent:
            self.last_error = error or self.last_error
            self.updated_at = time()
            return
        if target not in _ALLOWED_TRANSITIONS[self.state]:
            raise ValueError(f"invalid rollout replica transition: {self.state.value} -> {target.value}")

        self.state = target
        self.last_error = error
        self.updated_at = time()

    def as_event_fields(self) -> dict[str, Any]:
        """Return JSON-serializable fields for event logs."""

        return {
            "replica_id": self.replica_id,
            "server_id": self.server_id,
            "state": self.state.value,
            "active_requests": self.active_requests,
            "last_error": self.last_error,
            "updated_at": self.updated_at,
            "schedulable": self.schedulable,
            "checkpoint_participant": self.checkpoint_participant,
        }


class RolloutReplicaStateMachine:
    """In-memory rollout replica lifecycle registry."""

    def __init__(self) -> None:
        self._replicas: dict[str, RolloutReplica] = {}

    def register_alive(self, replica_id: str, server_id: str | None = None) -> RolloutReplica:
        """Register or refresh an alive rollout replica."""

        replica = self._replicas.get(replica_id)
        if replica is None:
            replica = RolloutReplica(replica_id=replica_id, server_id=server_id)
            self._replicas[replica_id] = replica
            return replica

        replica.server_id = server_id or replica.server_id
        replica.state = RolloutReplicaState.ALIVE
        replica.last_error = None
        replica.updated_at = time()
        return replica

    def get(self, replica_id: str) -> RolloutReplica | None:
        """Return a replica record if it exists."""

        return self._replicas.get(replica_id)

    def mark_draining(self, replica_id: str, *, reason: str | None = None) -> RolloutReplica:
        """Stop scheduling new requests while allowing in-flight requests to finish."""

        replica = self._require(replica_id)
        replica.transition(RolloutReplicaState.DRAINING, error=reason)
        return replica

    def mark_dead(self, replica_id: str, *, reason: str | None = None) -> RolloutReplica:
        """Mark a replica as failed and no longer usable."""

        replica = self._require(replica_id)
        replica.transition(RolloutReplicaState.DEAD, error=reason)
        return replica

    def mark_removed(self, replica_id: str, *, reason: str | None = None) -> RolloutReplica:
        """Mark a replica as removed from load balancer and checkpoint manager."""

        replica = self._require(replica_id)
        if replica.state == RolloutReplicaState.ALIVE:
            replica.transition(RolloutReplicaState.DEAD, error=reason)
        replica.transition(RolloutReplicaState.REMOVED, error=reason)
        return replica

    def mark_rebuilding(self, replica_id: str, *, reason: str | None = None) -> RolloutReplica:
        """Mark a replacement rollout replica as being rebuilt."""

        replica = self._require(replica_id)
        replica.transition(RolloutReplicaState.REBUILDING, error=reason)
        return replica

    def mark_alive(self, replica_id: str, server_id: str | None = None) -> RolloutReplica:
        """Mark a rebuilt rollout replica as ready for scheduling."""

        replica = self._require(replica_id)
        replica.server_id = server_id or replica.server_id
        replica.transition(RolloutReplicaState.ALIVE, error=None)
        return replica

    def schedulable_server_ids(self) -> list[str]:
        """Return server ids that may receive new rollout requests."""

        return [
            replica.server_id
            for replica in self._replicas.values()
            if replica.schedulable and replica.server_id is not None
        ]

    def checkpoint_replica_ids(self) -> list[str]:
        """Return replica ids allowed to participate in checkpoint operations."""

        return [
            replica.replica_id
            for replica in self._replicas.values()
            if replica.checkpoint_participant
        ]

    def should_skip_full_weight_sync(self) -> bool:
        """Short-term policy: skip full update_weights after any replica removal."""

        return any(replica.state == RolloutReplicaState.REMOVED for replica in self._replicas.values())

    def as_events(self) -> list[dict[str, Any]]:
        """Return all replica states as JSON-serializable records."""

        return [replica.as_event_fields() for replica in self._replicas.values()]

    def _require(self, replica_id: str) -> RolloutReplica:
        replica = self._replicas.get(replica_id)
        if replica is None:
            raise KeyError(f"unknown rollout replica: {replica_id}")
        return replica

