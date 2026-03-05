"""Maps to: DS-007"""

from pathlib import Path


def test_storybook_config_exists() -> None:
    root = Path(__file__).resolve().parents[2]
    assert (root / "web/.storybook/main.ts").exists()
    assert (root / "web/.storybook/preview.ts").exists()
