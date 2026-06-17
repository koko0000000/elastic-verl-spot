"""Main elastic controller.

The controller consumes cluster events, phase changes, and failure signals,
then asks the role reallocation policy for a desired placement plan. It should
not contain verl-specific calls directly; those belong in adapters.
"""

from dataclasses import dataclass, field


@dataclass
class ElasticController:
    """Coordinates phase management, placement, and recovery."""

    events_seen: list[str] = field(default_factory=list)

    def handle_event(self, event_name: str) -> None:
        """Record an event until the real reconcile loop is implemented."""
        self.events_seen.append(event_name)

