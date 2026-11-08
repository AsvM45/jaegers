"""Synthetic demonstration fixtures for dashboard testing and zero-run fallback."""

from pathlib import Path

FIXTURES_DIR = Path(__file__).parent.resolve()
METADATA_PATH = FIXTURES_DIR / "metadata.json"
DEMO_REGISTRY_PATH = FIXTURES_DIR / "demo_registry.json"
