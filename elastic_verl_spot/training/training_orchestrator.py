"""Actor training orchestrator.

Feeds completed GRPO batches into the actor training group, tracks optimizer
steps, and coordinates safe-point entry before checkpoint or reconfiguration.
"""


class TrainingOrchestrator:
    """Minimal training orchestrator shell."""

    def train_batch(self, batch: dict) -> dict:
        """Train on one prepared batch."""
        return {"status": "not_implemented", "batch": batch}

