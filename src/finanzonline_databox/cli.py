"""CLI adapter wiring the behavior helpers into a rich-click interface.

Expose a stable command-line surface so tooling, documentation, and packaging
automation can be exercised while the richer logging helpers are being built.

Contents:
    * :data:`CLICK_CONTEXT_SETTINGS` – shared Click settings.
    * :func:`apply_traceback_preferences` – synchronises traceback configuration.
    * :func:`snapshot_traceback_state` / :func:`restore_traceback_state` – state management.
    * :func:`cli` – root command group wiring global options.
    * :func:`main` – entry point for console scripts and ``python -m`` execution.

System Role:
    The CLI is the primary adapter for local development workflows; packaging
    targets register the console script defined in :mod:`finanzonline_databox.__init__conf__`.
"""

from __future__ import annotations

import errno
import logging
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Final

import lib_cli_exit_tools
import lib_log_rich.runtime
import rich_click as click
from click.core import ParameterSource
from lib_layered_config import Config

from . import __init__conf__
from ._datetime_utils import local_now
from .adapters.finanzonline import DataboxClient, FinanzOnlineSessionClient
from .adapters.notification import EmailNotificationAdapter
from .adapters.output import (
    format_list_result_human,
    format_list_result_json,
    format_sync_result_human,
    format_sync_result_json,
)
from .application.use_cases import (
    DownloadEntryUseCase,
    ListDataboxUseCase,
    SyncDataboxUseCase,
    SyncResult,
)
from .behaviors import emit_greeting, noop_main, raise_intentional_failure
from .config import FinanzOnlineConfig, get_config, load_app_config, load_finanzonline_config
from .config_deploy import deploy_configuration
from .config_show import display_config
from .domain.errors import (
    AuthenticationError,
    ConfigurationError,
    DataboxError,
    DataboxErrorInfo,
    DataboxOperationError,
    FilesystemError,
    SessionError,
)
from .domain.models import DataboxEntry, DataboxListRequest, DataboxListResult, FinanzOnlineCredentials
from .domain.return_codes import CliExitCode, get_return_code_info
from .enums import DeployTarget, OutputFormat, ReadFilter
from .i18n import _, setup_locale
from .logging_setup import init_logging
from .mail import EmailConfig, load_email_config_from_dict

#: Shared Click context flags so help output stays consistent across commands.
CLICK_CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"]}  # noqa: C408


#: Character budget used when printing truncated tracebacks.
TRACEBACK_SUMMARY_LIMIT: Final[int] = 500
#: Character budget used when verbose tracebacks are enabled.
TRACEBACK_VERBOSE_LIMIT: Final[int] = 10_000
TracebackState = tuple[bool, bool]

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class CliContext:
    """Typed context object for CLI command invocations.

    Replaces raw dict access on ctx.obj with typed field access.

    Attributes:
        traceback: Whether verbose tracebacks are enabled.
        config: Loaded layered configuration object.
        profile: Optional configuration profile name.
    """

    traceback: bool
    config: Config
    profile: str | None = None


def _get_cli_context(ctx: click.Context) -> CliContext:
    """Extract typed CliContext from Click context.

    Args:
        ctx: Click context with CliContext stored in obj.

    Returns:
        Typed CliContext object.
    """
    return ctx.obj  # type: ignore[return-value]


def apply_traceback_preferences(enabled: bool) -> None:
    """Synchronise shared traceback flags with the requested preference.

    Args:
        enabled: ``True`` enables full tracebacks with colour.

    Example:
        >>> apply_traceback_preferences(True)
        >>> bool(lib_cli_exit_tools.config.traceback)
        True
    """
    lib_cli_exit_tools.config.traceback = bool(enabled)
    lib_cli_exit_tools.config.traceback_force_color = bool(enabled)


def snapshot_traceback_state() -> TracebackState:
    """Capture the current traceback configuration for later restoration.

    Returns:
        Tuple of ``(traceback_enabled, force_color)``.
    """
    return (
        bool(getattr(lib_cli_exit_tools.config, "traceback", False)),
        bool(getattr(lib_cli_exit_tools.config, "traceback_force_color", False)),
    )


def restore_traceback_state(state: TracebackState) -> None:
    """Reapply a previously captured traceback configuration.

    Args:
        state: Tuple returned by :func:`snapshot_traceback_state`.
    """
    lib_cli_exit_tools.config.traceback = bool(state[0])
    lib_cli_exit_tools.config.traceback_force_color = bool(state[1])


def _store_cli_context(
    ctx: click.Context,
    *,
    traceback: bool,
    config: Config,
    profile: str | None = None,
) -> None:
    """Store CLI state in the Click context for subcommand access.

    Args:
        ctx: Click context associated with the current invocation.
        traceback: Whether verbose tracebacks were requested.
        config: Loaded layered configuration object for all subcommands.
        profile: Optional configuration profile name.
    """
    ctx.obj = CliContext(traceback=traceback, config=config, profile=profile)


def _run_cli(argv: Sequence[str] | None) -> int:
    """Execute the CLI via lib_cli_exit_tools with exception handling.

    Args:
        argv: Optional sequence of CLI arguments. None uses sys.argv.

    Returns:
        Exit code produced by the command.
    """
    try:
        return lib_cli_exit_tools.run_cli(
            cli,
            argv=list(argv) if argv is not None else None,
            prog_name=__init__conf__.shell_command,
        )
    except BaseException as exc:  # noqa: BLE001 - handled by shared printers
        tracebacks_enabled = bool(getattr(lib_cli_exit_tools.config, "traceback", False))
        apply_traceback_preferences(tracebacks_enabled)
        length_limit = TRACEBACK_VERBOSE_LIMIT if tracebacks_enabled else TRACEBACK_SUMMARY_LIMIT
        lib_cli_exit_tools.print_exception_message(trace_back=tracebacks_enabled, length_limit=length_limit)
        return lib_cli_exit_tools.get_system_exit_code(exc)


