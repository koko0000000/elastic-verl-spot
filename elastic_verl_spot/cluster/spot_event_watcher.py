"""Cloud spot preemption watcher.

This module should adapt the current compute platform's preemption notices into
controller events. Platform-specific HTTP metadata or scheduler hooks belong
behind this interface.
"""


class SpotEventWatcher:
    """Placeholder for cloud-platform spot notices."""

    def poll(self) -> list[dict]:
        """Return pending preemption events."""
        return []

