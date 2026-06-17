"""verl checkpoint adapter.

Calls verl native checkpoint save/load methods for FSDP or Megatron backends
and normalizes metadata for the elastic manifest store.
"""


class VerlCheckpointAdapter:
    """verl checkpoint adapter shell."""

