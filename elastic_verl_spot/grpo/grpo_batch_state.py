"""GRPO grouped batch state.

Tracks prompt groups and their n sampled responses, including pending,
running, complete, failed, retried, and stale states.
"""

from dataclasses import dataclass, field


@dataclass
class GRPOBatchState:
    """State for one grouped rollout batch."""

    prompt_ids: list[str] = field(default_factory=list)
    responses_per_prompt: int = 1

