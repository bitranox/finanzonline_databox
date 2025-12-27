"""Port definitions for external dependencies.

Purpose
-------
Define protocol interfaces (ports) that abstract external dependencies.
Adapters implement these protocols to integrate with actual services.

Contents
--------
* :class:`SessionPort` - Session management interface
* :class:`DataboxPort` - DataBox operations interface
* :class:`NotificationPort` - Notification delivery interface

System Role
-----------
Application layer - defines contracts for Dependency Inversion Principle.
Use cases depend on these abstractions, not concrete implementations.

Examples
--------
>>> class MockSessionPort:
...     def login(self, credentials):
...         return SessionInfo(session_id="test", return_code=0, message="OK")
...     def logout(self, session_id, credentials):
...         return True
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from finanzonline_databox.domain.models import (
        DataboxDownloadRequest,
        DataboxDownloadResult,
        DataboxListRequest,
        DataboxListResult,
        FinanzOnlineCredentials,
        SessionInfo,
    )


class SessionPort(Protocol):
    """Port for FinanzOnline session management.

    Defines the contract for login/logout operations with the
    FinanzOnline Session Webservice.

    Implementations must handle SOAP communication with the BMF
    session service endpoint.
    """

    def login(self, credentials: FinanzOnlineCredentials) -> SessionInfo:
        """Authenticate with FinanzOnline and obtain a session.

        Args:
            credentials: FinanzOnline credentials (tid, benid, pin).

        Returns:
            SessionInfo with session_id if successful.

        Raises:
            AuthenticationError: If credentials are invalid.
            SessionError: If session creation fails.
        """
        ...

    def logout(self, session_id: str, credentials: FinanzOnlineCredentials) -> bool:
        """End a FinanzOnline session.

        Args:
            session_id: Active session identifier.
            credentials: FinanzOnline credentials.

        Returns:
            True if logout succeeded, False otherwise.
            Logout failures are typically not critical.
        """
        ...


class DataboxPort(Protocol):
    """Port for DataBox operations.

    Defines the contract for listing and downloading documents from
    the FinanzOnline DataBox-Download Webservice.

    Implementations must handle SOAP communication with the BMF
    DataBox service endpoint.
    """

    def list_entries(
        self,
        session_id: str,
        credentials: FinanzOnlineCredentials,
        request: DataboxListRequest,
    ) -> DataboxListResult:
        """List databox entries.

        Args:
            session_id: Active session identifier from login.
            credentials: FinanzOnline credentials (tid, benid).
            request: List request with optional filters.

        Returns:
            DataboxListResult with entries and status.

        Raises:
            SessionError: If session is invalid or expired.
            DataboxOperationError: If operation fails.
        """
        ...

    def download_entry(
        self,
        session_id: str,
        credentials: FinanzOnlineCredentials,
        request: DataboxDownloadRequest,
    ) -> DataboxDownloadResult:
        """Download a specific document from databox.

        Args:
            session_id: Active session identifier from login.
            credentials: FinanzOnline credentials (tid, benid).
            request: Download request with applkey.

        Returns:
            DataboxDownloadResult with document content.

        Raises:
            SessionError: If session is invalid or expired.
            DataboxOperationError: If operation fails.
        """
        ...


class NotificationPort(Protocol):
    """Port for sending result notifications.

    Defines the contract for delivering DataBox download notifications
    to recipients via email or other channels.

    Implementations handle email formatting and delivery using
    the configured mail infrastructure.
    """

    def send_download_notification(
        self,
        entries_downloaded: int,
        total_size: int,
        recipients: list[str],
    ) -> bool:
        """Send download notification.

        Args:
            entries_downloaded: Number of documents downloaded.
            total_size: Total size of downloaded documents in bytes.
            recipients: Email addresses to send notification to.

        Returns:
            True if notification sent successfully, False otherwise.
            Notification failures are typically non-fatal.
        """
        ...
