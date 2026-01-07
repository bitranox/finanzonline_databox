"""Email notification adapter for DataBox download operations.

Purpose
-------
Implement NotificationPort for sending DataBox sync/download
notifications via email using btx_lib_mail infrastructure.

Contents
--------
* :class:`EmailNotificationAdapter` - Email notification implementation
* :func:`format_sync_result_plain` - Plain text sync result formatter
* :func:`format_sync_result_html` - HTML sync result formatter

System Role
-----------
Adapters layer - integrates with btx_lib_mail for email delivery.
"""

from __future__ import annotations

import html
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from finanzonline_databox._datetime_utils import format_local_time, local_now
from finanzonline_databox._format_utils import format_bytes as _format_bytes
from finanzonline_databox._format_utils import get_erltyp_display_name
from finanzonline_databox.domain.models import DataboxEntry, Diagnostics
from finanzonline_databox.enums import EmailFormat
from finanzonline_databox.i18n import _
from finanzonline_databox.mail import EmailConfig, send_email

if TYPE_CHECKING:
    from finanzonline_databox.application.use_cases import SyncResult


logger = logging.getLogger(__name__)


# HTML template fragments for email formatting
_HTML_DOCTYPE = '<!DOCTYPE html>\n<html>\n<head>\n    <meta charset="utf-8">\n    <title>{title}</title>\n</head>'
_HTML_BODY_STYLE = "font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;"
_HTML_TABLE_STYLE = "width: 100%; border-collapse: collapse; margin: 20px 0;"
_HTML_TD_STYLE = "padding: 8px 15px;"


def _get_html_footer() -> str:
    """Get translated HTML footer."""
    return f'<p style="color: #7f8c8d; font-size: 0.9em; margin-top: 30px; border-top: 1px solid #eee; padding-top: 15px;">{_("This is an automated message from finanzonline-databox.")}</p>'


def _format_diagnostics_plain(diagnostics: Diagnostics | None) -> list[str]:
    """Format diagnostics as plain text lines."""
    if not diagnostics or diagnostics.is_empty:
        return []
    lines = ["", _("Diagnostic Information"), "-" * 30]
    lines.extend(f"{key.replace('_', ' ').title()}: {value}" for key, value in diagnostics.items())
    return lines


def _is_html_content(value: str) -> bool:
    """Check if value appears to be HTML content."""
    lower = value.lower()
    return "<html" in lower or "<!doctype" in lower


def _format_diagnostic_value_html(key: str, value: str) -> str:
    """Format a single diagnostic value for HTML display.

    Args:
        key: The diagnostic field name.
        value: The diagnostic value.

    Returns:
        HTML table row for the diagnostic entry.
    """
    label = key.replace("_", " ").title()
    label_td = f'<td style="padding: 6px 15px; font-weight: bold; color: #666; font-size: 0.9em;">{label}:</td>'

    # For HTML content (server responses), render the HTML and show source code
    if _is_html_content(value):
        escaped = html.escape(value)
        value_td = f"""<td style="padding: 6px 15px;">
            <div style="border: 1px solid #ddd; padding: 10px; margin-bottom: 10px; background: white; max-height: 400px; overflow-y: auto; border-radius: 4px;">
                <strong style="color: #856404;">{_("Server Message")}:</strong>
                <div style="margin-top: 8px;">{value}</div>
            </div>
            <details>
                <summary style="cursor: pointer; color: #666; font-size: 0.85em;">{_("HTML Source Code")} - {_("Click to expand")}</summary>
                <pre style="font-family: monospace; font-size: 0.8em; background-color: #f8f9fa; padding: 10px; border-radius: 4px; overflow-x: auto; max-height: 300px; overflow-y: auto; white-space: pre-wrap; word-break: break-all; margin-top: 8px;">{escaped}</pre>
            </details>
        </td>"""
    else:
        value_td = f'<td style="padding: 6px 15px; font-family: monospace; font-size: 0.85em; word-break: break-all;">{html.escape(value)}</td>'

    return f"<tr>{label_td}{value_td}</tr>"


