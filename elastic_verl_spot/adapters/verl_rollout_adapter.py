"""Adapter for verl rollout hooks.

The vendored verl source should stay as a thin hook layer.  This module owns the
elastic rollout control logic: event logging, fault injection bookkeeping,
state-machine updates, and checkpoint-manager coordination.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import numpy as np

from elastic_verl_spot.rollout.request_store import InMemoryRequestStore
from elastic_verl_spot.rollout.state_machine import RolloutReplicaStateMachine
from elastic_verl_spot.rollout.trajectory_store import InMemoryTrajectoryStore


class JsonlElasticRolloutLogger:
    """Append-only JSONL event logger used by the elastic rollout adapter."""

    def __init__(self, path: str | Path):
        self.path = Path(path).expanduser()
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def emit(self, event_type: str, **fields: Any) -> None:
        record = {
            "event_type": event_type,
            "ts": time.time(),
            **fields,
        }
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


def _get_cfg(config: Any, key: str, default: Any = None) -> Any:
    if config is None:
        return default
    get = getattr(config, "get", None)
    if callable(get):
        return get(key, default)
    return getattr(config, key, default)


def _base_request_ids(batch: Any) -> list[str]:
    if "uid" in batch.non_tensor_batch:
        return [str(uid) for uid in batch.non_tensor_batch["uid"]]
    return [f"elastic-req-{idx:06d}" for idx in range(len(batch))]


def _request_ids_with_sample_index(batch: Any) -> list[str]:
    """Build request ids that are unique after rollout.n repeats prompts."""

    seen: dict[str, int] = {}
    request_ids = []
    for base_id in _base_request_ids(batch):
        sample_index = seen.get(base_id, 0)
        seen[base_id] = sample_index + 1
        request_ids.append(f"{base_id}:sample-{sample_index}")
    return request_ids


def _inject_elastic_request_ids(batch: Any, request_ids: list[str]) -> None:
    """Attach stable request ids so verl agent loops can forward them to runtime hooks."""

    batch.non_tensor_batch["elastic_request_id"] = np.array(request_ids, dtype=object)


def _record_replica_removed_state(
    fault_manager: Any,
    checkpoint_manager: Any,
    server_index: int,
    server_id: str | None,
) -> dict[str, Any]:
    """Record ALIVE -> DEAD -> REMOVED in the system state machine."""

    state_machine = getattr(checkpoint_manager, "elastic_rollout_state_machine", None)
    if state_machine is None:
        state_machine = RolloutReplicaStateMachine()
        for idx, address in enumerate(fault_manager.get_addresses()):
            state_machine.register_alive(replica_id=f"rollout-{idx}", server_id=address)
        setattr(checkpoint_manager, "elastic_rollout_state_machine", state_machine)

    replica_id = f"rollout-{server_index}"
    if state_machine.get(replica_id) is None:
        state_machine.register_alive(replica_id=replica_id, server_id=server_id)

    state_machine.mark_dead(replica_id, reason="fault_injection_killed")
    removed = state_machine.mark_removed(replica_id, reason="removed_from_control_plane")
    return {
        "state_machine": "updated",
        "replica_id": replica_id,
        "replica_state": removed.state.value,
        "schedulable": removed.schedulable,
        "checkpoint_participant": removed.checkpoint_participant,
        "skip_update_weights": state_machine.should_skip_full_weight_sync(),
    }


def remove_replica_from_checkpoint_manager(
    fault_manager: Any,
    checkpoint_manager: Any,
    kill_result: dict[str, Any],
) -> dict[str, Any]:
    """Remove the killed rollout replica from checkpoint sleep/update paths."""

    if checkpoint_manager is None:
        return {"removed": False, "reason": "checkpoint_manager_missing"}
    if fault_manager is None:
        return {"removed": False, "reason": "fault_manager_missing"}
    if not kill_result.get("killed", False):
        return {"removed": False, "reason": "server_not_killed"}

    server_index = kill_result.get("server_index")
    if server_index is None:
        return {"removed": False, "reason": "server_index_missing"}

    replicas = fault_manager.get_replicas()
    if server_index < 0 or server_index >= len(replicas):
        return {
            "removed": False,
            "reason": "server_index_out_of_range",
            "server_index": server_index,
            "replica_count": len(replicas),
        }

    checkpoint_manager.remove_replicas([replicas[server_index]])
    state_machine_result = _record_replica_removed_state(
        fault_manager=fault_manager,
        checkpoint_manager=checkpoint_manager,
        server_index=server_index,
        server_id=kill_result.get("server_id"),
    )
    should_skip_update_weights = state_machine_result.get("skip_update_weights", True)
    setattr(checkpoint_manager, "elastic_skip_update_weights", should_skip_update_weights)
    return {
        "removed": True,
        "server_index": server_index,
        "server_id": kill_result.get("server_id"),
        "active_checkpoint_replicas": len(getattr(checkpoint_manager, "replicas", [])),
        "skip_update_weights": should_skip_update_weights,
        **state_machine_result,
    }


def generate_sequences_with_elastic_events(
    rollout_manager: Any,
    batch: Any,
    elastic_config: Any,
    global_steps: int,
    fault_manager: Any | None = None,
    checkpoint_manager: Any | None = None,
) -> Any:
    """Call verl's native rollout manager and record elastic-rollout events."""

    event_log_path = _get_cfg(elastic_config, "event_log_path", None)
    if not event_log_path:
        rollout_data_dir = _get_cfg(elastic_config, "rollout_data_dir", None)
        if rollout_data_dir:
            event_log_path = Path(rollout_data_dir) / "elastic_rollout_events.jsonl"
        else:
            event_log_path = "elastic_rollout_events.jsonl"

    logger = JsonlElasticRolloutLogger(event_log_path)
    request_ids = _request_ids_with_sample_index(batch)
    _inject_elastic_request_ids(batch, request_ids)
    request_store = InMemoryRequestStore()
    trajectory_store = InMemoryTrajectoryStore()
    dry_run_fail_after = int(_get_cfg(elastic_config, "dry_run_fail_after_dispatches", -1))
    dry_run_fail_worker = str(_get_cfg(elastic_config, "dry_run_fail_worker_id", "rollout-0"))
    fault_injection_enable = bool(_get_cfg(elastic_config, "fault_injection_enable", False))
    fault_injection_step = int(_get_cfg(elastic_config, "fault_injection_step", -1))
    fault_injection_after = int(_get_cfg(elastic_config, "fault_injection_after_dispatches", -1))
    fault_injection_server_index = int(_get_cfg(elastic_config, "fault_injection_server_index", 0))
    fault_injection_no_restart = bool(_get_cfg(elastic_config, "fault_injection_no_restart", True))
    fault_injection_mode = str(_get_cfg(elastic_config, "fault_injection_mode", "pre_generate"))
    fault_injection_delay_sec = float(_get_cfg(elastic_config, "fault_injection_delay_sec", 0.5))
    should_inject_fault = fault_injection_enable and (
        fault_injection_step < 0 or fault_injection_step == global_steps
    )
    fault_injected = False

    logger.emit(
        "elastic_rollout_started",
        global_steps=global_steps,
        requests=len(request_ids),
        dry_run=not fault_injection_enable,
    )
    for idx, request_id in enumerate(request_ids, start=1):
        request_store.submit(request_id)
        trajectory_store.upsert_partial(request_id, trajectory_id=request_id)
        logger.emit("request_submitted", global_steps=global_steps, request_id=request_id)
        request_store.mark_running(request_id, worker_id="native_verl_rollout")
        logger.emit(
            "request_dispatched",
            global_steps=global_steps,
            request_id=request_id,
            worker_id="native_verl_rollout",
            attempt=1,
        )
        if dry_run_fail_after > 0 and idx == dry_run_fail_after:
            logger.emit(
                "worker_kill_requested_dry_run",
                global_steps=global_steps,
                worker_id=dry_run_fail_worker,
                after_dispatches=dry_run_fail_after,
                note="No Ray actor is killed in the first full-RL shim.",
            )
        if should_inject_fault and not fault_injected and idx == fault_injection_after:
            logger.emit(
                "worker_kill_requested",
                global_steps=global_steps,
                request_id=request_id,
                server_index=fault_injection_server_index,
                after_dispatches=fault_injection_after,
                mode=fault_injection_mode,
            )
            if fault_manager is None:
                logger.emit(
                    "worker_kill_failed",
                    global_steps=global_steps,
                    server_index=fault_injection_server_index,
                    reason="fault_manager_missing",
                )
            else:
                try:
                    if fault_injection_mode == "runtime":
                        configured = fault_manager.configure_runtime_fault_injection(
                            server_index=fault_injection_server_index,
                            after_dispatches=fault_injection_after,
                            delay_sec=fault_injection_delay_sec,
                            no_restart=fault_injection_no_restart,
                        )
                        logger.emit(
                            "worker_kill_configured_runtime",
                            global_steps=global_steps,
                            **configured,
                        )
                    else:
                        kill_result = fault_manager.kill_server_for_fault_injection(
                            server_index=fault_injection_server_index,
                            no_restart=fault_injection_no_restart,
                        )
                        logger.emit("worker_killed", global_steps=global_steps, **kill_result)
                        remove_result = remove_replica_from_checkpoint_manager(
                            fault_manager=fault_manager,
                            checkpoint_manager=checkpoint_manager,
                            kill_result=kill_result,
                        )
                        logger.emit(
                            "checkpoint_replica_removed",
                            global_steps=global_steps,
                            **remove_result,
                        )
                except Exception as exc:
                    logger.emit(
                        "worker_kill_failed",
                        global_steps=global_steps,
                        server_index=fault_injection_server_index,
                        error=repr(exc),
                    )
            fault_injected = True

    started_at = time.time()
    try:
        output = rollout_manager.generate_sequences(batch)
    except Exception as exc:
        elapsed_sec = time.time() - started_at
        logger.emit(
            "elastic_rollout_failed",
            global_steps=global_steps,
            submitted=len(request_ids),
            elapsed_sec=elapsed_sec,
            error=repr(exc),
        )
        raise
    elapsed_sec = time.time() - started_at

    if should_inject_fault and fault_injection_mode == "runtime" and fault_manager is not None:
        kill_result = fault_manager.get_runtime_fault_result()
        if kill_result and kill_result.get("killed", False):
            logger.emit("worker_killed", global_steps=global_steps, **kill_result)
            remove_result = remove_replica_from_checkpoint_manager(
                fault_manager=fault_manager,
                checkpoint_manager=checkpoint_manager,
                kill_result=kill_result,
            )
            logger.emit(
                "checkpoint_replica_removed",
                global_steps=global_steps,
                **remove_result,
            )

    completed_count = len(output)
    done_request_ids = request_ids[:completed_count]
    if completed_count > len(done_request_ids):
        done_request_ids.extend(_request_ids_with_sample_index(output)[len(done_request_ids) :])

    for request_id in done_request_ids:
        request_store.mark_done(request_id)
        trajectory_store.mark_done(request_id)
        logger.emit(
            "request_done",
            global_steps=global_steps,
            request_id=request_id,
            worker_id="native_verl_rollout",
            attempt=1,
            retried=False,
        )

    logger.emit(
        "elastic_rollout_finished",
        global_steps=global_steps,
        submitted=len(request_ids),
        completed=len(done_request_ids),
        elapsed_sec=elapsed_sec,
        output_batch_size=len(output),
    )

    output.meta_info.setdefault("elastic_rollout", {})
    output.meta_info["elastic_rollout"].update(
        {
            "enabled": True,
            "dry_run": not fault_injection_enable,
            "fault_injected": fault_injected,
            "event_log_path": str(event_log_path),
            "submitted": len(request_ids),
            "completed": len(done_request_ids),
            "request_store_records": len(request_store.all()),
            "trajectory_store_records": len(trajectory_store.all()),
        }
    )
    output.meta_info.setdefault("timing", {})
    output.meta_info["timing"]["elastic_rollout_shim"] = elapsed_sec
    return output
