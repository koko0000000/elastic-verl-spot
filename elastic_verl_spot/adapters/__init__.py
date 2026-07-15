"""Adapters for verl, Ray, vLLM, and SGLang integration."""

from elastic_verl_spot.adapters.verl_fully_async_adapter import (
    ensure_fully_async_lifecycle_manager,
    get_fully_async_lifecycle_state,
    record_fully_async_model_version,
    record_fully_async_replica_enabled,
    record_fully_async_scale_up,
)
from elastic_verl_spot.adapters.verl_rollout_adapter import generate_sequences_with_elastic_events

__all__ = [
    "ensure_fully_async_lifecycle_manager",
    "generate_sequences_with_elastic_events",
    "get_fully_async_lifecycle_state",
    "record_fully_async_model_version",
    "record_fully_async_replica_enabled",
    "record_fully_async_scale_up",
]
