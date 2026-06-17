"""Placement-plan to verl resource-pool adapter.

Converts elastic placement decisions into the ResourcePoolManager and Ray
placement-group structures expected by verl.
"""


class ResourcePoolAdapter:
    """Translate placement plans into verl resource pools."""

    def to_verl_resource_pool(self, placement_plan: dict) -> dict:
        """Return a placeholder resource-pool spec."""
        return placement_plan

