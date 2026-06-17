"""Training safe-point definitions.

The first implementation should treat complete optimizer steps, full GRPO
iteration boundaries, and completed checkpoints as safe. Microbatch-level
recovery should remain out of scope until gradient/RNG/optimizer partial state
is explicitly saved.
"""

from enum import Enum


class SafePointKind(str, Enum):
    """Supported safe-point kinds."""

    OPTIMIZER_STEP = "optimizer_step"
    GRPO_ITERATION = "grpo_iteration"
    CHECKPOINT = "checkpoint"