def _format_diagnostics_html(diagnostics: Diagnostics | None) -> str:
    """Format diagnostics as HTML section."""
    if not diagnostics or diagnostics.is_empty:
        return ""
    diag_rows = "".join(_format_diagnostic_value_html(k, v) for k, v in diagnostics.items())
    return f"""<h3 style="color: #856404; border-bottom: 1px solid #ffc107; padding-bottom: 8px; margin-top: 30px;">{_("Diagnostic Information")}</h3>
        <table style="width: 100%; border-collapse: collapse; margin: 10px 0; background-color: #fff3cd; border-radius: 4px;">{diag_rows}</table>"""


def format_sync_result_plain(result: SyncResult, output_dir: str) -> str:
    """Format sync result as plain text.

    Args:
        result: Sync operation result.
        output_dir: Directory where files were saved.

    Returns:
        Plain text representation of the result.
    """
    timestamp = format_local_time(local_now())
    status = _("SUCCESS") if result.is_success else _("COMPLETED WITH ERRORS")

    lines = [
        _("DataBox Sync Result"),
        "=" * 50,
        "",
        f"{_('Status:')}      {status}",
        f"{_('Output Dir:')}  {output_dir}",
        f"{_('Timestamp:')}   {timestamp}",
        "",
        _("Statistics"),
        "-" * 30,
        f"{_('Total Listed:')}    {result.total_listed}",
        f"{_('Downloaded:')}      {result.downloaded}",
        f"{_('Skipped:')}         {result.skipped}",
        f"{_('Failed:')}          {result.failed}",
        f"{_('Total Size:')}      {_format_bytes(result.total_bytes)}",
    ]

    if result.downloaded > 0:
        lines.extend(
            [
                "",
                _("New documents have been downloaded to your DataBox folder."),
            ]
        )

    if result.failed > 0:
        lines.extend(
            [
                "",
                _("WARNING: Some downloads failed. Please check the logs for details."),
            ]
        )

    lines.extend(["", "-" * 50, _("This is an automated message from finanzonline-databox.")])

    return "\n".join(lines)


def format_sync_result_html(result: SyncResult, output_dir: str) -> str:
    """Format sync result as HTML.

    Args:
        result: Sync operation result.
        output_dir: Directory where files were saved.

    Returns:
        HTML representation of the result.
    """
    timestamp = format_local_time(local_now())
    status = _("SUCCESS") if result.is_success else _("COMPLETED WITH ERRORS")
    status_color = "#28a745" if result.is_success else "#ffc107"
    status_span = f'<span style="background-color: {status_color}; color: white; padding: 4px 12px; border-radius: 4px; font-weight: bold;">{status}</span>'

    rows = f"""
        <tr><td style="{_HTML_TD_STYLE} font-weight: bold;">{_("Status:")}</td><td style="{_HTML_TD_STYLE}">{status_span}</td></tr>
        <tr><td style="{_HTML_TD_STYLE} font-weight: bold;">{_("Output Dir:")}</td><td style="{_HTML_TD_STYLE}"><code>{output_dir}</code></td></tr>
        <tr><td style="{_HTML_TD_STYLE} font-weight: bold;">{_("Timestamp:")}</td><td style="{_HTML_TD_STYLE}">{timestamp}</td></tr>
    """

    stats_rows = f"""
        <tr><td style="{_HTML_TD_STYLE} font-weight: bold;">{_("Total Listed:")}</td><td style="{_HTML_TD_STYLE}">{result.total_listed}</td></tr>
        <tr><td style="{_HTML_TD_STYLE} font-weight: bold;">{_("Downloaded:")}</td><td style="{_HTML_TD_STYLE}">{result.downloaded}</td></tr>
        <tr><td style="{_HTML_TD_STYLE} font-weight: bold;">{_("Skipped:")}</td><td style="{_HTML_TD_STYLE}">{result.skipped}</td></tr>
        <tr><td style="{_HTML_TD_STYLE} font-weight: bold;">{_("Failed:")}</td><td style="{_HTML_TD_STYLE}">{result.failed}</td></tr>
        <tr><td style="{_HTML_TD_STYLE} font-weight: bold;">{_("Total Size:")}</td><td style="{_HTML_TD_STYLE}">{_format_bytes(result.total_bytes)}</td></tr>
    """

    notices = ""
    if result.downloaded > 0:
        notices += f'<div style="background-color: #d4edda; border: 1px solid #c3e6cb; border-radius: 4px; padding: 15px; margin: 20px 0; color: #155724;">{_("New documents have been downloaded to your DataBox folder.")}</div>'

    if result.failed > 0:
        notices += f'<div style="background-color: #fff3cd; border: 1px solid #ffc107; border-radius: 4px; padding: 15px; margin: 20px 0; color: #856404;">{_("WARNING: Some downloads failed. Please check the logs for details.")}</div>'

    title = _("DataBox Sync Result")
    return f"""{_HTML_DOCTYPE.format(title=title)}
<body style="{_HTML_BODY_STYLE}">
    <h2 style="color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px;">{title}</h2>
    <table style="{_HTML_TABLE_STYLE}">{rows}</table>
    <h3 style="color: #333;">{_("Statistics")}</h3>
    <table style="{_HTML_TABLE_STYLE}">{stats_rows}</table>
    {notices}
    {_get_html_footer()}
</body>
</html>"""


