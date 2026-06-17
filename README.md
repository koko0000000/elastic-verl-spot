# elastic-verl-spot

Elastic GRPO execution layer for verl on H200 spot instances.

This repository is a scaffold for a spot-aware elastic verl system. The first target is synchronous GRPO on verl `0.9.0.dev`:

- rollout workers are elastic replica groups;
- actor training workers are safe-point rebuilt gang groups;
- colocated, separated, and hybrid placement are modeled as policies;
- the platform's existing verl installation is reused instead of vendoring or reinstalling verl.

## verl placement

The repository intentionally does not copy the verl source tree.

At runtime, `elastic_verl_spot.adapters.verl_import` resolves verl in this order:

1. `VERL_SOURCE_DIR`, if set;
2. `third_party/verl/verl-src`, if you create a symlink or checkout there;
3. the already installed Python package, expected on the compute platform as `verl==0.9.0.dev`.

On the compute platform, if verl is already installed in the active environment, clone this repository and run scripts directly with the same environment. No verl reinstall is required.

## Initial development scope

The MVP is deliberately conservative:

- GRPO first;
- sync mode first;
- rollout request/trajectory recovery first;
- training recovery at optimizer-step or GRPO-iteration safe points;
- no cross-node attention KV cache migration in the first version.

## Repository map

See `elastic_verl_spot/` for the architecture skeleton. Every module includes a file-level docstring explaining its role.