@click.group(
    help=__init__conf__.title,
    context_settings=CLICK_CONTEXT_SETTINGS,
    invoke_without_command=True,
)
@click.version_option(
    version=__init__conf__.version,
    prog_name=__init__conf__.shell_command,
    message=f"{__init__conf__.shell_command} version {__init__conf__.version}",
)
@click.option(
    "--traceback/--no-traceback",
    is_flag=True,
    default=False,
    help=_("Show full Python traceback on errors"),
)
@click.option(
    "--profile",
    type=str,
    default=None,
    help=_("Load configuration from a named profile (e.g., 'production', 'test')"),
)
@click.pass_context
def cli(ctx: click.Context, traceback: bool, profile: str | None) -> None:
    """Root command storing global flags and syncing shared traceback state.

    Loads configuration once with the profile and stores it in the Click context
    for all subcommands to access. Mirrors the traceback flag into
    ``lib_cli_exit_tools.config`` so downstream helpers observe the preference.

    Example:
        >>> from click.testing import CliRunner
        >>> runner = CliRunner()
        >>> result = runner.invoke(cli, ["hello"])
        >>> result.exit_code
        0
        >>> "Hello World" in result.output
        True
    """
    config = get_config(profile=profile)
    app_config = load_app_config(config)
    setup_locale(app_config.language)
    init_logging(config)
    _store_cli_context(ctx, traceback=traceback, config=config, profile=profile)
    apply_traceback_preferences(traceback)

    if ctx.invoked_subcommand is None:
        # No subcommand: show help unless --traceback was explicitly passed
        source = ctx.get_parameter_source("traceback")
        if source not in (ParameterSource.DEFAULT, None):
            cli_main()
        else:
            click.echo(ctx.get_help())


def cli_main() -> None:
    """Run the placeholder domain entry when callers opt into execution."""
    noop_main()


@cli.command("info", context_settings=CLICK_CONTEXT_SETTINGS)
def cli_info() -> None:
    """Print resolved metadata so users can inspect installation details."""
    with lib_log_rich.runtime.bind(job_id="cli-info", extra={"command": "info"}):
        logger.info("Displaying package information")
        __init__conf__.print_info()


@cli.command("hello", context_settings=CLICK_CONTEXT_SETTINGS)
def cli_hello() -> None:
    """Demonstrate the success path by emitting the canonical greeting."""
    with lib_log_rich.runtime.bind(job_id="cli-hello", extra={"command": "hello"}):
        logger.info("Executing hello command")
        emit_greeting()


@cli.command("fail", context_settings=CLICK_CONTEXT_SETTINGS)
def cli_fail() -> None:
    """Trigger the intentional failure helper to test error handling."""
    with lib_log_rich.runtime.bind(job_id="cli-fail", extra={"command": "fail"}):
        logger.warning("Executing intentional failure command")
        raise_intentional_failure()


@cli.command("config", context_settings=CLICK_CONTEXT_SETTINGS)
@click.option(
    "--format",
    type=click.Choice(list(OutputFormat), case_sensitive=False),
    default=OutputFormat.HUMAN,
    help=_("Output format (human-readable or JSON)"),
)
@click.option(
    "--section",
    type=str,
    default=None,
    help=_("Show only a specific configuration section (e.g., 'lib_log_rich')"),
)
@click.option(
    "--profile",
    type=str,
    default=None,
    help=_("Override profile from root command (e.g., 'production', 'test')"),
)
@click.pass_context
def cli_config(ctx: click.Context, format: str, section: str | None, profile: str | None) -> None:
    """Display the current merged configuration from all sources.

    Shows configuration loaded from defaults, application/user config files,
    .env files, and environment variables.

    Precedence: defaults -> app -> host -> user -> dotenv -> env
    """
    cli_ctx = _get_cli_context(ctx)

    # Use config from context; reload if profile override specified
    if profile:
        config = get_config(profile=profile)
        effective_profile = profile
    else:
        config = cli_ctx.config
        effective_profile = cli_ctx.profile

    output_format = OutputFormat(format.lower())
    extra = {"command": "config", "format": output_format, "profile": effective_profile}
    with lib_log_rich.runtime.bind(job_id="cli-config", extra=extra):
        logger.info("Displaying configuration", extra={"format": output_format, "section": section, "profile": effective_profile})
        display_config(config, format=output_format, section=section)


def _display_deploy_result(deployed_paths: list[Path], effective_profile: str | None, *, force: bool = False) -> None:
    """Display deployment result to user."""
    if deployed_paths:
        profile_msg = f" ({_('profile')}: {effective_profile})" if effective_profile else ""
        click.echo(f"\n{_('Configuration deployed successfully')}{profile_msg}:")
        for path in deployed_paths:
            click.echo(f"  ✓ {path}")
    elif force:
        # Force was used but nothing deployed - content is identical
        click.echo(f"\n{_('All configuration files are already up to date (content unchanged).')}")
    else:
        click.echo(f"\n{_('No files were created (all target files already exist).')}")
        click.echo(_("Use --force to overwrite existing configuration files."))


