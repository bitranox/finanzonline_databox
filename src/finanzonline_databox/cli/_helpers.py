"""Orchestration helpers for CLI commands.

Purpose
-------
Date parsing, date-range chunking, result aggregation, entry filtering,
output formatting, and chunked execution logic shared across CLI commands.

Contents
--------
* Date helpers: :func:`_parse_date`, :func:`_chunk_date_range`, :func:`_resolve_date_range`.
* Result helpers: :func:`_aggregate_sync_results`, :func:`_aggregate_list_results`.
* Filter helpers: :func:`_apply_list_filters`, :func:`_filter_by_reference`.
* Execution helpers: :func:`_execute_chunked_list`, :func:`_execute_chunked_sync`.

System Role
-----------
CLI adapter layer — orchestration utilities for databox commands.
"""

# pyright: reportUnusedFunction=false
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from pathlib import Path

import rich_click as click
from lib_layered_config import Config

from .._datetime_utils import local_now
from ..adapters.finanzonline import DataboxClient, FinanzOnlineSessionClient
from ..adapters.output import (
    format_list_result_human,
    format_list_result_json,
    format_sync_result_human,
    format_sync_result_json,
)
from ..application.use_cases import ListDataboxUseCase, SyncDataboxUseCase, SyncResult
from ..config import load_finanzonline_config
from ..domain.errors import ConfigurationError
from ..domain.models import DataboxEntry, DataboxListRequest, DataboxListResult, FinanzOnlineCredentials
from ..enums import OutputFormat, ReadFilter
from ..i18n import _

logger = logging.getLogger(__name__)


def _parse_date(date_str: str | None) -> datetime | None:
    """Parse a date string to datetime.

    Args:
        date_str: Date string in YYYY-MM-DD format or None.

    Returns:
        Parsed datetime with local timezone or None.

    Raises:
        click.BadParameter: If date format is invalid.
    """
    if date_str is None:
        return None
    try:
        parsed = datetime.strptime(date_str, "%Y-%m-%d")  # noqa: DTZ007
        return parsed.astimezone()  # Convert to local timezone
    except ValueError as exc:
        msg = f"Invalid date format: {date_str}. Use YYYY-MM-DD."
        raise click.BadParameter(msg) from exc


def _compute_date_range_from_days(days: int, max_days: int = 7) -> tuple[datetime, datetime]:
    """Compute date range from --days option.

    Args:
        days: Number of days to look back.
        max_days: Maximum allowed days (default 7 for list, 31 for sync).

    Returns:
        Tuple of (ts_zust_von, ts_zust_bis).

    Raises:
        click.BadParameter: If days is out of range.
    """
    if days < 1 or days > max_days:
        raise click.BadParameter(f"Days must be between 1 and {max_days} (API limit)", param_hint="--days")
    now = local_now()
    return now - timedelta(days=days), now


def _chunk_date_range(
    ts_zust_von: datetime,
    ts_zust_bis: datetime,
    chunk_days: int = 7,
) -> list[tuple[datetime, datetime]]:
    """Split a date range into chunks of max chunk_days each.

    The BMF DataBox API only allows 7 days between ts_zust_von and ts_zust_bis.
    This function splits larger ranges into multiple 7-day chunks.

    Args:
        ts_zust_von: Start of date range (oldest).
        ts_zust_bis: End of date range (newest).
        chunk_days: Maximum days per chunk (default 7, API limit).

    Returns:
        List of (start, end) datetime tuples, ordered from oldest to newest.
    """
    chunks: list[tuple[datetime, datetime]] = []
    current_start = ts_zust_von

    while current_start < ts_zust_bis:
        current_end = min(current_start + timedelta(days=chunk_days), ts_zust_bis)
        chunks.append((current_start, current_end))
        current_start = current_end

    return chunks


def _sum_sync_stats(results: list[SyncResult]) -> tuple[int, int, int, int, int, int, int]:
    """Sum statistics from multiple sync results."""
    total_retrieved = total_listed = unread_listed = downloaded = skipped = failed = total_bytes = 0
    for r in results:
        total_retrieved += r.total_retrieved
        total_listed += r.total_listed
        unread_listed += r.unread_listed
        downloaded += r.downloaded
        skipped += r.skipped
        failed += r.failed
        total_bytes += r.total_bytes
    return total_retrieved, total_listed, unread_listed, downloaded, skipped, failed, total_bytes


def _collect_downloaded_files(results: list[SyncResult]) -> tuple[tuple[DataboxEntry, Path], ...]:
    """Collect all downloaded files from multiple sync results."""
    all_files: list[tuple[DataboxEntry, Path]] = []
    for r in results:
        all_files.extend(r.downloaded_files)
    return tuple(all_files)


