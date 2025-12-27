"""Shared formatting utilities for internal use.

This module provides common formatting functions used across multiple
adapters to avoid code duplication.

Contents:
    * :func:`format_bytes` - Format byte size to human readable string
    * :func:`get_erltyp_display_name` - Get translated display name for document type
    * :func:`mask_credential` - Mask sensitive values for logging
"""

from __future__ import annotations

from finanzonline_databox.i18n import _


def get_erltyp_display_name(erltyp: str) -> str:
    """Get translated display name for document type.

    Args:
        erltyp: Document type code (B, M, I, P, EU, etc.).

    Returns:
        Translated display name for the document type.

    Examples:
        >>> get_erltyp_display_name("B")
        'Bescheid'
        >>> get_erltyp_display_name("M")
        'Mitteilung'
    """
    type_names = {
        "B": _("Bescheid"),
        "M": _("Mitteilung"),
        "I": _("Information"),
        "P": _("Protokoll"),
        "EU": _("EU-Erledigung"),
    }
    return type_names.get(erltyp, erltyp)


def mask_credential(value: str, visible_chars: int = 4) -> str:
    """Mask a sensitive value, showing only first/last few characters.

    Args:
        value: The sensitive value to mask.
        visible_chars: Number of characters to show at start and end.

    Returns:
        Masked string like "abc...xyz" or "****" for short values.

    Examples:
        >>> mask_credential("secretpassword123")
        'secr...123'
        >>> mask_credential("short")
        '*****'
    """
    if len(value) <= visible_chars * 2:
        return "*" * len(value)
    return f"{value[:visible_chars]}...{value[-visible_chars:]}"


def format_bytes(size: int) -> str:
    """Format byte size to human readable string.

    Args:
        size: Size in bytes.

    Returns:
        Human readable string (e.g., "1.5 KB", "2.3 MB").

    Examples:
        >>> format_bytes(500)
        '500 B'
        >>> format_bytes(1536)
        '1.5 KB'
        >>> format_bytes(2621440)
        '2.5 MB'
    """
    if size < 1024:
        return f"{size} B"
    if size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    return f"{size / (1024 * 1024):.1f} MB"
