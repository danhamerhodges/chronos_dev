# ChronosRefine Test Templates

**Version:** 2.12  
**Last Updated:** February 2026  
**Purpose:** Reusable test templates for all requirement categories

**Repo Note:** Test-file references in canon for phases not yet implemented on `main` are target mappings and may not exist until the corresponding packet lands. Completed-phase references should align to checked-in tests.

**Change Note (v2.12 - February 2026):** Applied 3 critical fixes + 3 medium-priority improvements (CLEAN GOVERNANCE):
1. **FIX #1 (CRITICAL):** Traceability validator `return Falsee` typo (CI-breaking NameError, corrected to `return False`)
2. **FIX #2 (CRITICAL):** Rate-limit reset call missing auth headers (would return 401 under middleware, added `headers=auth_headers_test`)
3. **FIX #3 (IMPORTANT):** `validate_test_environment()` called at import time (moved to `pytest_configure` hook, no longer surprises IDEs/linters/collect-only)
4. **IMPROVEMENT #1 (RECOMMENDED):** Traceability validator blank-line tolerance (switched to non-empty line scanning, 8-line limit, avoids CI friction from blank lines/wrapped text)
5. **IMPROVEMENT #2 (HYGIENE):** Conftest.py unused imports (removed `requests`, hoisted `uuid`/`typing` to module level, deduplicated `TestClient` import)
6. **IMPROVEMENT #3 (CONSISTENCY):** Rate-limit reset semantics unified (both `db_cleanup` and API template now use `TestClient(app)` + auth header, same canonical pattern)

**Change Note (v2.11 - February 2026):** Applied 2 critical fixes + 3 improvements (TRULY WORKING UNIT-ONLY MODE):
1. **FIX #1 (CRITICAL):** db_cleanup HTTP server dependency (switched to TestClient(app) for in-process reset, no connection errors)
2. **FIX #2 (CRITICAL):** Rate-limit test skips in unit-only mode (removed test_user dependency, tests actually run)
3. **IMPROVEMENT #1 (RECOMMENDED):** Traceability validator proximity (requires bullets immediately after "Maps to:", stronger enforcement)
4. **IMPROVEMENT #2 (MINOR):** Version history ordering (fixed chronological order)
5. **IMPROVEMENT #3 (MINOR):** Env vars documentation (added "Unit-Only Mode Minimal Env" section)

**Change Note (v2.10 - February 2026):** Applied 3 critical fixes + 3 governance improvements (FULLY WORKING UNIT-ONLY MODE):
1. **FIX #1 (CRITICAL):** auth_headers_test fixture dependency (removed test_user dependency, generates unique user ID, works in unit-only mode)
2. **FIX #2 (CRITICAL):** db_cleanup crashes in unit-only mode (guards Supabase operations, keeps rate-limit reset)
3. **FIX #3 (CRITICAL):** tests/helpers/db.py import-time failure (conditional Supabase client creation, raises clear errors)
4. **GOVERNANCE A (IMPORTANT):** Traceability validator bullet format (enforces `- FR-XXX` format, not just substring)
5. **GOVERNANCE B (MINOR):** _unit_only_mode unused variable (removed dead code)
6. **GOVERNANCE C (MINOR):** Required env vars ambiguous (clarified unit-only mode requirements in docstring)

**Change Note (v2.9 - February 2026):** Applied 1 critical fix + 3 important improvements (WORKING UNIT-ONLY MODE):
1. **FIX #1 (CRITICAL):** Supabase client creation at import time (made conditional, fixtures skip gracefully, unit-only mode actually works)
2. **IMPROVEMENT A (IMPORTANT):** validate_test_environment() early return (removed, consistent validation logic for all environments)
3. **IMPROVEMENT B (RECOMMENDED):** JWT issuer substring matching (hostname-based comparison, fewer false positives)
4. **IMPROVEMENT C (IMPORTANT):** Traceability validator weak enforcement (require at least one real requirement ID, no "TBD" passes)

**Change Note (v2.8 - February 2026):** Applied 5-fix robust governance pack:
1. **FIX #1 (CRITICAL):** Locust template double docstring (merged into single module docstring, fixes Python semantics violation)
2. **FIX #2 (CRITICAL):** Weak traceability validator (replaced bash with Python AST validator, prevents false passes)
3. **FIX #3 (IMPORTANT):** Service role key hard-requirement (allow missing key for localhost + TEST_AUTH_OVERRIDE unit-only mode)
4. **FIX #4 (RECOMMENDED):** Weak service role warning (decode JWT and validate claims, stronger defense-in-depth)
5. **FIX #5 (POLISH):** Next Steps numbering duplicates (corrected to 1-7, no duplicates)

**Change Note (v2.7 - February 2026):** Applied 4-enhancement governance closure pack:
1. **ENHANCEMENT #1 (CRITICAL SAFETY):** Supabase service role guard (prevents accidental production key usage)
2. **ENHANCEMENT #2 (HYGIENE):** Redundant imports cleanup (hoisted to module-level)
3. **ENHANCEMENT #3 (DOCUMENTATION):** validate_test_environment() strictness note (documented intentional behavior)
4. **ENHANCEMENT #4 (STRATEGIC GOVERNANCE):** Test File Header Contract (closes governance loop with mechanical traceability enforcement)

**Change Note (v2.6 - February 2026):** Applied 5-fix final drift/correctness pack:
1. **FIX #1 (CRITICAL):** Integration template job status string literal (use JobStatus enum)
2. **FIX #2 (IMPORTANT):** Next Steps wording outdated (separate backend/template tasks)
3. **FIX #3 (IMPORTANT):** validate_test_environment() substring matching (exact hostname matching)
4. **FIX #4 (IMPORTANT):** db_cleanup swallows reset failures silently (warn on unexpected errors)
5. **FIX #5 (HYGIENE):** Unused timedelta import in conftest.py (removed)

**Change Note (v2.5 - February 2026):** Applied 4-fix drift prevention pack:
1. **FIX #1 (IMPORTANT):** Misleading effort text (rewrote as cumulative effort across v2.0-v2.5)
2. **FIX #2 (CLEANUP):** Dead imports (removed unused jwt/datetime from auth_tokens.py)
3. **FIX #3 (CONSISTENCY):** Upload status string drift (added UploadStatus enum)
4. **FIX #4 (MINOR):** AI IDE prompt filename (changed to stable name, no version suffix)

**Change Note (v2.4 - February 2026): Applied 6-edit recommended consistency/correctness pack:
1. **FIX #1 (BLOCKING):** Test-only endpoint path doubled (changed to relative path `/reset-rate-limits`)
2. **FIX #2 (BLOCKING):** Load test signature mismatch (updated Locust template to match v2.3 function signature)
3. **FIX #3 (BLOCKING):** Version history incomplete (added v2.2 and v2.3 rows)
4. **FIX #4 (BLOCKING):** Fix count inconsistent (corrected to 6 fixes for v2.3)
5. **FIX #5 (RECOMMENDED):** Allowlist hardcoded (made configurable via TEST_SUPABASE_URL_ALLOWLIST)
6. **FIX #6 (RECOMMENDED):** Helper file organization (added note to move wait_for_job_completion to tests/helpers/jobs.py)

**Change Note (v2.3 - February 2026):** Applied 6-fix blocking consistency/correctness pack:
1. **FIX #1 (MODERATE):** Version drift (updated all v2.1 references to v2.3, added v2.2/v2.3 to Version History)
2. **FIX #2 (CRITICAL):** Auth bypass mismatch (standardized on prefix tokens for load tests, not JWT)
3. **FIX #3 (CRITICAL):** JobStatus string literals (imported and used canonical enum in helper)
4. **FIX #4 (IMPORTANT):** Email collision (use uuid for unique emails in integration template)
5. **FIX #5 (IMPORTANT):** SUPABASE_URL validation (added allowlist check to validate_test_environment)
6. **FIX #6 (CRITICAL):** Rate limit flushdb danger (use key prefix scoping, not flushdb)

