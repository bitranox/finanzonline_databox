"""Tests for return code definitions.

Tests cover all known return codes, severity mappings, and
handling of unknown codes.
"""

from __future__ import annotations

import pytest

from finanzonline_databox.domain.return_codes import (
    ReturnCode,
    ReturnCodeInfo,
    Severity,
    get_return_code_info,
    is_retryable,
    is_success,
)

pytestmark = pytest.mark.os_agnostic


class TestSeverity:
    """Tests for Severity enum."""

    def test_severity_values(self) -> None:
        """Should have expected severity levels."""
        assert Severity.SUCCESS.value == "success"
        assert Severity.WARNING.value == "warning"
        assert Severity.ERROR.value == "error"
        assert Severity.CRITICAL.value == "critical"


class TestReturnCode:
    """Tests for ReturnCode enum."""

    def test_success_code(self) -> None:
        """Should have OK as 0."""
        assert ReturnCode.OK.value == 0

    def test_session_errors(self) -> None:
        """Should have negative session error codes."""
        assert ReturnCode.SESSION_INVALID.value == -1
        assert ReturnCode.SYSTEM_MAINTENANCE.value == -2
        assert ReturnCode.TECHNICAL_ERROR.value == -3

    def test_databox_specific_codes(self) -> None:
        """Should have databox-specific error codes."""
        assert ReturnCode.DATE_PARAMS_REQUIRED.value == -4
        assert ReturnCode.DATE_TOO_OLD.value == -5
        assert ReturnCode.DATE_RANGE_TOO_WIDE.value == -6


class TestReturnCodeInfo:
    """Tests for ReturnCodeInfo dataclass."""

    def test_create_info(self) -> None:
        """Should create return code info."""
        info = ReturnCodeInfo(code=0, meaning="Valid", severity=Severity.SUCCESS)
        assert info.code == 0
        assert info.meaning == "Valid"
        assert info.severity == Severity.SUCCESS
        assert info.retryable is False

    def test_retryable_default(self) -> None:
        """Should default retryable to False."""
        info = ReturnCodeInfo(code=1, meaning="Test", severity=Severity.ERROR)
        assert info.retryable is False

    def test_retryable_explicit(self) -> None:
        """Should accept explicit retryable."""
        info = ReturnCodeInfo(code=1, meaning="Test", severity=Severity.ERROR, retryable=True)
        assert info.retryable is True


class TestGetReturnCodeInfo:
    """Tests for get_return_code_info function."""

    def test_success(self) -> None:
        """Should return success info for code 0."""
        info = get_return_code_info(0)
        assert info.code == 0
        assert info.severity == Severity.SUCCESS
        assert info.retryable is False

    def test_session_invalid(self) -> None:
        """Should return error for session invalid."""
        info = get_return_code_info(-1)
        assert info.severity == Severity.ERROR
        assert "session" in info.meaning.lower() or "Session" in info.meaning

    def test_system_maintenance_retryable(self) -> None:
        """Should mark system maintenance as retryable."""
        info = get_return_code_info(-2)
        assert info.retryable is True
        assert "maintenance" in info.meaning.lower()

    def test_technical_error_retryable(self) -> None:
        """Should mark technical error as retryable."""
        info = get_return_code_info(-3)
        assert info.retryable is True
        assert "technical" in info.meaning.lower() or "Technical" in info.meaning

    def test_date_params_required(self) -> None:
        """Should return error for missing date params."""
        info = get_return_code_info(-4)
        assert info.severity == Severity.ERROR
        assert info.retryable is False
        assert "ts_zust" in info.meaning.lower()

    def test_date_too_old(self) -> None:
        """Should return error for date too old."""
        info = get_return_code_info(-5)
        assert info.severity == Severity.ERROR
        assert "31" in info.meaning  # 31 days

    def test_date_range_too_wide(self) -> None:
        """Should return error for date range too wide."""
        info = get_return_code_info(-6)
        assert info.severity == Severity.ERROR
        assert "7" in info.meaning  # 7 days

    def test_unknown_code(self) -> None:
        """Should return generic error for unknown codes."""
        info = get_return_code_info(9999)
        assert info.code == 9999
        assert "Unknown" in info.meaning or "unknown" in info.meaning
        assert info.severity == Severity.ERROR
        assert info.retryable is False

    @pytest.mark.parametrize(
        ("code", "expected_severity"),
        [
            (0, Severity.SUCCESS),
            (-1, Severity.ERROR),
            (-2, Severity.WARNING),
            (-3, Severity.ERROR),
            (-4, Severity.ERROR),
            (-5, Severity.ERROR),
            (-6, Severity.ERROR),
        ],
    )
    def test_severity_mappings(self, code: int, expected_severity: Severity) -> None:
        """Should map codes to correct severity."""
        info = get_return_code_info(code)
        assert info.severity == expected_severity

    @pytest.mark.parametrize(
        ("code", "expected_retryable"),
        [
            (0, False),
            (-1, False),
            (-2, True),
            (-3, True),
            (-4, False),
            (-5, False),
            (-6, False),
        ],
    )
    def test_retryable_mappings(self, code: int, expected_retryable: bool) -> None:
        """Should map codes to correct retryable status."""
        info = get_return_code_info(code)
        assert info.retryable == expected_retryable


class TestIsSuccess:
    """Tests for is_success function."""

    def test_success_true(self) -> None:
        """Should return True for code 0."""
        assert is_success(0) is True

    def test_success_false(self) -> None:
        """Should return False for non-zero codes."""
        assert is_success(-1) is False
        assert is_success(-2) is False
        assert is_success(-4) is False


class TestIsRetryable:
    """Tests for is_retryable function."""

    def test_retryable_true(self) -> None:
        """Should return True for retryable codes."""
        assert is_retryable(-2) is True  # System maintenance
        assert is_retryable(-3) is True  # Technical error

    def test_retryable_false(self) -> None:
        """Should return False for non-retryable codes."""
        assert is_retryable(0) is False
        assert is_retryable(-1) is False
        assert is_retryable(-4) is False
