"""Ray adapter.

Centralizes Ray imports and operations: node discovery, actor creation, actor
health, placement groups, and controlled teardown. Tests can replace this with
a fake adapter.
"""


class RayAdapter:
    """Ray operation shell."""

    def available(self) -> bool:
        """Return whether Ray can be imported."""
        try:
            __import__("ray")
        except ImportError:
            return False
        return True

