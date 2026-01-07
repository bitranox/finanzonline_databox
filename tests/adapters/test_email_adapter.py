"""Behavioral tests for email notification adapter."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from finanzonline_databox.adapters.notification.email_adapter import (
    EmailNotificationAdapter,
    format_error_html,
    format_error_plain,
    format_sync_result_html,
    format_sync_result_plain,
)
from finanzonline_databox.application.use_cases import SyncResult
from finanzonline_databox.domain.models import Diagnostics
from finanzonline_databox.enums import EmailFormat
from finanzonline_databox.mail import EmailConfig

pytestmark = pytest.mark.os_agnostic


def _make_email_config() -> EmailConfig:
    """Create test email config."""
    return EmailConfig(
        smtp_hosts=["smtp.test.com:587"],
        from_address="test@example.com",
    )


def _make_sync_result(
    *,
    downloaded: int = 5,
    skipped: int = 2,
    failed: int = 0,
    total_bytes: int = 1024,
    unread_listed: int | None = None,
    total_retrieved: int | None = None,
) -> SyncResult:
    """Create test sync result."""
    total_listed = downloaded + skipped + failed
    return SyncResult(
        total_retrieved=total_retrieved if total_retrieved is not None else total_listed,
        total_listed=total_listed,
        unread_listed=unread_listed if unread_listed is not None else downloaded,
        downloaded=downloaded,
        skipped=skipped,
        failed=failed,
        total_bytes=total_bytes,
    )


class TestFormatSyncResultPlain:
    """Behavioral tests for plain text sync result formatting."""

    def test_includes_status_success(self) -> None:
        """Success sync shows SUCCESS status."""
        result = _make_sync_result(failed=0)
        output = format_sync_result_plain(result, "/tmp/output")
        assert "SUCCESS" in output or "ERFOLG" in output

    def test_includes_status_error(self) -> None:
        """Failed sync shows error status."""
        result = _make_sync_result(failed=2)
        output = format_sync_result_plain(result, "/tmp/output")
        assert "ERROR" in output or "FEHLER" in output or "WARNING" in output

    def test_includes_output_directory(self) -> None:
        """Shows output directory path."""
        result = _make_sync_result()
        output = format_sync_result_plain(result, "/path/to/docs")
        assert "/path/to/docs" in output

    def test_includes_statistics(self) -> None:
        """Shows all statistics."""
        result = _make_sync_result(downloaded=10, skipped=3, failed=1, total_bytes=2048)
        output = format_sync_result_plain(result, "/tmp")

        assert "10" in output  # downloaded
        assert "3" in output  # skipped
        assert "1" in output  # failed

    def test_shows_download_notice_when_downloaded(self) -> None:
        """Shows download notice when files were downloaded."""
        result = _make_sync_result(downloaded=5)
        output = format_sync_result_plain(result, "/tmp")
        assert "download" in output.lower()

    def test_shows_warning_when_failed(self) -> None:
        """Shows warning when downloads failed."""
        result = _make_sync_result(failed=2)
        output = format_sync_result_plain(result, "/tmp")
        assert "WARNING" in output or "WARNUNG" in output or "fail" in output.lower()


class TestFormatSyncResultHtml:
    """Behavioral tests for HTML sync result formatting."""

    def test_returns_valid_html(self) -> None:
        """Returns valid HTML structure."""
        result = _make_sync_result()
        output = format_sync_result_html(result, "/tmp")

        assert "<!DOCTYPE html>" in output
        assert "<html>" in output
        assert "</html>" in output
        assert "<body" in output
        assert "</body>" in output

    def test_includes_status_with_color(self) -> None:
        """Status is shown with appropriate color."""
        result = _make_sync_result(failed=0)
        output = format_sync_result_html(result, "/tmp")
        assert "#28a745" in output or "green" in output.lower()  # success color

    def test_includes_error_color_when_failed(self) -> None:
        """Error status uses warning/error color."""
        result = _make_sync_result(failed=2)
        output = format_sync_result_html(result, "/tmp")
        assert "#ffc107" in output  # warning color

    def test_includes_statistics_in_table(self) -> None:
        """Statistics are displayed in HTML table."""
        result = _make_sync_result(downloaded=8, skipped=2)
        output = format_sync_result_html(result, "/tmp")

        assert "<table" in output
        assert "8" in output
        assert "2" in output


class TestFormatErrorPlain:
    """Behavioral tests for plain text error formatting."""

    def test_includes_error_type(self) -> None:
        """Shows error type."""
        output = format_error_plain("Authentication Error", "Login failed")
        assert "Authentication Error" in output

    def test_includes_error_message(self) -> None:
        """Shows error message."""
        output = format_error_plain("Session Error", "Session expired")
        assert "Session expired" in output

    def test_includes_operation(self) -> None:
        """Shows operation that failed."""
        output = format_error_plain("Error", "Message", operation="download")
        assert "download" in output

    def test_includes_return_code_when_provided(self) -> None:
        """Shows return code when provided."""
        output = format_error_plain("Error", "Message", return_code=-4)
        assert "-4" in output

    def test_shows_retryable_yes(self) -> None:
        """Shows retryable=Yes when retryable."""
        output = format_error_plain("Error", "Message", retryable=True)
        assert "Yes" in output or "Ja" in output

    def test_shows_retryable_no(self) -> None:
        """Shows retryable=No when not retryable."""
        output = format_error_plain("Error", "Message", retryable=False)
        assert "No" in output or "Nein" in output

    def test_includes_diagnostics_when_provided(self) -> None:
        """Shows diagnostics information when provided."""
        diagnostics = Diagnostics(
            operation="login",
            tid="123***789",
            benid="TEST***",
        )
        output = format_error_plain("Error", "Message", diagnostics=diagnostics)
        assert "123***789" in output
        assert "Diagnostic" in output


class TestFormatErrorHtml:
    """Behavioral tests for HTML error formatting."""

    def test_returns_valid_html(self) -> None:
        """Returns valid HTML structure."""
        output = format_error_html("Error", "Message")

        assert "<!DOCTYPE html>" in output
        assert "<html>" in output
        assert "</html>" in output

    def test_uses_error_color(self) -> None:
        """Uses red error color."""
        output = format_error_html("Error", "Message")
        assert "#dc3545" in output  # Bootstrap danger red

    def test_includes_return_code_when_provided(self) -> None:
        """Shows return code in table."""
        output = format_error_html("Error", "Message", return_code=-1)
        assert "-1" in output

    def test_includes_diagnostics_section(self) -> None:
        """Shows diagnostics section when provided."""
        diagnostics = Diagnostics(
            operation="login",
            tid="123***789",
        )
        output = format_error_html("Error", "Message", diagnostics=diagnostics)
        assert "Diagnostic" in output
        assert "123***789" in output


class TestEmailNotificationAdapter:
    """Behavioral tests for EmailNotificationAdapter."""

    def test_skips_notification_when_no_recipients(self) -> None:
        """Returns False when no recipients provided."""
        adapter = EmailNotificationAdapter(_make_email_config())
        result = adapter.send_sync_result(_make_sync_result(), "/tmp", [])
        assert result is False

    @patch("finanzonline_databox.adapters.notification.email_adapter.send_email")
    def test_sends_sync_result_notification(self, mock_send: MagicMock) -> None:
        """Sends sync result notification."""
        mock_send.return_value = True
        adapter = EmailNotificationAdapter(_make_email_config())

        result = adapter.send_sync_result(
            _make_sync_result(downloaded=3),
            "/tmp/output",
            ["test@example.com"],
        )

        assert result is True
        mock_send.assert_called_once()
        call_kwargs = mock_send.call_args.kwargs
        assert "test@example.com" in call_kwargs["recipients"]
        assert "DataBox" in call_kwargs["subject"]

    @patch("finanzonline_databox.adapters.notification.email_adapter.send_email")
    def test_sends_download_notification(self, mock_send: MagicMock) -> None:
        """Sends download notification."""
        mock_send.return_value = True
        adapter = EmailNotificationAdapter(_make_email_config())

        result = adapter.send_download_notification(
            entries_downloaded=5,
            total_size=10240,
            recipients=["user@example.com"],
        )

        assert result is True
        mock_send.assert_called_once()
        call_kwargs = mock_send.call_args.kwargs
        assert "5 documents" in call_kwargs["subject"]

    @patch("finanzonline_databox.adapters.notification.email_adapter.send_email")
    def test_sends_error_notification(self, mock_send: MagicMock) -> None:
        """Sends error notification."""
        mock_send.return_value = True
        adapter = EmailNotificationAdapter(_make_email_config())

        result = adapter.send_error(
            error_type="Authentication Error",
            error_message="Login failed",
            operation="sync",
            recipients=["admin@example.com"],
            return_code=-4,
        )

        assert result is True
        mock_send.assert_called_once()
        call_kwargs = mock_send.call_args.kwargs
        assert "ERROR" in call_kwargs["subject"]
        assert "Authentication Error" in call_kwargs["subject"]

    @patch("finanzonline_databox.adapters.notification.email_adapter.send_email")
    def test_plain_format_excludes_html(self, mock_send: MagicMock) -> None:
        """Plain format sends only plain text body."""
        mock_send.return_value = True
        adapter = EmailNotificationAdapter(_make_email_config(), EmailFormat.PLAIN)

        adapter.send_sync_result(_make_sync_result(), "/tmp", ["test@example.com"])

        call_kwargs = mock_send.call_args.kwargs
        assert call_kwargs["body"] != ""
        assert call_kwargs["body_html"] == ""

    @patch("finanzonline_databox.adapters.notification.email_adapter.send_email")
    def test_html_format_excludes_plain(self, mock_send: MagicMock) -> None:
        """HTML format sends only HTML body."""
        mock_send.return_value = True
        adapter = EmailNotificationAdapter(_make_email_config(), EmailFormat.HTML)

        adapter.send_sync_result(_make_sync_result(), "/tmp", ["test@example.com"])

        call_kwargs = mock_send.call_args.kwargs
        assert call_kwargs["body"] == ""
        assert call_kwargs["body_html"] != ""

    @patch("finanzonline_databox.adapters.notification.email_adapter.send_email")
    def test_both_format_includes_both(self, mock_send: MagicMock) -> None:
        """Both format sends both plain and HTML bodies."""
        mock_send.return_value = True
        adapter = EmailNotificationAdapter(_make_email_config(), EmailFormat.BOTH)

        adapter.send_sync_result(_make_sync_result(), "/tmp", ["test@example.com"])

        call_kwargs = mock_send.call_args.kwargs
        assert call_kwargs["body"] != ""
        assert call_kwargs["body_html"] != ""

    @patch("finanzonline_databox.adapters.notification.email_adapter.send_email")
    def test_returns_false_on_send_failure(self, mock_send: MagicMock) -> None:
        """Returns False when email sending fails."""
        mock_send.side_effect = RuntimeError("SMTP error")
        adapter = EmailNotificationAdapter(_make_email_config())

        result = adapter.send_sync_result(_make_sync_result(), "/tmp", ["test@example.com"])

        assert result is False

    def test_download_notification_skips_no_recipients(self) -> None:
        """Download notification skips when no recipients."""
        adapter = EmailNotificationAdapter(_make_email_config())
        result = adapter.send_download_notification(5, 1024, [])
        assert result is False

    def test_error_notification_skips_no_recipients(self) -> None:
        """Error notification skips when no recipients."""
        adapter = EmailNotificationAdapter(_make_email_config())
        result = adapter.send_error("Error", "Message", "sync", [])
        assert result is False
