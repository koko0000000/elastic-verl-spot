#!/usr/bin/env python3
"""Install elastic lifecycle hooks into collaborator-patched verl fully async files.

Run this after applying ``add_trace.20260708.patch`` to a verl checkout.
The script is intentionally idempotent: if a hook is already present, it will
not insert it again.
"""

from __future__ import annotations

import argparse
from pathlib import Path


ADAPTER_IMPORT = """from elastic_verl_spot.adapters.verl_fully_async_adapter import (
    ensure_fully_async_lifecycle_manager,
    get_fully_async_lifecycle_state,
    record_fully_async_model_version,
    record_fully_async_replica_enabled,
    record_fully_async_scale_up,
)
"""


ROLLOUTER = Path("verl/experimental/fully_async_policy/fully_async_rollouter.py")
TRAINER = Path("verl/experimental/fully_async_policy/fully_async_trainer.py")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def _insert_import(text: str, names: list[str]) -> str:
    if all(name in text for name in names):
        return text
    marker = "class "
    index = text.find(marker)
    if index < 0:
        raise RuntimeError("cannot find class marker for import insertion")
    return text[:index] + ADAPTER_IMPORT + "\n" + text[index:]


def patch_rollouter(path: Path) -> bool:
    text = _read(path)
    original = text
    text = _insert_import(
        text,
        [
            "record_fully_async_replica_enabled",
            "record_fully_async_scale_up",
            "get_fully_async_lifecycle_state",
        ],
    )

    old = "        scale_stats = await self.async_rollout_manager.add_replicas(num_replicas=num_replicas)\n"
    new = (
        "        start_index = len(self.async_rollout_manager.rollout_replicas)\n"
        "        scale_stats = await self.async_rollout_manager.add_replicas(num_replicas=num_replicas)\n"
        "        elastic_scale_stats = record_fully_async_scale_up(\n"
        "            self,\n"
        "            start_index=start_index,\n"
        "            num_replicas=num_replicas,\n"
        "            model_version=getattr(self, \"current_param_version\", None),\n"
        "        )\n"
    )
    if "elastic_scale_stats = record_fully_async_scale_up(" not in text:
        text = text.replace(old, new)

    old = (
        '            "max_concurrent_samples": self.max_concurrent_samples,\n'
        "            **scale_stats,\n"
    )
    new = (
        '            "max_concurrent_samples": self.max_concurrent_samples,\n'
        '            "elastic_lifecycle": elastic_scale_stats,\n'
        "            **scale_stats,\n"
    )
    if '"elastic_lifecycle": elastic_scale_stats' not in text:
        text = text.replace(old, new)

    old = (
        "        return {\n"
        '            "rollout_enabled": self.rollout_enabled,\n'
        '            "paused": self.paused,\n'
        '            "replica_id": replica_id,\n'
        '            "replica_enabled": enabled,\n'
        '            "disabled_replica_ids": sorted(self.disabled_replica_ids),\n'
        "            **routing_stats,\n"
        "        }\n"
    )
    new = (
        "        elastic_lifecycle = record_fully_async_replica_enabled(\n"
        "            self,\n"
        "            replica_id,\n"
        "            enabled,\n"
        "            model_version=getattr(self, \"current_param_version\", None),\n"
        "        )\n"
        "        return {\n"
        '            "rollout_enabled": self.rollout_enabled,\n'
        '            "paused": self.paused,\n'
        '            "replica_id": replica_id,\n'
        '            "replica_enabled": enabled,\n'
        '            "disabled_replica_ids": sorted(self.disabled_replica_ids),\n'
        '            "elastic_lifecycle": elastic_lifecycle,\n'
        "            **routing_stats,\n"
        "        }\n"
    )
    if "elastic_lifecycle = record_fully_async_replica_enabled(" not in text:
        text = text.replace(old, new)

    old = (
        "        return {\n"
        '            "rollout_enabled": self.rollout_enabled,\n'
        '            "paused": self.paused,\n'
        '            "manager_ready": True,\n'
        '            "num_total_replicas": replica_count,\n'
        '            "num_active_replicas": len(active_replica_ids),\n'
        '            "active_replica_ids": active_replica_ids,\n'
        '            "disabled_replica_ids": sorted(self.disabled_replica_ids),\n'
        '            "max_concurrent_samples": self.max_concurrent_samples,\n'
        "        }\n"
    )
    new = (
        "        ensure_fully_async_lifecycle_manager(self)\n"
        "        return {\n"
        '            "rollout_enabled": self.rollout_enabled,\n'
        '            "paused": self.paused,\n'
        '            "manager_ready": True,\n'
        '            "num_total_replicas": replica_count,\n'
        '            "num_active_replicas": len(active_replica_ids),\n'
        '            "active_replica_ids": active_replica_ids,\n'
        '            "disabled_replica_ids": sorted(self.disabled_replica_ids),\n'
        '            "max_concurrent_samples": self.max_concurrent_samples,\n'
        '            "elastic_lifecycle": get_fully_async_lifecycle_state(self),\n'
        "        }\n"
    )
    if '"elastic_lifecycle": get_fully_async_lifecycle_state(self)' not in text:
        text = text.replace(old, new)

    if text != original:
        _write(path, text)
        return True
    return False


def patch_trainer(path: Path) -> bool:
    text = _read(path)
    original = text
    text = _insert_import(text, ["record_fully_async_model_version"])

    old = (
        "        self.checkpoint_manager.add_replicas(new_replicas)\n"
        "        await self.checkpoint_manager.update_weights(global_steps=self.current_param_version)\n"
    )
    new = (
        "        self.checkpoint_manager.add_replicas(new_replicas)\n"
        "        await self.checkpoint_manager.update_weights(global_steps=self.current_param_version)\n"
        "        record_fully_async_model_version(self.rollouter, self.current_param_version)\n"
    )
    if "record_fully_async_model_version(self.rollouter" not in text:
        text = text.replace(old, new)

    if text != original:
        _write(path, text)
        return True
    return False


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--verl-root",
        default=".",
        help="Path to the verl repository root. Defaults to current directory.",
    )
    args = parser.parse_args()
    root = Path(args.verl_root).resolve()

    rollouter = root / ROLLOUTER
    trainer = root / TRAINER
    for path in [rollouter, trainer]:
        if not path.exists():
            raise SystemExit(f"missing expected file: {path}")

    changed = {
        str(ROLLOUTER): patch_rollouter(rollouter),
        str(TRAINER): patch_trainer(trainer),
    }
    print(changed)


if __name__ == "__main__":
    main()
