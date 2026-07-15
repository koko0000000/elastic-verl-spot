"""Tests for the verl fully-async lifecycle adapter."""

import json

from elastic_verl_spot.adapters.verl_fully_async_adapter import (
    ensure_fully_async_lifecycle_manager,
    record_fully_async_model_version,
    record_fully_async_replica_enabled,
    record_fully_async_scale_up,
)
from elastic_verl_spot.rollout.state_machine import RolloutReplicaState


class FakeAsyncRolloutManager:
    def __init__(self):
        self.rollout_replicas = ["replica-0", "replica-1"]
        self.server_addresses = ["10.0.0.1:1000", "10.0.0.2:1000"]


class FakeOwner:
    def __init__(self, event_path):
        self.config = {
            "async_training": {
                "elastic_rollout_event_log_path": str(event_path),
            }
        }
        self.async_rollout_manager = FakeAsyncRolloutManager()


def test_fully_async_adapter_records_disable_enable_and_scale_up(tmp_path) -> None:
    """Fully async runtime calls should update common lifecycle state and JSONL events."""

    event_path = tmp_path / "events.jsonl"
    owner = FakeOwner(event_path)

    manager = ensure_fully_async_lifecycle_manager(owner)
    assert manager.control_state()["active_replica_ids"] == ["rollout-0", "rollout-1"]

    disabled = record_fully_async_replica_enabled(owner, 0, False)
    assert disabled["active_replica_ids"] == ["rollout-1"]
    assert manager.state_machine.get("rollout-0").state == RolloutReplicaState.REMOVED

    enabled = record_fully_async_replica_enabled(owner, 0, True, model_version=3)
    assert enabled["active_replica_ids"] == ["rollout-0", "rollout-1"]
    assert manager.state_machine.get("rollout-0").state == RolloutReplicaState.ALIVE

    record_fully_async_model_version(owner, 4)
    owner.async_rollout_manager.rollout_replicas.append("replica-2")
    owner.async_rollout_manager.server_addresses.append("10.0.0.3:1000")
    scaled = record_fully_async_scale_up(owner, start_index=2, num_replicas=1)
    assert scaled["new_replica_ids"] == ["rollout-2"]
    assert scaled["active_replica_ids"] == ["rollout-0", "rollout-1", "rollout-2"]

    events = [json.loads(line) for line in event_path.read_text(encoding="utf-8").splitlines()]
    event_types = [event["event_type"] for event in events]
    assert "rollout_replicas_registered" in event_types
    assert "worker_disabled" in event_types
    assert "worker_rejoined" in event_types
    assert "checkpoint_weight_synced" in event_types
    assert "rollout_replicas_scaled_up" in event_types
