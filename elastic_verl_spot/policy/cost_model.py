"""Cost model for elastic actions.

Estimates the benefit of adding rollout capacity, the cost of rebuilding a
training gang, lost rollout tokens, checkpoint time, expected spot lifetime,
and useful tokens per dollar.
"""


class CostModel:
    """Placeholder cost model."""

    def score(self, action: dict) -> float:
        """Score a candidate action."""
        return 0.0