def _handle_deploy_error(exc: Exception) -> None:
    """Handle deployment errors with appropriate logging and messages."""
    if isinstance(exc, PermissionError):
        logger.error("Permission denied when deploying configuration", extra={"error": str(exc)})
        click.echo(f"\n{_('Error')}: {_('Permission denied.')} {exc}", err=True)
        click.echo(_("Hint: System-wide deployment (--target app/host) may require sudo."), err=True)
    else:
        logger.error("Failed to deploy configuration", extra={"error": str(exc), "error_type": type(exc).__name__})
        click.echo(f"\n{_('Error')}: {_('Failed to deploy configuration:')} {exc}", err=True)
    raise SystemExit(1)


@cli.command("config-deploy", context_settings=CLICK_CONTEXT_SETTINGS)
@click.option(
    "--target",
    "targets",
    type=click.Choice(list(DeployTarget), case_sensitive=False),
    multiple=True,
    required=True,
    help=_("Target configuration layer(s) to deploy to (can specify multiple)"),
)
@click.option(
    "--force",
    is_flag=True,
    default=False,
    help=_("Overwrite existing configuration files"),
)
@click.option(
    "--profile",
    type=str,
    default=None,
    help=_("Override profile from root command (e.g., 'production', 'test')"),
)
@click.pass_context
def cli_config_deploy(ctx: click.Context, targets: tuple[str, ...], force: bool, profile: str | None) -> None:
    r"""Deploy default configuration to system or user directories.

    Creates configuration files in platform-specific locations:

    \b
    - app:  System-wide application config (requires privileges)
    - host: System-wide host config (requires privileges)
    - user: User-specific config (~/.config on Linux)

    By default, existing files are not overwritten. Use --force to overwrite.
    """
    cli_ctx = _get_cli_context(ctx)
    effective_profile = profile if profile else cli_ctx.profile
    deploy_targets = tuple(DeployTarget(t.lower()) for t in targets)
    extra = {"command": "config-deploy", "targets": deploy_targets, "force": force, "profile": effective_profile}

    with lib_log_rich.runtime.bind(job_id="cli-config-deploy", extra=extra):
        logger.info("Deploying configuration", extra={"targets": deploy_targets, "force": force, "profile": effective_profile})

        try:
            deployed_paths = deploy_configuration(targets=deploy_targets, force=force, profile=effective_profile)
            _display_deploy_result(deployed_paths, effective_profile, force=force)
        except Exception as exc:
            _handle_deploy_error(exc)


# =============================================================================
# DataBox Commands
# =============================================================================


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


def _log_notification_result(success: bool, recipients: list[str], notification_type: str) -> None:
    """Log the result of a notification attempt."""
    if success:
        logger.info("%s email sent", notification_type, extra={"recipients": recipients})
    else:
        logger.warning("%s email failed", notification_type)


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


def _resolve_notification_recipients(
    explicit: list[str],
    email_config: EmailConfig,
    fo_config: FinanzOnlineConfig | None,
) -> list[str]:
    """Resolve final recipients: explicit > email config > fo_config."""
    if explicit:
        return explicit
    if email_config.default_recipients:
        return email_config.default_recipients
    if fo_config and fo_config.default_recipients:
        return fo_config.default_recipients
    return []


def _prepare_notification(
    config: Config,
    fo_config: FinanzOnlineConfig | None,
    recipients: list[str],
    notification_type: str,
) -> tuple[EmailNotificationAdapter, list[str]] | None:
    """Prepare email notification adapter and recipients.

    Args:
        config: Application configuration.
        fo_config: FinanzOnline configuration (may be None).
        recipients: Explicit recipients list.
        notification_type: Type for logging (e.g., "Email", "Error").

    Returns:
        Tuple of (adapter, final_recipients) if ready, None if skipped.
    """
    email_config = load_email_config_from_dict(config.as_dict())

    if not email_config.smtp_hosts:
        logger.warning("%s notification skipped: no SMTP hosts configured", notification_type)
        return None

    final_recipients = _resolve_notification_recipients(recipients, email_config, fo_config)
    if not final_recipients:
        logger.warning("%s notification skipped: no recipients configured", notification_type)
        return None

    return EmailNotificationAdapter(email_config), final_recipients


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


def _send_sync_notification(
    config: Config,
    fo_config: FinanzOnlineConfig,
    result: SyncResult,
    output_dir: str,
    recipients: list[str],
) -> None:
    """Send email notification for sync result (non-fatal on failure)."""
    try:
        prepared = _prepare_notification(config, fo_config, recipients, "Sync")
        if not prepared:
            return

        adapter, final_recipients = prepared
        success = adapter.send_sync_result(result, output_dir, final_recipients)
        _log_notification_result(success, final_recipients, "Sync")

    except Exception as e:
        logger.warning("Sync notification error (non-fatal): %s", e)


def _resolve_document_recipients(
    explicit: list[str],
    fo_config: FinanzOnlineConfig | None,
) -> list[str]:
    """Resolve final document recipients: explicit > fo_config.

    Args:
        explicit: Explicitly specified recipients from CLI.
        fo_config: FinanzOnline configuration (may be None).

    Returns:
        List of recipients for per-document emails, may be empty.
    """
    if explicit:
        return explicit
    if fo_config and fo_config.document_recipients:
        return fo_config.document_recipients
    return []


def _resolve_output_dir(
    explicit: str | None,
    config: Config,
    *,
    default: str,
) -> Path:
    """Resolve output directory: CLI option > config > default.

    Args:
        explicit: Explicitly specified output directory from CLI (None if not specified).
        config: Application configuration.
        default: Default path to use if not configured.

    Returns:
        Resolved output directory as Path.
    """
    if explicit is not None:
        return Path(explicit)

    # Try to get from config (load silently, use default on error)
    try:
        fo_config = load_finanzonline_config(config)
        if fo_config.output_dir is not None:
            return fo_config.output_dir
    except ConfigurationError:
        pass  # Credentials may be missing, but we can still use default output_dir

    return Path(default)


