"""CLI adapter wiring the behavior helpers into a rich-click interface.

Expose a stable command-line surface so tooling, documentation, and packaging
automation can be exercised while the richer logging helpers are being built.

Contents:
    * :data:`CLICK_CONTEXT_SETTINGS` -- shared Click settings.
    * :func:`apply_traceback_preferences` -- synchronises traceback configuration.
    * :func:`snapshot_traceback_state` / :func:`restore_traceback_state` -- state management.
    * :func:`cli` -- root command group wiring global options.
    * :func:`main` -- entry point for console scripts and ``python -m`` execution.

System Role:
    The CLI is the primary adapter for local development workflows; packaging
    targets register the console script defined in :mod:`finanzonline_databox.__init__conf__`.
"""

# pyright: reportPrivateUsage=false

# Re-export public API from submodules for backward compatibility.
# Entry points (pyproject.toml) reference ``finanzonline_databox.cli:main``.
# Tests import private helpers via ``from finanzonline_databox.cli import _parse_date`` etc.

from ._app import (
    CLICK_CONTEXT_SETTINGS,
    TRACEBACK_SUMMARY_LIMIT,
    TRACEBACK_VERBOSE_LIMIT,
    CliContext,
    apply_traceback_preferences,
    cli,
    main,
    restore_traceback_state,
    snapshot_traceback_state,
)
from ._error_handling import (
    _get_databox_error_info,
    _get_error_info,
)
from ._helpers import (
    _filter_unread_entries,
    _parse_date,
)
from ._notifications import (
    _resolve_notification_recipients,
)

# Trigger command registration on the ``cli`` group.
from . import _commands as _commands  # noqa: F401

__all__ = [
    "CLICK_CONTEXT_SETTINGS",
    "TRACEBACK_SUMMARY_LIMIT",
    "TRACEBACK_VERBOSE_LIMIT",
    "CliContext",
    "apply_traceback_preferences",
    "cli",
    "main",
    "restore_traceback_state",
    "snapshot_traceback_state",
    # Private helpers re-exported for test access
    "_get_databox_error_info",
    "_get_error_info",
    "_filter_unread_entries",
    "_parse_date",
    "_resolve_notification_recipients",
]
