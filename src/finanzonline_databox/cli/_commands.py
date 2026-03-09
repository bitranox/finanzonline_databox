"""CLI command definitions for configuration and DataBox operations.

Purpose
-------
Register ``config``, ``config-deploy``, ``list``, ``download``, and ``sync``
commands on the root CLI group.

Contents
--------
* :func:`cli_config` – display merged configuration.
* :func:`cli_config_deploy` – deploy default configuration files.
* :func:`cli_list` – list DataBox entries.
* :func:`cli_download` – download a single document.
* :func:`cli_sync` – sync all new documents to a local directory.

System Role
-----------
CLI adapter layer — command wiring and argument handling.
"""

# pyright: reportPrivateUsage=false
from __future__ import annotations

import logging
from pathlib import Path

import lib_log_rich.runtime
import rich_click as click

from ..adapters.finanzonline import DataboxClient, FinanzOnlineSessionClient
from ..application.use_cases import DownloadEntryUseCase, ListDataboxUseCase, SyncDataboxUseCase
from ..config import FinanzOnlineConfig, get_config, load_finanzonline_config
from ..config_deploy import deploy_configuration
from ..config_show import display_config
from ..domain.errors import (
    AuthenticationError,
    ConfigurationError,
    DataboxError,
    DataboxOperationError,
    FilesystemError,
    SessionError,
)
from ..domain.return_codes import CliExitCode
from ..enums import DeployTarget, OutputFormat, ReadFilter
from ..i18n import _
from ._app import CLICK_CONTEXT_SETTINGS, _flush_all_log_handlers, _get_cli_context, cli  # pyright: ignore[reportPrivateUsage]
from ._error_handling import _handle_command_exception  # pyright: ignore[reportPrivateUsage]
from ._helpers import (  # pyright: ignore[reportPrivateUsage]
    _apply_list_filters,
    _compute_date_range_from_days,
    _execute_chunked_sync,
    _execute_list_operation,
    _format_list_result,
    _format_sync_result,
    _resolve_date_range,
    _resolve_download_filename,
    _resolve_effective_days,
    _resolve_output_dir,
)
from ._notifications import _send_sync_notifications_if_enabled  # pyright: ignore[reportPrivateUsage]

logger = logging.getLogger(__name__)


# =============================================================================
# Configuration Commands
# =============================================================================


def _display_deploy_result(deployed_paths: list[Path], effective_profile: str | None, *, force: bool = False) -> None:
    """Display deployment result to user."""
    if deployed_paths:
        profile_msg = f" ({_('profile')}: {effective_profile})" if effective_profile else ""
        click.echo(f"\n{_('Configuration deployed successfully')}{profile_msg}:")
        for path in deployed_paths:
            click.echo(f"  \u2713 {path}")
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

            _flush_all_log_handlers()
            click.echo(_format_sync_result(result, str(output_dir), output_format))
            _send_sync_notifications_if_enabled(no_email, config, fo_config, result, str(output_dir), recipients_list, document_recipients_list)

            raise SystemExit(CliExitCode.SUCCESS if result.is_success else CliExitCode.DOWNLOAD_ERROR)

        except (ConfigurationError, AuthenticationError, SessionError, DataboxOperationError, FilesystemError, ValueError, DataboxError) as exc:
            _handle_command_exception(exc, config=config, fo_config=fo_config, recipients=recipients_list, send_notification=not no_email, operation="sync")
