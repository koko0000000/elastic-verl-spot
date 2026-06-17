"""Ray cluster watcher.

This file should call Ray APIs to discover live nodes, actor health, and
placement-group status. It is isolated so the rest of the controller can be
tested without a running Ray cluster.
"""


class RayClusterWatcher:
    """Placeholder for Ray cluster polling."""

    def list_nodes(self) -> list[dict]:
        """Return live Ray node metadata."""
        return []

