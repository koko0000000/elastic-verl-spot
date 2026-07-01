"""Tests for rollout replica lifecycle state."""

import pytest

from elastic_verl_spot.rollout.state_machine import RolloutReplicaState, RolloutReplicaStateMachine


def test_rollout_replica_failure_path() -> None:
    """A failed replica should stop scheduling and checkpoint participation."""

    machine = RolloutReplicaStateMachine()
    machine.register_alive("rollout-0", server_id="10.0.0.1:1234")

    dead = machine.mark_dead("rollout-0", reason="ray_actor_died")
    assert dead.state == RolloutReplicaState.DEAD
    assert not dead.schedulable
    assert not dead.checkpoint_participant

    removed = machine.mark_removed("rollout-0")
    assert removed.state == RolloutReplicaState.REMOVED
    assert machine.schedulable_server_ids() == []
    assert machine.checkpoint_replica_ids() == []
    assert machine.should_skip_full_weight_sync()


def test_rollout_replica_draining_path() -> None:
    """A draining replica stops accepting new requests before removal."""

    machine = RolloutReplicaStateMachine()
    machine.register_alive("rollout-0", server_id="10.0.0.1:1234")

    draining = machine.mark_draining("rollout-0", reason="spot_preemption_notice")
    assert draining.state == RolloutReplicaState.DRAINING
    assert not draining.schedulable

    removed = machine.mark_removed("rollout-0")
    assert removed.state == RolloutReplicaState.REMOVED


def test_invalid_transition_is_rejected() -> None:
    """Removed replicas must be rebuilt before becoming alive again."""

    machine = RolloutReplicaStateMachine()
    machine.register_alive("rollout-0")
    machine.mark_removed("rollout-0")

    with pytest.raises(ValueError):
        machine.mark_alive("rollout-0")

