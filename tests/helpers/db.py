"""Maps to: ENG-016"""

from pathlib import Path


def migrations_dir(root: Path) -> Path:
    return root / "supabase" / "migrations"
