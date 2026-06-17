"""Response cache for optional rollout reuse.

Caches completed responses keyed by prompt hash, model version, and sampling
configuration. This is an optimization and must not be required for correctness.
"""


class ResponseCache:
    """In-memory placeholder response cache."""

    def __init__(self) -> None:
        self._items: dict[str, dict] = {}