**Change Note (v2.2 - February 2026):** Applied 7-fix consistency & robustness pack:
1. **FIX #1 (CRITICAL):** Integration template async inconsistency (made fully synchronous)
2. **FIX #2 (CRITICAL):** validate_test_environment() fragile (use ENVIRONMENT variable, not URL matching)
3. **FIX #3 (CRITICAL):** auth_headers_test contract incomplete (added middleware behavior documentation)
4. **FIX #4 (IMPORTANT):** Rate limit reset endpoint undefined (added implementation contract)
5. **FIX #5 (IMPORTANT):** Load test token crash risk (added explicit guard with clear error)
6. **FIX #6 (IMPORTANT):** Job status inconsistency (added canonical JobStatus enum)
7. **FIX #7 (MODERATE):** Coverage matrix reference drift (removed version number)

**Change Note (v2.1 - February 2026):** Applied 7-fix comprehensive update pack:
1. **FIX #1 (CRITICAL):** Auth strategy hybrid (Supabase tokens for integration/E2E, TEST_AUTH_OVERRIDE for unit/API)
2. **FIX #2 (CRITICAL):** Fixture design (removed global client, implemented real db_cleanup)
3. **FIX #3 (IMPORTANT):** CI safety guards (runtime validation, fail-fast for non-test environments)
4. **FIX #4 (IMPORTANT):** Async correctness (made helpers synchronous, removed misleading async declarations)
5. **FIX #5 (IMPORTANT):** Rate limiting determinism (user-based keys, test-only reset endpoint)
6. **FIX #6 (MODERATE):** UI helper robustness (null handle checks, transparent background resolution)
7. **FIX #7 (MODERATE):** Locust import path (moved token helper to app.testing, fixed packaging)

**Change Note (v2.0 - February 2026):** Applied 6-patch critical fix pack:
1. Standardized import paths to `app.*` everywhere (was `src.main`)
2. Added `tests/conftest.py` with auth fixtures and defined `generate_test_token()` helper
3. Fixed rate-limiting test to capture first 429 and isolate test users
4. Made integration helpers DB-agnostic (Supabase-compatible, not MongoDB)
5. Split helpers by language (Python: `tests/helpers/*.py`, TS: `tests/ui/helpers/*.ts`)
6. Added performance auth clarification (Supabase Auth integration documented)

---

## Template Contract (REQUIRED)

**All test templates MUST adhere to:**

### Required Environment Variables

#### Integration/E2E Tests (Full Environment)

```bash
# .env.test (full environment for integration/E2E tests)
ENVIRONMENT=test  # REQUIRED: Must be 'test' to run tests
DATABASE_URL=postgresql://user:pass@localhost:5432/chronosrefine_test
SUPABASE_URL=https://test-project.supabase.co
SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_ROLE_KEY=eyJ...  # For test user creation only (NEVER in staging/prod)
JWT_SECRET=test_secret_key_for_local_ci_only
TEST_AUTH_OVERRIDE=true  # Enables test auth bypass (local/CI only, NEVER in staging/prod)
```

#### Unit-Only Mode (Minimal Environment)

For running unit tests without Supabase:

```bash
# .env.test (minimal environment for unit-only mode)
ENVIRONMENT=test  # REQUIRED: Must be 'test' to run tests
SUPABASE_URL=http://localhost:54321  # REQUIRED but doesn't need to be real
TEST_AUTH_OVERRIDE=true  # REQUIRED for unit-only mode
# SUPABASE_SERVICE_ROLE_KEY not required - unit tests will skip Supabase-dependent fixtures
```

**Note:** Unit-only mode allows contributors to run unit tests without Supabase secrets. Tests using `test_user` or `auth_headers_supabase` will skip gracefully.

**Phase 1 Baseline Variable Mapping (Current Repo):**

- `DATABASE_URL = N/A` (not required for current Phase 1 baseline test runs)
- `SUPABASE_URL = SUPABASE_URL_DEV`
- `SUPABASE_ANON_KEY = SUPABASE_ANON_KEY_DEV`

### Required Fixtures (tests/conftest.py)
- `test_user`: Authenticated test user with seeded credentials
- `auth_headers_supabase`: Real Supabase access token (for integration/E2E tests)
- `auth_headers_test`: TEST_AUTH_OVERRIDE bypass (for unit/API tests)
- `client`: FastAPI TestClient with auth
- `db_cleanup`: Automatic cleanup after each test (with resource tracking)

### Canonical Import Root
**All imports MUST use `app.*` as the root package:**
```python
from app.main import app
from app.ml.era_detection import EraDetectionModel
from app.api.endpoints import upload
```

### Authentication Rules
- **MUST NOT stub auth** in production-like tests
- **Integration/E2E tests:** MUST use real Supabase tokens (`auth_headers_supabase`)
- **Unit/API tests:** MAY use TEST_AUTH_OVERRIDE bypass (`auth_headers_test`)
- **MUST use Supabase Auth** for test user creation (seeded test users)
- **MAY use TEST_AUTH_OVERRIDE** for local/CI only (never in staging/prod)

### Test File Header Contract (STRATEGIC GOVERNANCE)

**Every test file MUST begin with a traceability header:**

```python
"""
Maps to:
- FR-001 (Upload and Validation)
- NFR-012 (Usage Metering)
- AC-FR-001-01, AC-FR-001-02, AC-NFR-012-03
"""
```

**Rules:**
1. Header MUST be the first docstring in the file
2. Header MUST include at least one requirement ID (FR/NFR/ENG/DS/SEC/OPS)
3. Header SHOULD include specific AC IDs when testing acceptance criteria
4. Header format: `Maps to:` followed by bullet list of IDs

**Enforcement:**

CI pipeline MUST reject test files without traceability headers:

```python
#!/usr/bin/env python3
# scripts/validate_test_traceability.py
"""
Validate test file traceability headers (AST-based)

Ensures every test file has "Maps to:" in its module docstring with at least one requirement ID.
This prevents false passes from "Maps to:" appearing in comments or test bodies,
and ensures mechanical enforcement of actual requirement IDs (not just "TBD").
"""
import ast
import re
import sys
from pathlib import Path

def validate_file(filepath: Path) -> bool:
    """
    Check if file has "Maps to:" in module docstring with at least one requirement ID
    
    Returns:
        True if valid, False otherwise
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            tree = ast.parse(f.read(), filename=str(filepath))
        
        docstring = ast.get_docstring(tree)
        
        if docstring is None:
            print(f"❌ {filepath}: No module docstring")
            return False
        
        # Check for "Maps to:" section and requirement ID bullets (blank-line tolerant)
        # Strategy: find "Maps to:", then scan subsequent non-empty lines for a bullet
        maps_to_match = re.search(r'Maps to:\s*\n', docstring)
        
        if not maps_to_match:
            print(f"❌ {filepath}: Module docstring missing 'Maps to:' section")
            return False
        
        # Scan up to 8 non-empty lines after "Maps to:" for a requirement ID bullet
        # (blank-line tolerant: blank lines don't count toward the limit)
        req_id_bullet_pattern = r'^\s*-\s+(FR|NFR|ENG|DS|SEC|OPS)-\d+\b'
        after_maps_to = docstring[maps_to_match.end():]
        non_empty_lines_seen = 0
        found_bullet = False
        
        for line in after_maps_to.splitlines():
            if line.strip() == '':
                continue  # Skip blank lines (don't count toward limit)
            non_empty_lines_seen += 1
            if re.match(req_id_bullet_pattern, line):
                found_bullet = True
                break
            if non_empty_lines_seen >= 8:  # Stop after 8 non-empty lines
                break
        
        if not found_bullet:
            print(f"❌ {filepath}: Module docstring missing requirement ID bullet after 'Maps to:' (within 8 non-empty lines)")
            return False
        
        return True
    
    except SyntaxError as e:
        print(f"❌ {filepath}: Syntax error - {e}")
        return False
    except Exception as e:
        print(f"❌ {filepath}: Validation error - {e}")
        return False

def main():
    """Find all test files and validate traceability headers"""
    test_dir = Path("tests")
    
    if not test_dir.exists():
        print("❌ tests/ directory not found")
        sys.exit(1)
    
    # Find all test files
    test_files = list(test_dir.rglob("test_*.py")) + list(test_dir.rglob("*_test.py"))
    
    if not test_files:
        print("⚠️  No test files found")
        sys.exit(0)
    
    print(f"🔍 Validating {len(test_files)} test files...")
    
    invalid_files = []
    for filepath in test_files:
        if not validate_file(filepath):
            invalid_files.append(filepath)
    
    if not invalid_files:
        print(f"✅ All {len(test_files)} test files have valid traceability headers")
        sys.exit(0)
    else:
        print(f"\n❌ {len(invalid_files)} test file(s) missing traceability headers:")
        for filepath in invalid_files:
            print(f"   - {filepath}")
        sys.exit(1)

if __name__ == "__main__":
    main()
```

