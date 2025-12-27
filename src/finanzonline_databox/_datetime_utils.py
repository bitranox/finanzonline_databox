"""Shared datetime utilities for internal use.

This module provides common datetime parsing and formatting functions
used across multiple adapters to avoid code duplication.

Contents:
    * :func:`local_now` - Get current local time (timezone-aware)
    * :func:`parse_iso_datetime` - Parse ISO format string to datetime
    * :func:`format_iso_datetime` - Format datetime to ISO string
    * :func:`format_local_time` - Format datetime as local time string
"""

from __future__ import annotations

from datetime import datetime


def local_now() -> datetime:
    """Get current local time as timezone-aware datetime.

    Returns:
        Current datetime with local timezone.
    """
    return datetime.now().astimezone()


def parse_iso_datetime(iso_str: str) -> datetime:
    """Parse ISO format datetime string to datetime object.

    Args:
        iso_str: ISO format datetime string (e.g., "2025-01-15T10:30:00Z").

    Returns:
        Timezone-aware datetime object.
    """
    return datetime.fromisoformat(iso_str.replace("Z", "+00:00"))


def format_iso_datetime(dt: datetime) -> str:
    """Format datetime to ISO string.

    Args:
        dt: Datetime object (naive or timezone-aware).

    Returns:
        ISO format string with timezone offset.
    """
    if dt.tzinfo is None:
        dt = dt.astimezone()  # Use local timezone
    return dt.isoformat()


def format_local_time(dt: datetime) -> str:
    """Format datetime as local time string.

    Args:
        dt: Datetime object (can be UTC or timezone-aware).

    Returns:
        Formatted string in local time: "YYYY-MM-DD HH:MM:SS"
    """
    local_dt = dt.astimezone()  # Convert to local timezone
    return local_dt.strftime("%Y-%m-%d %H:%M:%S")
