"""Output formatters for CLI display.

Purpose
-------
Transform DataBox results into formatted output for
console display in either human-readable or JSON format.

Contents
--------
* :func:`format_entries_human` - Human-readable entry list
* :func:`format_entries_json` - JSON entry list
* :func:`format_sync_result_human` - Human-readable sync result

System Role
-----------
Adapters layer - transforms domain models into CLI output strings.

Examples
--------
>>> from datetime import datetime, date
>>> from finanzonline_databox.domain.models import DataboxEntry, FileType, ReadStatus
>>> entry = DataboxEntry(
...     stnr="12-345/6789", name="Test", anbringen="E1",
...     zrvon="2024", zrbis="2024", datbesch=date(2024, 1, 15),
...     erltyp="B", fileart=FileType.PDF, ts_zust=datetime(2024, 1, 15).astimezone(),
...     applkey="abc123def456", filebez="Test doc", status=ReadStatus.UNREAD
... )
>>> output = format_entries_human([entry])
>>> "E1" in output
True
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from finanzonline_databox._format_utils import format_bytes as _format_bytes
from finanzonline_databox.i18n import _

if TYPE_CHECKING:
    from finanzonline_databox.application.use_cases import SyncResult
    from finanzonline_databox.domain.models import DataboxEntry, DataboxListResult


# ANSI color constants
_RESET = "\033[0m"
_BOLD = "\033[1m"
_GREEN = "\033[32m"
_RED = "\033[31m"
_YELLOW = "\033[33m"
_CYAN = "\033[36m"
_DIM = "\033[2m"


def _entry_to_dict(entry: DataboxEntry) -> dict[str, Any]:
    """Convert DataboxEntry to JSON-serializable dict.

    Note on enum serialization:
        IntEnum fields (fileart, status) serialize to their names (e.g., "PDF", "UNREAD")
        for human readability in JSON output. This matches the common expectation that
        JSON consumers want descriptive strings rather than internal integer codes.
        The original integer values are not exposed in JSON output.
    """
    return {
        "stnr": entry.stnr,
        "name": entry.name,
        "anbringen": entry.anbringen,
        "zrvon": entry.zrvon,
        "zrbis": entry.zrbis,
        "datbesch": entry.datbesch.isoformat(),
        "erltyp": entry.erltyp,
        "fileart": entry.fileart.name,
        "ts_zust": entry.ts_zust.isoformat(),
        "applkey": entry.applkey,
        "filebez": entry.filebez,
        "status": entry.status.name,
        "is_unread": entry.is_unread,
        "suggested_filename": entry.suggested_filename,
    }


def _format_status(entry: DataboxEntry, width: int = 8) -> str:
    """Format read status with color, padded to specified width."""
    if entry.is_unread:
        text = _("NEW")
        padding = " " * (width - len(text))
        return f"{_YELLOW}{_BOLD}{text}{_RESET}{padding}"
    text = _("read")
    padding = " " * (width - len(text))
    return f"{_DIM}{text}{_RESET}{padding}"


def _format_entry_line(entry: DataboxEntry, index: int) -> str:
    """Format a single entry as a line for list display."""
    status = _format_status(entry, width=8)
    date_str = entry.datbesch.strftime("%Y-%m-%d")
    idx_str = f"[{index + 1}]"
    return f"{_DIM}{idx_str:4}{_RESET} {_CYAN}{entry.erltyp:5}{_RESET} {date_str:11} {entry.anbringen:11} {status}{entry.filebez[:40]:42} {_DIM}{entry.applkey}{_RESET}"


def format_entries_human(entries: list[DataboxEntry] | tuple[DataboxEntry, ...]) -> str:
    """Format databox entries as human-readable text.

    Produces colored console output suitable for terminal display.
    Uses ANSI escape codes for color highlighting.

    Args:
        entries: List of databox entries to format.

    Returns:
        Formatted string for console output.
    """
    if not entries:
        return f"{_YELLOW}{_('No entries found')}{_RESET}"

    unread_count = sum(1 for e in entries if e.is_unread)
    header_lines = [
        f"{_BOLD}{_('DataBox Entries')}{_RESET}",
        "=" * 95,
        f"{_('Total:')} {len(entries)} ({unread_count} {_('unread')})",
        "",
        f"{_DIM}{'#':4} {'Type':5} {'Date':11} {'Reference':11} {'Status':8} {'Description':42} {'Applkey'}{_RESET}",
        "-" * 95,
    ]

    entry_lines = [_format_entry_line(entry, i) for i, entry in enumerate(entries)]

    return "\n".join(header_lines + entry_lines)


def format_entries_json(entries: list[DataboxEntry] | tuple[DataboxEntry, ...]) -> str:
    """Format databox entries as JSON.

    Produces structured JSON output suitable for programmatic
    consumption and piping to other tools.

    Args:
        entries: List of databox entries to format.

    Returns:
        JSON string representation.
    """
    data = [_entry_to_dict(entry) for entry in entries]
    return json.dumps({"entries": data, "count": len(data)}, indent=2)


def format_list_result_human(result: DataboxListResult) -> str:
    """Format list result as human-readable text.

    Args:
        result: DataBox list result to format.

    Returns:
        Formatted string for console output.
    """
    if not result.is_success:
        return f"{_RED}{_BOLD}{_('Error')}{_RESET}: {result.msg} (code {result.rc})"

    return format_entries_human(result.entries)


def format_list_result_json(result: DataboxListResult) -> str:
    """Format list result as JSON.

    Args:
        result: DataBox list result to format.

    Returns:
        JSON string representation.
    """
    if not result.is_success:
        return json.dumps(
            {
                "success": False,
                "rc": result.rc,
                "msg": result.msg,
                "entries": [],
                "count": 0,
            },
            indent=2,
        )

    data = [_entry_to_dict(entry) for entry in result.entries]
    return json.dumps(
        {
            "success": True,
            "rc": result.rc,
            "entries": data,
            "count": len(data),
            "unread_count": result.unread_count,
            "timestamp": result.timestamp.isoformat(),
        },
        indent=2,
    )


def _get_sync_notices(result: SyncResult) -> list[str]:
    """Get status notices for sync result."""
    notices: list[str] = []
    if result.downloaded > 0:
        notices.extend(["", f"{_GREEN}{_('New documents have been downloaded.')}{_RESET}"])
    if result.failed > 0:
        notices.extend(["", f"{_YELLOW}{_('WARNING: Some downloads failed. Check logs for details.')}{_RESET}"])
    return notices


def format_sync_result_human(result: SyncResult, output_dir: str) -> str:
    """Format sync result as human-readable text.

    Args:
        result: Sync operation result.
        output_dir: Directory where files were saved.

    Returns:
        Formatted string for console output.
    """
    status_color = _GREEN if result.is_success else _YELLOW
    status = _("SUCCESS") if result.is_success else _("COMPLETED WITH WARNINGS")
    failed_color = _RED if result.failed > 0 else _DIM

    lines = [
        f"{_BOLD}{_('DataBox Sync Result')}{_RESET}",
        "=" * 50,
        f"{_('Status:')}       {status_color}{status}{_RESET}",
        f"{_('Output Dir:')}   {output_dir}",
        "",
        f"{_BOLD}{_('Statistics')}{_RESET}",
        "-" * 30,
        f"{_('Total Listed:')}   {result.total_listed}",
        f"{_('Downloaded:')}     {_GREEN}{result.downloaded}{_RESET}",
        f"{_('Skipped:')}        {_DIM}{result.skipped}{_RESET}",
        f"{_('Failed:')}         {failed_color}{result.failed}{_RESET}",
        f"{_('Total Size:')}     {_format_bytes(result.total_bytes)}",
    ]
    lines.extend(_get_sync_notices(result))
    return "\n".join(lines)


def format_sync_result_json(result: SyncResult, output_dir: str) -> str:
    """Format sync result as JSON.

    Args:
        result: Sync operation result.
        output_dir: Directory where files were saved.

    Returns:
        JSON string representation.
    """
    return json.dumps(
        {
            "success": result.is_success,
            "output_dir": output_dir,
            "total_listed": result.total_listed,
            "downloaded": result.downloaded,
            "skipped": result.skipped,
            "failed": result.failed,
            "total_bytes": result.total_bytes,
            "has_new_downloads": result.has_new_downloads,
        },
        indent=2,
    )