def _send_single_document_notification(
    adapter: EmailNotificationAdapter,
    entry: DataboxEntry,
    document_path: Path,
    recipients: list[str],
) -> bool:
    """Send notification for a single document, returning success status."""
    try:
        return adapter.send_document_notification(entry, document_path, recipients)
    except Exception as e:
        logger.warning("Document notification error for %s (non-fatal): %s", entry.applkey[:8], e)
        return False


def _send_document_notifications(
    config: Config,
    fo_config: FinanzOnlineConfig,
    downloaded_files: tuple[tuple[DataboxEntry, Path], ...],
    recipients: list[str],
) -> None:
    """Send per-document email notifications with attachments."""
    final_recipients = _resolve_document_recipients(recipients, fo_config)
    if not final_recipients:
        logger.debug("No document recipients configured, skipping per-document emails")
        return

    email_config = load_email_config_from_dict(config.as_dict())
    if not email_config.smtp_hosts:
        logger.warning("Document notification skipped: no SMTP hosts configured")
        return

    adapter = EmailNotificationAdapter(email_config, fo_config.email_format)
    results = [_send_single_document_notification(adapter, entry, path, final_recipients) for entry, path in downloaded_files]

    success_count = sum(results)
    logger.info("Document notifications: %d sent, %d failed to %d recipients", success_count, len(results) - success_count, len(final_recipients))


def _parse_date(date_str: str | None) -> datetime | None:
    """Parse a date string to datetime.

    Args:
        date_str: Date string in YYYY-MM-DD format or None.

    Returns:
        Parsed datetime with local timezone or None.

    Raises:
        click.BadParameter: If date format is invalid.
    """
    if date_str is None:
        return None
    try:
        parsed = datetime.strptime(date_str, "%Y-%m-%d")  # noqa: DTZ007
        return parsed.astimezone()  # Convert to local timezone
    except ValueError as exc:
        msg = f"Invalid date format: {date_str}. Use YYYY-MM-DD."
        raise click.BadParameter(msg) from exc


def _compute_date_range_from_days(days: int, max_days: int = 7) -> tuple[datetime, datetime]:
    """Compute date range from --days option.

    Args:
        days: Number of days to look back.
        max_days: Maximum allowed days (default 7 for list, 31 for sync).

    Returns:
        Tuple of (ts_zust_von, ts_zust_bis).

    Raises:
        click.BadParameter: If days is out of range.
    """
    if days < 1 or days > max_days:
        raise click.BadParameter(f"Days must be between 1 and {max_days} (API limit)", param_hint="--days")
    now = local_now()
    return now - timedelta(days=days), now


def _chunk_date_range(
    ts_zust_von: datetime,
    ts_zust_bis: datetime,
    chunk_days: int = 7,
) -> list[tuple[datetime, datetime]]:
    """Split a date range into chunks of max chunk_days each.

    The BMF DataBox API only allows 7 days between ts_zust_von and ts_zust_bis.
    This function splits larger ranges into multiple 7-day chunks.

    Args:
        ts_zust_von: Start of date range (oldest).
        ts_zust_bis: End of date range (newest).
        chunk_days: Maximum days per chunk (default 7, API limit).

    Returns:
        List of (start, end) datetime tuples, ordered from oldest to newest.
    """
    chunks: list[tuple[datetime, datetime]] = []
    current_start = ts_zust_von

    while current_start < ts_zust_bis:
        current_end = min(current_start + timedelta(days=chunk_days), ts_zust_bis)
        chunks.append((current_start, current_end))
        current_start = current_end

    return chunks


def _sum_sync_stats(results: list[SyncResult]) -> tuple[int, int, int, int, int, int, int]:
    """Sum statistics from multiple sync results."""
    total_retrieved = total_listed = unread_listed = downloaded = skipped = failed = total_bytes = 0
    for r in results:
        total_retrieved += r.total_retrieved
        total_listed += r.total_listed
        unread_listed += r.unread_listed
        downloaded += r.downloaded
        skipped += r.skipped
        failed += r.failed
        total_bytes += r.total_bytes
    return total_retrieved, total_listed, unread_listed, downloaded, skipped, failed, total_bytes


def _collect_downloaded_files(results: list[SyncResult]) -> tuple[tuple[DataboxEntry, Path], ...]:
    """Collect all downloaded files from multiple sync results."""
    all_files: list[tuple[DataboxEntry, Path]] = []
    for r in results:
        all_files.extend(r.downloaded_files)
    return tuple(all_files)


def _aggregate_sync_results(results: list[SyncResult]) -> SyncResult:
    """Aggregate multiple SyncResults into one."""
    if not results:
        return SyncResult(
            total_retrieved=0,
            total_listed=0,
            unread_listed=0,
            downloaded=0,
            skipped=0,
            failed=0,
            total_bytes=0,
            downloaded_files=(),
        )

    total_retrieved, total_listed, unread_listed, downloaded, skipped, failed, total_bytes = _sum_sync_stats(results)
    return SyncResult(
        total_retrieved=total_retrieved,
        total_listed=total_listed,
        unread_listed=unread_listed,
        downloaded=downloaded,
        skipped=skipped,
        failed=failed,
        total_bytes=total_bytes,
        downloaded_files=_collect_downloaded_files(results),
    )


