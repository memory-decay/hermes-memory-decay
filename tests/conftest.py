"""Shared test fixtures for hermes-memory-decay tests."""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure the src directory is on the path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