**Add to CI pipeline:**

```yaml
# .github/workflows/test.yml
- name: Validate test traceability
  run: python3 scripts/validate_test_traceability.py
```

**Why this matters:**

Your system assumes traceability between:
- Coverage Matrix
- Requirements (FR/NFR/ENG/DS/SEC/OPS)
- Test Templates

This header contract **mechanically enforces** that traceability loop. Without it, traceability depends on manual discipline.

### Test Isolation
- **MUST use unique user IDs** per test to avoid rate-limit cross-contamination
- **MUST clean up test data** after each test (use `db_cleanup` fixture)
- **MUST NOT share state** between tests
- **Rate limiting:** MUST key by user ID (not IP) for deterministic tests

### Placeholder Replacement
- **All placeholder tags (e.g., `{REQ}`, `{Feature}`) MUST be replaced before PR**
- Enforce with lint check: `grep -r "{REQ}" tests/` should return zero results

### Required Middleware Behavior (for TEST_AUTH_OVERRIDE)

**App auth middleware MUST implement TEST_AUTH_OVERRIDE bypass:**

```python
# app/api/middleware/auth.py
def verify_token(token: str):
    """
    Verify JWT token (supports TEST_AUTH_OVERRIDE)
    
    Args:
        token: Bearer token from Authorization header
    
    Returns:
        User dict with user_id, email
    
    Raises:
        HTTPException: If token is invalid
    """
    # Test-only bypass
    if os.getenv("TEST_AUTH_OVERRIDE") == "true":
        if token.startswith("test_"):
            user_id = token.replace("test_", "")
            return {"user_id": user_id, "email": f"test@example.com"}
    
    # Production: Verify Supabase JWT
    return verify_supabase_jwt(token)
```

**Without this middleware implementation, `auth_headers_test` fixture will not work.**

### Required Test-Only Endpoints

**App MUST implement test-only reset endpoint:**

```python
# app/api/endpoints/testing.py (only enabled if TEST_AUTH_OVERRIDE=true)
from fastapi import APIRouter, HTTPException
import os

router = APIRouter()

@router.post("/reset-rate-limits")
def reset_rate_limits():
    """
    Reset all rate limit buckets (test-only)
    
    SAFETY:
    - Only mounted in test mode (see router registration below)
    - Only deletes keys with chronosrefine:test:ratelimit: prefix
    - Never uses flushdb() (too dangerous - could wipe unrelated keys)
    
    Returns:
        Status dict with deleted key count
    
    Raises:
        HTTPException: If not in test environment
    """
    if os.getenv("TEST_AUTH_OVERRIDE") != "true":
        raise HTTPException(status_code=404, detail="Not found")
    
    # Delete only rate limit keys with test prefix (SAFE)
    pattern = "chronosrefine:test:ratelimit:*"
    cursor = 0
    deleted_count = 0
    
    while True:
        cursor, keys = redis_client.scan(cursor, match=pattern, count=100)
        if keys:
            redis_client.delete(*keys)
            deleted_count += len(keys)
        if cursor == 0:
            break
    
    return {
        "status": "reset",
        "deleted_keys": deleted_count,
        "pattern": pattern
    }

# REQUIRED: Only mount this endpoint in test mode
# app/api/router.py
def create_app():
    app = FastAPI()
    
    # Always mount core endpoints
    app.include_router(api_router, prefix="/v1")
    
    # Only mount testing endpoints in test mode
    if os.getenv("TEST_AUTH_OVERRIDE") == "true":
        from app.api.endpoints import testing
        app.include_router(testing.router, prefix="/v1/testing", tags=["testing"])
    
    return app
```

**Without this endpoint, rate limiting tests will be flaky.**

### **Canonical Job Statuses**

**All job status checks MUST use these canonical values:**

```python
# app/models/job.py
from enum import Enum

class JobStatus(str, Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
```

**Canonical Upload Statuses**

**All upload status checks MUST use these canonical values:**

```python
# app/models/upload.py
from enum import Enum

class UploadStatus(str, Enum):
    PENDING = "pending"
    UPLOADING = "uploading"
    COMPLETE = "complete"
    FAILED = "failed"
```

**Usage in tests:**
```python
from app.models.job import JobStatus

def wait_for_job_completion(job_id: str):
    ...
    if job["status"] in [JobStatus.COMPLETED, JobStatus.FAILED]:
        return job
```

**DO NOT use string literals** (`"complete"`, `"completed"`, etc.) as they will drift.

---

## Table of Contents

