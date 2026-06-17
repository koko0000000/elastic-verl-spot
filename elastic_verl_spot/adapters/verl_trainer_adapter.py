"""verl trainer adapter.

Wraps verl's GRPO/PPO trainer entrypoints so the elastic controller can run a
synchronous GRPO iteration without depending on verl internals throughout the
codebase.
"""

from .verl_import import import_verl


class VerlTrainerAdapter:
    """Adapter shell around the installed verl package."""

    def resolve_verl(self):
        """Return the active verl module."""
        return import_verl()

