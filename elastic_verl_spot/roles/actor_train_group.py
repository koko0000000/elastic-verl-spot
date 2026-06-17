"""Actor training role group.

This group wraps the actor update side of GRPO. It is a gang group because
FSDP/Megatron/NCCL ranks cannot be resized in place during an unsafe step.
"""

from .gang_group import ElasticGangGroup


class ActorTrainGroup(ElasticGangGroup):
    """Gang group specialized for actor training."""

