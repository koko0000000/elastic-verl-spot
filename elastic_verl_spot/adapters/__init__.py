"""Adapters for verl, Ray, vLLM, and SGLang integration."""

from elastic_verl_spot.adapters.verl_rollout_adapter import generate_sequences_with_elastic_events

__all__ = ["generate_sequences_with_elastic_events"]
