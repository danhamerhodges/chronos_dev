"""Maps to: ENG-010, ENG-016, SEC-013"""

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
        "0008_org_log_settings_rls.sql",
        "0009_phase3_async_jobs.sql",
        "0010_phase3_async_job_rls.sql",
        "0011_phase3_realtime_authorization.sql",
        "0012_phase3_quality_manifest.sql",
        "0013_phase3_quality_manifest_rls.sql",
        "0014_phase3_runtime_ops.sql",
        "0015_phase4_upload_sessions.sql",
        "0016_phase4_upload_sessions_rls.sql",
        "0017_phase4_upload_configuration.sql",
        "0018_phase4_output_delivery.sql",
        "0019_phase4_output_delivery_rls.sql",
    ]


def test_realtime_authorization_migration_covers_subscribe_and_publish() -> None:
    root = Path(__file__).resolve().parents[2]
    sql = (root / "supabase" / "migrations" / "0011_phase3_realtime_authorization.sql").read_text(encoding="utf-8")
    assert "CREATE POLICY realtime_job_progress_subscribe" in sql
    assert "FOR SELECT" in sql
    assert "TO authenticated" in sql
    assert "realtime.messages.extension = 'broadcast'" in sql
    assert "CREATE POLICY realtime_job_progress_publish" in sql
    assert "FOR INSERT" in sql
    assert "TO service_role" in sql
    assert "realtime.topic() LIKE 'job_progress:%'" in sql


def test_manifest_rls_migration_covers_owner_reads() -> None:
    root = Path(__file__).resolve().parents[2]
    sql = (root / "supabase" / "migrations" / "0013_phase3_quality_manifest_rls.sql").read_text(encoding="utf-8")
    assert "ALTER TABLE public.job_manifests ENABLE ROW LEVEL SECURITY" in sql
    assert "CREATE POLICY job_manifests_owner_select" in sql
    assert "FOR SELECT" in sql
    assert "public.media_jobs.owner_user_id = auth.uid()" in sql


def test_runtime_ops_migration_covers_gpu_leases_and_incidents() -> None:
    root = Path(__file__).resolve().parents[2]
    sql = (root / "supabase" / "migrations" / "0014_phase3_runtime_ops.sql").read_text(encoding="utf-8")
    assert "ALTER TABLE public.media_jobs" in sql
    assert "ADD COLUMN IF NOT EXISTS cache_summary" in sql
    assert "CREATE TABLE IF NOT EXISTS public.gpu_worker_leases" in sql
    assert "lease_state IN ('idle', 'busy', 'released')" in sql
    assert "CREATE TABLE IF NOT EXISTS public.incident_events" in sql
    assert "severity IN ('P0', 'P1', 'P2', 'P3')" in sql


def test_upload_session_migrations_cover_owner_scoped_writes() -> None:
    root = Path(__file__).resolve().parents[2]
    sql = (root / "supabase" / "migrations" / "0015_phase4_upload_sessions.sql").read_text(encoding="utf-8")
    rls_sql = (root / "supabase" / "migrations" / "0016_phase4_upload_sessions_rls.sql").read_text(encoding="utf-8")

    assert "CREATE TABLE IF NOT EXISTS public.upload_sessions" in sql
    assert "external_upload_id TEXT NOT NULL UNIQUE" in sql
    assert "ADD COLUMN IF NOT EXISTS external_upload_id TEXT" in sql
    assert "ALTER TABLE public.upload_sessions ENABLE ROW LEVEL SECURITY" in rls_sql
    assert "CREATE POLICY upload_sessions_owner_access" in rls_sql
    assert "CREATE POLICY gcs_pointers_owner_access" in rls_sql


def test_upload_configuration_migration_adds_detection_and_launch_config_columns() -> None:
    root = Path(__file__).resolve().parents[2]
    sql = (root / "supabase" / "migrations" / "0017_phase4_upload_configuration.sql").read_text(encoding="utf-8")

    assert "ADD COLUMN IF NOT EXISTS detection_snapshot JSONB NOT NULL DEFAULT '{}'::JSONB" in sql
    assert "ADD COLUMN IF NOT EXISTS launch_config JSONB NOT NULL DEFAULT '{}'::JSONB" in sql
    assert "ADD COLUMN IF NOT EXISTS configured_at TIMESTAMPTZ" in sql


def test_output_delivery_migrations_add_export_and_job_proof_tables() -> None:
    root = Path(__file__).resolve().parents[2]
    sql = (root / "supabase" / "migrations" / "0018_phase4_output_delivery.sql").read_text(encoding="utf-8")
    rls_sql = (root / "supabase" / "migrations" / "0019_phase4_output_delivery_rls.sql").read_text(encoding="utf-8")

    assert "CREATE TABLE IF NOT EXISTS public.job_deletion_proofs" in sql
    assert "CREATE TABLE IF NOT EXISTS public.job_export_packages" in sql
    assert "variant IN ('av1', 'h264')" in sql
    assert "CONSTRAINT job_export_packages_deletion_proof_fk" in sql
    assert "ALTER TABLE public.job_deletion_proofs ENABLE ROW LEVEL SECURITY" in rls_sql
    assert "ALTER TABLE public.job_export_packages ENABLE ROW LEVEL SECURITY" in rls_sql
    assert "CREATE POLICY job_deletion_proofs_owner_select" in rls_sql
    assert "CREATE POLICY job_export_packages_owner_select" in rls_sql
