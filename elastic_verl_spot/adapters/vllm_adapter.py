"""vLLM adapter.

Wraps vLLM rollout engines when verl is configured to generate responses using
vLLM. The first version should not attempt cross-node attention KV migration.
"""


class VLLMAdapter:
    """vLLM adapter shell."""

