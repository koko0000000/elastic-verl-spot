"""Event definitions and in-process event bus.

Events include node join, node loss, preemption notice, rollout worker failure,
training rank failure, checkpoint completion, and safe-point arrival.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Event:
    """A minimal elastic-system event."""

    name: str
    payload: dict

