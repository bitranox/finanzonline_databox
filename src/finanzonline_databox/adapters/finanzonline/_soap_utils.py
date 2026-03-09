"""Shared utilities for FinanzOnline SOAP clients.

Purpose
-------
Common helpers used by both session and databox SOAP client adapters.

System Role
-----------
Adapters layer - shared infrastructure utilities.
"""

from __future__ import annotations

from zeep.exceptions import XMLSyntaxError

# Maximum length of HTML content to include in diagnostics (for email)
_MAX_HTML_CONTENT_LENGTH = 4000


def is_maintenance_page(content: str | bytes | None) -> bool:
    """Detect if content is a FinanzOnline maintenance page.

    Args:
        content: Raw HTML content (string or bytes).

    Returns:
        True if content appears to be a maintenance page.

    Examples:
        >>> is_maintenance_page('<html><a href="/wartung/error.css">Error</a></html>')
        True
        >>> is_maintenance_page('<html><body>Normal response</body></html>')
        False
        >>> is_maintenance_page(None)
        False
    """
    if not content:
        return False
    content_str = content.decode("utf-8", errors="replace") if isinstance(content, bytes) else content
    return "/wartung/" in content_str.lower()


def extract_xml_error_content(exc: XMLSyntaxError) -> str:
    """Extract HTML/XML content from XMLSyntaxError for diagnostics.

    Args:
        exc: The XMLSyntaxError exception.

    Returns:
        Truncated content string for inclusion in error diagnostics.
    """
    content = getattr(exc, "content", None)
    if not content:
        return str(exc)

    content_str = content.decode("utf-8", errors="replace") if isinstance(content, bytes) else str(content)
    if len(content_str) > _MAX_HTML_CONTENT_LENGTH:
        return content_str[:_MAX_HTML_CONTENT_LENGTH] + "\n... [truncated]"
    return content_str