def _build_error_base_lines(
    operation: str,
    error_type: str,
    error_message: str,
    return_code: int | None,
    retryable: bool,
    timestamp: str,
) -> list[str]:
    """Build base error lines for plain text format."""
    lines = [
        _("DataBox ERROR Notification"),
        "=" * 50,
        "",
        f"{_('Operation:')}   {operation}",
        f"{_('Status:')}      {_('ERROR')}",
        f"{_('Error Type:')}  {error_type}",
        f"{_('Message:')}     {error_message}",
    ]
    if return_code is not None:
        lines.append(f"{_('Return Code:')} {return_code}")
    lines.extend([f"{_('Retryable:')}   {_('Yes') if retryable else _('No')}", f"{_('Timestamp:')}   {timestamp}"])
    return lines


def format_error_plain(
    error_type: str,
    error_message: str,
    operation: str = "sync",
    return_code: int | None = None,
    retryable: bool = False,
    diagnostics: Diagnostics | None = None,
) -> str:
    """Format error notification as plain text.

    Args:
        error_type: Type of error (e.g., "Authentication Error").
        error_message: Error message details.
        operation: The operation that failed.
        return_code: Optional return code from BMF.
        retryable: Whether the error is retryable.
        diagnostics: Optional Diagnostics object for debugging.

    Returns:
        Plain text error notification.
    """
    timestamp = format_local_time(local_now())
    lines = _build_error_base_lines(operation, error_type, error_message, return_code, retryable, timestamp)
    lines.extend(_format_diagnostics_plain(diagnostics))
    lines.extend(["", "-" * 50, _("This is an automated error notification from finanzonline-databox.")])
    return "\n".join(lines)


def _build_error_html_rows(
    operation: str,
    error_type: str,
    error_message: str,
    return_code: int | None,
    retryable: bool,
    timestamp: str,
) -> str:
    """Build HTML table rows for error notification."""
    error_span = f'<span style="background-color: #dc3545; color: white; padding: 4px 12px; border-radius: 4px; font-weight: bold;">{_("ERROR")}</span>'
    rows = f"""
        <tr><td style="{_HTML_TD_STYLE} font-weight: bold;">{_("Operation:")}</td><td style="{_HTML_TD_STYLE}">{operation}</td></tr>
        <tr><td style="{_HTML_TD_STYLE} font-weight: bold;">{_("Status:")}</td><td style="{_HTML_TD_STYLE}">{error_span}</td></tr>
        <tr><td style="{_HTML_TD_STYLE} font-weight: bold;">{_("Error Type:")}</td><td style="{_HTML_TD_STYLE}" style="color: #dc3545; font-weight: bold;">{error_type}</td></tr>
        <tr><td style="{_HTML_TD_STYLE} font-weight: bold;">{_("Message:")}</td><td style="{_HTML_TD_STYLE}">{error_message}</td></tr>
    """
    if return_code is not None:
        rows += f'<tr><td style="{_HTML_TD_STYLE} font-weight: bold;">{_("Return Code:")}</td><td style="{_HTML_TD_STYLE}">{return_code}</td></tr>'
    rows += f"""
        <tr><td style="{_HTML_TD_STYLE} font-weight: bold;">{_("Retryable:")}</td><td style="{_HTML_TD_STYLE}">{_("Yes - try again later") if retryable else _("No")}</td></tr>
        <tr><td style="{_HTML_TD_STYLE} font-weight: bold;">{_("Timestamp:")}</td><td style="{_HTML_TD_STYLE}">{timestamp}</td></tr>
    """
    return rows


