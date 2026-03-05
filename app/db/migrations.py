"""Migration helper utilities for ENG-016."""

from __future__ import annotations

from pathlib import Path


def migration_files(root: Path) -> list[Path]:
    migrations_dir = root / "supabase" / "migrations"
    if not migrations_dir.exists():
        return []
    return sorted(path for path in migrations_dir.glob("*.sql") if path.is_file())
