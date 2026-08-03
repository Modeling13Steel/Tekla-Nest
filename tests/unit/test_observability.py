from __future__ import annotations

from tekla_nest.observability import redact, redacted_fields


def test_redact_removes_machine_ids_and_license_keys():
    text = (
        "machine_id=0123456789abcdef0123456789abcdef "
        "license_key=12345678-1234-1234-1234-123456789abc"
    )

    redacted = redact(text)

    assert "0123456789abcdef" not in redacted
    assert "12345678-1234" not in redacted
    assert "[REDACTED]" in redacted


def test_redacted_fields_stringifies_and_redacts_values():
    result = redacted_fields({"machine": "abcdefabcdefabcdefabcdefabcdefabcdef"})

    assert result["machine"] == "[REDACTED]"
