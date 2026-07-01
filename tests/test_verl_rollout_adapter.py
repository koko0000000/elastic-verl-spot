"""Tests for the verl rollout adapter."""

import json
from pathlib import Path

from elastic_verl_spot.adapters.verl_rollout_adapter import generate_sequences_with_elastic_events


class FakeBatch:
    def __init__(self) -> None:
        self.non_tensor_batch = {"uid": ["req-a", "req-a", "req-b", "req-b"]}

    def __len__(self) -> int:
        return 4


class FakeOutput(FakeBatch):
    def __init__(self) -> None:
        super().__init__()
        self.meta_info = {}


class FakeRolloutManager:
    def generate_sequences(self, batch):
        return FakeOutput()


class FakeFaultManager:
    def __init__(self) -> None:
        self.replicas = ["replica-0", "replica-1"]

    def get_addresses(self):
        return ["10.0.0.1:1000", "10.0.0.2:1000"]

    def get_replicas(self):
        return self.replicas

    def kill_server_for_fault_injection(self, server_index: int = 0, no_restart: bool = True):
        return {
            "server_id": self.get_addresses()[server_index],
            "killed": True,
            "no_restart": no_restart,
            "active_servers": self.get_addresses()[1:],
            "server_index": server_index,
        }


class FakeCheckpointManager:
    def __init__(self) -> None:
        self.replicas = ["replica-0", "replica-1"]

    def remove_replicas(self, replicas):
        remove = set(replicas)
        self.replicas = [replica for replica in self.replicas if replica not in remove]


def test_adapter_updates_state_machine_and_logs_fault(tmp_path: Path) -> None:
    """Fault injection should remove one replica and emit state-machine fields."""

    event_log_path = tmp_path / "events.jsonl"
    checkpoint_manager = FakeCheckpointManager()

    output = generate_sequences_with_elastic_events(
        rollout_manager=FakeRolloutManager(),
        batch=FakeBatch(),
        elastic_config={
            "event_log_path": str(event_log_path),
            "fault_injection_enable": True,
            "fault_injection_step": 2,
            "fault_injection_after_dispatches": 2,
            "fault_injection_server_index": 0,
        },
        global_steps=2,
        fault_manager=FakeFaultManager(),
        checkpoint_manager=checkpoint_manager,
    )

    assert len(output) == 4
    assert checkpoint_manager.replicas == ["replica-1"]
    assert checkpoint_manager.elastic_skip_update_weights is True

    events = [json.loads(line) for line in event_log_path.read_text(encoding="utf-8").splitlines()]
    removed_event = next(event for event in events if event["event_type"] == "checkpoint_replica_removed")
    assert removed_event["state_machine"] == "updated"
    assert removed_event["replica_id"] == "rollout-0"
    assert removed_event["replica_state"] == "REMOVED"
    assert removed_event["schedulable"] is False
    assert removed_event["checkpoint_participant"] is False

