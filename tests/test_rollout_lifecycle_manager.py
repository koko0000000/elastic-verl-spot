"""Tests for rollout lifecycle integration from the fully-async rejoin patch."""

from elastic_verl_spot.rollout.lifecycle_manager import RolloutLifecycleManager
from elastic_verl_spot.rollout.state_machine import RolloutReplicaState


def test_disable_enable_replica_updates_active_set_and_events() -> None:
    """Replica disable/enable should map to REMOVED -> REBUILDING -> ALIVE."""

    events = []
    manager = RolloutLifecycleManager(event_sink=events.append)
    manager.register_replicas(
        [
            ("rollout-0", "10.0.0.1:1000"),
            ("rollout-1", "10.0.0.2:1000"),
        ]
    )

    disabled = manager.disable_replica("rollout-0")
    assert disabled["active_replica_ids"] == ["rollout-1"]
    assert disabled["checkpoint_replica_ids"] == ["rollout-1"]
    assert manager.state_machine.get("rollout-0").state == RolloutReplicaState.REMOVED

    enabled = manager.enable_replica("rollout-0", server_id="10.0.0.1:1001", model_version=8)
    assert enabled["active_replica_ids"] == ["rollout-0", "rollout-1"]
    assert enabled["checkpoint_replica_ids"] == ["rollout-0", "rollout-1"]
    assert manager.state_machine.get("rollout-0").state == RolloutReplicaState.ALIVE
    assert manager.state_machine.get("rollout-0").server_id == "10.0.0.1:1001"

    event_types = [event["event_type"] for event in events]
    assert "worker_disabled" in event_types
    assert "checkpoint_replica_removed" in event_types
    assert "worker_rebuilding" in event_types
    assert "checkpoint_weight_synced" in event_types
    assert "worker_rejoined" in event_types
    assert event_types.count("load_balancer_updated") == 2


def test_scale_up_adds_rebuilding_replica_and_syncs_weights() -> None:
    """Scale-up should add a new replica, sync weights, and mark it schedulable."""

    events = []
    manager = RolloutLifecycleManager(event_sink=events.append)
    manager.register_replicas([("rollout-0", "10.0.0.1:1000")])
    manager.update_model_version(12)

    result = manager.scale_up([("rollout-1", "10.0.0.2:1000")])

    assert result["new_replica_ids"] == ["rollout-1"]
    assert result["active_replica_ids"] == ["rollout-0", "rollout-1"]
    assert result["checkpoint_replica_ids"] == ["rollout-0", "rollout-1"]
    assert result["current_model_version"] == 12
    assert manager.state_machine.get("rollout-1").state == RolloutReplicaState.ALIVE

    sync_events = [event for event in events if event["event_type"] == "checkpoint_weight_synced"]
    assert sync_events[-1]["replica_id"] == "rollout-1"
    assert sync_events[-1]["model_version"] == 12
