"""Notification helpers for CLI commands.

Purpose
-------
Prepare and send email notifications for sync results, per-document
attachments, and error reports.

Contents
--------
* Shared helpers: :func:`_log_notification_result`, :func:`_resolve_notification_recipients`,
  :func:`_prepare_notification`.
* Sync notifications: :func:`_send_sync_notification`, :func:`_send_sync_notifications_if_enabled`.
* Document notifications: :func:`_send_document_notifications`.

System Role
-----------
CLI adapter layer — notification orchestration for CLI commands.
"""

# pyright: reportUnusedFunction=false
from __future__ import annotations

import logging
from pathlib import Path

from lib_layered_config import Config

from ..adapters.notification import EmailNotificationAdapter
from ..application.use_cases import SyncResult
from ..config import FinanzOnlineConfig
from ..domain.models import DataboxEntry
from ..mail import EmailConfig, load_email_config_from_dict

logger = logging.getLogger(__name__)


def _log_notification_result(success: bool, recipients: list[str], notification_type: str) -> None:
    """Log the result of a notification attempt."""
    if success:
        logger.info("%s email sent", notification_type, extra={"recipients": recipients})
    else:
        logger.warning("%s email failed", notification_type)


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
