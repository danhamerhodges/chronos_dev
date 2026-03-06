"""Maps to: ENG-016"""

from pathlib import Path

from app.db.migrations import migration_files


def test_expected_migrations_present() -> None:
    root = Path(__file__).resolve().parents[2]
    files = [p.name for p in migration_files(root)]
    assert files == [
        "0001_init_schema.sql",
        "0002_rls_policies.sql",
        "0003_indexes.sql",
        "0004_phase2_entities.sql",
        "0005_phase2_indexes.sql",
        "0006_phase2_request_rls.sql",
        "0007_phase2_gemini_usage.sql",
    ]
