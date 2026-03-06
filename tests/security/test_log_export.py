"""Maps to: SEC-009"""

from app.services.security_service import supported_export_targets


def test_supported_log_export_targets_are_declared() -> None:
    targets = supported_export_targets()
    assert targets == ["cloud_logging", "cloudwatch", "splunk", "syslog"]