def _deduplicate_entries(results: list[DataboxListResult]) -> tuple[DataboxEntry, ...]:
    """Collect and deduplicate entries from multiple results by applkey."""
    seen: set[str] = set()
    unique: list[DataboxEntry] = []
    for r in results:
        for entry in r.entries:
            if entry.applkey not in seen:
                unique.append(entry)
                seen.add(entry.applkey)
    return tuple(unique)


def _aggregate_list_results(results: list[DataboxListResult]) -> DataboxListResult:
    """Aggregate multiple list results from date range chunks."""
    if not results:
        return DataboxListResult(rc=0, msg="OK", entries=())

    all_success = all(r.is_success for r in results)
    return DataboxListResult(
        rc=0 if all_success else -1,
        msg="OK" if all_success else "Some chunks failed",
        entries=_deduplicate_entries(results),
    )


def _resolve_date_range(
    days: int | None,
    date_from: str | None,
    date_to: str | None,
    max_days: int = 7,
) -> tuple[datetime | None, datetime | None]:
    """Resolve date range from --days or --from/--to options.

    Args:
        days: Number of days to look back (overrides date_from/date_to).
        date_from: Start date string.
        date_to: End date string.
        max_days: Maximum allowed days for --days option.

    Returns:
        Tuple of (ts_zust_von, ts_zust_bis), either may be None.
    """
    if days is not None:
        return _compute_date_range_from_days(days, max_days)
    return _parse_date(date_from), _parse_date(date_to)


def _format_sync_result(result: SyncResult, output_dir: str, output_format: str) -> str:
    """Format sync result for output.

    Args:
        result: SyncResult to format.
        output_dir: Output directory path.
        output_format: Output format string ('json' or 'human').

    Returns:
        Formatted string.
    """
    if OutputFormat(output_format.lower()) == OutputFormat.JSON:
        return format_sync_result_json(result, output_dir)
    return format_sync_result_human(result, output_dir)


def _format_list_result(result: DataboxListResult, output_format: str) -> str:
    """Format list result for output.

    Args:
        result: DataboxListResult to format.
        output_format: Output format string ('json' or 'human').

    Returns:
        Formatted string.
    """
    if OutputFormat(output_format.lower()) == OutputFormat.JSON:
        return format_list_result_json(result)
    return format_list_result_human(result)


def _filter_unread_entries(result: DataboxListResult) -> DataboxListResult:
    """Filter list result to include only unread entries.

    Args:
        result: Original list result with all entries.

    Returns:
        New DataboxListResult with only unread entries.
    """
    unread_entries = tuple(e for e in result.entries if e.is_unread)
    return DataboxListResult(
        rc=result.rc,
        msg=result.msg,
        entries=unread_entries,
        timestamp=result.timestamp,
    )


def _filter_read_entries(result: DataboxListResult) -> DataboxListResult:
    """Filter list result to include only read entries.

    Args:
        result: Original list result with all entries.

    Returns:
        New DataboxListResult with only read entries.
    """
    read_entries = tuple(e for e in result.entries if e.is_read)
    return DataboxListResult(
        rc=result.rc,
        msg=result.msg,
        entries=read_entries,
        timestamp=result.timestamp,
    )


def _resolve_effective_days(
    days: int | None,
    date_from: str | None,
    date_to: str | None,
    read_filter: ReadFilter,
) -> int | None:
    """Resolve effective days, auto-setting for read/all filters.

    BMF API requires date range to return read documents, so auto-set 31 days
    when --all or --read is specified without explicit date parameters.
    """
    if days is not None or date_from is not None or date_to is not None:
        return days

    if read_filter in (ReadFilter.ALL, ReadFilter.READ):
        logger.info("Auto-setting --days 31 for read_filter=%s (API requires date range)", read_filter)
        return 31

    return days


def _execute_chunked_list(
    use_case: ListDataboxUseCase,
    credentials: FinanzOnlineCredentials,
    erltyp: str,
    ts_zust_von: datetime,
    ts_zust_bis: datetime,
) -> DataboxListResult:
    """Execute list operation with date range chunking."""
    date_chunks = _chunk_date_range(ts_zust_von, ts_zust_bis, chunk_days=7)
    logger.debug("Listing %d date range chunk(s)", len(date_chunks))

    chunk_results: list[DataboxListResult] = []
    for chunk_start, chunk_end in date_chunks:
        request = DataboxListRequest(
            erltyp=erltyp,
            ts_zust_von=chunk_start,
            ts_zust_bis=chunk_end,
        )
        chunk_result = use_case.execute(credentials=credentials, request=request)
        chunk_results.append(chunk_result)

    return _aggregate_list_results(chunk_results)


def _execute_list_operation(
    use_case: ListDataboxUseCase,
    credentials: FinanzOnlineCredentials,
    erltyp: str,
    ts_zust_von: datetime | None,
    ts_zust_bis: datetime | None,
) -> DataboxListResult:
    """Execute list operation, using chunking if date range is provided."""
    if ts_zust_von is not None and ts_zust_bis is not None:
        return _execute_chunked_list(use_case, credentials, erltyp, ts_zust_von, ts_zust_bis)

    request = DataboxListRequest(erltyp=erltyp)
    return use_case.execute(credentials=credentials, request=request)


def _apply_list_filters(
    result: DataboxListResult,
    read_filter: ReadFilter,
    reference: str,
) -> DataboxListResult:
    """Apply read status and reference filters to list result."""
    if not result.is_success:
        return result

    if read_filter == ReadFilter.UNREAD:
        result = _filter_unread_entries(result)
    elif read_filter == ReadFilter.READ:
        result = _filter_read_entries(result)

    if reference:
        result = _filter_by_reference(result, reference)

    return result


