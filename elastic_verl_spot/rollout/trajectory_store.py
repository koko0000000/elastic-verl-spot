"""Shared trajectory buffer.

Stores completed or partial GRPO trajectories: prompt ID, group ID, response
tokens, rewards, logprobs, reference logprobs, advantage fields, model version,
and completion status.
"""

from dataclasses import dataclass, field


@dataclass
class Trajectory:
    """Serializable rollout trajectory."""

    request_id: str
    model_version: int
    response_tokens: list[int] = field(default_factory=list)
    reward: float | None = None

