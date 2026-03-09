"""CLI application root group and entry point.

Purpose
-------
Define the root Click command group, global options, traceback management,
and the ``main()`` entry point.

Contents
--------
* :class:`CliContext` – typed context object for CLI commands.
* :func:`cli` – root command group with global options.
* :func:`main` – entry point for console scripts and ``python -m`` execution.

System Role
-----------
CLI adapter layer — top-level command group and entry point wiring.
"""

# pyright: reportUnusedFunction=false
from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Final

import lib_cli_exit_tools
import lib_log_rich
import lib_log_rich.runtime
import rich_click as click
from click.core import ParameterSource
from lib_layered_config import Config

from .. import __init__conf__
from ..behaviors import emit_greeting, noop_main, raise_intentional_failure
from ..config import get_config, load_app_config
from ..i18n import _, setup_locale
from ..logging_setup import init_logging

#: Shared Click context flags so help output stays consistent across commands.
CLICK_CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"]}  # noqa: C408

#: Character budget used when printing truncated tracebacks.
TRACEBACK_SUMMARY_LIMIT: Final[int] = 500
#: Character budget used when verbose tracebacks are enabled.
TRACEBACK_VERBOSE_LIMIT: Final[int] = 10_000
TracebackState = tuple[bool, bool]

logger = logging.getLogger(__name__)


def _flush_all_log_handlers() -> None:
    """Flush all handlers to ensure log output appears before subsequent prints.

    lib_log_rich uses a queue-based async console adapter. This function
    drains the queue and flushes adapters before returning, ensuring all
    pending log messages are written to the console.
    """
    if lib_log_rich.runtime.is_initialised():
        lib_log_rich.flush(timeout=2.0)


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
