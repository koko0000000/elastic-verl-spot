"""Reference-policy role group.

Computes reference log probabilities for KL or related objectives. Depending on
the verl configuration, this may be colocated with actor/rollout workers or run
as a separate replica-style service.
"""

from .replica_group import ElasticReplicaGroup


class RefGroup(ElasticReplicaGroup):
    """Reference-policy replica group shell."""

