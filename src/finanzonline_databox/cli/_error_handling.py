"""Error handling for CLI commands.

Purpose
-------
Map domain exceptions to user-facing error output, exit codes, and
optional email notifications.

Contents
--------
* :class:`ErrorTypeInfo` / :class:`FilesystemErrorHint` – typed error mappings.
* :func:`_handle_command_exception` – top-level handler for databox commands.

System Role
-----------
CLI adapter layer — error presentation and notification dispatch.
"""

# pyright: reportUnusedFunction=false
from __future__ import annotations

import errno
import logging
from dataclasses import dataclass

import rich_click as click
from lib_layered_config import Config

from ..config import FinanzOnlineConfig
from ..domain.errors import (
    AuthenticationError,
    ConfigurationError,
    DataboxError,
    DataboxErrorInfo,
    DataboxOperationError,
    FilesystemError,
    SessionError,
)
from ..domain.return_codes import CliExitCode, get_return_code_info
from ..i18n import _
from ._notifications import _log_notification_result, _prepare_notification  # pyright: ignore[reportPrivateUsage]

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ErrorTypeInfo:
    """Mapping of error type to display label and exit code.

    Provides type-safe structure for error type mappings instead of raw tuples.

    Attributes:
        label: Human-readable label for the error type (e.g., "Configuration Error").
        exit_code: CLI exit code to return for this error type.
    """

    label: str
    exit_code: CliExitCode


#: Maps exception types to their display info. Uses dataclass instead of tuple.
_ERROR_TYPE_MAP: dict[type[DataboxError], ErrorTypeInfo] = {
    ConfigurationError: ErrorTypeInfo(_("Configuration Error"), CliExitCode.CONFIG_ERROR),
    AuthenticationError: ErrorTypeInfo(_("Authentication Error"), CliExitCode.AUTH_ERROR),
    SessionError: ErrorTypeInfo(_("Session Error"), CliExitCode.DOWNLOAD_ERROR),
    DataboxOperationError: ErrorTypeInfo(_("DataBox Operation Error"), CliExitCode.DOWNLOAD_ERROR),
    FilesystemError: ErrorTypeInfo(_("Filesystem Error"), CliExitCode.IO_ERROR),
}

#: Default error info when exception type is not in the map.
_DEFAULT_ERROR_INFO: ErrorTypeInfo = ErrorTypeInfo(_("DataBox Error"), CliExitCode.DOWNLOAD_ERROR)


def _get_databox_error_info(exc: DataboxError) -> DataboxErrorInfo:
    """Get DataboxErrorInfo for DataboxError subclasses."""
    exc_type = type(exc)
    error_info = _ERROR_TYPE_MAP.get(exc_type, _DEFAULT_ERROR_INFO)
    return DataboxErrorInfo(
        error_type=error_info.label,
        message=exc.message,
        exit_code=error_info.exit_code,
        return_code=getattr(exc, "return_code", None),
        retryable=getattr(exc, "retryable", False),
        diagnostics=getattr(exc, "diagnostics", None),
    )


@dataclass(frozen=True, slots=True)
class FilesystemErrorHint:
    """Mapping of errno to actionable hint message.

    Provides type-safe structure for filesystem error hints instead of raw dict.

    Attributes:
        errno_value: The errno constant (e.g., errno.EACCES).
        hint: User-friendly hint message for this error type.
    """

    errno_value: int
    hint: str


#: Hints for common filesystem errors, providing actionable guidance.
_FILESYSTEM_ERROR_HINTS: tuple[FilesystemErrorHint, ...] = (
    FilesystemErrorHint(errno.EACCES, _("Use --output to specify a different directory, or check file permissions.")),
    FilesystemErrorHint(errno.ENOSPC, _("Free up disk space or use --output to specify a different disk.")),
    FilesystemErrorHint(errno.EROFS, _("Use --output to specify a writable directory.")),
    FilesystemErrorHint(errno.ENAMETOOLONG, _("Use --filename to specify a shorter filename.")),
)


def _get_filesystem_error_hint(exc: FilesystemError) -> str | None:
    """Get actionable hint for filesystem error.

    Args:
        exc: The filesystem error.

    Returns:
        Hint string or None if no specific hint available.
    """
    if exc.original_error is None:
        return None

    err_no = exc.original_error.errno
    if err_no is None:
        return None

    for hint_info in _FILESYSTEM_ERROR_HINTS:
        if hint_info.errno_value == err_no:
            return hint_info.hint
    return None


