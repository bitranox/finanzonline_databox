"""Tests for _datetime_utils module."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from finanzonline_databox._datetime_utils import (
    format_iso_datetime,
    format_local_time,
    parse_iso_datetime,
)

pytestmark = pytest.mark.os_agnostic


class TestParseIsoDatetime:
    """Tests for parse_iso_datetime function."""

    def test_parses_z_suffix(self) -> None:
        """Parses ISO datetime with Z suffix."""
        result = parse_iso_datetime("2025-01-15T10:30:00Z")
        assert result.year == 2025
        assert result.month == 1
        assert result.day == 15
        assert result.hour == 10
        assert result.minute == 30
        assert result.second == 0
        assert result.tzinfo == timezone.utc

    def test_parses_offset(self) -> None:
        """Parses ISO datetime with timezone offset."""
        result = parse_iso_datetime("2025-01-15T10:30:00+00:00")
        assert result.tzinfo == timezone.utc

    def test_returns_timezone_aware(self) -> None:
        """Result is always timezone aware."""
        result = parse_iso_datetime("2025-06-15T14:00:00Z")
        assert result.tzinfo is not None


class TestFormatIsoDatetime:
    """Tests for format_iso_datetime function."""

    def test_formats_utc_with_offset(self) -> None:
        """UTC times get +00:00 offset."""
        dt = datetime(2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        result = format_iso_datetime(dt)
        assert result == "2025-01-15T10:30:00+00:00"

    def test_formats_naive_as_local(self) -> None:
        """Naive datetimes use local timezone."""
        dt = datetime(2025, 1, 15, 10, 30, 0)
        result = format_iso_datetime(dt)
        # Should have timezone offset (e.g., +01:00, -05:00)
        assert "+" in result or result.count("-") > 2

    def test_includes_microseconds(self) -> None:
        """Microseconds are preserved in output."""
        dt = datetime(2025, 1, 15, 10, 30, 0, 123456, tzinfo=timezone.utc)
        result = format_iso_datetime(dt)
        assert "123456" in result


class TestFormatLocalTime:
    """Tests for format_local_time function."""

    def test_formats_correctly(self) -> None:
        """Output matches expected format."""
        dt = datetime(2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        result = format_local_time(dt)
        # Format should be YYYY-MM-DD HH:MM:SS
        assert len(result) == 19
        assert result[4] == "-"
        assert result[7] == "-"
        assert result[10] == " "
        assert result[13] == ":"
        assert result[16] == ":"

    def test_converts_to_local(self) -> None:
        """UTC time is converted to local timezone."""
        dt = datetime(2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        result = format_local_time(dt)
        # Result should be a valid datetime string
        datetime.strptime(result, "%Y-%m-%d %H:%M:%S")
