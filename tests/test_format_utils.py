"""Tests for _format_utils module."""

from __future__ import annotations

import pytest

from finanzonline_databox._format_utils import format_bytes

pytestmark = pytest.mark.os_agnostic


class TestFormatBytes:
    """Tests for format_bytes function."""

    def test_bytes_under_one_kb(self) -> None:
        """Values under 1024 show as bytes."""
        assert format_bytes(0) == "0 B"
        assert format_bytes(1) == "1 B"
        assert format_bytes(500) == "500 B"
        assert format_bytes(1023) == "1023 B"

    def test_kilobytes(self) -> None:
        """Values 1KB to 1MB show as KB."""
        assert format_bytes(1024) == "1.0 KB"
        assert format_bytes(1536) == "1.5 KB"
        assert format_bytes(10240) == "10.0 KB"
        assert format_bytes(1024 * 1024 - 1) == "1024.0 KB"

    def test_megabytes(self) -> None:
        """Values 1MB and above show as MB."""
        assert format_bytes(1024 * 1024) == "1.0 MB"
        assert format_bytes(2621440) == "2.5 MB"
        assert format_bytes(10 * 1024 * 1024) == "10.0 MB"
        assert format_bytes(100 * 1024 * 1024) == "100.0 MB"

    def test_precision(self) -> None:
        """Decimal precision is one digit."""
        assert format_bytes(1500) == "1.5 KB"
        assert format_bytes(1550) == "1.5 KB"  # Rounds down
        assert format_bytes(1600) == "1.6 KB"