def _execute_chunked_sync(
    use_case: SyncDataboxUseCase,
    credentials: FinanzOnlineCredentials,
    output_dir: Path,
    erltyp: str,
    reference: str,
    read_filter: ReadFilter,
    skip_existing: bool,
    ts_zust_von: datetime,
    ts_zust_bis: datetime,
) -> SyncResult:
    """Execute sync operation across chunked date ranges."""
    date_chunks = _chunk_date_range(ts_zust_von, ts_zust_bis, chunk_days=7)
    logger.debug("Syncing %d date range chunk(s)", len(date_chunks))

    chunk_results: list[SyncResult] = []
    for chunk_idx, (chunk_start, chunk_end) in enumerate(date_chunks, start=1):
        # Calculate days from original start date
        days_start = (chunk_start - ts_zust_von).days
        days_end = (chunk_end - ts_zust_von).days

        request = DataboxListRequest(erltyp=erltyp, ts_zust_von=chunk_start, ts_zust_bis=chunk_end)
        chunk_result = use_case.execute(
            credentials=credentials,
            output_dir=output_dir,
            request=request,
            skip_existing=skip_existing,
            anbringen_filter=reference,
            read_filter=read_filter,
        )
        chunk_results.append(chunk_result)

        # Log chunk progress
        logger.info(
            _("Chunk %d (days %d-%d): %d from API, %d after filter - %d unread"),
            chunk_idx,
            days_start,
            days_end,
            chunk_result.total_retrieved,
            chunk_result.total_listed,
            chunk_result.unread_listed,
        )

    return _aggregate_sync_results(chunk_results)


def _send_sync_notifications_if_enabled(
    no_email: bool,
    config: Config,
    fo_config: FinanzOnlineConfig,
    result: SyncResult,
    output_dir: str,
    recipients: list[str],
    document_recipients: list[str],
) -> None:
    """Send sync and document notifications if enabled and applicable."""
    if no_email:
        return

    if result.has_new_downloads:
        _send_sync_notification(config, fo_config, result, output_dir, recipients)

    if result.downloaded_files:
        _send_document_notifications(config, fo_config, result.downloaded_files, document_recipients)


def _filter_by_reference(result: DataboxListResult, reference: str) -> DataboxListResult:
    """Filter list result to include only entries matching the reference.

    Args:
        result: Original list result with all entries.
        reference: Reference (anbringen) to filter by.

    Returns:
        New DataboxListResult with only matching entries.
    """
    filtered = tuple(e for e in result.entries if e.anbringen == reference)
    return DataboxListResult(
        rc=result.rc,
        msg=result.msg,
        entries=filtered,
        timestamp=result.timestamp,
    )


@cli.command("list", context_settings=CLICK_CONTEXT_SETTINGS)
@click.option(
    "--erltyp",
    "-t",
    type=str,
    default="",
    help=_("Document type filter (B=Bescheide, M=Mitteilungen, I=Info, P=Protokolle, empty=all unread)"),
)
@click.option(
    "--from",
    "date_from",
    type=str,
    default=None,
    help=_("Start date filter (YYYY-MM-DD, max 31 days ago)"),
)
@click.option(
    "--to",
    "date_to",
    type=str,
    default=None,
    help=_("End date filter (YYYY-MM-DD, max 7 days after start)"),
)
@click.option(
    "--days",
    "-d",
    type=int,
    default=None,
    help=_("List documents from last N days (overrides --from/--to, max 31)"),
)
@click.option(
    "--unread",
    "-u",
    "read_filter",
    flag_value=ReadFilter.UNREAD.value,
    default=ReadFilter.UNREAD.value,
    help=_("Show only unread documents (default)"),
)
@click.option(
    "--read",
    "read_filter",
    flag_value=ReadFilter.READ.value,
    help=_("Show only read documents"),
)
@click.option(
    "--all",
    "-a",
    "read_filter",
    flag_value=ReadFilter.ALL.value,
    help=_("Show all documents"),
)
@click.option(
    "--reference",
    "-r",
    type=str,
    default="",
    help=_("Reference filter (anbringen, e.g., UID, E1)"),
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(list(OutputFormat), case_sensitive=False),
    default=OutputFormat.HUMAN,
    help=_("Output format (default: human)"),
)
@click.pass_context
def cli_list(
    ctx: click.Context,
    erltyp: str,
    date_from: str | None,
    date_to: str | None,
    days: int | None,
    read_filter: str,
    reference: str,
    output_format: str,
) -> None:
    """List DataBox entries (documents available for download).

    Lists unread documents from your FinanzOnline DataBox. Use filters
    to narrow down the results by document type or date range.

    \b
    Document Types (erltyp):
      B  - Bescheide (decisions/decrees)
      M  - Mitteilungen (notifications)
      I  - Informationen (information)
      P  - Protokolle (protocols)
      EU - EU-Erledigungen
      (empty) - All unread documents

    \b
    Exit Codes:
      0 - Success (entries listed)
      2 - Configuration error
      3 - Authentication error
      4 - Operation error

    \b
    Examples:
      finanzonline-databox list
      finanzonline-databox list --erltyp B
      finanzonline-databox list -t P -r UID
      finanzonline-databox list --days 7 --unread
      finanzonline-databox list --days 7 --read
      finanzonline-databox list --days 7 --all
      finanzonline-databox list --from 2024-01-01 --to 2024-01-07
      finanzonline-databox list --format json
    """
    cli_ctx = _get_cli_context(ctx)
    config = cli_ctx.config

    # Convert string to enum at boundary (Click passes strings via flag_value)
    read_filter_enum = ReadFilter(read_filter)

    effective_days = _resolve_effective_days(days, date_from, date_to, read_filter_enum)
    ts_zust_von, ts_zust_bis = _resolve_date_range(effective_days, date_from, date_to, max_days=31)

    extra = {"command": "list", "erltyp": erltyp, "reference": reference, "format": output_format, "days": effective_days, "read_filter": read_filter_enum}

    with lib_log_rich.runtime.bind(job_id="cli-list", extra=extra):
        try:
            fo_config = load_finanzonline_config(config)
            logger.info("FinanzOnline configuration loaded")

            use_case = ListDataboxUseCase(
                FinanzOnlineSessionClient(timeout=fo_config.session_timeout),
                DataboxClient(timeout=fo_config.query_timeout),
            )

            result = _execute_list_operation(use_case, fo_config.credentials, erltyp, ts_zust_von, ts_zust_bis)
            result = _apply_list_filters(result, read_filter_enum, reference)

            click.echo(_format_list_result(result, output_format))
            raise SystemExit(CliExitCode.SUCCESS if result.is_success else CliExitCode.DOWNLOAD_ERROR)

        except (ConfigurationError, AuthenticationError, SessionError, DataboxOperationError, FilesystemError, ValueError, DataboxError) as exc:
            _handle_command_exception(exc, config=config, fo_config=None, recipients=[], send_notification=False, operation="list")


