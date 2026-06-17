"""GRPO role graph.

Defines the first supported algorithm path: prompts enter rollout, responses
receive reward and reference logprobs, advantages are computed, and actor
training consumes the completed grouped trajectories.
"""


GRPO_ROLE_GRAPH = ("prompt", "rollout", "reward_ref", "advantage", "actor_train")

