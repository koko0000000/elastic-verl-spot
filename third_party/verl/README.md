# verl source binding

Do not commit the full verl source tree here.

Use one of these layouts on the compute platform:

1. Preferred: keep using the already installed `verl==0.9.0.dev` package.
2. Source-linked: set `VERL_SOURCE_DIR=/path/to/platform/verl`.
3. Repo-local link: create `third_party/verl/verl-src` as a symlink to the platform's existing verl source directory.

The adapter in `elastic_verl_spot/adapters/verl_import.py` resolves these options automatically.

