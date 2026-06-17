"""Rollout worker adapter.

Wraps verl, vLLM, or SGLang rollout workers so the scheduler can call a stable
interface while the underlying engine remains configurable.
"""


class RolloutWorkerAdapter:
    """Adapter shell for rollout generation."""

    def generate(self, request: dict) -> dict:
        """Generate a response for one request."""
        raise NotImplementedError

