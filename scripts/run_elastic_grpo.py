"""Run elastic GRPO.

Entry point for launching the synchronous GRPO MVP on a Ray cluster that
already has verl 0.9.0.dev installed in the active Python environment.
"""

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from elastic_verl_spot.adapters.verl_import import import_verl


def main() -> None:
    """Resolve verl and print the module path until full launch wiring exists."""
    verl = import_verl()
    print(f"Resolved verl from: {getattr(verl, '__file__', '<namespace>')}")


if __name__ == "__main__":
    main()
