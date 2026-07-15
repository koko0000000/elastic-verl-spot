#!/usr/bin/env python3
"""Control fully-async rollouter runtime state via Ray.

Examples:
  python scripts/control_rollouter.py status
  python scripts/control_rollouter.py global --enabled false
  python scripts/control_rollouter.py global --enabled true
  python scripts/control_rollouter.py replica --id 0 --enabled false
  python scripts/control_rollouter.py replica --id 0 --enabled true
    python scripts/control_rollouter.py scale-up --num-replicas 1

If your Ray job uses a non-default namespace, pass --namespace.
"""

from __future__ import annotations

import argparse
import json
from typing import Any

import ray
from ray.util import list_named_actors
from ray.exceptions import RayTaskError


def _parse_bool(value: str) -> bool:
    v = value.strip().lower()
    if v in {"1", "true", "t", "yes", "y", "on"}:
        return True
    if v in {"0", "false", "f", "no", "n", "off"}:
        return False
    raise argparse.ArgumentTypeError(f"invalid bool value: {value}")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Control fully-async rollouter")
    parser.add_argument("--address", default="auto", help="Ray address, default: auto")
    parser.add_argument("--namespace", default="default", help="Ray namespace, default: default")
    parser.add_argument(
        "--actor-name",
        default="fully_async_rollouter",
        help="Named rollouter actor, default: fully_async_rollouter",
    )
    parser.add_argument(
        "--trainer-actor-name",
        default="fully_async_trainer",
        help="Named trainer actor for scale-up orchestration, default: fully_async_trainer",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("status", help="Get rollout control state")

    p_global = subparsers.add_parser("global", help="Enable/disable rollout globally")
    p_global.add_argument("--enabled", required=True, type=_parse_bool, help="true/false")

    p_replica = subparsers.add_parser("replica", help="Enable/disable one replica")
    p_replica.add_argument("--id", required=True, type=int, help="Replica id")
    p_replica.add_argument("--enabled", required=True, type=_parse_bool, help="true/false")

    p_scale = subparsers.add_parser("scale-up", help="Dynamically add rollout replicas/vllm servers")
    p_scale.add_argument("--num-replicas", required=True, type=int, help="Number of replicas to add")

    return parser


def _print_result(result: Any) -> None:
    print(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True))


def _find_named_actor(actor_name: str):
    """Find a named Ray actor across all namespaces."""
    all_actors = list_named_actors(all_namespaces=True)
    matched_actors = [actor for actor in all_actors if actor.get("name") == actor_name]

    if len(matched_actors) == 1:
        return ray.get_actor(**matched_actors[0])

    if len(matched_actors) == 0:
        available = [f"{actor.get('name')}@{actor.get('namespace')}" for actor in all_actors]
        raise ValueError(
            f"No actor named '{actor_name}' found. Available named actors: {available}"
        )

    matches = [f"{actor.get('name')}@{actor.get('namespace')}" for actor in matched_actors]
    raise ValueError(f"Multiple actors named '{actor_name}' found: {matches}")


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    ray.init(address=args.address, namespace=args.namespace, ignore_reinit_error=True)

    try:
        rollouter = _find_named_actor(args.actor_name)
    except ValueError as exc:
        raise SystemExit(
            "Cannot find rollouter actor. Check --actor-name/--namespace and ensure training is running. "
            f"Original error: {exc}"
        )

    if args.command == "status":
        try:
            result = ray.get(rollouter.get_rollout_control_state.remote())
        except RayTaskError as exc:
            raise SystemExit(
                "Failed to query rollouter status. Rollouter may still be initializing or startup failed. "
                f"Original error: {exc}"
            )
        _print_result(result)
        return

    if args.command == "global":
        try:
            result = ray.get(rollouter.set_rollout_enabled.remote(args.enabled))
        except RayTaskError as exc:
            raise SystemExit(
                "Failed to toggle rollout globally. Rollouter may still be initializing or startup failed. "
                f"Original error: {exc}"
            )
        _print_result(result)
        return

    if args.command == "replica":
        try:
            result = ray.get(rollouter.set_rollout_replica_enabled.remote(args.id, args.enabled))
        except RayTaskError as exc:
            raise SystemExit(
                "Failed to toggle replica. Rollouter may still be initializing or startup failed. "
                f"Original error: {exc}"
            )
        _print_result(result)
        return

    if args.command == "scale-up":
        try:
            trainer = _find_named_actor(args.trainer_actor_name)
        except ValueError as exc:
            raise SystemExit(
                "Cannot find trainer actor for rollout scale-up. Ensure training is running with the updated code. "
                f"Original error: {exc}"
            )

        try:
            result = ray.get(trainer.scale_up_rollout_replicas.remote(args.num_replicas))
        except RayTaskError as exc:
            raise SystemExit(
                "Failed to scale up rollout replicas. Trainer/rollouter may not be fully initialized. "
                f"Original error: {exc}"
            )
        _print_result(result)
        return

    raise SystemExit(f"Unknown command: {args.command}")


if __name__ == "__main__":
    main()