def _resolve_download_filename(
    output_dir: Path,
    filename: str | None,
    applkey: str,
    credentials: FinanzOnlineCredentials,
    session_client: FinanzOnlineSessionClient,
    databox_client: DataboxClient,
) -> Path:
    """Resolve output path for download, looking up entry metadata if needed."""
    if filename:
        return output_dir / filename

    # Look up entry to get filebez for proper filename
    list_use_case = ListDataboxUseCase(session_client, databox_client)
    list_result = list_use_case.execute(credentials)

    entry = next((e for e in list_result.entries if e.applkey == applkey), None)
    if entry:
        return output_dir / entry.suggested_filename

    # Fallback if entry not found in list (may be older than 31 days)
    return output_dir / f"{applkey}.bin"


@cli.command("download", context_settings=CLICK_CONTEXT_SETTINGS)
@click.argument("applkey")
@click.option(
    "--output",
    "-o",
    type=click.Path(exists=False, dir_okay=True, file_okay=False),
    default=None,
    help=_("Output directory for downloaded file (default: config or current directory)"),
)
@click.option(
    "--filename",
    "-f",
    type=str,
    default=None,
    help=_("Override output filename (default: auto-generated from entry metadata)"),
)
@click.pass_context
def cli_download(
    ctx: click.Context,
    applkey: str,
    output: str | None,
    filename: str | None,
) -> None:
    """Download a specific document from DataBox.

    Downloads a document using its applkey (obtained from 'list' command).
    The document is saved to the specified output directory.

    \b
    Exit Codes:
      0 - Success (document downloaded)
      2 - Configuration error
      3 - Authentication error
      4 - Operation error

    \b
    Examples:
      finanzonline-databox download abc123def456
      finanzonline-databox download abc123def456 --output /tmp/downloads
      finanzonline-databox download abc123def456 -f my_document.pdf
    """
    cli_ctx = _get_cli_context(ctx)
    config = cli_ctx.config

    # Resolve output directory: CLI option > config > default (current directory)
    output_dir = _resolve_output_dir(output, config, default=".")

    extra = {"command": "download", "applkey": applkey, "output_dir": str(output_dir)}

    with lib_log_rich.runtime.bind(job_id="cli-download", extra=extra):
        try:
            fo_config = load_finanzonline_config(config)
            logger.info("FinanzOnline configuration loaded")

            # Ensure output directory exists
            output_dir.mkdir(parents=True, exist_ok=True)

            session_client = FinanzOnlineSessionClient(timeout=fo_config.session_timeout)
            databox_client = DataboxClient(timeout=fo_config.query_timeout)

            output_path = _resolve_download_filename(output_dir, filename, applkey, fo_config.credentials, session_client, databox_client)

            download_use_case = DownloadEntryUseCase(session_client, databox_client)
            result, saved_path = download_use_case.execute(
                credentials=fo_config.credentials,
                applkey=applkey,
                output_path=output_path,
            )

            if result.is_success:
                click.echo(f"{_('Downloaded')}: {saved_path}")
                click.echo(f"{_('Size')}: {result.content_size} bytes")
                raise SystemExit(CliExitCode.SUCCESS)
            else:
                click.echo(f"{_('Error')}: {result.msg}", err=True)
                raise SystemExit(CliExitCode.DOWNLOAD_ERROR)

        except (ConfigurationError, AuthenticationError, SessionError, DataboxOperationError, FilesystemError, ValueError, DataboxError) as exc:
            _handle_command_exception(exc, config=config, fo_config=None, recipients=[], send_notification=False, operation="download")


