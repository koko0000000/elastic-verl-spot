"""Durable rollout request state.

Stores prompt text or token IDs, partial response tokens, sampling parameters,
model version, RNG seed, worker lease, and request status. This state should be
CPU-side and durable enough to survive spot worker loss.
"""

from dataclasses import dataclass, field


@dataclass
class RolloutRequest:
    """Serializable rollout request state."""

    request_id: str
    prompt: str
    model_version: int
    status: str = "pending"
    partial_tokens: list[int] = field(default_factory=list)

