"""Output formatters for CLI.

Purpose
-------
Format DataBox results for console output in human-readable
or JSON format.

Contents
--------
* :func:`.formatters.format_entries_human` - Human-readable entry list
* :func:`.formatters.format_entries_json` - JSON entry list
* :func:`.formatters.format_list_result_human` - Human-readable list result
* :func:`.formatters.format_list_result_json` - JSON list result
* :func:`.formatters.format_sync_result_human` - Human-readable sync result
* :func:`.formatters.format_sync_result_json` - JSON sync result

System Role
-----------
Adapters layer - transforms domain models into CLI output.
"""

from __future__ import annotations

from .formatters import (
    format_entries_human,
    format_entries_json,
    format_list_result_human,
    format_list_result_json,
    format_sync_result_human,
    format_sync_result_json,
)

__all__ = [
    "format_entries_human",
    "format_entries_json",
    "format_list_result_human",
    "format_list_result_json",
    "format_sync_result_human",
    "format_sync_result_json",
]
