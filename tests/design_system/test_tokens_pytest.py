"""Maps to: DS-007"""

from pathlib import Path


def test_tokens_files_exist() -> None:
    root = Path(__file__).resolve().parents[2]
    assert (root / "web/src/styles/tokens.css").exists()
    assert (root / "web/src/styles/tokens.ts").exists()