def _aggregate_sync_results(results: list[SyncResult]) -> SyncResult:
    """Aggregate multiple SyncResults into one."""
    if not results:
        return SyncResult(
            total_retrieved=0,
            total_listed=0,
            unread_listed=0,
            downloaded=0,
            skipped=0,
            failed=0,
            total_bytes=0,
            downloaded_files=(),
            applied_filters=(),
        )

    total_retrieved, total_listed, unread_listed, downloaded, skipped, failed, total_bytes = _sum_sync_stats(results)
    # All chunks have the same filters, take from first result
    applied_filters = results[0].applied_filters if results else ()
    return SyncResult(
        total_retrieved=total_retrieved,
        total_listed=total_listed,
        unread_listed=unread_listed,
        downloaded=downloaded,
        skipped=skipped,
        failed=failed,
        total_bytes=total_bytes,
        downloaded_files=_collect_downloaded_files(results),
        applied_filters=applied_filters,
    )


def _deduplicate_entries(results: list[DataboxListResult]) -> tuple[DataboxEntry, ...]:
    """Collect and deduplicate entries from multiple results by applkey."""
    seen: set[str] = set()
    unique: list[DataboxEntry] = []
    for r in results:
        for entry in r.entries:
            if entry.applkey not in seen:
                unique.append(entry)
                seen.add(entry.applkey)
    return tuple(unique)


def _aggregate_list_results(results: list[DataboxListResult]) -> DataboxListResult:
    """Aggregate multiple list results from date range chunks."""
    if not results:
        return DataboxListResult(rc=0, msg="OK", entries=())

    all_success = all(r.is_success for r in results)
    return DataboxListResult(
        rc=0 if all_success else -1,
        msg="OK" if all_success else "Some chunks failed",
        entries=_deduplicate_entries(results),
    )


def _resolve_date_range(
    days: int | None,
    date_from: str | None,
    date_to: str | None,
    max_days: int = 7,
) -> tuple[datetime | None, datetime | None]:
    """Resolve date range from --days or --from/--to options.

    Args:
        days: Number of days to look back (overrides date_from/date_to).
        date_from: Start date string.
        date_to: End date string.
        max_days: Maximum allowed days for --days option.

    Returns:
        Tuple of (ts_zust_von, ts_zust_bis), either may be None.
    """
    if days is not None:
        return _compute_date_range_from_days(days, max_days)
    return _parse_date(date_from), _parse_date(date_to)


def _format_sync_result(result: SyncResult, output_dir: str, output_format: str) -> str:
    """Format sync result for output.

    Args:
        result: SyncResult to format.
        output_dir: Output directory path.
        output_format: Output format string ('json' or 'human').

    Returns:
        Formatted string.
    """
    if OutputFormat(output_format.lower()) == OutputFormat.JSON:
        return format_sync_result_json(result, output_dir)
    return format_sync_result_human(result, output_dir)


def _format_list_result(result: DataboxListResult, output_format: str) -> str:
    """Format list result for output.

    Args:
        result: DataboxListResult to format.
        output_format: Output format string ('json' or 'human').

    Returns:
        Formatted string.
    """
    if OutputFormat(output_format.lower()) == OutputFormat.JSON:
        return format_list_result_json(result)
    return format_list_result_human(result)


def _filter_unread_entries(result: DataboxListResult) -> DataboxListResult:
    """Filter list result to include only unread entries.

    Args:
        result: Original list result with all entries.

    Returns:
        New DataboxListResult with only unread entries.
    """
    unread_entries = tuple(e for e in result.entries if e.is_unread)
    return DataboxListResult(
        rc=result.rc,
        msg=result.msg,
        entries=unread_entries,
        timestamp=result.timestamp,
    )


def _filter_read_entries(result: DataboxListResult) -> DataboxListResult:
    """Filter list result to include only read entries.

    Args:
        result: Original list result with all entries.

    Returns:
        New DataboxListResult with only read entries.
    """
    read_entries = tuple(e for e in result.entries if e.is_read)
    return DataboxListResult(
        rc=result.rc,
        msg=result.msg,
        entries=read_entries,
        timestamp=result.timestamp,
    )


def _filter_by_reference(result: DataboxListResult, reference: str) -> DataboxListResult:
    """Filter list result to include only entries matching the reference.

    Args:
        result: Original list result with all entries.
        reference: Reference (anbringen) to filter by.

    Returns:
        New DataboxListResult with only matching entries.
    """
    filtered = tuple(e for e in result.entries if e.anbringen == reference)
    return DataboxListResult(
        rc=result.rc,
        msg=result.msg,
        entries=filtered,
        timestamp=result.timestamp,
    )


def _resolve_effective_days(
    days: int | None,
    date_from: str | None,
    date_to: str | None,
    read_filter: ReadFilter,
) -> int | None:
    """Resolve effective days, auto-setting for read/all filters.

    BMF API requires date range to return read documents, so auto-set 31 days
    when --all or --read is specified without explicit date parameters.
    """
    if days is not None or date_from is not None or date_to is not None:
        return days

    if read_filter in (ReadFilter.ALL, ReadFilter.READ):
        logger.info("Auto-setting --days 31 for read_filter=%s (API requires date range)", read_filter)
        return 31

    return days


