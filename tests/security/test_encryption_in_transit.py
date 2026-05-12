"""
Maps to:
- SEC-002
"""

from __future__ import annotations

from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
SECURITY_SPEC = ROOT / "docs/specs/chronosrefine_security_operations_requirements.md"
PACKET_NOTE = ROOT / "docs/specs/chronosrefine_phase5_packet5i_implementation_note.md"

REQUIRED_TLS_VERSION = "TLS 1.3"
REQUIRED_TLS13_CIPHERS = (
    "TLS_AES_128_GCM_SHA256",
    "TLS_AES_256_GCM_SHA384",
    "TLS_CHACHA20_POLY1305_SHA256",
)
DEPRECATED_TLS_VERSIONS = ("TLS 1.0", "TLS 1.1")


@pytest.mark.parametrize("cipher_suite", REQUIRED_TLS13_CIPHERS)
def test_sec002_spec_lists_required_tls13_cipher_suites(cipher_suite: str) -> None:
    spec = SECURITY_SPEC.read_text()
    note = PACKET_NOTE.read_text()

    assert REQUIRED_TLS_VERSION in spec
    assert cipher_suite in spec
    assert "edge or certificate-terminating platform" in note


@pytest.mark.parametrize("version", DEPRECATED_TLS_VERSIONS)
def test_deprecated_tls_rejection_remains_hosted_runtime_evidence(version: str) -> None:
    spec = SECURITY_SPEC.read_text()
    note = PACKET_NOTE.read_text()

    assert "TLS 1.0/1.1" in spec
    assert version in note
    assert "TLS 1.0/1.1 rejection evidence" in note
    assert "does not emulate live protocol negotiation" in note


def test_tls13_closeout_requires_hosted_ssl_labs_and_runtime_evidence() -> None:
    spec = SECURITY_SPEC.read_text()
    note = PACKET_NOTE.read_text()

    assert "SSL Labs A+ rating" in spec
    assert "score \u226595/100" in spec
    assert "<50ms TLS handshake time" in spec
    assert "SSL Labs A+ scan" in note
    assert "TLS 1.0/1.1 rejection evidence" in note
    assert "TLS handshake p95 evidence" in note
