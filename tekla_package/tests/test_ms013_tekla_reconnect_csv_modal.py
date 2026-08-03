"""Tests for ms-013: Tekla lazy reconnect + reliable modal on all failures."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# AC-001: load_parts_from_provider creates TeklaPartProvider when None
# ---------------------------------------------------------------------------


def test_lazy_provider_created_when_none():
    """When _part_provider is None, a TeklaPartProvider is created on first load."""
    from tekla_nest.presenters.nest_presenter import NestPresenter

    pres = NestPresenter()
    assert pres._part_provider is None

    fake_provider = MagicMock()
    fake_provider.get_parts.return_value = []
    fake_provider.project_name = ""

    with patch(
        "tekla_nest.providers.tekla_provider.TeklaPartProvider",
        return_value=fake_provider,
    ):
        pres.load_parts_from_provider()

    assert pres._part_provider is fake_provider


def test_lazy_provider_creation_failure_emits_csv_error_occurred():
    """If TeklaPartProvider() itself raises, csv_error_occurred must fire."""
    from tekla_nest.presenters.nest_presenter import NestPresenter

    pres = NestPresenter()
    csv_errors: list[tuple[str, str]] = []
    pres.csv_error_occurred.connect(lambda t, d: csv_errors.append((t, d)))

    with patch(
        "tekla_nest.providers.tekla_provider.TeklaPartProvider",
        side_effect=RuntimeError("pythonnet not installed"),
    ):
        pres.load_parts_from_provider()

    assert csv_errors, "csv_error_occurred not emitted when provider init fails"


# ---------------------------------------------------------------------------
# AC-002: get_parts() failure emits csv_error_occurred (modal)
# ---------------------------------------------------------------------------


def test_get_parts_failure_emits_csv_error_occurred():
    """RuntimeError from get_parts() must emit csv_error_occurred."""
    from tekla_nest.presenters.nest_presenter import NestPresenter

    pres = NestPresenter()
    csv_errors: list[tuple[str, str]] = []
    pres.csv_error_occurred.connect(lambda t, d: csv_errors.append((t, d)))

    fake_provider = MagicMock()
    fake_provider.get_parts.side_effect = RuntimeError(
        "Cannot connect to Tekla Structures. Ensure the application is running."
    )

    with patch(
        "tekla_nest.providers.tekla_provider.TeklaPartProvider",
        return_value=fake_provider,
    ):
        pres.load_parts_from_provider()

    assert csv_errors, "csv_error_occurred not emitted when get_parts fails"
    assert "Tekla" in csv_errors[0][0] or "tekla" in csv_errors[0][0].lower(), (
        f"Expected Tekla error title, got: {csv_errors[0][0]!r}"
    )


def test_get_parts_failure_with_existing_provider_emits_csv_error_occurred():
    """Same test when provider was already set (not lazily created)."""
    from tekla_nest.presenters.nest_presenter import NestPresenter
    from tekla_nest.providers.base_provider import PartProvider

    fake_provider = MagicMock(spec=PartProvider)
    fake_provider.get_parts.side_effect = RuntimeError("Model is not open.")

    pres = NestPresenter(part_provider=fake_provider)
    csv_errors: list[tuple[str, str]] = []
    pres.csv_error_occurred.connect(lambda t, d: csv_errors.append((t, d)))

    pres.load_parts_from_provider()

    assert csv_errors, "csv_error_occurred not emitted for pre-set provider failure"


# ---------------------------------------------------------------------------
# AC-005: second call succeeds after first failure (stateless retry)
# ---------------------------------------------------------------------------


def test_retry_succeeds_after_first_failure():
    """After a failed load, a second call with a working provider must succeed."""
    from tekla_nest.models import PartEntry
    from tekla_nest.presenters.nest_presenter import NestPresenter

    pres = NestPresenter()
    parts_received: list = []
    pres.parts_loaded.connect(lambda p: parts_received.extend(p))

    part = PartEntry(quantity=1, length=3000.0, reference="P1", profile="HEA240", material="S235JR")

    call_count = 0

    def _get_parts():
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise RuntimeError("Tekla not running")
        return [part]

    fake_provider = MagicMock()
    fake_provider.get_parts.side_effect = _get_parts
    fake_provider.project_name = ""

    with patch(
        "tekla_nest.providers.tekla_provider.TeklaPartProvider",
        return_value=fake_provider,
    ):
        pres.load_parts_from_provider()  # first call — fails
        pres.load_parts_from_provider()  # second call — succeeds

    assert parts_received, "Parts not loaded on second attempt"
    assert len(parts_received) == 1


# ---------------------------------------------------------------------------
# AC-004: startup notice emitted when find_tekla_bin returns None
# ---------------------------------------------------------------------------


def test_tekla_not_detected_notice_string_exists():
    """The i18n key status.tekla_not_detected must resolve to a non-empty string."""
    from tekla_common.i18n import tr

    msg = tr("status.tekla_not_detected")
    assert msg and "Tekla" in msg, f"Unexpected notice text: {msg!r}"


def test_tekla_load_title_string_exists():
    """The i18n key errors.tekla_load_title must resolve to a non-empty string."""
    from tekla_common.i18n import tr

    msg = tr("errors.tekla_load_title")
    assert msg and len(msg) > 3, f"Unexpected title text: {msg!r}"


# ---------------------------------------------------------------------------
# Regression: CSV errors still emit csv_error_occurred (guard from ms-012)
# ---------------------------------------------------------------------------


def test_csv_error_still_emits_for_parts(monkeypatch):
    """CsvError during parts CSV load still emits csv_error_occurred (ms-012 guard)."""
    from tekla_nest.presenters.nest_presenter import NestPresenter
    from tekla_nest.services.csv_loader import CsvError

    pres = NestPresenter()
    csv_errors: list = []
    pres.csv_error_occurred.connect(lambda t, d: csv_errors.append((t, d)))

    with patch(
        "tekla_nest.presenters.nest_presenter.load_parts_csv", side_effect=CsvError("bad header")
    ):
        pres.load_parts_from_csv("/fake/path.csv")

    assert csv_errors
