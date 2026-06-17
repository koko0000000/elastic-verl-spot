"""Training phase state machine.

This module tracks whether the system is in rollout, training, checkpointing,
reconfiguring, or validation. Spot events are handled differently depending on
the current phase.
"""

from enum import Enum


class Phase(str, Enum):
    """High-level elastic execution phases."""

    ROLLOUT = "rollout"
    TRAINING = "training"
    CHECKPOINTING = "checkpointing"
    RECONFIGURING = "reconfiguring"
    VALIDATING = "validating"

