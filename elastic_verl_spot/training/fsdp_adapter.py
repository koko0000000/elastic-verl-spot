"""FSDP training adapter.

Handles FSDP-specific checkpoint shards, world-size changes at safe points,
and rank mapping for actor training.
"""

from .training_group_adapter import TrainingGroupAdapter


class FSDPAdapter(TrainingGroupAdapter):
    """FSDP backend shell."""