def format_error_html(
    error_type: str,
    error_message: str,
    operation: str = "sync",
    return_code: int | None = None,
    retryable: bool = False,
    diagnostics: Diagnostics | None = None,
) -> str:
    """Format error notification as HTML.

    Args:
        error_type: Type of error (e.g., "Authentication Error").
        error_message: Error message details.
        operation: The operation that failed.
        return_code: Optional return code from BMF.
        retryable: Whether the error is retryable.
        diagnostics: Optional Diagnostics object for debugging.

    Returns:
        HTML error notification.
    """
    timestamp = format_local_time(local_now())
    rows = _build_error_html_rows(operation, error_type, error_message, return_code, retryable, timestamp)
    diag_section = _format_diagnostics_html(diagnostics)
    footer = f'<p style="color: #7f8c8d; font-size: 0.9em; margin-top: 30px; border-top: 1px solid #eee; padding-top: 15px;">{_("This is an automated error notification from finanzonline-databox.")}</p>'

    return f"""{_HTML_DOCTYPE.format(title=_("DataBox Error"))}
<body style="{_HTML_BODY_STYLE}">
    <h2 style="color: #dc3545; border-bottom: 2px solid #dc3545; padding-bottom: 10px;">{_("DataBox ERROR")}</h2>
    <table style="{_HTML_TABLE_STYLE}">{rows}</table>
    {diag_section}
    {footer}
</body>
</html>"""


def format_document_subject(entry: DataboxEntry) -> str:
    """Format email subject for a document notification.

    Args:
        entry: DataBox entry metadata.

    Returns:
        Email subject line with document information.

    Example:
        "FinanzOnline DataBox: Bescheid - Einkommensteuerbescheid 2024 (E1, 2024-12-20)"
    """
    type_name = get_erltyp_display_name(entry.erltyp)
    description = entry.filebez if entry.filebez else entry.name
    date_str = entry.datbesch.strftime("%Y-%m-%d")
    return f"FinanzOnline DataBox: {type_name} - {description} ({entry.anbringen}, {date_str})"


def format_document_email_plain(entry: DataboxEntry) -> str:
    """Format document notification as plain text.

    Args:
        entry: DataBox entry metadata.

    Returns:
        Plain text email body with full document metadata.
    """
    type_name = get_erltyp_display_name(entry.erltyp)
    timestamp = format_local_time(entry.ts_zust)
    period = f"{entry.zrvon} - {entry.zrbis}" if entry.zrvon != entry.zrbis else entry.zrvon

    lines = [
        _("FinanzOnline DataBox - Document Notification"),
        "=" * 50,
        "",
        _("Document Details"),
        "-" * 30,
        f"{_('Type:')}           {type_name}",
        f"{_('Description:')}    {entry.filebez or entry.name}",
        f"{_('Tax Number:')}     {entry.stnr}",
        f"{_('Reference:')}      {entry.anbringen}",
        f"{_('Period:')}         {period}",
        f"{_('Document Date:')}  {entry.datbesch.strftime('%Y-%m-%d')}",
        f"{_('Delivered:')}      {timestamp}",
        f"{_('File Type:')}      {entry.fileart}",
        "",
        _("The document is attached to this email."),
        "",
        "-" * 50,
        _("This is an automated message from finanzonline-databox."),
    ]

    return "\n".join(lines)


