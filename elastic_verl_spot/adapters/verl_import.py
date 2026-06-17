"""verl import resolver.

This module lets the project reuse the compute platform's existing verl
0.9.0.dev installation. It optionally prepends VERL_SOURCE_DIR or
third_party/verl/verl-src to sys.path, then imports the installed verl package.
"""

from __future__ import annotations

import importlib
import os
from pathlib import Path
import sys


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def configure_verl_path() -> None:
    """Add an optional local verl source directory before importing verl."""
    candidates = []
    env_path = os.environ.get("VERL_SOURCE_DIR")
    if env_path:
        candidates.append(Path(env_path))
    candidates.append(_repo_root() / "third_party" / "verl" / "verl-src")

    for candidate in candidates:
        if candidate.exists() and str(candidate) not in sys.path:
            sys.path.insert(0, str(candidate))
            return


def import_verl():
    """Import and return the resolved verl module."""
    configure_verl_path()
    return importlib.import_module("verl")

