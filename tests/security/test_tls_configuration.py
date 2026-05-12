"""
Maps to:
- SEC-002
"""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SECURITY_SPEC = ROOT / "docs/specs/chronosrefine_security_operations_requirements.md"
PACKET_NOTE = ROOT / "docs/specs/chronosrefine_phase5_packet5i_implementation_note.md"

REQUIRED_HSTS_MAX_AGE_SECONDS = 31_536_000


def _hsts_header_is_sec002_compliant(header_value: str) -> bool:
    directives = {
        part.strip().lower()
        for part in header_value.split(";")
        if part.strip()
    }
    return {
        f"max-age={REQUIRED_HSTS_MAX_AGE_SECONDS}",
        "includesubdomains",
        "preload",
    }.issubset(directives)


def test_hsts_contract_requires_one_year_max_age() -> None:
    spec = SECURITY_SPEC.read_text()
    note = PACKET_NOTE.read_text()

    assert "HSTS" in spec
    assert "1-year max-age = 31536000 seconds" in spec
    assert "includeSubDomains" in note
    assert "preload" in note
    assert _hsts_header_is_sec002_compliant("max-age=31536000; includeSubDomains; preload")
    assert not _hsts_header_is_sec002_compliant("max-age=31536000; preload")
    assert not _hsts_header_is_sec002_compliant("max-age=86400; includeSubDomains; preload")


def test_certificate_auto_renewal_remains_hosted_evidence_gate() -> None:
    spec = SECURITY_SPEC.read_text()
    note = PACKET_NOTE.read_text()

    assert "TLS certificate auto-renewal tested with **10+ scenarios**" in spec
    assert "certificate auto-renewal scenarios" in note
    assert "does not claim certificate-renewal closeout" in note


def test_sec002_global_closeout_requires_external_cryptographic_audit() -> None:
    spec = SECURITY_SPEC.read_text()
    note = PACKET_NOTE.read_text()

    assert "cryptographic audit by certified auditor" in spec
    assert "zero critical/high vulnerabilities" in spec
    assert "external cryptographic audit" in note.lower()
    assert "SEC-002 remains open" in note