@cli.command("sync", context_settings=CLICK_CONTEXT_SETTINGS)
@click.option(
    "--output",
    "-o",
    type=click.Path(exists=False, dir_okay=True, file_okay=False),
    default=None,
    help=_("Output directory for downloaded files (default: config or ./databox)"),
)
@click.option(
    "--erltyp",
    "-t",
    type=str,
    default="",
    help=_("Document type filter (B=Bescheide, M=Mitteilungen, I=Info, P=Protokolle, empty=all)"),
)
@click.option(
    "--reference",
    "-r",
    type=str,
    default="",
    help=_("Reference filter (anbringen, e.g., UID, E1)"),
)
@click.option(
    "--days",
    type=int,
    default=31,
    help=_("Number of days to look back (default: 31, max: 31)"),
)
@click.option(
    "--unread",
    "-u",
    "read_filter",
    flag_value=ReadFilter.UNREAD.value,
    default=ReadFilter.UNREAD.value,
    help=_("Sync only unread documents (default)"),
)
@click.option(
    "--read",
    "read_filter",
    flag_value=ReadFilter.READ.value,
    help=_("Sync only read documents"),
)
@click.option(
    "--all",
    "-a",
    "read_filter",
    flag_value=ReadFilter.ALL.value,
    help=_("Sync all documents"),
)
@click.option(
    "--skip-existing/--no-skip-existing",
    default=True,
    help=_("Skip files that already exist (default: skip)"),
)
@click.option(
    "--no-email",
    is_flag=True,
    default=False,
    help=_("Disable email notification (default: email enabled)"),
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(list(OutputFormat), case_sensitive=False),
    default=OutputFormat.HUMAN,
    help=_("Output format (default: human)"),
)
@click.option(
    "--recipient",
    "recipients",
    multiple=True,
    help=_("Email recipient for sync summary (can specify multiple, uses config default if not specified)"),
)
@click.option(
    "--document-recipient",
    "document_recipients",
    multiple=True,
    help=_("Email recipient for per-document notifications with attachments (can specify multiple)"),
)
@click.pass_context
def cli_sync(
    ctx: click.Context,
    output: str | None,
    erltyp: str,
    reference: str,
    days: int,
    read_filter: str,
    skip_existing: bool,
    no_email: bool,
    output_format: str,
    recipients: tuple[str, ...],
    document_recipients: tuple[str, ...],
) -> None:
    """Sync all new DataBox entries to local directory.

    Downloads all new documents from FinanzOnline DataBox that match
    the specified filters. Documents are organized by date and type.

    \b
    Exit Codes:
      0 - Success (all synced)
      1 - Partial success (some failed)
      2 - Configuration error
      3 - Authentication error
      4 - Operation error

    \b
    Examples:
      finanzonline-databox sync
      finanzonline-databox sync --output /var/databox
      finanzonline-databox sync --erltyp B --days 7
      finanzonline-databox sync --days 7 --unread
      finanzonline-databox sync --days 7 --read
      finanzonline-databox sync --days 7 --all
      finanzonline-databox sync -t P -r UID
      finanzonline-databox sync --no-skip-existing
      finanzonline-databox sync --format json --no-email
    """
    cli_ctx = _get_cli_context(ctx)
    config = cli_ctx.config

    # Convert string to enum at boundary (Click passes strings via flag_value)
    read_filter_enum = ReadFilter(read_filter)

    # Resolve output directory: CLI option > config > default
    output_dir = _resolve_output_dir(output, config, default="./databox")
    recipients_list = list(recipients)
    document_recipients_list = list(document_recipients)
    fo_config: FinanzOnlineConfig | None = None
    clamped_days = min(days, 31)  # Max 31 days
    ts_zust_von, ts_zust_bis = _compute_date_range_from_days(clamped_days, max_days=31)

    extra = {
        "command": "sync",
        "output_dir": str(output_dir),
        "erltyp": erltyp,
        "reference": reference,
        "days": clamped_days,
        "read_filter": read_filter_enum,
        "skip_existing": skip_existing,
        "format": output_format,
    }

    with lib_log_rich.runtime.bind(job_id="cli-sync", extra=extra):
        try:
            fo_config = load_finanzonline_config(config)
            logger.info("FinanzOnline configuration loaded")

            output_dir.mkdir(parents=True, exist_ok=True)

            use_case = SyncDataboxUseCase(
                FinanzOnlineSessionClient(timeout=fo_config.session_timeout),
                DataboxClient(timeout=fo_config.query_timeout),
            )

            result = _execute_chunked_sync(
                use_case, fo_config.credentials, output_dir, erltyp, reference, read_filter_enum, skip_existing, ts_zust_von, ts_zust_bis
            )

            click.echo(_format_sync_result(result, str(output_dir), output_format))
            _send_sync_notifications_if_enabled(no_email, config, fo_config, result, str(output_dir), recipients_list, document_recipients_list)

            raise SystemExit(CliExitCode.SUCCESS if result.is_success else CliExitCode.DOWNLOAD_ERROR)

        except (ConfigurationError, AuthenticationError, SessionError, DataboxOperationError, FilesystemError, ValueError, DataboxError) as exc:
            _handle_command_exception(exc, config=config, fo_config=fo_config, recipients=recipients_list, send_notification=not no_email, operation="sync")


def main(argv: Sequence[str] | None = None, *, restore_traceback: bool = True) -> int:
    """Execute the CLI with error handling and return the exit code.

    Provides the single entry point used by console scripts and
    ``python -m`` execution so that behaviour stays identical across transports.

    Args:
        argv: Optional sequence of CLI arguments. None uses sys.argv.
        restore_traceback: Whether to restore prior traceback configuration after execution.

    Returns:
        Exit code reported by the CLI run.
    """
    previous_state = snapshot_traceback_state()
    try:
        return _run_cli(argv)
    finally:
        if restore_traceback:
            restore_traceback_state(previous_state)
        if lib_log_rich.runtime.is_initialised():
            lib_log_rich.runtime.shutdown()
