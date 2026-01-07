"""Application use cases for DataBox operations.

Purpose
-------
Orchestrate DataBox operations by coordinating between
domain models and adapter ports. Contains the core business logic
flow without implementation details.

Contents
--------
* :class:`ListDataboxUseCase` - List databox entries
* :class:`DownloadEntryUseCase` - Download a single entry
* :class:`SyncDataboxUseCase` - Sync all new entries to local storage

System Role
-----------
Application layer - orchestrates domain operations through ports.
Depends on domain models and port protocols, not concrete adapters.

Examples
--------
>>> use_case = ListDataboxUseCase(session_client, databox_client)  # doctest: +SKIP
>>> result = use_case.execute(credentials)  # doctest: +SKIP
>>> len(result.entries)  # doctest: +SKIP
5
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from finanzonline_databox.domain.errors import (
    SessionError,
    filesystem_error_from_oserror,
)
from finanzonline_databox.domain.models import (
    DataboxDownloadRequest,
    DataboxEntry,
    DataboxListRequest,
)
from finanzonline_databox.enums import ReadFilter

if TYPE_CHECKING:
    from finanzonline_databox.application.ports import DataboxPort, SessionPort
    from finanzonline_databox.domain.models import (
        DataboxDownloadResult,
        DataboxListResult,
        FinanzOnlineCredentials,
        SessionInfo,
    )


logger = logging.getLogger(__name__)


def _filter_by_anbringen(
    entries: tuple[DataboxEntry, ...],
    anbringen_filter: str,
) -> tuple[DataboxEntry, ...]:
    """Filter entries by anbringen reference."""
    if not anbringen_filter:
        return entries
    filtered = tuple(e for e in entries if e.anbringen == anbringen_filter)
    logger.info("Filtered to %d entries with anbringen='%s'", len(filtered), anbringen_filter)
    return filtered


def _filter_by_read_status(
    entries: tuple[DataboxEntry, ...],
    read_filter: ReadFilter,
) -> tuple[DataboxEntry, ...]:
    """Filter entries by read status."""
    if read_filter == ReadFilter.ALL:
        return entries
    if read_filter == ReadFilter.UNREAD:
        filtered = tuple(e for e in entries if e.is_unread)
        logger.info("Filtered to %d unread entries", len(filtered))
        return filtered
    if read_filter == ReadFilter.READ:
        filtered = tuple(e for e in entries if e.is_read)
        logger.info("Filtered to %d read entries", len(filtered))
        return filtered
    return entries


def _filter_sync_entries(
    entries: tuple[DataboxEntry, ...],
    anbringen_filter: str,
    read_filter: ReadFilter,
) -> tuple[DataboxEntry, ...]:
    """Filter entries by anbringen and read status for sync operation."""
    entries = _filter_by_anbringen(entries, anbringen_filter)
    return _filter_by_read_status(entries, read_filter)


def _login_session(
    session_client: SessionPort,
    credentials: FinanzOnlineCredentials,
) -> SessionInfo:
    """Login to FinanzOnline, raising SessionError on failure.

    Args:
        session_client: Session management port implementation.
        credentials: FinanzOnline credentials.

    Returns:
        SessionInfo with valid session ID.

    Raises:
        SessionError: If login fails.
    """
    logger.debug("Logging in to FinanzOnline")
    session = session_client.login(credentials)
    if not session.is_valid:
        raise SessionError(f"Login failed: {session.message}", return_code=session.return_code)
    logger.debug("Session established: %s...", session.session_id[:8])
    return session


def _logout_session(
    session_client: SessionPort,
    session_id: str,
    credentials: FinanzOnlineCredentials,
) -> None:
    """Logout from session, logging but not raising on failure.

    Args:
        session_client: Session management port implementation.
        session_id: Session ID to logout.
        credentials: FinanzOnline credentials.
    """
    try:
        session_client.logout(session_id, credentials)
    except Exception as e:
        logger.warning("Logout failed (non-fatal): %s", e)


_MAX_UNIQUE_PATH_ATTEMPTS = 10000


def _get_unique_path(base_path: Path) -> Path:
    """Get unique file path by adding _2, _3, etc. suffix if file exists.

    Args:
        base_path: The desired file path.

    Returns:
        The original path if it doesn't exist, otherwise a unique path
        with _2, _3, etc. appended to the stem.

    Raises:
        RuntimeError: If no unique path found after MAX attempts.

    Examples:
        >>> from pathlib import Path
        >>> # For a non-existent file, returns the original path
        >>> _get_unique_path(Path("/tmp/nonexistent.xml"))  # doctest: +SKIP
        PosixPath('/tmp/nonexistent.xml')
    """
    if not base_path.exists():
        return base_path

    stem = base_path.stem
    suffix = base_path.suffix
    parent = base_path.parent

    for counter in range(2, _MAX_UNIQUE_PATH_ATTEMPTS + 2):
        new_path = parent / f"{stem}_{counter}{suffix}"
        if not new_path.exists():
            return new_path

    raise RuntimeError(f"Could not find unique path after {_MAX_UNIQUE_PATH_ATTEMPTS} attempts: {base_path}")


class ListDataboxUseCase:
    """Use case for listing databox entries.

    Orchestrates the complete list operation flow:
    1. Login to FinanzOnline session service
    2. Execute getDatabox query with optional filters
    3. Logout from session (always, even on error)

    Attributes:
        _session_client: Session management port implementation.
        _databox_client: DataBox operations port implementation.
    """

    def __init__(
        self,
        session_client: SessionPort,
        databox_client: DataboxPort,
    ) -> None:
        """Initialize use case with required adapters.

        Args:
            session_client: Implementation of SessionPort for login/logout.
            databox_client: Implementation of DataboxPort for list/download.
        """
        self._session_client = session_client
        self._databox_client = databox_client

    def execute(
        self,
        credentials: FinanzOnlineCredentials,
        request: DataboxListRequest | None = None,
    ) -> DataboxListResult:
        """List databox entries.

        Args:
            credentials: FinanzOnline credentials.
            request: Optional list request with filters. If None, lists all unread.

        Returns:
            DataboxListResult with entries and status.

        Raises:
            SessionError: Login or session management failed.
            DataboxOperationError: List operation failed.
        """
        if request is None:
            request = DataboxListRequest()

        logger.info("Listing databox entries (erltyp=%r)", request.erltyp or "all")

        session = _login_session(self._session_client, credentials)

        try:
            result = self._databox_client.list_entries(
                session_id=session.session_id,
                credentials=credentials,
                request=request,
            )
            logger.info(
                "Listed %d entries (%d unread)",
                result.entry_count,
                result.unread_count,
            )
            return result
        finally:
            logger.debug("Logging out from FinanzOnline")
            _logout_session(self._session_client, session.session_id, credentials)


class DownloadEntryUseCase:
    """Use case for downloading a single databox entry.

    Orchestrates the complete download operation flow:
    1. Login to FinanzOnline session service
    2. Execute getDataboxEntry query
    3. Optionally save to file
    4. Logout from session (always, even on error)

    Attributes:
        _session_client: Session management port implementation.
        _databox_client: DataBox operations port implementation.
    """

    def __init__(
        self,
        session_client: SessionPort,
        databox_client: DataboxPort,
    ) -> None:
        """Initialize use case with required adapters.

        Args:
            session_client: Implementation of SessionPort for login/logout.
            databox_client: Implementation of DataboxPort for list/download.
        """
        self._session_client = session_client
        self._databox_client = databox_client

    def execute(
        self,
        credentials: FinanzOnlineCredentials,
        applkey: str,
        output_path: Path | None = None,
    ) -> tuple[DataboxDownloadResult, Path | None]:
        """Download a databox entry.

        Args:
            credentials: FinanzOnline credentials.
            applkey: Document key to download.
            output_path: Optional path to save the downloaded file.

        Returns:
            Tuple of (DataboxDownloadResult, actual_saved_path).
            The saved path may differ from output_path if unique suffix was added.

        Raises:
            SessionError: Login or session management failed.
            DataboxOperationError: Download operation failed.
            FilesystemError: File write failed (if output_path specified).
        """
        logger.info("Downloading entry with applkey=%s", applkey)

        request = DataboxDownloadRequest(applkey=applkey)
        session = _login_session(self._session_client, credentials)

        try:
            result = self._databox_client.download_entry(
                session_id=session.session_id,
                credentials=credentials,
                request=request,
            )

            saved_path = output_path
            if result.is_success and output_path is not None:
                saved_path = self._save_to_file(result, output_path)

            logger.info(
                "Download completed: %s bytes",
                result.content_size if result.is_success else "failed",
            )
            return result, saved_path
        finally:
            logger.debug("Logging out from FinanzOnline")
            _logout_session(self._session_client, session.session_id, credentials)

    def _save_to_file(self, result: DataboxDownloadResult, output_path: Path) -> Path:
        """Save downloaded content to file.

        Uses unique path to avoid overwriting existing files.

        Args:
            result: Download result containing content to save.
            output_path: Desired file path.

        Returns:
            The actual path where the file was saved.

        Raises:
            FilesystemError: If directory cannot be created or file cannot be written.
        """
        if result.content is None:
            return output_path

        # Get unique path to avoid overwriting existing files
        actual_path = _get_unique_path(output_path)

        try:
            actual_path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise filesystem_error_from_oserror(exc, path=actual_path.parent, operation="create directory") from exc

        try:
            actual_path.write_bytes(result.content)
        except OSError as exc:
            raise filesystem_error_from_oserror(exc, path=actual_path, operation="write file") from exc

        logger.info("Saved %d bytes to %s", len(result.content), actual_path)
        return actual_path


class SyncDataboxUseCase:
    """Use case for syncing all new databox entries to local storage.

    Orchestrates the complete sync operation flow:
    1. Login to FinanzOnline session service
    2. List all entries (unread or filtered by date)
    3. Download each entry that isn't already saved locally
    4. Save downloaded files to output directory
    5. Logout from session (always, even on error)

    Attributes:
        _session_client: Session management port implementation.
        _databox_client: DataBox operations port implementation.
    """

    def __init__(
        self,
        session_client: SessionPort,
        databox_client: DataboxPort,
    ) -> None:
        """Initialize use case with required adapters.

        Args:
            session_client: Implementation of SessionPort for login/logout.
            databox_client: Implementation of DataboxPort for list/download.
        """
        self._session_client = session_client
        self._databox_client = databox_client

    def execute(
        self,
        credentials: FinanzOnlineCredentials,
        output_dir: Path,
        request: DataboxListRequest | None = None,
        skip_existing: bool = True,
        anbringen_filter: str = "",
        read_filter: ReadFilter = ReadFilter.ALL,
    ) -> SyncResult:
        """Sync databox entries to local storage.

        Args:
            credentials: FinanzOnline credentials.
            output_dir: Directory to save downloaded files.
            request: Optional list request with filters. If None, lists all unread.
            skip_existing: If True, skip entries that already exist locally.
            anbringen_filter: If set, only sync entries with matching anbringen (reference).
            read_filter: Read status filter (ReadFilter.UNREAD, ReadFilter.READ, or ReadFilter.ALL).

        Returns:
            SyncResult with statistics about the sync operation.

        Raises:
            SessionError: Login or session management failed.
            DataboxOperationError: List or download operation failed.
            FilesystemError: Output directory cannot be created.
        """
        if request is None:
            request = DataboxListRequest()

        date_from = request.ts_zust_von.date() if request.ts_zust_von else "open"
        date_to = request.ts_zust_bis.date() if request.ts_zust_bis else "open"
        logger.info("Starting databox sync (%s to %s) to %s", date_from, date_to, output_dir)
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise filesystem_error_from_oserror(exc, path=output_dir, operation="create directory") from exc

        # Build list of applied filters for display
        applied_filters: list[str] = []
        if read_filter != ReadFilter.ALL:
            applied_filters.append(read_filter.value.capitalize())
        if anbringen_filter:
            applied_filters.append(f"UID:{anbringen_filter}")
        filters_tuple = tuple(applied_filters)

        session = _login_session(self._session_client, credentials)

        try:
            list_result = self._databox_client.list_entries(session_id=session.session_id, credentials=credentials, request=request)

            if not list_result.is_success:
                logger.error("Failed to list entries: %s", list_result.msg)
                return SyncResult(
                    total_retrieved=0, total_listed=0, unread_listed=0, downloaded=0, skipped=0, failed=0, total_bytes=0, applied_filters=filters_tuple
                )

            raw_count = len(list_result.entries)
            entries = _filter_sync_entries(list_result.entries, anbringen_filter, read_filter)
            return self._download_entries(session.session_id, credentials, entries, output_dir, skip_existing, raw_count, filters_tuple)
        finally:
            logger.debug("Logging out from FinanzOnline")
            _logout_session(self._session_client, session.session_id, credentials)

    def _try_download_entry(
        self,
        session_id: str,
        credentials: FinanzOnlineCredentials,
        entry: DataboxEntry,
        output_path: Path,
    ) -> tuple[bool, int]:
        """Try to download a single entry.

        Returns:
            Tuple of (success, bytes_downloaded).
        """
        try:
            result = self._download_single_entry(session_id, credentials, entry, output_path)
            return (result.is_success, result.content_size if result.is_success else 0)
        except Exception as e:
            logger.error("Failed to download %s: %s", entry.applkey, e)
            return (False, 0)

    def _should_skip_entry(self, base_path: Path, skip_existing: bool) -> bool:
        """Check if entry should be skipped (already exists)."""
        if skip_existing and base_path.exists():
            logger.debug("Skipping existing: %s", base_path.name)
            return True
        return False

    def _download_entries(
        self,
        session_id: str,
        credentials: FinanzOnlineCredentials,
        entries: tuple[DataboxEntry, ...],
        output_dir: Path,
        skip_existing: bool,
        raw_count: int,
        applied_filters: tuple[str, ...],
    ) -> SyncResult:
        """Download all entries to output directory.

        Args:
            session_id: Active session ID.
            credentials: FinanzOnline credentials.
            entries: Filtered entries to download.
            output_dir: Directory to save files.
            skip_existing: Skip files that already exist.
            raw_count: Raw count from API before filtering.
            applied_filters: Names of filters that were applied.

        Returns:
            SyncResult with download statistics.
        """
        downloaded, skipped, failed, total_bytes = 0, 0, 0, 0
        downloaded_files: list[tuple[DataboxEntry, Path]] = []
        unread_count = sum(1 for e in entries if e.is_unread)

        for entry in entries:
            base_path = output_dir / entry.suggested_filename

            if self._should_skip_entry(base_path, skip_existing):
                skipped += 1
                continue

            output_path = _get_unique_path(base_path)
            success, byte_count = self._try_download_entry(session_id, credentials, entry, output_path)

            if success:
                downloaded += 1
                total_bytes += byte_count
                downloaded_files.append((entry, output_path))
            else:
                failed += 1

        logger.info("Sync complete: %d downloaded, %d skipped, %d failed (%d bytes total)", downloaded, skipped, failed, total_bytes)
        return SyncResult(
            total_retrieved=raw_count,
            total_listed=len(entries),
            unread_listed=unread_count,
            downloaded=downloaded,
            skipped=skipped,
            failed=failed,
            total_bytes=total_bytes,
            downloaded_files=tuple(downloaded_files),
            applied_filters=applied_filters,
        )

    def _download_single_entry(
        self,
        session_id: str,
        credentials: FinanzOnlineCredentials,
        entry: DataboxEntry,
        output_path: Path,
    ) -> DataboxDownloadResult:
        """Download and save a single entry.

        Args:
            session_id: Active session ID.
            credentials: FinanzOnline credentials.
            entry: Entry to download.
            output_path: Path to save the file.

        Returns:
            DataboxDownloadResult indicating success or failure.

        Raises:
            OSError: If file cannot be written (caught by _try_download_entry).
        """
        request = DataboxDownloadRequest(applkey=entry.applkey)

        result = self._databox_client.download_entry(
            session_id=session_id,
            credentials=credentials,
            request=request,
        )

        if result.is_success and result.content is not None:
            try:
                output_path.parent.mkdir(parents=True, exist_ok=True)
            except OSError as exc:
                logger.error(
                    "Cannot create directory for %s: %s",
                    output_path.name,
                    exc,
                )
                raise

            try:
                output_path.write_bytes(result.content)
            except OSError as exc:
                logger.error(
                    "Cannot write file %s: %s",
                    output_path.name,
                    exc,
                )
                raise

            logger.info("Downloaded: %s (%d bytes)", output_path.name, len(result.content))

        return result


@dataclass(frozen=True, slots=True)
class SyncResult:
    """Result of a sync operation.

    Attributes:
        total_retrieved: Raw count of entries returned by API before filtering.
        total_listed: Entries after filtering (by read status, reference, etc.).
        unread_listed: Number of unread entries listed.
        downloaded: Number of entries successfully downloaded.
        skipped: Number of entries skipped (already exist locally).
        failed: Number of entries that failed to download.
        total_bytes: Total bytes downloaded.
        downloaded_files: Tuples of (DataboxEntry, Path) for each downloaded file.
        applied_filters: Names of filters that were applied (e.g., "Unread", "UID:123").
    """

    total_retrieved: int
    total_listed: int
    unread_listed: int
    downloaded: int
    skipped: int
    failed: int
    total_bytes: int
    downloaded_files: tuple[tuple[DataboxEntry, Path], ...] = ()
    applied_filters: tuple[str, ...] = ()

    @property
    def is_success(self) -> bool:
        """Check if sync completed without failures."""
        return self.failed == 0

    @property
    def has_new_downloads(self) -> bool:
        """Check if any new files were downloaded."""
        return self.downloaded > 0