def format_document_email_html(entry: DataboxEntry) -> str:
    """Format document notification as HTML.

    Args:
        entry: DataBox entry metadata.

    Returns:
        HTML email body with styled document metadata table.
    """
    type_name = get_erltyp_display_name(entry.erltyp)
    timestamp = format_local_time(entry.ts_zust)
    period = f"{entry.zrvon} - {entry.zrbis}" if entry.zrvon != entry.zrbis else entry.zrvon

    rows = f"""
        <tr><td style="{_HTML_TD_STYLE} font-weight: bold; width: 140px;">{_("Type:")}</td><td style="{_HTML_TD_STYLE}">{type_name}</td></tr>
        <tr style="background-color: #f8f9fa;"><td style="{_HTML_TD_STYLE} font-weight: bold;">{_("Description:")}</td><td style="{_HTML_TD_STYLE}">{entry.filebez or entry.name}</td></tr>
        <tr><td style="{_HTML_TD_STYLE} font-weight: bold;">{_("Tax Number:")}</td><td style="{_HTML_TD_STYLE}"><code>{entry.stnr}</code></td></tr>
        <tr style="background-color: #f8f9fa;"><td style="{_HTML_TD_STYLE} font-weight: bold;">{_("Reference:")}</td><td style="{_HTML_TD_STYLE}">{entry.anbringen}</td></tr>
        <tr><td style="{_HTML_TD_STYLE} font-weight: bold;">{_("Period:")}</td><td style="{_HTML_TD_STYLE}">{period}</td></tr>
        <tr style="background-color: #f8f9fa;"><td style="{_HTML_TD_STYLE} font-weight: bold;">{_("Document Date:")}</td><td style="{_HTML_TD_STYLE}">{entry.datbesch.strftime("%Y-%m-%d")}</td></tr>
        <tr><td style="{_HTML_TD_STYLE} font-weight: bold;">{_("Delivered:")}</td><td style="{_HTML_TD_STYLE}">{timestamp}</td></tr>
        <tr style="background-color: #f8f9fa;"><td style="{_HTML_TD_STYLE} font-weight: bold;">{_("File Type:")}</td><td style="{_HTML_TD_STYLE}"><span style="background-color: #007bff; color: white; padding: 2px 8px; border-radius: 3px; font-size: 0.9em;">{entry.fileart}</span></td></tr>
    """

    attachment_notice = f'<div style="background-color: #d4edda; border: 1px solid #c3e6cb; border-radius: 4px; padding: 15px; margin: 20px 0; color: #155724;">{_("The document is attached to this email.")}</div>'

    title = _("FinanzOnline DataBox - Document Notification")
    return f"""{_HTML_DOCTYPE.format(title=title)}
<body style="{_HTML_BODY_STYLE}">
    <h2 style="color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px;">{title}</h2>
    <h3 style="color: #333; margin-top: 25px;">{_("Document Details")}</h3>
    <table style="{_HTML_TABLE_STYLE} border: 1px solid #dee2e6; border-radius: 4px;">{rows}</table>
    {attachment_notice}
    {_get_html_footer()}
</body>
</html>"""