- [Test Configuration](#test-configuration)
- [API Test Templates](#api-test-templates)
- [ML/AI Test Templates](#mlai-test-templates)
- [UI Test Templates](#ui-test-templates)
- [Integration Test Templates](#integration-test-templates)
- [Performance Test Templates](#performance-test-templates)
- [Helper Functions](#helper-functions)

---

## Test Configuration

### tests/conftest.py

```python
# tests/conftest.py
"""
Shared pytest fixtures for all tests

Provides:
- test_user: Authenticated test user (integration/E2E only, skips in unit-only mode)
- auth_headers_supabase: Real Supabase access token (integration/E2E only, skips in unit-only mode)
- auth_headers_test: TEST_AUTH_OVERRIDE bypass (works in unit-only mode)
- client: FastAPI TestClient
- db_cleanup: Automatic cleanup with resource tracking

Required environment variables:
- ENVIRONMENT=test (always required)
- SUPABASE_URL (always required)
- SUPABASE_SERVICE_ROLE_KEY (required for integration/E2E; optional for unit-only mode with localhost + TEST_AUTH_OVERRIDE=true)
- TEST_AUTH_OVERRIDE=true (required for unit-only mode and auth_headers_test)
"""
import pytest
import os
import sys
import uuid
from datetime import datetime
from typing import Optional
from fastapi.testclient import TestClient
from supabase import create_client, Client
from app.main import app

# Runtime guards: fail fast if not a test environment
def validate_test_environment():
    """
    Validate that we're running in a test environment
    
    Checks:
    1. ENVIRONMENT must be 'test'
    2. SUPABASE_URL hostname must match allowlist (exact match or subdomain)
    
    Raises:
        SystemExit: If validation fails (fail-fast)
    """
    from urllib.parse import urlparse
    
    # Check 1: ENVIRONMENT variable
    env = os.getenv("ENVIRONMENT", "")
    if env != "test":
        print(f"❌ FATAL: ENVIRONMENT must be 'test', got: '{env}'")
        print("   Set ENVIRONMENT=test in .env.test to run tests")
        sys.exit(1)
    
    # Check 2: SUPABASE_URL allowlist (exact hostname matching)
    supabase_url = os.getenv("SUPABASE_URL", "")
    
    # Configurable allowlist (defaults provided)
    allowlist_str = os.getenv(
        "TEST_SUPABASE_URL_ALLOWLIST",
        "localhost,127.0.0.1,test-project.supabase.co"
    )
    allowed_hosts = [h.strip() for h in allowlist_str.split(",")]
    
    # Parse hostname from SUPABASE_URL
    parsed = urlparse(supabase_url)
    hostname = parsed.hostname or ""
    
    # Mark localhost for special handling (but don't return early)
    is_localhost = hostname in ["localhost", "127.0.0.1"]
    
    # Check against allowlist (exact match or endswith for subdomains)
    if not is_localhost and not any(hostname == h or hostname.endswith(f".{h}") for h in allowed_hosts):
        print(f"❌ FATAL: SUPABASE_URL hostname '{hostname}' not in allowlist")
        print(f"   Got: {supabase_url}")
        print(f"   Allowed hosts: {allowed_hosts}")
        print("   This prevents accidentally running tests against production")
        sys.exit(1)
    
    # Check 3: SUPABASE_SERVICE_ROLE_KEY guard (prevents accidental production key usage)
    service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    
    # Allow missing service role key for pure unit test workflows (localhost + TEST_AUTH_OVERRIDE)
    is_test_override = os.getenv("TEST_AUTH_OVERRIDE") == "true"
    
    if not service_role_key:
        if is_localhost and is_test_override:
            print("⚠️  WARNING: SUPABASE_SERVICE_ROLE_KEY missing (unit-only mode)")
            print("   Integration/E2E tests will fail without service role key")
        else:
            print("❌ FATAL: SUPABASE_SERVICE_ROLE_KEY required in test environment")
            print("   Set SUPABASE_SERVICE_ROLE_KEY in .env.test")
            sys.exit(1)
    
    # Check 4: Validate service role key JWT claims (defense-in-depth)
    if service_role_key:
        try:
            # Decode JWT payload without verification (just extract claims)
            import base64
            import json
            
            # JWT format: header.payload.signature
            parts = service_role_key.split('.')
            if len(parts) == 3:
                # Decode payload (add padding if needed)
                payload_b64 = parts[1]
                padding = 4 - (len(payload_b64) % 4)
                if padding != 4:
                    payload_b64 += '=' * padding
                
                payload = json.loads(base64.urlsafe_b64decode(payload_b64))
                
                # Check if role is service_role
                role = payload.get('role', '')
                if role != 'service_role':
                    print(f"⚠️  WARNING: JWT role is '{role}', expected 'service_role'")
                
                # Check if issuer matches SUPABASE_URL (hostname-based comparison)
                iss = payload.get('iss', '')
                if iss:
                    try:
                        iss_parsed = urlparse(iss)
                        url_parsed = urlparse(supabase_url)
                        
                        if iss_parsed.hostname != url_parsed.hostname:
                            print(f"⚠️  WARNING: JWT issuer hostname '{iss_parsed.hostname}' doesn't match SUPABASE_URL hostname '{url_parsed.hostname}'")
                            print("   Ensure service role key matches test environment")
                    except Exception:
                        # Fallback to substring check if URL parsing fails
                        if iss not in supabase_url:
                            print(f"⚠️  WARNING: JWT issuer '{iss}' doesn't match SUPABASE_URL '{supabase_url}'")
                            print("   Ensure service role key matches test environment")
        
        except Exception:
            # If JWT decode fails, fall back to substring check
            if "test" not in service_role_key.lower() and "test" not in supabase_url.lower():
                print("⚠️  WARNING: Service role key validation failed, ensure this is a test environment")
    
    # Final validation message
    if is_localhost:
        print("✅ Test environment validated (localhost)")
    else:
        print("✅ Test environment validated")

def pytest_configure(config):
    """
    Pytest hook: validate test environment before any test collection or execution.
    
    Using pytest_configure instead of module-level call avoids surprising:
    - IDE linting/type checking that imports test modules
    - `pytest --collect-only` in non-test shells
    - 'import conftest to reuse fixtures' patterns
    
    Still fails fast: runs before any test is collected or executed.
    """
    validate_test_environment()

# Supabase test client (conditional creation for unit-only mode support)
supabase: Optional[Client] = None

service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
if service_role_key:
    supabase = create_client(
        os.getenv("SUPABASE_URL"),
        service_role_key
    )
else:
    # Unit-only mode: skip Supabase client creation
    from urllib.parse import urlparse
    hostname = urlparse(os.getenv("SUPABASE_URL", "")).hostname or ""
    is_localhost = hostname in ["localhost", "127.0.0.1"]
    is_test_override = os.getenv("TEST_AUTH_OVERRIDE") == "true"
    if is_localhost and is_test_override:
        print("⚠️  Unit-only mode: Supabase client not created")
        print("   test_user and auth_headers_supabase fixtures will skip")

@pytest.fixture
def client():
    """FastAPI test client"""
    return TestClient(app)

@pytest.fixture
def test_user():
    """
    Create authenticated test user
    
    Skips in unit-only mode (when SUPABASE_SERVICE_ROLE_KEY is missing)
    
    Returns user with:
    - user_id: Unique test user ID
    - email: test_<timestamp>@example.com
    - password: test_password_123
    - tier: "pro" (for full feature access)
    """
    if supabase is None:
        pytest.skip("Supabase client not available (unit-only mode)")
    
    # Create unique test user to avoid rate-limit cross-contamination
    timestamp = datetime.utcnow().timestamp()
    email = f"test_{timestamp}@example.com"
    password = "test_password_123"
    
    # Create user via Supabase Auth
    user_response = supabase.auth.admin.create_user({
        "email": email,
        "password": password,
        "email_confirm": True
    })
    
    user_id = user_response.user.id
    
    # Insert user profile
    supabase.table("users").insert({
        "id": user_id,
        "email": email,
        "tier": "pro",
        "created_at": datetime.utcnow().isoformat()
    }).execute()
    
    yield {
        "user_id": user_id,
        "email": email,
        "password": password,
        "tier": "pro"
    }
    
    # Cleanup: delete user and associated data
    supabase.table("uploads").delete().eq("user_id", user_id).execute()
    supabase.table("jobs").delete().eq("user_id", user_id).execute()
    supabase.table("users").delete().eq("id", user_id).execute()
    supabase.auth.admin.delete_user(user_id)

@pytest.fixture
def auth_headers_supabase(test_user):
    """
    Generate real Supabase access token (for integration/E2E tests)
    
    Skips in unit-only mode (when SUPABASE_SERVICE_ROLE_KEY is missing)
    
    This fixture uses real Supabase Auth to generate tokens,
    ensuring auth logic is tested realistically.
    
    Use this for:
    - Integration tests
    - E2E tests
    - Tests that validate auth flows
    """
    if supabase is None:
        pytest.skip("Supabase client not available (unit-only mode)")
    
    # Sign in via Supabase Auth
    response = supabase.auth.sign_in_with_password({
        "email": test_user["email"],
        "password": test_user["password"]
    })
    
    access_token = response.session.access_token
    return {"Authorization": f"Bearer {access_token}"}

@pytest.fixture
def auth_headers_test():
    """
    Generate TEST_AUTH_OVERRIDE bypass token (for unit/API tests)
    
    Works in unit-only mode (doesn't require Supabase)
    
    This fixture bypasses auth entirely when TEST_AUTH_OVERRIDE=true,
    allowing fast unit tests without auth overhead.
    
    Use this for:
    - Unit tests
    - Fast API tests
    - Tests that don't validate auth logic
    
    IMPORTANT: This requires app auth middleware to check TEST_AUTH_OVERRIDE
    """
    if os.getenv("TEST_AUTH_OVERRIDE") != "true":
        raise ValueError("TEST_AUTH_OVERRIDE must be true to use auth_headers_test")
    
    # Always works, even in unit-only mode
    # Generate unique user ID for test isolation (uuid imported at module level)
    user_id = f"unit_test_{uuid.uuid4().hex[:8]}"
    
    # Return special test token that app middleware will recognize
    return {"Authorization": f"Bearer test_{user_id}"}

@pytest.fixture
def db_cleanup():
    """
    Automatic cleanup fixture with resource tracking
    
    In unit-only mode: skips Supabase cleanup, still resets rate limits
    
    Usage:
        def test_something(db_cleanup):
            # Track resources created in test
            db_cleanup("uploads", "upload_123")
            db_cleanup("jobs", "job_456")
            
            # Cleanup happens automatically after test
    """
    created_resources = []
    
    def track_resource(table: str, id: str):
        created_resources.append((table, id))
    
    yield track_resource
    
    # Cleanup all tracked resources (only if Supabase available)
    if supabase is not None:
        for table, id in created_resources:
            try:
                supabase.table(table).delete().eq("id", id).execute()
            except Exception as e:
                print(f"⚠️  Cleanup failed for {table}/{id}: {e}")
    
    # Always reset rate limits (works in unit-only mode too)
    # Uses TestClient(app) - same in-process mechanism as the `client` fixture
    # Auth header required: middleware enforces auth even for test-only endpoints
    if os.getenv("TEST_AUTH_OVERRIDE") == "true":
        try:
            _tc = TestClient(app)  # TestClient already imported at module level
            resp = _tc.post(
                "/v1/testing/reset-rate-limits",
                headers={"Authorization": "Bearer test_admin"}
            )
            if resp.status_code not in (200, 404):
                print(f"⚠️  Rate limit reset failed: {resp.status_code} {resp.text}")
        except Exception as e:
            print(f"⚠️  Rate limit reset failed: {e}")
```

### app/testing/auth_tokens.py

```python
# app/testing/auth_tokens.py
"""
Test auth token generation (for load tests and non-pytest contexts)

This module provides token generation for Locust and other
non-pytest contexts where conftest.py is not available.
"""
import os

def generate_test_token(user_id: str, tier: str = "free") -> str:
    """
    Generate test auth token for load testing
    
    Returns prefix token (test_{user_id}) for TEST_AUTH_OVERRIDE bypass.
    DO NOT use JWT - middleware bypass expects prefix tokens.
    
    Args:
        user_id: User ID for token (e.g., "loadtest_user_123")
        tier: User tier (unused, kept for API compatibility)
    
    Returns:
        Prefix token string (e.g., "test_loadtest_user_123")
    
    Raises:
        RuntimeError: If TEST_AUTH_OVERRIDE is not enabled
    """
    if os.getenv("TEST_AUTH_OVERRIDE") != "true":
        raise RuntimeError(
            "generate_test_token() requires TEST_AUTH_OVERRIDE=true. "
            "This function is for test environments only. "
            "Set TEST_AUTH_OVERRIDE=true in .env.test"
        )
    
    return f"test_{user_id}"
```

---

## API Test Templates

### Template: API Endpoint Test (pytest)

```python
# tests/api/test_{feature}.py
"""
Maps to:
- {REQUIREMENT_ID} ({Requirement Name})
- AC-{REQ}-01, AC-{REQ}-02
- DoD-{REQ}-01
"""
import pytest

class Test{Feature}API:
    """
    Tests for {REQUIREMENT_ID}: {Requirement Name}
    
    Validates:
    - AC-{REQ}-01: {Description}
    - AC-{REQ}-02: {Description}
    - DoD-{REQ}-01: {Description}
    """
    
    def test_successful_request(self, client, auth_headers_test):
        """
        Test successful API request
        Validates: AC-{REQ}-01
        """
        response = client.post(
            "/v1/endpoint",
            json={"param": "value"},
            headers=auth_headers_test
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "expected_field" in data
        assert data["expected_field"] == "expected_value"
    
    def test_invalid_request_returns_400(self, client, auth_headers_test):
        """
        Test invalid request returns 400 Bad Request
        Validates: AC-{REQ}-02
        """
        response = client.post(
            "/v1/endpoint",
            json={"invalid_param": "value"},
            headers=auth_headers_test
        )
        
        assert response.status_code == 400
        error = response.json()
        assert "error" in error
        assert "message" in error
    
    def test_unauthorized_request_returns_401(self, client):
        """
        Test unauthorized request returns 401
        Validates: DoD-{REQ}-01 (authentication required)
        """
        response = client.post(
            "/v1/endpoint",
            json={"param": "value"}
        )
        
        assert response.status_code == 401
    
    def test_rate_limiting(self, client, auth_headers_test):
        """
        Test rate limiting returns 429
        Validates: DoD-{REQ}-02 (rate limiting enforced)
        
        Works in unit-only mode (doesn't require Supabase)
        
        IMPORTANT: 
        - Uses unique user ID from auth_headers_test to avoid cross-test contamination
        - Rate limiter MUST key by user ID (not IP) for deterministic tests
        - Stops at first 429 for speed
        """
        # Reset rate limits before test (must include auth headers - middleware enforces auth even in test mode)
        client.post("/v1/testing/reset-rate-limits", headers=auth_headers_test)
        
        responses = []
        
        # Send requests until we hit rate limit
        for i in range(101):
            response = client.post(
                "/v1/endpoint",
                json={"param": f"value_{i}"},
                headers=auth_headers_test
            )
            responses.append(response)
            
            # Stop once first 429 is seen (faster + less flaky)
            if response.status_code == 429:
                break
        
        # Assert we got at least one 429 (rate limit exceeded)
        saw_429 = any(r.status_code == 429 for r in responses)
        assert saw_429, "Expected at least one 429 (rate limit exceeded) response"
        
        # Verify 429 response has correct error message
        first_429 = next(r for r in responses if r.status_code == 429)
        error = first_429.json()
        assert "rate limit exceeded" in error["message"].lower()
```

**Usage:** Copy this template and replace:
- `{Feature}` with feature name (e.g., `Upload`, `EraDetection`)
- `{REQUIREMENT_ID}` with requirement ID (e.g., `FR-001`)
- `{REQ}` with short requirement ID (e.g., `FR-001`)
- `/v1/endpoint` with actual endpoint path
- Test assertions with actual validation logic

**Note:** Use `auth_headers_test` for fast unit tests, `auth_headers_supabase` for integration tests.

---



---

### Template: Schema Validation Test

```python
# tests/api/test_schema_validation.py
import pytest
from jsonschema import validate, ValidationError
import json

class TestSchemaValidation:
    """
    Tests for ENG-001: JSON Schema Validation
    
    Validates:
    - AC-ENG-001-01: JSON Schema v2020-12 compliance
    - AC-ENG-001-02: All validation rules enforced
    - AC-ENG-001-05: User-friendly error messages
    """
    
    @pytest.fixture
    def schema(self):
        """Load JSON Schema"""
        with open("schemas/era_profile_v2020-12.json") as f:
            return json.load(f)
    
    @pytest.fixture
    def valid_payload(self):
        """Valid request payload"""
        return {
            "era_id": "1950s-1960s",
            "fidelity_tier": "restore",
            "capture_medium": "kodachrome",
            "grain_intensity": 0.50
        }
    
    def test_valid_payload_passes(self, schema, valid_payload):
        """
        Test valid payload passes validation
        Validates: AC-ENG-001-01
        """
        # Should not raise ValidationError
        validate(instance=valid_payload, schema=schema)
    
    def test_missing_required_field_fails(self, schema, valid_payload):
        """
        Test missing required field fails validation
        Validates: AC-ENG-001-02 (VR-001: Required fields)
        """
        del valid_payload["era_id"]
        
        with pytest.raises(ValidationError) as exc_info:
            validate(instance=valid_payload, schema=schema)
        
        assert "era_id" in str(exc_info.value)
    
    def test_invalid_enum_value_fails(self, schema, valid_payload):
        """
        Test invalid enum value fails validation
        Validates: AC-ENG-001-06 (Canonical enum definitions)
        """
        valid_payload["fidelity_tier"] = "invalid_tier"
        
        with pytest.raises(ValidationError) as exc_info:
            validate(instance=valid_payload, schema=schema)
        
        assert "fidelity_tier" in str(exc_info.value)
    
    @pytest.mark.parametrize("tier,max_hallucination", [
        ("conserve", 0.05),
        ("restore", 0.10),
        ("enhance", 0.20)
    ])
    def test_tier_specific_limits(self, schema, valid_payload, tier, max_hallucination):
        """
        Test tier-specific parameter limits
        Validates: AC-ENG-001-03 (Locked vs tunable matrix)
        """
        valid_payload["fidelity_tier"] = tier
        valid_payload["hallucination_limit"] = max_hallucination + 0.01
        
        with pytest.raises(ValidationError):
            validate(instance=valid_payload, schema=schema)
```

---

---

## ML/AI Test Templates

### Template: ML Model Test

```python
# tests/ml/test_{model}.py
import pytest
import numpy as np
import time
from app.ml.{model} import {ModelClass}

class Test{ModelName}:
    """
    Tests for {REQUIREMENT_ID}: {Model Name}
    
    Validates:
    - AC-{REQ}-01: Model accuracy
    - AC-{REQ}-02: Inference latency
    - DoD-{REQ}-01: Performance targets
    """
    
    @pytest.fixture
    def model(self):
        """Initialize model"""
        return {ModelClass}()
    
    @pytest.fixture
    def test_data(self):
        """Load test dataset"""
        return load_heritage_test_set()
    
    def test_model_accuracy(self, model, test_data):
        """
        Test model meets accuracy target
        Validates: AC-{REQ}-01, DoD-{REQ}-01
        """
        predictions = []
        ground_truth = []
        
        for sample in test_data:
            pred = model.predict(sample.input)
            predictions.append(pred)
            ground_truth.append(sample.label)
        
        accuracy = calculate_accuracy(predictions, ground_truth)
        
        # DoD-{REQ}-01: Accuracy >90%
        assert accuracy >= 0.90, f"Accuracy {accuracy:.2%} below 90% threshold"
    
    def test_inference_latency(self, model, test_data):
        """
        Test inference latency meets SLO
        Validates: AC-{REQ}-02, DoD-{REQ}-02
        """
        latencies = []
        
        for sample in test_data[:100]:  # Sample 100 items
            start_time = time.time()
            model.predict(sample.input)
            latency = time.time() - start_time
            latencies.append(latency)
        
        p95_latency = np.percentile(latencies, 95)
        
        # DoD-{REQ}-02: P95 latency <5s
        assert p95_latency < 5.0, f"P95 latency {p95_latency:.2f}s exceeds 5s threshold"
    
    def test_confidence_scoring(self, model, test_data):
        """
        Test confidence scores in valid range
        Validates: AC-{REQ}-03
        """
        for sample in test_data:
            result = model.predict_with_confidence(sample.input)
            
            assert 0.0 <= result.confidence <= 1.0, \
                f"Confidence {result.confidence} outside [0, 1] range"
```

---

---

## UI Test Templates

### Template: Component Test (Playwright)

```typescript
// tests/ui/test_{component}.spec.ts
import { test, expect } from '@playwright/test';
import { getColorContrast } from './helpers/a11y';

test.describe('{Component Name} - {REQUIREMENT_ID}', () => {
  /**
   * Tests for {REQUIREMENT_ID}: {Requirement Name}
   * 
   * Validates:
   * - AC-{REQ}-01: {Description}
   * - AC-{REQ}-02: {Description}
   * - DoD-{REQ}-01: {Description}
   */
  
  test.beforeEach(async ({ page }) => {
    // Navigate to component page
    await page.goto('/component-path');
    
    // Wait for component to load
    await page.waitForSelector('[data-testid="component-root"]');
  });
  
  test('renders correctly', async ({ page }) => {
    /**
     * Test component renders with expected elements
     * Validates: AC-{REQ}-01
     */
    const component = page.locator('[data-testid="component-root"]');
    await expect(component).toBeVisible();
    
    // Verify expected elements
    await expect(page.locator('[data-testid="element-1"]')).toBeVisible();
    await expect(page.locator('[data-testid="element-2"]')).toBeVisible();
  });
  
  test('handles user interaction', async ({ page }) => {
    /**
     * Test component responds to user interaction
     * Validates: AC-{REQ}-02
     */
    const button = page.locator('[data-testid="action-button"]');
    await button.click();
    
    // Verify expected outcome
    await expect(page.locator('[data-testid="result"]')).toHaveText('Expected Result');
  });
  
  test('displays error state', async ({ page }) => {
    /**
     * Test component displays error state correctly
     * Validates: AC-{REQ}-03
     */
    // Trigger error condition
    await page.locator('[data-testid="error-trigger"]').click();
    
    // Verify error message displayed
    const errorMessage = page.locator('[data-testid="error-message"]');
    await expect(errorMessage).toBeVisible();
    await expect(errorMessage).toContainText('Error');
  });
  
  test('meets accessibility requirements', async ({ page }) => {
    /**
     * Test component is accessible
     * Validates: DoD-{REQ}-01 (WCAG AA compliance)
     */
    // Check color contrast using TypeScript helper
    const element = page.locator('[data-testid="text-element"]');
    const contrast = await getColorContrast(page, element);
    expect(contrast).toBeGreaterThanOrEqual(4.5);
    
    // Check keyboard navigation
    await page.keyboard.press('Tab');
    const focusedElement = await page.evaluate(() => document.activeElement?.getAttribute('data-testid'));
    expect(focusedElement).toBe('first-focusable-element');
  });
});
```

---

---

## Integration Test Templates

### Template: End-to-End Workflow Test

```python
# tests/integration/test_{workflow}.py
"""
Maps to:
- FR-001 (Upload and Validation)
- FR-002 (Video Processing)
- ENG-003 (Video Processing Pipeline)
"""
import pytest
import os
from tests.helpers.db import create_test_user, cleanup_test_user
from tests.helpers.upload import upload_test_video
from tests.helpers.jobs import wait_for_job_completion

class Test{Workflow}Integration:
    """
    Integration tests for {workflow name}
    
    Validates complete user journey:
    - FR-001: Upload
    - FR-002: Era Detection
    - FR-003: Fidelity Selection
    - FR-004: Processing
    - FR-005: Download
    """
    
    @pytest.fixture
    def test_user(self):
        """Create test user via Supabase"""
        import uuid
        user = create_test_user(
            email=f"test_{uuid.uuid4().hex[:8]}@example.com",  # Unique per run
            tier="pro"
        )
        yield user
        cleanup_test_user(user["id"])
    
    def test_complete_workflow(self, test_user):
        """
        Test complete restoration workflow
        Validates: FR-001, FR-002, FR-003, FR-004, FR-005
        
        NOTE: This test is synchronous because all helpers are synchronous.
        If you need async, convert helpers to async first.
        """
        # Step 1: Upload video (FR-001)
        from app.models.upload import UploadStatus
        
        upload_response = upload_test_video(
            user_id=test_user["id"],
            video_path="tests/fixtures/sample_1950s.mp4"
        )
        assert upload_response["status"] == UploadStatus.COMPLETE.value
        upload_id = upload_response["upload_id"]
        
        # Step 2: Detect era (FR-002)
        era_response = detect_era(upload_id)
        assert era_response["era_id"] == "1950s-1960s"
        assert era_response["confidence"] >= 0.70
        
        # Step 3: Select fidelity tier (FR-003)
        fidelity_config = get_fidelity_config(
            tier="restore",
            duration_seconds=120
        )
        assert fidelity_config["estimated_cost_usd"] > 0
        
        # Step 4: Submit job (FR-004)
        from app.models.job import JobStatus
        
        job_response = create_job(
            upload_id=upload_id,
            era_id=era_response["era_id"],
            fidelity_tier="restore"
        )
        assert job_response["status"] == JobStatus.QUEUED.value
        job_id = job_response["job_id"]
        
        # Wait for processing to complete
        wait_for_job_completion(job_id, timeout_seconds=300)
        
        # Step 5: Download result (FR-005)
        export_response = export_job(job_id)
        assert export_response["download_url"].startswith("https://")
        assert export_response["file_size_bytes"] > 0
        
        # Verify output file exists and is valid
        output_path = download_file(export_response["download_url"])
        assert os.path.exists(output_path)
        assert get_video_duration(output_path) == 120  # Same duration as input
```

---

---



---

## Helper Functions

### tests/helpers/db.py

```python
# tests/helpers/db.py
"""
Database helpers for integration tests (Supabase-compatible)

IMPORTANT: All helpers are SYNCHRONOUS (not async)
IMPORTANT: Use only in integration/E2E tests (raises error in unit-only mode)
"""
from supabase import create_client, Client
from typing import Optional
import os
from datetime import datetime

# Supabase client for test helpers (conditional creation for unit-only mode support)
supabase: Optional[Client] = None

service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
if service_role_key:
    supabase = create_client(
        os.getenv("SUPABASE_URL"),
        service_role_key
    )

def create_test_user(email: str, tier: str = "free") -> dict:
    """
    Create test user via Supabase Auth
    
    Args:
        email: User email
        tier: User tier (free/pro/enterprise)
    
    Returns:
        dict with user_id, email, tier
    
    Raises:
        RuntimeError: If Supabase client not available (unit-only mode)
    """
    if supabase is None:
        raise RuntimeError("Supabase client not available (unit-only mode). Use this helper only in integration/E2E tests.")
    
    # Create user via Supabase Auth
    user_response = supabase.auth.admin.create_user({
        "email": email,
        "password": "test_password_123",
        "email_confirm": True
    })
    
    user_id = user_response.user.id
    
    # Insert user profile
    supabase.table("users").insert({
        "id": user_id,
        "email": email,
        "tier": tier,
        "created_at": datetime.utcnow().isoformat()
    }).execute()
    
    return {"id": user_id, "email": email, "tier": tier}

def cleanup_test_user(user_id: str):
    """
    Clean up test user and associated data
    
    Raises:
        RuntimeError: If Supabase client not available (unit-only mode)
    """
    if supabase is None:
        raise RuntimeError("Supabase client not available (unit-only mode). Use this helper only in integration/E2E tests.")
    
    supabase.table("uploads").delete().eq("user_id", user_id).execute()
    supabase.table("jobs").delete().eq("user_id", user_id).execute()
    supabase.table("users").delete().eq("id", user_id).execute()
    supabase.auth.admin.delete_user(user_id)

def insert_upload_row(user_id: str, filename: str, status: str = "pending") -> str:
    """
    Insert upload row and return upload_id
    
    Raises:
        RuntimeError: If Supabase client not available (unit-only mode)
    """
    if supabase is None:
        raise RuntimeError("Supabase client not available (unit-only mode). Use this helper only in integration/E2E tests.")
    
    result = supabase.table("uploads").insert({
        "user_id": user_id,
        "filename": filename,
        "status": status,
        "created_at": datetime.utcnow().isoformat()
    }).execute()
    
    return result.data[0]["id"]

def wait_for_job_completion(job_id: str, timeout_seconds: int = 60) -> dict:
    """
    Poll job status until completion or timeout
    
    NOTE: Consider moving this to tests/helpers/jobs.py for better organization.
    This is a job-specific helper, not a database helper.
    
    Args:
        job_id: Job ID to poll
        timeout_seconds: Max wait time
    
    Returns:
        Final job record
    
    Raises:
        TimeoutError: If job doesn't complete
        RuntimeError: If Supabase client not available (unit-only mode)
    """
    if supabase is None:
        raise RuntimeError("Supabase client not available (unit-only mode). Use this helper only in integration/E2E tests.")
    
    import time
    from app.models.job import JobStatus
    
    start_time = time.time()
    
    while True:
        result = supabase.table("jobs").select("*").eq("id", job_id).execute()
        job = result.data[0]
        
        # Use canonical JobStatus enum (DO NOT use string literals)
        if job["status"] in {JobStatus.COMPLETED.value, JobStatus.FAILED.value}:
            return job
        
        if time.time() - start_time > timeout_seconds:
            raise TimeoutError(f"Job {job_id} did not complete within {timeout_seconds}s")
        
        time.sleep(1)
```

---

### tests/ui/helpers/a11y.ts

```typescript
// tests/ui/helpers/a11y.ts
/**
 * Accessibility helpers for UI tests (Playwright)
 */
import { Page, Locator } from '@playwright/test';

/**
 * Calculate WCAG color contrast ratio
 * 
 * @param page Playwright page
 * @param element Element to check
 * @returns Contrast ratio (e.g., 4.5, 7.0)
 */
export async function getColorContrast(page: Page, element: Locator): Promise<number> {
  // Assert handle exists
  const handle = await element.elementHandle();
  if (!handle) {
    throw new Error("Element handle is null - element may not be visible");
  }
  
  const contrast = await page.evaluate((el) => {
    const computedStyle = window.getComputedStyle(el);
    let color = computedStyle.color;
    let backgroundColor = computedStyle.backgroundColor;
    
    // Handle transparent backgrounds (inherit from parent)
    if (backgroundColor === "rgba(0, 0, 0, 0)" || backgroundColor === "transparent") {
      let parent = el.parentElement;
      while (parent && (backgroundColor === "rgba(0, 0, 0, 0)" || backgroundColor === "transparent")) {
        backgroundColor = window.getComputedStyle(parent).backgroundColor;
        parent = parent.parentElement;
      }
      
      // Default to white if no background found
      if (backgroundColor === "rgba(0, 0, 0, 0)" || backgroundColor === "transparent") {
        backgroundColor = "rgb(255, 255, 255)";
      }
    }
    
    // Parse RGB values
    const parseRGB = (rgb: string): number[] => {
      const match = rgb.match(/\d+/g);
      return match ? match.map(Number) : [0, 0, 0];
    };
    
    const [r1, g1, b1] = parseRGB(color);
    const [r2, g2, b2] = parseRGB(backgroundColor);
    
    // Calculate relative luminance
    const getLuminance = (r: number, g: number, b: number): number => {
      const [rs, gs, bs] = [r, g, b].map(c => {
        c = c / 255;
        return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
      });
      return 0.2126 * rs + 0.7152 * gs + 0.0722 * bs;
    };
    
    const l1 = getLuminance(r1, g1, b1);
    const l2 = getLuminance(r2, g2, b2);
    
    const lighter = Math.max(l1, l2);
    const darker = Math.min(l1, l2);
    
    return (lighter + 0.05) / (darker + 0.05);
  }, handle);
  
  return contrast;
}

/**
 * Check ARIA labels on interactive elements
 * 
 * @param page Playwright page
 * @param selector Selector for interactive elements
 * @returns Array of elements missing ARIA labels
 */
export async function checkAriaLabels(page: Page, selector: string): Promise<string[]> {
  const missingLabels = await page.evaluate((sel) => {
    const elements = document.querySelectorAll(sel);
    const missing: string[] = [];
    
    elements.forEach((el, index) => {
      const hasLabel = 
        el.hasAttribute('aria-label') ||
        el.hasAttribute('aria-labelledby') ||
        el.textContent?.trim();
      
      if (!hasLabel) {
        missing.push(`${sel}[${index}]`);
      }
    });
    
    return missing;
  }, selector);
  
  return missingLabels;
}

/**
 * Check keyboard navigation support
 * 
 * @param page Playwright page
 * @param startElement Starting element
 * @param expectedStops Expected number of tab stops
 * @returns Array of focusable elements
 */
export async function checkKeyboardNav(
  page: Page,
  startElement: Locator,
  expectedStops: number
): Promise<string[]> {
  await startElement.focus();
  
  const focusedElements: string[] = [];
  
  for (let i = 0; i < expectedStops; i++) {
    await page.keyboard.press('Tab');
    
    const focusedSelector = await page.evaluate(() => {
      const el = document.activeElement;
      if (!el) return null;
      
      // Generate selector
      let selector = el.tagName.toLowerCase();
      if (el.id) selector += `#${el.id}`;
      if (el.className) selector += `.${el.className.split(' ').join('.')}`;
      
      return selector;
    });
    
    if (focusedSelector) {
      focusedElements.push(focusedSelector);
    }
  }
  
  return focusedElements;
}
```

---

## Performance Test Templates

### Template: Locust Load Test

```python
# tests/load/test_{feature}_performance.py
"""
Maps to:
- NFR-002 (API Response Time)
- NFR-004 (Scalability)

Load tests for {REQUIREMENT_ID}: {Requirement Name}

Validates:
- NFR-002: System handles expected load
- NFR-003: P95 latency < {threshold}ms
"""
from locust import HttpUser, task, between
from app.testing.auth_tokens import generate_test_token

class {Feature}LoadTest(HttpUser):
    """
    Load test for {feature} endpoints
    
    Simulates {N} concurrent users performing {action}
    """
    wait_time = between(1, 3)  # Wait 1-3 seconds between tasks
    
    def on_start(self):
        """
        Setup: Authenticate user
        
        Uses prefix token (test_{user_id}) for TEST_AUTH_OVERRIDE bypass
        """
        self.token = generate_test_token(user_id="loadtest_user_123")
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    @task(3)  # Weight: 3x more frequent than other tasks
    def {primary_task}(self):
        """Primary task: {description}"""
        response = self.client.post(
            "/v1/endpoint",
            json={"param": "value"},
            headers=self.headers,
            name="/v1/endpoint (primary)"
        )
        
        if response.status_code != 200:
            print(f"❌ Primary task failed: {response.status_code}")
    
    @task(1)
    def {secondary_task}(self):
        """Secondary task: {description}"""
        response = self.client.get(
            "/v1/status",
            headers=self.headers,
            name="/v1/status (secondary)"
        )
        
        if response.status_code != 200:
            print(f"❌ Secondary task failed: {response.status_code}")
```

**Usage:**
```bash
# Run load test
locust -f tests/load/test_{feature}_performance.py --host=http://localhost:8000

# Run headless with specific load
locust -f tests/load/test_{feature}_performance.py \
  --host=http://localhost:8000 \
  --users=100 \
  --spawn-rate=10 \
  --run-time=5m \
  --headless
```

**Note:** For realistic auth testing, use `/v1/auth/login` instead of pre-generated tokens (slower but more realistic).

---

## End of Test Templates v2.12

**Next Steps:**

### Backend Implementation (Required Before Phase 1)
1. ✅ Test Templates v2.12 is production-ready (FINAL with CLEAN GOVERNANCE) - all 71 enhancements applied
2. 🔄 Update `AGENTS.md` to enforce test templates as mandatory
3. 🔄 Add `scripts/validate_test_traceability.py` to CI pipeline (closes governance loop with AST validation)
4. 🔄 Define DoD rules ("no PR merged without mapped tests")
5. 🔄 Implement backend endpoints (test templates already wired):
   - **Test-only reset endpoint:**
     - Route: `@router.post("/reset-rate-limits")` in `app/api/endpoints/testing.py`
     - Mount: `app.include_router(testing.router, prefix="/v1/testing")`
     - Full path: `/v1/testing/reset-rate-limits`
     - Contract already specified in templates (prefix scoping, TEST_AUTH_OVERRIDE guard)
   - **App auth middleware:**
     - Support TEST_AUTH_OVERRIDE bypass (prefix token pattern)
     - Contract already specified in templates (see Template Contract section)
6. 🔄 Implement canonical enums:
   - `JobStatus` enum in `app/models/job.py` (contract already specified)
   - `UploadStatus` enum in `app/models/upload.py` (contract already specified)
7. 🚀 Ready for Phase 1 implementation with zero drift, zero footguns, and robust governance!
**Total Effort Applied (v2.0 → v2.12):** ~22 hours across 71 enhancements:

- **v2.0:** 6 critical fixes (2-3 hours)
- **v2.1:** 7 comprehensive fixes (4-5 hours)
- **v2.2:** 7 consistency/robustness fixes (3-4 hours)
- **v2.3:** 6 blocking fixes (3-4 hours)
- **v2.4:** 6 recommended edits (1 hour)
- **v2.5:** 4 drift prevention fixes (30 minutes)
- **v2.6:** 5 final drift/correctness fixes (45 minutes)
- **v2.7:** 4 governance enhancements (40 minutes) - **CLOSES GOVERNANCE LOOP**
- **v2.8:** 5 robust governance fixes (1 hour) - **ROBUST GOVERNANCE ENFORCEMENT**
- **v2.9:** 4 critical/important fixes (1.25 hours) - **WORKING UNIT-ONLY MODE**
- **v2.10:** 6 critical/governance fixes (1.25 hours) - **FULLY WORKING UNIT-ONLY MODE**
- **v2.11:** 5 critical/improvements (1 hour) - **TRULY WORKING UNIT-ONLY MODE**
- **v2.12:** 6 critical/improvements (45 minutes) - **CLEAN GOVERNANCE**


---

## Related Documents

- **[Engineering Requirements](./chronosrefine_engineering_requirements.md)** - Architecture, infrastructure, and implementation constraints
- **[Implementation Plan](./chronosrefine_implementation_plan.md)** - Phase sequencing, packet scope, and delivery gates
- **[Requirements Documents](./chronosrefine_functional_requirements.md)** - Full requirement specifications
- **[Coverage Matrix](./ChronosRefine Requirements Coverage Matrix.md)** - Requirement-to-test mapping

---

**Version History**

| Version | Date | Changes |
|---|---|---|
| 1.0 | Feb 10, 2026 | Initial test templates for all test categories |
| 2.0 | Feb 2026 | Applied 6-patch critical fix pack (import paths, auth, rate-limiting, DB, UI helpers, performance) |
| 2.1 | Feb 2026 | Applied 7-fix comprehensive update (auth strategy hybrid, fixture design, CI safety, async correctness, rate limiting determinism, UI robustness, Locust imports) |
| 2.2 | Feb 2026 | Applied 7-fix consistency/robustness pack (async removal, ENVIRONMENT validation, middleware contract, rate limit endpoint, load test guards, JobStatus enum, coverage matrix reference) |
| 2.3 | Feb 2026 | Applied 6-fix blocking pack (version drift, auth bypass mismatch, JobStatus string literals, email collision, SUPABASE_URL allowlist, rate limit flushdb danger) |
| 2.4 | Feb 2026 | Applied 6-edit recommended pack (endpoint path fix, Locust signature fix, version history completion, fix count consistency, configurable allowlist, helper organization note) |
| 2.5 | Feb 2026 | Applied 4-fix drift prevention pack (cumulative effort text, dead imports removal, UploadStatus enum, stable AI IDE prompt filename) |
| 2.6 | Feb 2026 | Applied 5-fix final drift/correctness pack (JobStatus enum in integration template, Next Steps wording, exact hostname matching, db_cleanup error handling, unused timedelta removal) |
| 2.7 | Feb 2026 | Applied 4-enhancement governance closure pack (Supabase service role guard, redundant imports cleanup, strictness note, Test File Header Contract - **CLOSES GOVERNANCE LOOP**) |
| 2.8 | Feb 2026 | Applied 5-fix robust governance pack (Locust double docstring fix, Python AST traceability validator, unit-only mode support, JWT validation defense-in-depth, Next Steps numbering fix - **ROBUST GOVERNANCE ENFORCEMENT**) |
| 2.9 | Feb 2026 | Applied 1 critical fix + 3 important improvements (Conditional Supabase client creation, fixtures skip gracefully, consistent validation logic, hostname-based JWT issuer comparison, require real requirement IDs - **WORKING UNIT-ONLY MODE**) |
| 2.10 | Feb 2026 | Applied 3 critical fixes + 3 governance improvements (Removed auth_headers_test dependency, guards Supabase operations in db_cleanup, conditional client creation in helpers/db.py, enforces bullet format in traceability validator, removed unused variable, clarified env var requirements - **FULLY WORKING UNIT-ONLY MODE**) |
| 2.11 | Feb 2026 | Applied 2 critical fixes + 3 improvements (Switched db_cleanup to TestClient(app), removed test_user dependency from rate-limit test, tighter traceability validator, version history ordering, env vars documentation - **TRULY WORKING UNIT-ONLY MODE**) |
| 2.12 | Feb 2026 | Applied 3 critical fixes + 3 improvements (`return Falsee` typo fix, rate-limit reset auth headers, pytest_configure hook, blank-line tolerant validator, conftest hygiene, unified reset semantics - **CLEAN GOVERNANCE**) |

---

**Usage Instructions:**

1. **Copy template** for your test type (API, ML, UI, Integration, Performance)
2. **Replace placeholders** ({Feature}, {REQUIREMENT_ID}, {REQ}, etc.)
3. **Customize assertions** based on specific acceptance criteria
4. **Add test data** fixtures as needed
5. **Run tests** with pytest, Playwright, or Locust

**AI IDE Prompt Example:**
```
@chronosrefine_test_templates.md Create tests for FR-001 (Video Upload) using the API test template. Include tests for all acceptance criteria (AC-FR-001-01 through AC-FR-001-05).
```

**NOTE:** The test templates file uses a stable name (`chronosrefine_test_templates.md`) without version suffix to avoid prompt drift. When updating test templates, replace the existing file rather than creating versioned copies.
