"""Adapter helpers for verl fully-async rollout runtime hooks.

The collaborator patch adds real runtime controls in verl's fully-async path.
This module is the system-side bridge those thin hooks should call so that
replica enable/disable/scale-up operations update the common elastic rollout
state machine and JSONL event stream.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from elastic_verl_spot.rollout.lifecycle_manager import RolloutLifecycleManager


def _get_cfg(config: Any, path: str, default: Any = None) -> Any:
    """Read a possibly nested config value from dict/OmegaConf-like objects."""

    current = config
    for part in path.split("."):
        if current is None:
            return default
        get = getattr(current, "get", None)
        if callable(get):
            current = get(part, default)
        else:
            current = getattr(current, part, default)
    return current


class JsonlEventSink:
    """Small JSONL event sink safe to attach to Ray actors."""

    def __init__(self, path: str | Path):
        self.path = Path(path).expanduser()
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def __call__(self, event: dict[str, Any]) -> None:
        record = {
            "ts": time.time(),
            **event,
        }
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


def fully_async_event_log_path(config: Any) -> str | None:
    """Resolve the event log path for fully-async lifecycle hooks."""

    return (
        os.getenv("ELASTIC_ROLLOUT_EVENT_LOG_PATH")
        or _get_cfg(config, "async_training.elastic_rollout_event_log_path")
        or _get_cfg(config, "trainer.elastic_rollout.event_log_path")
        or _get_cfg(config, "trainer.rollout_data_dir")
    )


def _event_sink_from_config(config: Any):
    path = fully_async_event_log_path(config)
    if not path:
        return None
    if str(path).endswith(".jsonl"):
        return JsonlEventSink(path)
    return JsonlEventSink(Path(path) / "fully_async_rollout_lifecycle_events.jsonl")


def _replica_id(index: int) -> str:
    return f"rollout-{index}"


def _server_id(owner: Any, replica_index: int) -> str | None:
    manager = getattr(owner, "async_rollout_manager", None)
    addresses = getattr(manager, "server_addresses", None)
    if addresses is None:
        return None
    try:
        return str(addresses[replica_index])
    except Exception:
        return None


def _replicas_from_owner(owner: Any) -> list[tuple[str, str | None]]:
    manager = getattr(owner, "async_rollout_manager", None)
    replicas = getattr(manager, "rollout_replicas", None) or []
    return [(_replica_id(index), _server_id(owner, index)) for index in range(len(replicas))]


def ensure_fully_async_lifecycle_manager(owner: Any, *, max_samples_per_replica: int = 16) -> RolloutLifecycleManager:
    """Return or initialize a lifecycle manager on a verl fully-async actor."""

    manager = getattr(owner, "elastic_rollout_lifecycle_manager", None)
    if manager is None:
        manager = RolloutLifecycleManager(
            event_sink=_event_sink_from_config(getattr(owner, "config", None)),
            max_samples_per_replica=max_samples_per_replica,
        )
        setattr(owner, "elastic_rollout_lifecycle_manager", manager)

    replicas = _replicas_from_owner(owner)
    if replicas and manager.control_state()["num_total_replicas"] == 0:
        manager.register_replicas(replicas)
    return manager


def record_fully_async_model_version(owner: Any, model_version: int | None) -> dict[str, Any]:
    """Record the current checkpoint/model version known by the trainer."""

    manager = ensure_fully_async_lifecycle_manager(owner)
    if model_version is None:
        return manager.control_state()
    return manager.update_model_version(int(model_version))


def record_fully_async_replica_enabled(
    owner: Any,
    replica_id: int,
    enabled: bool,
    *,
    model_version: int | None = None,
) -> dict[str, Any]:
    """Record a real fully-async replica enable/disable operation."""

    manager = ensure_fully_async_lifecycle_manager(owner)
    replica_key = _replica_id(replica_id)
    if enabled:
        return manager.enable_replica(
            replica_key,
            server_id=_server_id(owner, replica_id),
            model_version=model_version,
            reason="fully_async_enable",
        )
    return manager.disable_replica(replica_key, reason="fully_async_disable")


def record_fully_async_scale_up(
    owner: Any,
    *,
    start_index: int,
    num_replicas: int,
    model_version: int | None = None,
) -> dict[str, Any]:
    """Record newly added fully-async rollout replicas."""

    manager = ensure_fully_async_lifecycle_manager(owner)
    replicas = [
        (_replica_id(index), _server_id(owner, index))
        for index in range(start_index, start_index + num_replicas)
    ]
    return manager.scale_up(replicas, model_version=model_version)


def get_fully_async_lifecycle_state(owner: Any) -> dict[str, Any]:
    """Return current lifecycle state for control/status commands."""

    return ensure_fully_async_lifecycle_manager(owner).control_state()