class EmailNotificationAdapter:
    """Email notification adapter implementing NotificationPort.

    Sends DataBox sync/download results via email using btx_lib_mail.

    Attributes:
        _config: Email configuration settings.
        _email_format: Email body format (html, text, or both).
    """

    def __init__(
        self,
        config: EmailConfig,
        email_format: EmailFormat = EmailFormat.BOTH,
    ) -> None:
        """Initialize email notification adapter.

        Args:
            config: Email configuration with SMTP settings.
            email_format: Email body format - html, text, or both.
        """
        self._config = config
        self._email_format = email_format

    def _get_body_parts(self, plain_body: str, html_body: str) -> tuple[str, str]:
        """Get body parts based on configured email format.

        Args:
            plain_body: Plain text body content.
            html_body: HTML body content.

        Returns:
            Tuple of (plain_body, html_body) with empty string for excluded format.
        """
        if self._email_format == EmailFormat.PLAIN:
            return plain_body, ""
        if self._email_format == EmailFormat.HTML:
            return "", html_body
        return plain_body, html_body

    def send_download_notification(
        self,
        entries_downloaded: int,
        total_size: int,
        recipients: list[str],
    ) -> bool:
        """Send download notification via email.

        Args:
            entries_downloaded: Number of documents downloaded.
            total_size: Total size of downloaded documents in bytes.
            recipients: Email addresses to send notification to.

        Returns:
            True if notification sent successfully, False otherwise.
        """
        if not recipients:
            logger.warning("No recipients specified, skipping notification")
            return False

        # Create a simple sync result for formatting
        from finanzonline_databox.application.use_cases import SyncResult

        result = SyncResult(
            total_listed=entries_downloaded,
            downloaded=entries_downloaded,
            skipped=0,
            failed=0,
            total_bytes=total_size,
        )

        subject = f"DataBox: {entries_downloaded} documents downloaded ({_format_bytes(total_size)})"

        plain_body, html_body = self._get_body_parts(
            format_sync_result_plain(result, ""),
            format_sync_result_html(result, ""),
        )

        logger.info(
            "Sending DataBox download notification to %d recipients (format=%s)",
            len(recipients),
            self._email_format,
        )

        try:
            return send_email(
                config=self._config,
                recipients=recipients,
                subject=subject,
                body=plain_body,
                body_html=html_body,
            )
        except Exception as e:
            logger.error("Failed to send notification: %s", e)
            return False

    def send_sync_result(
        self,
        result: SyncResult,
        output_dir: str,
        recipients: list[str],
    ) -> bool:
        """Send sync result notification via email.

        Args:
            result: Sync operation result.
            output_dir: Directory where files were saved.
            recipients: Email addresses to send notification to.

        Returns:
            True if notification sent successfully, False otherwise.
        """
        if not recipients:
            logger.warning("No recipients specified, skipping notification")
            return False

        status = "Success" if result.is_success else "Completed with errors"
        subject = f"DataBox Sync: {status} - {result.downloaded} downloaded, {result.skipped} skipped"

        plain_body, html_body = self._get_body_parts(
            format_sync_result_plain(result, output_dir),
            format_sync_result_html(result, output_dir),
        )

        logger.info(
            "Sending DataBox sync notification to %d recipients (format=%s)",
            len(recipients),
            self._email_format,
        )

        try:
            return send_email(
                config=self._config,
                recipients=recipients,
                subject=subject,
                body=plain_body,
                body_html=html_body,
            )
        except Exception as e:
            logger.error("Failed to send notification: %s", e)
            return False

    def send_error(
        self,
        error_type: str,
        error_message: str,
        operation: str,
        recipients: list[str],
        return_code: int | None = None,
        retryable: bool = False,
        diagnostics: Diagnostics | None = None,
    ) -> bool:
        """Send error notification via email.

        Args:
            error_type: Type of error (e.g., "Authentication Error").
            error_message: Error message details.
            operation: The operation that failed.
            recipients: Email addresses to send notification to.
            return_code: Optional return code from BMF.
            retryable: Whether the error is retryable.
            diagnostics: Optional Diagnostics object for debugging.

        Returns:
            True if notification sent successfully, False otherwise.
        """
        if not recipients:
            logger.warning("No recipients specified, skipping error notification")
            return False

        subject = f"DataBox ERROR: {operation} - {error_type}"

        plain_body, html_body = self._get_body_parts(
            format_error_plain(error_type, error_message, operation, return_code, retryable, diagnostics),
            format_error_html(error_type, error_message, operation, return_code, retryable, diagnostics),
        )

        logger.info(
            "Sending DataBox error notification to %d recipients (format=%s)",
            len(recipients),
            self._email_format,
        )

        try:
            return send_email(
                config=self._config,
                recipients=recipients,
                subject=subject,
                body=plain_body,
                body_html=html_body,
            )
        except Exception as e:
            logger.error("Failed to send error notification: %s", e)
            return False

    def send_document_notification(
        self,
        entry: DataboxEntry,
        document_path: Path,
        recipients: list[str],
    ) -> bool:
        """Send document notification with attachment via email.

        Args:
            entry: DataBox entry metadata.
            document_path: Path to the downloaded document file.
            recipients: Email addresses to send notification to.

        Returns:
            True if notification sent successfully, False otherwise.
        """
        if not recipients:
            logger.warning("No recipients specified, skipping document notification")
            return False

        if not document_path.exists():
            logger.error("Document file not found: %s", document_path)
            return False

        subject = format_document_subject(entry)

        plain_body, html_body = self._get_body_parts(
            format_document_email_plain(entry),
            format_document_email_html(entry),
        )

        logger.info(
            "Sending document notification for %s to %d recipients (format=%s)",
            entry.applkey[:8],
            len(recipients),
            self._email_format,
        )

        try:
            return send_email(
                config=self._config,
                recipients=recipients,
                subject=subject,
                body=plain_body,
                body_html=html_body,
                attachments=[document_path],
            )
        except Exception as e:
            logger.error("Failed to send document notification: %s", e)
            return False
