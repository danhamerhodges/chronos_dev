"""Maps to: DS-007"""

from pathlib import Path


def test_core_components_exist() -> None:
    root = Path(__file__).resolve().parents[2]
    for name in ["Button.tsx", "InputField.tsx", "Card.tsx", "Modal.tsx", "ProgressBar.tsx"]:
        assert (root / "web/src/components" / name).exists()
