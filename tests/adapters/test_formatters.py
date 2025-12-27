"""Behavioral tests for output formatters."""

from __future__ import annotations

import json
from datetime import date, datetime, timezone

import pytest

from finanzonline_databox.adapters.output.formatters import (
    format_entries_human,
    format_entries_json,
    format_list_result_human,
    format_list_result_json,
    format_sync_result_human,
    format_sync_result_json,
)
from finanzonline_databox.application.use_cases import SyncResult
from finanzonline_databox.domain.models import DataboxEntry, DataboxListResult, FileType, ReadStatus

pytestmark = pytest.mark.os_agnostic


def _make_entry(
    *,
    applkey: str = "abc123def456",
    erltyp: str = "B",
    status: ReadStatus = ReadStatus.UNREAD,
    filebez: str = "Test document",
    anbringen: str = "E1",
) -> DataboxEntry:
    """Create a test DataboxEntry."""
    return DataboxEntry(
        stnr="12-345/6789",
        name="Test Company",
        anbringen=anbringen,
        zrvon="2024",
        zrbis="2024",
        datbesch=date(2024, 1, 15),
        erltyp=erltyp,
        fileart=FileType.PDF,
        ts_zust=datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc),
        applkey=applkey,
        filebez=filebez,
        status=status,
    )


class TestFormatEntriesHuman:
    """Behavioral tests for human-readable entry formatting."""

    def test_empty_list_shows_no_entries_message(self) -> None:
        """When no entries exist, shows 'no entries' message."""
        result = format_entries_human([])
        assert "No entries" in result or "Keine Einträge" in result

    def test_single_entry_shows_header_and_entry(self) -> None:
        """Single entry shows header with count and the entry."""
        entry = _make_entry()
        result = format_entries_human([entry])

        assert "DataBox" in result
        assert "Total:" in result or "Gesamt:" in result
        assert "1" in result
        assert "E1" in result
        assert "2024-01-15" in result

    def test_unread_entry_shows_new_status(self) -> None:
        """Unread entries (status='') show NEW marker."""
        entry = _make_entry(status=ReadStatus.UNREAD)
        result = format_entries_human([entry])
        assert "NEW" in result or "NEU" in result

    def test_read_entry_shows_read_status(self) -> None:
        """Read entries (status='1') show read marker."""
        entry = _make_entry(status=ReadStatus.READ)
        result = format_entries_human([entry])
        assert "read" in result.lower() or "gelesen" in result.lower()

    def test_multiple_entries_shows_correct_count(self) -> None:
        """Multiple entries show correct total count."""
        entries = [
            _make_entry(applkey="key1"),
            _make_entry(applkey="key2"),
            _make_entry(applkey="key3"),
        ]
        result = format_entries_human(entries)
        assert "3" in result

    def test_unread_count_is_displayed(self) -> None:
        """Shows count of unread entries."""
        entries = [
            _make_entry(applkey="key1", status=ReadStatus.UNREAD),  # unread
            _make_entry(applkey="key2", status=ReadStatus.READ),  # read
            _make_entry(applkey="key3", status=ReadStatus.UNREAD),  # unread
        ]
        result = format_entries_human(entries)
        assert "2" in result  # 2 unread
        assert "unread" in result.lower() or "ungelesen" in result.lower()

    def test_entry_type_is_displayed(self) -> None:
        """Entry type (erltyp) is shown."""
        entry = _make_entry(erltyp="M")
        result = format_entries_human([entry])
        assert "M" in result

    def test_description_is_truncated(self) -> None:
        """Long descriptions are truncated to 40 chars."""
        long_desc = "A" * 100
        entry = _make_entry(filebez=long_desc)
        result = format_entries_human([entry])
        # Should not contain full 100 chars
        assert "A" * 100 not in result
        # But should contain truncated version
        assert "A" * 40 in result


class TestFormatEntriesJson:
    """Behavioral tests for JSON entry formatting."""

    def test_empty_list_returns_valid_json(self) -> None:
        """Empty list returns valid JSON with zero count."""
        result = format_entries_json([])
        data = json.loads(result)
        assert data["count"] == 0
        assert data["entries"] == []

    def test_single_entry_includes_all_fields(self) -> None:
        """Single entry JSON contains all expected fields."""
        entry = _make_entry()
        result = format_entries_json([entry])
        data = json.loads(result)

        assert data["count"] == 1
        assert len(data["entries"]) == 1

        e = data["entries"][0]
        assert e["stnr"] == "12-345/6789"
        assert e["name"] == "Test Company"
        assert e["anbringen"] == "E1"
        assert e["erltyp"] == "B"
        assert e["fileart"] == "PDF"
        assert e["applkey"] == "abc123def456"
        assert e["is_unread"] is True
        assert "suggested_filename" in e

    def test_read_entry_has_is_unread_false(self) -> None:
        """Read entry has is_unread=false."""
        entry = _make_entry(status=ReadStatus.READ)
        result = format_entries_json([entry])
        data = json.loads(result)
        assert data["entries"][0]["is_unread"] is False

    def test_dates_are_iso_formatted(self) -> None:
        """Dates are in ISO format."""
        entry = _make_entry()
        result = format_entries_json([entry])
        data = json.loads(result)

        assert data["entries"][0]["datbesch"] == "2024-01-15"
        assert "2024-01-15" in data["entries"][0]["ts_zust"]

    def test_multiple_entries_count_matches(self) -> None:
        """Count matches number of entries."""
        entries = [_make_entry(applkey=f"key{i}") for i in range(5)]
        result = format_entries_json(entries)
        data = json.loads(result)
        assert data["count"] == 5
        assert len(data["entries"]) == 5


