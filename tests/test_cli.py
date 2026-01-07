"""Behavioral tests for CLI commands."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from finanzonline_databox.cli import (
    _get_databox_error_info,  # pyright: ignore[reportPrivateUsage]
    _get_error_info,  # pyright: ignore[reportPrivateUsage]
    _parse_date,  # pyright: ignore[reportPrivateUsage]
    _resolve_notification_recipients,  # pyright: ignore[reportPrivateUsage]
    apply_traceback_preferences,
    cli,
    restore_traceback_state,
    snapshot_traceback_state,
)
from finanzonline_databox.domain.errors import (
    AuthenticationError,
    ConfigurationError,
    DataboxOperationError,
    SessionError,
)
from finanzonline_databox.domain.return_codes import CliExitCode
from finanzonline_databox.mail import EmailConfig

if TYPE_CHECKING:
    from click.testing import CliRunner

pytestmark = pytest.mark.os_agnostic


class TestTracebackPreferences:
    """Tests for traceback configuration management."""

    def test_apply_traceback_enabled(self) -> None:
        """Enabling tracebacks sets both flags to True."""
        apply_traceback_preferences(True)
        import lib_cli_exit_tools

        assert lib_cli_exit_tools.config.traceback is True
        assert lib_cli_exit_tools.config.traceback_force_color is True

    def test_apply_traceback_disabled(self) -> None:
        """Disabling tracebacks sets both flags to False."""
        apply_traceback_preferences(False)
        import lib_cli_exit_tools

        assert lib_cli_exit_tools.config.traceback is False
        assert lib_cli_exit_tools.config.traceback_force_color is False

    def test_snapshot_and_restore_state(self) -> None:
        """Snapshot captures state that can be restored."""
        apply_traceback_preferences(True)
        state = snapshot_traceback_state()

        apply_traceback_preferences(False)
        import lib_cli_exit_tools

        assert lib_cli_exit_tools.config.traceback is False

        restore_traceback_state(state)
        assert lib_cli_exit_tools.config.traceback is True


class TestParseDateFunction:
    """Tests for _parse_date helper function."""

    def test_none_returns_none(self) -> None:
        """None input returns None."""
        assert _parse_date(None) is None

    def test_valid_date_string(self) -> None:
        """Valid date string is parsed correctly."""
        result = _parse_date("2024-01-15")
        assert result is not None
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15
        assert result.tzinfo is not None  # Has local timezone

    def test_invalid_date_raises_bad_parameter(self) -> None:
        """Invalid date format raises click.BadParameter."""
        import click

        with pytest.raises(click.BadParameter, match="Invalid date format"):
            _parse_date("15-01-2024")

    def test_invalid_date_format(self) -> None:
        """Non-date string raises click.BadParameter."""
        import click

        with pytest.raises(click.BadParameter):
            _parse_date("not-a-date")


class TestGetErrorInfo:
    """Tests for error info extraction."""

    def test_configuration_error(self) -> None:
        """ConfigurationError returns correct info."""
        exc = ConfigurationError("Missing TID")
        info = _get_databox_error_info(exc)

        assert info.error_type == "Configuration Error"
        assert info.message == "Missing TID"
        assert info.exit_code == CliExitCode.CONFIG_ERROR

    def test_authentication_error(self) -> None:
        """AuthenticationError returns correct info."""
        exc = AuthenticationError("Invalid PIN", return_code=-1)
        info = _get_databox_error_info(exc)

        assert info.error_type == "Authentication Error"
        assert info.message == "Invalid PIN"
        assert info.exit_code == CliExitCode.AUTH_ERROR
        assert info.return_code == -1

    def test_session_error(self) -> None:
        """SessionError returns correct info."""
        exc = SessionError("Session expired", return_code=-2)
        info = _get_databox_error_info(exc)

        assert info.error_type == "Session Error"
        assert info.exit_code == CliExitCode.DOWNLOAD_ERROR
        assert info.return_code == -2

    def test_databox_operation_error(self) -> None:
        """DataboxOperationError returns correct info."""
        exc = DataboxOperationError("API error", return_code=-3)
        info = _get_databox_error_info(exc)

        assert info.error_type == "DataBox Operation Error"
        assert info.exit_code == CliExitCode.DOWNLOAD_ERROR

    def test_get_error_info_for_value_error(self) -> None:
        """ValueError returns validation error info."""
        exc = ValueError("Invalid input")
        info = _get_error_info(exc)

        assert info.error_type == "Validation Error"
        assert info.exit_code == CliExitCode.CONFIG_ERROR

    def test_get_error_info_for_generic_exception(self) -> None:
        """Generic exception returns unexpected error info."""
        exc = RuntimeError("Something went wrong")
        info = _get_error_info(exc)

        assert info.error_type == "Unexpected Error"
        assert info.exit_code == CliExitCode.DOWNLOAD_ERROR


class TestResolveNotificationRecipients:
    """Tests for recipient resolution logic."""

    def test_explicit_recipients_take_precedence(self) -> None:
        """Explicit recipients override all others."""
        explicit = ["explicit@example.com"]
        email_config = EmailConfig(
            smtp_hosts=["smtp.test.com:587"],
            from_address="test@example.com",
            default_recipients=["default@example.com"],
        )
        fo_config = MagicMock()
        fo_config.default_recipients = ["fo@example.com"]

        result = _resolve_notification_recipients(explicit, email_config, fo_config)
        assert result == ["explicit@example.com"]

    def test_email_config_recipients_used_if_no_explicit(self) -> None:
        """Email config recipients used when no explicit provided."""
        email_config = EmailConfig(
            smtp_hosts=["smtp.test.com:587"],
            from_address="test@example.com",
            default_recipients=["default@example.com"],
        )
        fo_config = MagicMock()
        fo_config.default_recipients = ["fo@example.com"]

        result = _resolve_notification_recipients([], email_config, fo_config)
        assert result == ["default@example.com"]

    def test_fo_config_recipients_used_as_fallback(self) -> None:
        """FO config recipients used when no explicit or email config recipients."""
        email_config = EmailConfig(
            smtp_hosts=["smtp.test.com:587"],
            from_address="test@example.com",
        )
        fo_config = MagicMock()
        fo_config.default_recipients = ["fo@example.com"]

        result = _resolve_notification_recipients([], email_config, fo_config)
        assert result == ["fo@example.com"]

    def test_empty_when_no_recipients_configured(self) -> None:
        """Returns empty list when no recipients anywhere."""
        email_config = EmailConfig(
            smtp_hosts=["smtp.test.com:587"],
            from_address="test@example.com",
        )

        result = _resolve_notification_recipients([], email_config, None)
        assert result == []


class TestCliRootCommand:
    """Tests for root CLI command."""

    def test_shows_help_when_no_subcommand(self, cli_runner: CliRunner) -> None:
        """Shows help text when invoked without subcommand."""
        result = cli_runner.invoke(cli, [])
        assert result.exit_code == 0
        assert "Usage:" in result.output or "Commands:" in result.output

    def test_version_option(self, cli_runner: CliRunner) -> None:
        """Version option shows version information."""
        result = cli_runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "version" in result.output.lower()


class TestHelloCommand:
    """Tests for 'hello' command."""

    def test_hello_outputs_greeting(self, cli_runner: CliRunner) -> None:
        """Hello command outputs greeting."""
        result = cli_runner.invoke(cli, ["hello"])
        assert result.exit_code == 0
        assert "Hello" in result.output


class TestInfoCommand:
    """Tests for 'info' command."""

    def test_info_shows_package_info(self, cli_runner: CliRunner) -> None:
        """Info command shows package metadata."""
        result = cli_runner.invoke(cli, ["info"])
        assert result.exit_code == 0
        # Should contain package name or version info
        assert "finanzonline" in result.output.lower() or "version" in result.output.lower()


class TestFailCommand:
    """Tests for 'fail' command."""

    def test_fail_raises_exception(self, cli_runner: CliRunner) -> None:
        """Fail command triggers intentional failure."""
        result = cli_runner.invoke(cli, ["fail"])
        assert result.exit_code != 0


class TestConfigCommand:
    """Tests for 'config' command."""

    def test_config_shows_configuration(self, cli_runner: CliRunner) -> None:
        """Config command displays configuration."""
        result = cli_runner.invoke(cli, ["config"])
        # May exit 0 or show config
        assert result.exit_code == 0 or "[" in result.output

    def test_config_json_format(self, cli_runner: CliRunner) -> None:
        """Config command with JSON format outputs JSON."""
        result = cli_runner.invoke(cli, ["config", "--format", "json"])
        assert result.exit_code == 0
        # JSON output should contain braces
        assert "{" in result.output

    def test_config_invalid_section(self, cli_runner: CliRunner) -> None:
        """Config command with invalid section shows error."""
        result = cli_runner.invoke(cli, ["config", "--section", "nonexistent"])
        assert result.exit_code == 1
        assert "not found" in result.stderr.lower()


class TestConfigDeployCommand:
    """Tests for 'config-deploy' command."""

    def test_config_deploy_requires_target(self, cli_runner: CliRunner) -> None:
        """Config-deploy requires --target option."""
        result = cli_runner.invoke(cli, ["config-deploy"])
        assert result.exit_code != 0
        assert "target" in result.output.lower() or "required" in result.output.lower()

    @patch("finanzonline_databox.cli.deploy_configuration")
    def test_config_deploy_with_user_target(self, mock_deploy: MagicMock, cli_runner: CliRunner, tmp_path: Path) -> None:
        """Config-deploy with user target calls deploy_configuration."""
        mock_deploy.return_value = [str(tmp_path / "config.toml")]

        result = cli_runner.invoke(cli, ["config-deploy", "--target", "user"])
        assert result.exit_code == 0
        mock_deploy.assert_called_once()

    @patch("finanzonline_databox.cli.deploy_configuration")
    def test_config_deploy_no_files_created(self, mock_deploy: MagicMock, cli_runner: CliRunner) -> None:
        """Shows message when no files were created."""
        mock_deploy.return_value = []

        result = cli_runner.invoke(cli, ["config-deploy", "--target", "user"])
        assert result.exit_code == 0
        assert "No files were created" in result.output or "already exist" in result.output

    @patch("finanzonline_databox.cli.deploy_configuration")
    def test_config_deploy_permission_error(self, mock_deploy: MagicMock, cli_runner: CliRunner) -> None:
        """Shows permission error message on PermissionError."""
        mock_deploy.side_effect = PermissionError("Permission denied")

        result = cli_runner.invoke(cli, ["config-deploy", "--target", "app"])
        assert result.exit_code == 1
        assert "Permission" in result.stderr or "permission" in result.stderr.lower()


class TestListCommand:
    """Tests for 'list' command."""

    @patch("finanzonline_databox.cli.load_finanzonline_config")
    def test_list_config_error_shows_help(self, mock_load_config: MagicMock, cli_runner: CliRunner) -> None:
        """List command shows config help on configuration error."""
        mock_load_config.side_effect = ConfigurationError("tid is required")

        result = cli_runner.invoke(cli, ["list"])
        assert result.exit_code == CliExitCode.CONFIG_ERROR
        assert "tid" in result.stderr.lower() or "config" in result.stderr.lower()

    @patch("finanzonline_databox.cli.load_finanzonline_config")
    @patch("finanzonline_databox.cli.FinanzOnlineSessionClient")
    @patch("finanzonline_databox.cli.DataboxClient")
    @patch("finanzonline_databox.cli.ListDataboxUseCase")
    def test_list_success_human_format(
        self,
        mock_use_case_cls: MagicMock,
        mock_databox_cls: MagicMock,
        mock_session_cls: MagicMock,
        mock_load_config: MagicMock,
        cli_runner: CliRunner,
    ) -> None:
        """List command outputs human-readable format by default."""
        # Setup mocks
        mock_credentials = MagicMock()
        mock_fo_config = MagicMock()
        mock_fo_config.credentials = mock_credentials
        mock_fo_config.session_timeout = 30.0
        mock_fo_config.query_timeout = 60.0
        mock_load_config.return_value = mock_fo_config

        mock_result = MagicMock()
        mock_result.is_success = True
        mock_result.entries = []
        mock_result.rc = 0
        mock_result.msg = "OK"

        mock_use_case = MagicMock()
        mock_use_case.execute.return_value = mock_result
        mock_use_case_cls.return_value = mock_use_case

        result = cli_runner.invoke(cli, ["list"])
        assert result.exit_code == CliExitCode.SUCCESS

    @patch("finanzonline_databox.cli.load_finanzonline_config")
    @patch("finanzonline_databox.cli.FinanzOnlineSessionClient")
    @patch("finanzonline_databox.cli.DataboxClient")
    @patch("finanzonline_databox.cli.ListDataboxUseCase")
    def test_list_success_json_format(
        self,
        mock_use_case_cls: MagicMock,
        mock_databox_cls: MagicMock,
        mock_session_cls: MagicMock,
        mock_load_config: MagicMock,
        cli_runner: CliRunner,
    ) -> None:
        """List command outputs JSON format when requested."""
        from finanzonline_databox.domain.models import DataboxListResult

        # Setup mocks
        mock_credentials = MagicMock()
        mock_fo_config = MagicMock()
        mock_fo_config.credentials = mock_credentials
        mock_fo_config.session_timeout = 30.0
        mock_fo_config.query_timeout = 60.0
        mock_load_config.return_value = mock_fo_config

        # Use real DataboxListResult for JSON serialization
        mock_result = DataboxListResult(rc=0, msg="OK", entries=())

        mock_use_case = MagicMock()
        mock_use_case.execute.return_value = mock_result
        mock_use_case_cls.return_value = mock_use_case

        result = cli_runner.invoke(cli, ["list", "--format", "json"])
        assert result.exit_code == CliExitCode.SUCCESS
        assert "{" in result.output

    def test_list_with_invalid_date(self, cli_runner: CliRunner) -> None:
        """List command rejects invalid date format."""
        result = cli_runner.invoke(cli, ["list", "--from", "invalid-date"])
        assert result.exit_code != 0

    def test_list_days_invalid_range(self, cli_runner: CliRunner) -> None:
        """List command rejects --days outside valid range (1-31)."""
        result = cli_runner.invoke(cli, ["list", "--days", "0"])
        assert result.exit_code != 0
        assert "1 and 31" in result.output or "Days" in result.output

        result = cli_runner.invoke(cli, ["list", "--days", "32"])
        assert result.exit_code != 0

    @patch("finanzonline_databox.cli.load_finanzonline_config")
    @patch("finanzonline_databox.cli.FinanzOnlineSessionClient")
    @patch("finanzonline_databox.cli.DataboxClient")
    @patch("finanzonline_databox.cli.ListDataboxUseCase")
    def test_list_with_days_option(
        self,
        mock_use_case_cls: MagicMock,
        mock_databox_cls: MagicMock,
        mock_session_cls: MagicMock,
        mock_load_config: MagicMock,
        cli_runner: CliRunner,
    ) -> None:
        """List command with --days sets correct date range."""
        from finanzonline_databox.domain.models import DataboxListResult

        mock_credentials = MagicMock()
        mock_fo_config = MagicMock()
        mock_fo_config.credentials = mock_credentials
        mock_fo_config.session_timeout = 30.0
        mock_fo_config.query_timeout = 60.0
        mock_load_config.return_value = mock_fo_config

        mock_result = DataboxListResult(rc=0, msg="OK", entries=())
        mock_use_case = MagicMock()
        mock_use_case.execute.return_value = mock_result
        mock_use_case_cls.return_value = mock_use_case

        result = cli_runner.invoke(cli, ["list", "--days", "7"])
        assert result.exit_code == CliExitCode.SUCCESS

        # Verify the use case was called with date range
        mock_use_case.execute.assert_called_once()
        call_kwargs = mock_use_case.execute.call_args[1]
        request = call_kwargs["request"]
        assert request.ts_zust_von is not None
        assert request.ts_zust_bis is not None

    @patch("finanzonline_databox.cli.load_finanzonline_config")
    @patch("finanzonline_databox.cli.FinanzOnlineSessionClient")
    @patch("finanzonline_databox.cli.DataboxClient")
    @patch("finanzonline_databox.cli.ListDataboxUseCase")
    def test_list_with_unread_option(
        self,
        mock_use_case_cls: MagicMock,
        mock_databox_cls: MagicMock,
        mock_session_cls: MagicMock,
        mock_load_config: MagicMock,
        cli_runner: CliRunner,
    ) -> None:
        """List command with --unread filters to unread entries only."""
        from datetime import date, datetime
        from datetime import timezone as tz

        from finanzonline_databox.domain.models import DataboxEntry, DataboxListResult, FileType, ReadStatus

        mock_credentials = MagicMock()
        mock_fo_config = MagicMock()
        mock_fo_config.credentials = mock_credentials
        mock_fo_config.session_timeout = 30.0
        mock_fo_config.query_timeout = 60.0
        mock_load_config.return_value = mock_fo_config

        # Create entries with mixed read status
        unread_entry = DataboxEntry(
            stnr="12-345/6789",
            name="Unread Doc",
            anbringen="E1",
            zrvon="2024",
            zrbis="2024",
            datbesch=date(2024, 1, 15),
            erltyp="B",
            fileart=FileType.PDF,
            ts_zust=datetime(2024, 1, 15, 10, 30, tzinfo=tz.utc),
            applkey="abc123def456",
            filebez="Unread",
            status=ReadStatus.UNREAD,  # unread
        )
        read_entry = DataboxEntry(
            stnr="12-345/6789",
            name="Read Doc",
            anbringen="E2",
            zrvon="2024",
            zrbis="2024",
            datbesch=date(2024, 1, 14),
            erltyp="M",
            fileart=FileType.PDF,
            ts_zust=datetime(2024, 1, 14, 10, 30, tzinfo=tz.utc),
            applkey="def456ghi789",
            filebez="Read",
            status=ReadStatus.READ,  # read
        )

        mock_result = DataboxListResult(rc=0, msg="OK", entries=(unread_entry, read_entry))
        mock_use_case = MagicMock()
        mock_use_case.execute.return_value = mock_result
        mock_use_case_cls.return_value = mock_use_case

        result = cli_runner.invoke(cli, ["list", "--unread", "--format", "json"])
        assert result.exit_code == CliExitCode.SUCCESS

        # Verify that only unread entry is in output
        import json

        output_data = json.loads(result.output)
        assert output_data["count"] == 1
        assert output_data["entries"][0]["applkey"] == "abc123def456"


class TestFilterUnreadEntries:
    """Tests for _filter_unread_entries helper function."""

    def test_filter_unread_entries(self) -> None:
        """Filter removes read entries from result."""
        from datetime import date, datetime
        from datetime import timezone as tz

        from finanzonline_databox.cli import (
            _filter_unread_entries,  # pyright: ignore[reportPrivateUsage]
        )
        from finanzonline_databox.domain.models import DataboxEntry, DataboxListResult, FileType, ReadStatus

        unread = DataboxEntry(
            stnr="123",
            name="Unread",
            anbringen="E1",
            zrvon="2024",
            zrbis="2024",
            datbesch=date(2024, 1, 15),
            erltyp="B",
            fileart=FileType.PDF,
            ts_zust=datetime(2024, 1, 15, tzinfo=tz.utc),
            applkey="abc123def456",
            filebez="Unread",
            status=ReadStatus.UNREAD,
        )
        read = DataboxEntry(
            stnr="456",
            name="Read",
            anbringen="E2",
            zrvon="2024",
            zrbis="2024",
            datbesch=date(2024, 1, 14),
            erltyp="M",
            fileart=FileType.PDF,
            ts_zust=datetime(2024, 1, 14, tzinfo=tz.utc),
            applkey="def456ghi789",
            filebez="Read",
            status=ReadStatus.READ,
        )

        original = DataboxListResult(rc=0, msg="OK", entries=(unread, read))
        filtered = _filter_unread_entries(original)

        assert len(filtered.entries) == 1
        assert filtered.entries[0].applkey == "abc123def456"
        assert filtered.rc == original.rc
        assert filtered.msg == original.msg


class TestDownloadCommand:
    """Tests for 'download' command."""

    @patch("finanzonline_databox.cli.load_finanzonline_config")
    def test_download_config_error(self, mock_load_config: MagicMock, cli_runner: CliRunner) -> None:
        """Download command shows error on configuration error."""
        mock_load_config.side_effect = ConfigurationError("Missing credentials")

        result = cli_runner.invoke(cli, ["download", "abc123def456"])
        assert result.exit_code == CliExitCode.CONFIG_ERROR

    @patch("finanzonline_databox.cli.load_finanzonline_config")
    @patch("finanzonline_databox.cli.FinanzOnlineSessionClient")
    @patch("finanzonline_databox.cli.DataboxClient")
    @patch("finanzonline_databox.cli.ListDataboxUseCase")
    @patch("finanzonline_databox.cli.DownloadEntryUseCase")
    def test_download_success(
        self,
        mock_download_use_case_cls: MagicMock,
        mock_list_use_case_cls: MagicMock,
        mock_databox_cls: MagicMock,
        mock_session_cls: MagicMock,
        mock_load_config: MagicMock,
        cli_runner: CliRunner,
        tmp_path: Path,
    ) -> None:
        """Download command successfully downloads file."""
        # Setup mocks
        mock_credentials = MagicMock()
        mock_fo_config = MagicMock()
        mock_fo_config.credentials = mock_credentials
        mock_fo_config.session_timeout = 30.0
        mock_fo_config.query_timeout = 60.0
        mock_load_config.return_value = mock_fo_config

        # Mock list use case for entry lookup
        mock_entry = MagicMock()
        mock_entry.applkey = "abc123def456"
        mock_entry.suggested_filename = "test_document.pdf"
        mock_list_result = MagicMock()
        mock_list_result.entries = [mock_entry]
        mock_list_use_case = MagicMock()
        mock_list_use_case.execute.return_value = mock_list_result
        mock_list_use_case_cls.return_value = mock_list_use_case

        # Mock download use case
        mock_result = MagicMock()
        mock_result.is_success = True
        mock_result.content = b"PDF content"
        mock_result.content_size = 11
        saved_path = tmp_path / "test_document.pdf"

        mock_download_use_case = MagicMock()
        mock_download_use_case.execute.return_value = (mock_result, saved_path)
        mock_download_use_case_cls.return_value = mock_download_use_case

        result = cli_runner.invoke(cli, ["download", "abc123def456", "--output", str(tmp_path)])
        assert result.exit_code == CliExitCode.SUCCESS
        assert "Downloaded" in result.output or "Size" in result.output

    @patch("finanzonline_databox.cli.load_finanzonline_config")
    @patch("finanzonline_databox.cli.FinanzOnlineSessionClient")
    @patch("finanzonline_databox.cli.DataboxClient")
    @patch("finanzonline_databox.cli.ListDataboxUseCase")
    @patch("finanzonline_databox.cli.DownloadEntryUseCase")
    def test_download_failure(
        self,
        mock_download_use_case_cls: MagicMock,
        mock_list_use_case_cls: MagicMock,
        mock_databox_cls: MagicMock,
        mock_session_cls: MagicMock,
        mock_load_config: MagicMock,
        cli_runner: CliRunner,
        tmp_path: Path,
    ) -> None:
        """Download command shows error on failure."""
        # Setup mocks
        mock_credentials = MagicMock()
        mock_fo_config = MagicMock()
        mock_fo_config.credentials = mock_credentials
        mock_fo_config.session_timeout = 30.0
        mock_fo_config.query_timeout = 60.0
        mock_load_config.return_value = mock_fo_config

        # Mock list use case for entry lookup
        mock_entry = MagicMock()
        mock_entry.applkey = "abc123def456"
        mock_entry.suggested_filename = "test_document.pdf"
        mock_list_result = MagicMock()
        mock_list_result.entries = [mock_entry]
        mock_list_use_case = MagicMock()
        mock_list_use_case.execute.return_value = mock_list_result
        mock_list_use_case_cls.return_value = mock_list_use_case

        # Mock download use case with failure
        mock_result = MagicMock()
        mock_result.is_success = False
        mock_result.msg = "Document not found"

        mock_download_use_case = MagicMock()
        mock_download_use_case.execute.return_value = (mock_result, None)
        mock_download_use_case_cls.return_value = mock_download_use_case

        result = cli_runner.invoke(cli, ["download", "abc123def456", "--output", str(tmp_path)])
        assert result.exit_code == CliExitCode.DOWNLOAD_ERROR

    def test_download_requires_applkey(self, cli_runner: CliRunner) -> None:
        """Download command requires applkey argument."""
        result = cli_runner.invoke(cli, ["download"])
        assert result.exit_code != 0
        assert "applkey" in result.output.lower() or "missing" in result.output.lower()


class TestSyncCommand:
    """Tests for 'sync' command."""

    @patch("finanzonline_databox.cli.load_finanzonline_config")
    def test_sync_config_error(self, mock_load_config: MagicMock, cli_runner: CliRunner) -> None:
        """Sync command shows error on configuration error."""
        mock_load_config.side_effect = ConfigurationError("Missing credentials")

        result = cli_runner.invoke(cli, ["sync"])
        assert result.exit_code == CliExitCode.CONFIG_ERROR

    @patch("finanzonline_databox.cli.load_finanzonline_config")
    @patch("finanzonline_databox.cli.FinanzOnlineSessionClient")
    @patch("finanzonline_databox.cli.DataboxClient")
    @patch("finanzonline_databox.cli.SyncDataboxUseCase")
    def test_sync_success_human_format(
        self,
        mock_use_case_cls: MagicMock,
        mock_databox_cls: MagicMock,
        mock_session_cls: MagicMock,
        mock_load_config: MagicMock,
        cli_runner: CliRunner,
        tmp_path: Path,
    ) -> None:
        """Sync command outputs human-readable format by default."""
        # Setup mocks
        mock_credentials = MagicMock()
        mock_fo_config = MagicMock()
        mock_fo_config.credentials = mock_credentials
        mock_fo_config.session_timeout = 30.0
        mock_fo_config.query_timeout = 60.0
        mock_fo_config.default_recipients = []
        mock_load_config.return_value = mock_fo_config

        mock_result = MagicMock()
        mock_result.is_success = True
        mock_result.has_new_downloads = False
        mock_result.total_listed = 0
        mock_result.downloaded = 0
        mock_result.skipped = 0
        mock_result.failed = 0
        mock_result.total_bytes = 0

        mock_use_case = MagicMock()
        mock_use_case.execute.return_value = mock_result
        mock_use_case_cls.return_value = mock_use_case

        result = cli_runner.invoke(cli, ["sync", "--output", str(tmp_path), "--no-email"])
        assert result.exit_code == CliExitCode.SUCCESS

    @patch("finanzonline_databox.cli.load_finanzonline_config")
    @patch("finanzonline_databox.cli.FinanzOnlineSessionClient")
    @patch("finanzonline_databox.cli.DataboxClient")
    @patch("finanzonline_databox.cli.SyncDataboxUseCase")
    def test_sync_success_json_format(
        self,
        mock_use_case_cls: MagicMock,
        mock_databox_cls: MagicMock,
        mock_session_cls: MagicMock,
        mock_load_config: MagicMock,
        cli_runner: CliRunner,
        tmp_path: Path,
    ) -> None:
        """Sync command outputs JSON format when requested."""
        # Setup mocks
        mock_credentials = MagicMock()
        mock_fo_config = MagicMock()
        mock_fo_config.credentials = mock_credentials
        mock_fo_config.session_timeout = 30.0
        mock_fo_config.query_timeout = 60.0
        mock_fo_config.default_recipients = []
        mock_load_config.return_value = mock_fo_config

        mock_result = MagicMock()
        mock_result.is_success = True
        mock_result.has_new_downloads = False
        mock_result.total_retrieved = 5
        mock_result.total_listed = 5
        mock_result.downloaded = 3
        mock_result.skipped = 2
        mock_result.failed = 0
        mock_result.total_bytes = 1024

        mock_use_case = MagicMock()
        mock_use_case.execute.return_value = mock_result
        mock_use_case_cls.return_value = mock_use_case

        result = cli_runner.invoke(cli, ["sync", "--output", str(tmp_path), "--format", "json", "--no-email"])
        assert result.exit_code == CliExitCode.SUCCESS
        assert "{" in result.output

    @patch("finanzonline_databox.cli.load_finanzonline_config")
    @patch("finanzonline_databox.cli.FinanzOnlineSessionClient")
    @patch("finanzonline_databox.cli.DataboxClient")
    @patch("finanzonline_databox.cli.SyncDataboxUseCase")
    @patch("finanzonline_databox.cli._send_sync_notification")
    def test_sync_sends_notification_on_downloads(
        self,
        mock_send_notification: MagicMock,
        mock_use_case_cls: MagicMock,
        mock_databox_cls: MagicMock,
        mock_session_cls: MagicMock,
        mock_load_config: MagicMock,
        cli_runner: CliRunner,
        tmp_path: Path,
    ) -> None:
        """Sync command sends notification when downloads occur."""
        # Setup mocks
        mock_credentials = MagicMock()
        mock_fo_config = MagicMock()
        mock_fo_config.credentials = mock_credentials
        mock_fo_config.session_timeout = 30.0
        mock_fo_config.query_timeout = 60.0
        mock_fo_config.default_recipients = ["admin@example.com"]
        mock_load_config.return_value = mock_fo_config

        mock_result = MagicMock()
        mock_result.is_success = True
        mock_result.has_new_downloads = True
        mock_result.total_listed = 5
        mock_result.downloaded = 3
        mock_result.skipped = 2
        mock_result.failed = 0
        mock_result.total_bytes = 1024

        mock_use_case = MagicMock()
        mock_use_case.execute.return_value = mock_result
        mock_use_case_cls.return_value = mock_use_case

        result = cli_runner.invoke(cli, ["sync", "--output", str(tmp_path)])
        assert result.exit_code == CliExitCode.SUCCESS
        mock_send_notification.assert_called_once()

    @patch("finanzonline_databox.cli.load_finanzonline_config")
    @patch("finanzonline_databox.cli.FinanzOnlineSessionClient")
    @patch("finanzonline_databox.cli.DataboxClient")
    @patch("finanzonline_databox.cli.SyncDataboxUseCase")
    @patch("finanzonline_databox.cli._send_sync_notification")
    def test_sync_no_email_flag_skips_notification(
        self,
        mock_send_notification: MagicMock,
        mock_use_case_cls: MagicMock,
        mock_databox_cls: MagicMock,
        mock_session_cls: MagicMock,
        mock_load_config: MagicMock,
        cli_runner: CliRunner,
        tmp_path: Path,
    ) -> None:
        """Sync command skips notification when --no-email specified."""
        # Setup mocks
        mock_credentials = MagicMock()
        mock_fo_config = MagicMock()
        mock_fo_config.credentials = mock_credentials
        mock_fo_config.session_timeout = 30.0
        mock_fo_config.query_timeout = 60.0
        mock_load_config.return_value = mock_fo_config

        mock_result = MagicMock()
        mock_result.is_success = True
        mock_result.has_new_downloads = True
        mock_result.total_listed = 5
        mock_result.downloaded = 3
        mock_result.skipped = 2
        mock_result.failed = 0
        mock_result.total_bytes = 1024

        mock_use_case = MagicMock()
        mock_use_case.execute.return_value = mock_result
        mock_use_case_cls.return_value = mock_use_case

        result = cli_runner.invoke(cli, ["sync", "--output", str(tmp_path), "--no-email"])
        assert result.exit_code == CliExitCode.SUCCESS
        mock_send_notification.assert_not_called()

    @patch("finanzonline_databox.cli.load_finanzonline_config")
    @patch("finanzonline_databox.cli.FinanzOnlineSessionClient")
    @patch("finanzonline_databox.cli.DataboxClient")
    @patch("finanzonline_databox.cli.SyncDataboxUseCase")
    def test_sync_with_failures_returns_error_code(
        self,
        mock_use_case_cls: MagicMock,
        mock_databox_cls: MagicMock,
        mock_session_cls: MagicMock,
        mock_load_config: MagicMock,
        cli_runner: CliRunner,
        tmp_path: Path,
    ) -> None:
        """Sync command returns error code when failures occur."""
        # Setup mocks
        mock_credentials = MagicMock()
        mock_fo_config = MagicMock()
        mock_fo_config.credentials = mock_credentials
        mock_fo_config.session_timeout = 30.0
        mock_fo_config.query_timeout = 60.0
        mock_fo_config.default_recipients = []
        mock_load_config.return_value = mock_fo_config

        mock_result = MagicMock()
        mock_result.is_success = False
        mock_result.has_new_downloads = True
        mock_result.total_listed = 5
        mock_result.downloaded = 2
        mock_result.skipped = 1
        mock_result.failed = 2
        mock_result.total_bytes = 512

        mock_use_case = MagicMock()
        mock_use_case.execute.return_value = mock_result
        mock_use_case_cls.return_value = mock_use_case

        result = cli_runner.invoke(cli, ["sync", "--output", str(tmp_path), "--no-email"])
        assert result.exit_code == CliExitCode.DOWNLOAD_ERROR
