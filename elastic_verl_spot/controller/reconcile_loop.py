"""Desired-state reconciliation loop.

This loop compares the desired role placement against the current Ray cluster
state and issues create, destroy, restart, or defer actions through adapters.
"""


class ReconcileLoop:
    """Minimal reconcile-loop shell."""

    def run_once(self) -> None:
        """Perform one reconciliation pass."""
        return None