class TestFormatListResultHuman:
    """Behavioral tests for list result human formatting."""

    def test_error_result_shows_error_message(self) -> None:
        """Error result shows error code and message."""
        result = DataboxListResult(rc=-1, msg="Session expired", entries=())
        output = format_list_result_human(result)
        assert "Error" in output or "Fehler" in output
        assert "Session expired" in output
        assert "-1" in output

    def test_success_result_shows_entries(self) -> None:
        """Success result shows formatted entries."""
        entry = _make_entry()
        result = DataboxListResult(rc=0, msg="OK", entries=(entry,))
        output = format_list_result_human(result)
        assert "DataBox" in output
        assert "E1" in result.entries[0].anbringen


class TestFormatListResultJson:
    """Behavioral tests for list result JSON formatting."""

    def test_error_result_returns_failure_json(self) -> None:
        """Error result returns JSON with success=false."""
        result = DataboxListResult(rc=-2, msg="Maintenance", entries=())
        output = format_list_result_json(result)
        data = json.loads(output)

        assert data["success"] is False
        assert data["rc"] == -2
        assert data["msg"] == "Maintenance"
        assert data["entries"] == []
        assert data["count"] == 0

    def test_success_result_returns_full_json(self) -> None:
        """Success result returns JSON with all data."""
        entries = (
            _make_entry(applkey="key1", status=ReadStatus.UNREAD),
            _make_entry(applkey="key2", status=ReadStatus.READ),
        )
        result = DataboxListResult(rc=0, msg="OK", entries=entries)
        output = format_list_result_json(result)
        data = json.loads(output)

        assert data["success"] is True
        assert data["rc"] == 0
        assert data["count"] == 2
        assert data["unread_count"] == 1
        assert len(data["entries"]) == 2
        assert "timestamp" in data


class TestFormatSyncResultHuman:
    """Behavioral tests for sync result human formatting."""

    def test_success_shows_success_status(self) -> None:
        """Successful sync shows SUCCESS status."""
        result = SyncResult(
            total_listed=5,
            downloaded=3,
            skipped=2,
            failed=0,
            total_bytes=1024,
        )
        output = format_sync_result_human(result, "/tmp/output")
        assert "SUCCESS" in output or "ERFOLG" in output

    def test_failure_shows_warning_status(self) -> None:
        """Sync with failures shows warning."""
        result = SyncResult(
            total_listed=5,
            downloaded=2,
            skipped=1,
            failed=2,
            total_bytes=512,
        )
        output = format_sync_result_human(result, "/tmp/output")
        assert "WARNING" in output or "WARNUNG" in output

    def test_shows_statistics(self) -> None:
        """Shows all statistics."""
        result = SyncResult(
            total_listed=10,
            downloaded=5,
            skipped=3,
            failed=2,
            total_bytes=2048,
        )
        output = format_sync_result_human(result, "/tmp/output")

        assert "10" in output  # total_listed
        assert "5" in output  # downloaded
        assert "3" in output  # skipped
        assert "2" in output  # failed
        assert "2.0 KB" in output or "2,0 KB" in output  # bytes formatted

    def test_shows_output_directory(self) -> None:
        """Shows output directory path."""
        result = SyncResult(0, 0, 0, 0, 0)
        output = format_sync_result_human(result, "/path/to/downloads")
        assert "/path/to/downloads" in output

    def test_new_downloads_shows_message(self) -> None:
        """When new downloads exist, shows info message."""
        result = SyncResult(
            total_listed=1,
            downloaded=1,
            skipped=0,
            failed=0,
            total_bytes=100,
        )
        output = format_sync_result_human(result, "/tmp")
        assert "downloaded" in output.lower() or "heruntergeladen" in output.lower()


class TestFormatSyncResultJson:
    """Behavioral tests for sync result JSON formatting."""

    def test_returns_valid_json(self) -> None:
        """Returns valid parseable JSON."""
        result = SyncResult(10, 5, 3, 2, 1024)
        output = format_sync_result_json(result, "/tmp/out")
        data = json.loads(output)  # Should not raise
        assert isinstance(data, dict)

    def test_includes_all_fields(self) -> None:
        """JSON includes all required fields."""
        result = SyncResult(
            total_listed=10,
            downloaded=5,
            skipped=3,
            failed=2,
            total_bytes=2048,
        )
        output = format_sync_result_json(result, "/tmp/out")
        data = json.loads(output)

        assert data["success"] is False  # failed > 0
        assert data["output_dir"] == "/tmp/out"
        assert data["total_listed"] == 10
        assert data["downloaded"] == 5
        assert data["skipped"] == 3
        assert data["failed"] == 2
        assert data["total_bytes"] == 2048
        assert data["has_new_downloads"] is True

    def test_success_true_when_no_failures(self) -> None:
        """success=true when failed=0."""
        result = SyncResult(5, 5, 0, 0, 1000)
        output = format_sync_result_json(result, "/tmp")
        data = json.loads(output)
        assert data["success"] is True

    def test_has_new_downloads_false_when_none(self) -> None:
        """has_new_downloads=false when downloaded=0."""
        result = SyncResult(5, 0, 5, 0, 0)
        output = format_sync_result_json(result, "/tmp")
        data = json.loads(output)
        assert data["has_new_downloads"] is False
