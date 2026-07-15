"""Rollout replica lifecycle manager.

This module absorbs the reusable part of the fully-async rollout rejoin patch:
active replica routing, disable/enable, scale-up bookkeeping, and checkpoint
sync decisions.  It intentionally has no hard dependency on Ray or verl so that
thin verl hooks can call into it from different trainer entrypoints.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from time import time
from typing import Any, Callable

from elastic_verl_spot.rollout.state_machine import RolloutReplicaStateMachine


EventSink = Callable[[str], None]


@dataclass
class LifecycleEvent:
    """JSON-serializable rollout lifecycle event."""

    event_type: str
    ts: float = field(default_factory=time)
    fields: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        """Return a flat event dictionary."""

        return {
            "event_type": self.event_type,
            "ts": self.ts,
            **self.fields,
        }


class RolloutLifecycleManager:
    """System-side owner for rollout replica active-set transitions."""

    def __init__(
        self,
        *,
        state_machine: RolloutReplicaStateMachine | None = None,
        event_sink: Callable[[dict[str, Any]], None] | None = None,
        max_samples_per_replica: int = 16,
    ) -> None:
        self.state_machine = state_machine or RolloutReplicaStateMachine()
        self.event_sink = event_sink
        self.max_samples_per_replica = max_samples_per_replica
        self._active_replica_ids: list[str] = []
        self._disabled_replica_ids: set[str] = set()
        self._checkpoint_replica_ids: set[str] = set()
        self._current_model_version: int | None = None

    @property
    def active_replica_ids(self) -> list[str]:
        """Return active replicas in deterministic order."""

        return list(self._active_replica_ids)

    @property
    def disabled_replica_ids(self) -> list[str]:
        """Return disabled replicas in deterministic order."""

        return sorted(self._disabled_replica_ids)

    def register_replicas(self, replicas: list[tuple[str, str | None]]) -> dict[str, Any]:
        """Register existing rollout replicas as alive and schedulable."""

        for replica_id, server_id in replicas:
            self.state_machine.register_alive(replica_id, server_id=server_id)
            self._checkpoint_replica_ids.add(replica_id)
        self._active_replica_ids = [
            replica_id
            for replica_id, _server_id in replicas
            if replica_id not in self._disabled_replica_ids
        ]
        result = self.control_state()
        self._emit("rollout_replicas_registered", **result)
        return result

    def disable_replica(self, replica_id: str, *, reason: str = "manual_disable") -> dict[str, Any]:
        """Disable one replica and remove it from active routing."""

        self.state_machine.mark_draining(replica_id, reason=reason)
        removed = self.state_machine.mark_removed(replica_id, reason=reason)
        self._disabled_replica_ids.add(replica_id)
        self._active_replica_ids = [
            active_replica_id
            for active_replica_id in self._active_replica_ids
            if active_replica_id != replica_id
        ]
        self._checkpoint_replica_ids.discard(replica_id)
        result = self.control_state()
        self._emit(
            "worker_disabled",
            replica_id=replica_id,
            state_after=removed.state.value,
            reason=reason,
            **result,
        )
        self._emit("load_balancer_updated", active_replica_ids=self.active_replica_ids)
        self._emit("checkpoint_replica_removed", replica_id=replica_id, **result)
        return result

    def enable_replica(
        self,
        replica_id: str,
        *,
        server_id: str | None = None,
        model_version: int | None = None,
        reason: str = "manual_enable",
    ) -> dict[str, Any]:
        """Rebuild, weight-sync, and mark a replica alive for routing."""

        if self.state_machine.get(replica_id) is None:
            self.state_machine.register_alive(replica_id, server_id=server_id)
            self.state_machine.mark_dead(replica_id, reason="registered_for_rebuild")
            self.state_machine.mark_removed(replica_id, reason="registered_for_rebuild")
        rebuilding = self.state_machine.mark_rebuilding(replica_id, reason=reason)
        self._emit(
            "worker_rebuilding",
            replica_id=replica_id,
            server_id=server_id,
            state_after=rebuilding.state.value,
            reason=reason,
        )

        sync_version = self._current_model_version if model_version is None else model_version
        self._checkpoint_replica_ids.add(replica_id)
        self._emit(
            "checkpoint_weight_synced",
            replica_id=replica_id,
            model_version=sync_version,
            checkpoint_version=sync_version,
        )

        alive = self.state_machine.mark_alive(replica_id, server_id=server_id)
        self._disabled_replica_ids.discard(replica_id)
        if replica_id not in self._active_replica_ids:
            self._active_replica_ids.append(replica_id)
            self._active_replica_ids.sort()
        result = self.control_state()
        self._emit(
            "worker_rejoined",
            replica_id=replica_id,
            server_id=alive.server_id,
            state_after=alive.state.value,
            reason=reason,
            **result,
        )
        self._emit("load_balancer_updated", active_replica_ids=self.active_replica_ids)
        return result

    def scale_up(
        self,
        replicas: list[tuple[str, str | None]],
        *,
        model_version: int | None = None,
    ) -> dict[str, Any]:
        """Add new replicas through REBUILDING -> ALIVE and route to them."""

        new_replica_ids = []
        for replica_id, server_id in replicas:
            new_replica_ids.append(replica_id)
            if self.state_machine.get(replica_id) is None:
                self.state_machine.register_alive(replica_id, server_id=server_id)
                self.state_machine.mark_dead(replica_id, reason="scale_up_prepare")
                self.state_machine.mark_removed(replica_id, reason="scale_up_prepare")
            self.enable_replica(replica_id, server_id=server_id, model_version=model_version, reason="scale_up")
        result = {
            **self.control_state(),
            "new_replica_ids": new_replica_ids,
        }
        self._emit("rollout_replicas_scaled_up", **result)
        return result

    def update_model_version(self, model_version: int) -> dict[str, Any]:
        """Record current rollout model/checkpoint version."""

        self._current_model_version = model_version
        result = self.control_state()
        self._emit("rollout_model_version_updated", model_version=model_version, **result)
        return result

    def control_state(self) -> dict[str, Any]:
        """Return state suitable for a control API or status command."""

        return {
            "active_replica_ids": self.active_replica_ids,
            "disabled_replica_ids": self.disabled_replica_ids,
            "num_active_replicas": len(self._active_replica_ids),
            "num_total_replicas": len(self.state_machine.as_events()),
            "checkpoint_replica_ids": sorted(self._checkpoint_replica_ids),
            "max_concurrent_samples": len(self._active_replica_ids) * self.max_samples_per_replica,
            "current_model_version": self._current_model_version,
        }

    def _emit(self, event_type: str, **fields: Any) -> None:
        if self.event_sink is None:
            return
        self.event_sink(LifecycleEvent(event_type=event_type, fields=fields).as_dict())