def _apply_list_filters(
    result: DataboxListResult,
    read_filter: ReadFilter,
    reference: str,
) -> DataboxListResult:
    """Apply read status and reference filters to list result."""
    if not result.is_success:
        return result

    if read_filter == ReadFilter.UNREAD:
        result = _filter_unread_entries(result)
    elif read_filter == ReadFilter.READ:
        result = _filter_read_entries(result)

    if reference:
        result = _filter_by_reference(result, reference)

    return result


def _execute_chunked_list(
    use_case: ListDataboxUseCase,
    credentials: FinanzOnlineCredentials,
    erltyp: str,
    ts_zust_von: datetime,
    ts_zust_bis: datetime,
) -> DataboxListResult:
    """Execute list operation with date range chunking."""
    date_chunks = _chunk_date_range(ts_zust_von, ts_zust_bis, chunk_days=7)
    logger.debug("Listing %d date range chunk(s)", len(date_chunks))

    chunk_results: list[DataboxListResult] = []
    for chunk_start, chunk_end in date_chunks:
        request = DataboxListRequest(
            erltyp=erltyp,
            ts_zust_von=chunk_start,
            ts_zust_bis=chunk_end,
        )
        chunk_result = use_case.execute(credentials=credentials, request=request)
        chunk_results.append(chunk_result)

    return _aggregate_list_results(chunk_results)


def _execute_list_operation(
    use_case: ListDataboxUseCase,
    credentials: FinanzOnlineCredentials,
    erltyp: str,
    ts_zust_von: datetime | None,
    ts_zust_bis: datetime | None,
) -> DataboxListResult:
    """Execute list operation, using chunking if date range is provided."""
    if ts_zust_von is not None and ts_zust_bis is not None:
        return _execute_chunked_list(use_case, credentials, erltyp, ts_zust_von, ts_zust_bis)

    request = DataboxListRequest(erltyp=erltyp)
    return use_case.execute(credentials=credentials, request=request)


def _execute_chunked_sync(
    use_case: SyncDataboxUseCase,
    credentials: FinanzOnlineCredentials,
    output_dir: Path,
    erltyp: str,
    reference: str,
    read_filter: ReadFilter,
    skip_existing: bool,
    ts_zust_von: datetime,
    ts_zust_bis: datetime,
) -> SyncResult:
    """Execute sync operation across chunked date ranges."""
    date_chunks = _chunk_date_range(ts_zust_von, ts_zust_bis, chunk_days=7)
    logger.debug("Syncing %d date range chunk(s)", len(date_chunks))

    chunk_results: list[SyncResult] = []
    for chunk_idx, (chunk_start, chunk_end) in enumerate(date_chunks, start=1):
        # Calculate days from original start date
        days_start = (chunk_start - ts_zust_von).days
        days_end = (chunk_end - ts_zust_von).days

        request = DataboxListRequest(erltyp=erltyp, ts_zust_von=chunk_start, ts_zust_bis=chunk_end)
        chunk_result = use_case.execute(
            credentials=credentials,
            output_dir=output_dir,
            request=request,
            skip_existing=skip_existing,
            anbringen_filter=reference,
            read_filter=read_filter,
        )
        chunk_results.append(chunk_result)

        # Log chunk progress
        logger.info(
            _("Chunk %d (days %d-%d): %d from API, %d after filter - %d unread"),
            chunk_idx,
            days_start,
            days_end,
            chunk_result.total_retrieved,
            chunk_result.total_listed,
            chunk_result.unread_listed,
        )

    return _aggregate_sync_results(chunk_results)


def _resolve_output_dir(
    explicit: str | None,
    config: Config,
    *,
    default: str,
) -> Path:
    """Resolve output directory: CLI option > config > default.

    Args:
        explicit: Explicitly specified output directory from CLI (None if not specified).
        config: Application configuration.
        default: Default path to use if not configured.

    Returns:
        Resolved output directory as Path.
    """
    if explicit is not None:
        return Path(explicit)

    # Try to get from config (load silently, use default on error)
    try:
        fo_config = load_finanzonline_config(config)
        if fo_config.output_dir is not None:
            return fo_config.output_dir
    except ConfigurationError as exc:
        logger.warning("Could not load config for output_dir, using default: %s", exc)

    return Path(default)


def _resolve_download_filename(
    output_dir: Path,
    filename: str | None,
    applkey: str,
    credentials: FinanzOnlineCredentials,
    session_client: FinanzOnlineSessionClient,
    databox_client: DataboxClient,
) -> Path:
    """Resolve output path for download, looking up entry metadata if needed."""
    if filename:
        return output_dir / filename

    # Look up entry to get filebez for proper filename
    list_use_case = ListDataboxUseCase(session_client, databox_client)
    list_result = list_use_case.execute(credentials)

    entry = next((e for e in list_result.entries if e.applkey == applkey), None)
    if entry:
        return output_dir / entry.suggested_filename

    # Fallback if entry not found in list (may be older than 31 days)
    return output_dir / f"{applkey}.bin"