def _get_error_info(exc: Exception) -> DataboxErrorInfo:
    """Get DataboxErrorInfo for an exception.

    Args:
        exc: The exception to get info for.

    Returns:
        DataboxErrorInfo with error details.
    """
    if isinstance(exc, DataboxError):
        return _get_databox_error_info(exc)
    if isinstance(exc, ValueError):
        return DataboxErrorInfo(
            error_type="Validation Error",
            message=str(exc),
            exit_code=CliExitCode.CONFIG_ERROR,
        )
    return DataboxErrorInfo(
        error_type="Unexpected Error",
        message=str(exc),
        exit_code=CliExitCode.DOWNLOAD_ERROR,
    )


def _show_config_help(error_message: str) -> None:
    """Display configuration help for FinanzOnline credentials.

    Args:
        error_message: The configuration error message.
    """
    click.echo(f"\n{_('Error')}: {error_message}", err=True)
    click.echo(f"\n{_('Configure FinanzOnline credentials in your config file or via environment variables:')}", err=True)
    click.echo(f"  FINANZONLINE_DATABOX___FINANZONLINE__TID=... ({_('8-12 alphanumeric')})", err=True)
    click.echo(f"  FINANZONLINE_DATABOX___FINANZONLINE__BENID=... ({_('5-12 chars')})", err=True)
    click.echo(f"  FINANZONLINE_DATABOX___FINANZONLINE__PIN=... ({_('5-128 chars')})", err=True)
    click.echo(f"  FINANZONLINE_DATABOX___FINANZONLINE__HERSTELLERID=... ({_('10-24 alphanumeric')})", err=True)


def _send_error_notification(
    config: Config,
    fo_config: FinanzOnlineConfig | None,
    error_info: DataboxErrorInfo,
    recipients: list[str],
    operation: str = "databox",
) -> None:
    """Send email notification for databox error (non-fatal on failure)."""
    try:
        prepared = _prepare_notification(config, fo_config, recipients, "Error")
        if not prepared:
            return

        adapter, final_recipients = prepared
        success = adapter.send_error(
            error_type=error_info.error_type,
            error_message=error_info.message,
            operation=operation,
            recipients=final_recipients,
            return_code=error_info.return_code,
            retryable=error_info.retryable,
            diagnostics=error_info.diagnostics,
        )
        _log_notification_result(success, final_recipients, "Error")

    except Exception as e:
        logger.warning("Error notification error (non-fatal): %s", e)


def _handle_databox_error(
    error_info: DataboxErrorInfo,
    *,
    send_notification: bool,
    config: Config,
    fo_config: FinanzOnlineConfig | None,
    recipients: list[str],
    operation: str = "databox",
    hint: str | None = None,
) -> None:
    """Handle databox command errors with output and notification.

    Args:
        error_info: Consolidated error information.
        send_notification: Whether to send email notification.
        config: Application configuration.
        fo_config: FinanzOnline configuration (may be None).
        recipients: Email recipients.
        operation: Operation name for error reporting.
        hint: Optional actionable hint to display.

    Raises:
        SystemExit: Always raises with the specified exit code.
    """
    click.echo(f"\n{error_info.error_type}: {error_info.message}", err=True)

    if error_info.return_code is not None:
        info = get_return_code_info(error_info.return_code)
        click.echo(f"  {_('Return code:')} {error_info.return_code} ({info.meaning})", err=True)

    if error_info.retryable:
        click.echo(f"  {_('This error may be temporary. Try again later.')}", err=True)

    if hint:
        click.echo(f"  {_('Hint:')} {hint}", err=True)

    if send_notification:
        _send_error_notification(
            config=config,
            fo_config=fo_config,
            error_info=error_info,
            recipients=recipients,
            operation=operation,
        )

    raise SystemExit(error_info.exit_code)


def _handle_command_exception(
    exc: Exception,
    *,
    config: Config,
    fo_config: FinanzOnlineConfig | None,
    recipients: list[str],
    send_notification: bool,
    operation: str,
) -> None:
    """Handle exception from databox command with logging and error output."""
    error_info = _get_error_info(exc)
    logger.error(error_info.error_type, extra={"error": str(exc)})
    if isinstance(exc, ConfigurationError):
        _show_config_help(exc.message)

    # Get hint for filesystem errors
    hint = _get_filesystem_error_hint(exc) if isinstance(exc, FilesystemError) else None

    _handle_databox_error(
        error_info,
        send_notification=send_notification,
        config=config,
        fo_config=fo_config,
        recipients=recipients,
        operation=operation,
        hint=hint,
    )
