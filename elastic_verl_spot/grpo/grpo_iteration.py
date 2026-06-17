"""GRPO iteration lifecycle.

Represents one synchronous GRPO iteration: rollout a batch, complete rewards
and advantages, run actor optimizer steps, checkpoint, and publish a new model
version.
"""

from dataclasses import dataclass


@dataclass
class GRPOIteration:
    """Minimal GRPO iteration state."""

    global_step: int
    model_version: int
    status: str = "created"

