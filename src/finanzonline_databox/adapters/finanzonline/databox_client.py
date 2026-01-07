"""FinanzOnline DataBox adapter.

Purpose
-------
Implement DataBox operations for listing and downloading documents
from BMF FinanzOnline DataBox-Download webservice using SOAP/zeep.

Contents
--------
* :class:`DataboxClient` - DataBox SOAP client adapter

System Role
-----------
Adapters layer - SOAP client for FinanzOnline DataBox webservice.

Reference
---------
BMF DataBox-Download Webservice: https://finanzonline.bmf.gv.at/fon/ws/databoxService.wsdl
"""

from __future__ import annotations

import base64
import binascii
import logging
from datetime import date, datetime
from typing import TYPE_CHECKING, Any, cast

from zeep import Client
from zeep.exceptions import Fault, TransportError, XMLSyntaxError
from zeep.transports import Transport

from finanzonline_databox._datetime_utils import local_now
from finanzonline_databox._format_utils import mask_credential
from finanzonline_databox.domain.errors import DataboxOperationError, SessionError
from finanzonline_databox.domain.models import (
    RC_OK,
    RC_SESSION_INVALID,
    DataboxDownloadRequest,
    DataboxDownloadResult,
    DataboxEntry,
    DataboxListRequest,
    DataboxListResult,
    Diagnostics,
    FileType,
    FinanzOnlineCredentials,
    ReadStatus,
)

if TYPE_CHECKING:
    pass


logger = logging.getLogger(__name__)

DATABOX_SERVICE_WSDL = "https://finanzonline.bmf.gv.at/fon/ws/databoxService.wsdl"

# Maximum length of HTML content to include in diagnostics (for email)
_MAX_HTML_CONTENT_LENGTH = 4000


def _is_maintenance_page(content: str | bytes | None) -> bool:
    """Detect if content is a FinanzOnline maintenance page.

    Args:
        content: Raw HTML content (string or bytes).

    Returns:
        True if content appears to be a maintenance page.

    Examples:
        >>> _is_maintenance_page('<html><a href="/wartung/error.css">Error</a></html>')
        True
        >>> _is_maintenance_page('<html><body>Normal response</body></html>')
        False
        >>> _is_maintenance_page(None)
        False
    """
    if not content:
        return False
    content_str = content.decode("utf-8", errors="replace") if isinstance(content, bytes) else content
    content_lower = content_str.lower()
    return "/wartung/" in content_lower


def _extract_xml_error_content(exc: XMLSyntaxError) -> str:
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


def _build_list_diagnostics(
    session_id: str,
    credentials: FinanzOnlineCredentials,
    request: DataboxListRequest,
    response: Any | None = None,
    error: str | None = None,
) -> Diagnostics:
    """Build diagnostic information for list operation.

    Args:
        session_id: Active session ID (will be masked).
        credentials: The credentials used.
        request: The list request.
        response: Optional SOAP response object.
        error: Optional error message.

    Returns:
        Diagnostics object with diagnostic information.
    """
    return_code = ""
    response_message = ""

    if response is not None:
        return_code = str(getattr(response, "rc", ""))
        response_message = str(getattr(response, "msg", "") or "")

    return Diagnostics(
        operation="getDatabox",
        tid=credentials.tid,
        benid=credentials.benid,
        pin=mask_credential(credentials.pin),
        session_id=mask_credential(session_id),
        erltyp=request.erltyp,
        return_code=return_code,
        response_message=response_message,
        error_detail=error or "",
    )


def _build_download_diagnostics(
    session_id: str,
    credentials: FinanzOnlineCredentials,
    request: DataboxDownloadRequest,
    response: Any | None = None,
    error: str | None = None,
) -> Diagnostics:
    """Build diagnostic information for download operation.

    Args:
        session_id: Active session ID (will be masked).
        credentials: The credentials used.
        request: The download request.
        response: Optional SOAP response object.
        error: Optional error message.

    Returns:
        Diagnostics object with diagnostic information.
    """
    return_code = ""
    response_message = ""

    if response is not None:
        return_code = str(getattr(response, "rc", ""))
        response_message = str(getattr(response, "msg", "") or "")

    return Diagnostics(
        operation="getDataboxEntry",
        tid=credentials.tid,
        benid=credentials.benid,
        pin=mask_credential(credentials.pin),
        session_id=mask_credential(session_id),
        applkey=request.applkey,
        return_code=return_code,
        response_message=response_message,
        error_detail=error or "",
    )


def _parse_date(value: Any) -> date:
    """Parse date from SOAP response.

    Args:
        value: Date value from SOAP response (date object or string).

    Returns:
        Python date object.
    """
    # Check datetime first since datetime is a subclass of date
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    # Try parsing string format
    return datetime.strptime(str(value), "%Y-%m-%d").date()


def _parse_datetime(value: Any) -> datetime:
    """Parse datetime from SOAP response.

    BMF FinanzOnline returns naive datetime values that represent Austrian
    local time (Europe/Vienna). This function assumes the server runs in
    the same timezone as the BMF service. Naive datetimes are converted
    to the system's local timezone using astimezone().

    Note:
        If this application is run outside Austria/Europe, the timezone
        interpretation may be incorrect. For production use in other
        timezones, consider explicitly setting the timezone to Europe/Vienna
        before calling astimezone().

    Args:
        value: Datetime value from SOAP response (datetime object or ISO string).

    Returns:
        Python datetime object with timezone information attached.
    """
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.astimezone()  # Assume local timezone (expected: Europe/Vienna)
        return value
    # Try parsing string format
    dt = datetime.fromisoformat(str(value))
    if dt.tzinfo is None:
        return dt.astimezone()  # Assume local timezone (expected: Europe/Vienna)
    return dt


def _get_str_attr(obj: Any, name: str) -> str:
    """Get string attribute from object, defaulting to empty string."""
    return str(getattr(obj, name, "") or "")


def _extract_response_message(response: Any) -> str | None:
    """Extract message from SOAP response."""
    if not hasattr(response, "msg"):
        return None
    return str(getattr(response, "msg", "") or "")


def _decode_content(
    response: Any,
    applkey: str,
    session_id: str,
    credentials: FinanzOnlineCredentials,
) -> bytes | None:
    """Decode base64 content from download response.

    Args:
        response: SOAP response containing base64 encoded content.
        applkey: Document key for logging and diagnostics.
        session_id: Session ID for diagnostics.
        credentials: Credentials for diagnostics.

    Returns:
        Decoded bytes or None if no content.

    Raises:
        DataboxOperationError: If base64 decoding fails.
    """
    raw_content = getattr(response, "result", None)
    if not raw_content:
        return None

    try:
        content = base64.b64decode(raw_content)
    except binascii.Error as exc:
        request = DataboxDownloadRequest(applkey=applkey)
        diagnostics = _build_download_diagnostics(
            session_id,
            credentials,
            request,
            response,
            error=f"Invalid base64 content: {exc}",
        )
        raise DataboxOperationError(
            f"Failed to decode document content for applkey={applkey}: invalid base64 encoding",
            diagnostics=diagnostics,
        ) from exc

    logger.info("Downloaded %d bytes for applkey=%s", len(content), applkey)
    return content


def _parse_databox_entry(entry: Any) -> DataboxEntry:
    """Parse a single databox entry from SOAP response.

    Args:
        entry: Raw entry object from SOAP response.

    Returns:
        DataboxEntry domain object.
    """
    return DataboxEntry(
        stnr=_get_str_attr(entry, "stnr"),
        name=_get_str_attr(entry, "name"),
        anbringen=_get_str_attr(entry, "anbringen"),
        zrvon=_get_str_attr(entry, "zrvon"),
        zrbis=_get_str_attr(entry, "zrbis"),
        datbesch=_parse_date(getattr(entry, "datbesch", date.today())),
        erltyp=_get_str_attr(entry, "erltyp"),
        fileart=FileType.from_string(_get_str_attr(entry, "fileart")),
        ts_zust=_parse_datetime(getattr(entry, "ts_zust", local_now())),
        applkey=_get_str_attr(entry, "applkey"),
        filebez=_get_str_attr(entry, "filebez"),
        status=ReadStatus.from_string(_get_str_attr(entry, "status")),
    )


def _handle_list_exception(
    exc: Exception,
    session_id: str,
    credentials: FinanzOnlineCredentials,
    request: DataboxListRequest,
    response: Any | None,
) -> None:
    """Handle exceptions during list operation and raise appropriate domain error.

    Args:
        exc: The exception that occurred.
        session_id: Active session ID.
        credentials: FinanzOnline credentials.
        request: The list request.
        response: Optional SOAP response.

    Raises:
        SessionError: For session-related errors.
        DataboxOperationError: For all other errors.
    """
    if isinstance(exc, (SessionError, DataboxOperationError)):
        raise

    diagnostics = _build_list_diagnostics(session_id, credentials, request, response, error=str(exc))

    if isinstance(exc, Fault):
        logger.error("SOAP fault during databox list: %s", exc)
        raise DataboxOperationError(f"SOAP fault: {exc.message}", diagnostics=diagnostics) from exc

    if isinstance(exc, TransportError):
        logger.error("Transport error during databox list: %s", exc)
        raise DataboxOperationError(f"Connection error: {exc}", retryable=True, diagnostics=diagnostics) from exc

    if isinstance(exc, XMLSyntaxError):
        html_content = getattr(exc, "content", None)
        is_maintenance = _is_maintenance_page(html_content)
        error_type = "DataBox in Wartung" if is_maintenance else "Invalid XML Response"
        error_detail = _extract_xml_error_content(exc)
        diagnostics = _build_list_diagnostics(session_id, credentials, request, response, error=error_detail)
        logger.error("%s during databox list: %s", error_type, exc)
        raise DataboxOperationError(error_type, diagnostics=diagnostics, retryable=is_maintenance) from exc

    logger.error("Unexpected error during databox list: %s", exc)
    raise DataboxOperationError(f"Unexpected error: {exc}", diagnostics=diagnostics) from exc


def _handle_download_exception(
    exc: Exception,
    session_id: str,
    credentials: FinanzOnlineCredentials,
    request: DataboxDownloadRequest,
    response: Any | None,
) -> None:
    """Handle exceptions during download operation and raise appropriate domain error.

    Args:
        exc: The exception that occurred.
        session_id: Active session ID.
        credentials: FinanzOnline credentials.
        request: The download request.
        response: Optional SOAP response.

    Raises:
        SessionError: For session-related errors.
        DataboxOperationError: For all other errors.
    """
    if isinstance(exc, (SessionError, DataboxOperationError)):
        raise

    diagnostics = _build_download_diagnostics(session_id, credentials, request, response, error=str(exc))

    if isinstance(exc, Fault):
        logger.error("SOAP fault during databox download: %s", exc)
        raise DataboxOperationError(f"SOAP fault: {exc.message}", diagnostics=diagnostics) from exc

    if isinstance(exc, TransportError):
        logger.error("Transport error during databox download: %s", exc)
        raise DataboxOperationError(f"Connection error: {exc}", retryable=True, diagnostics=diagnostics) from exc

    if isinstance(exc, XMLSyntaxError):
        html_content = getattr(exc, "content", None)
        is_maintenance = _is_maintenance_page(html_content)
        error_type = "DataBox in Wartung" if is_maintenance else "Invalid XML Response"
        error_detail = _extract_xml_error_content(exc)
        diagnostics = _build_download_diagnostics(session_id, credentials, request, response, error=error_detail)
        logger.error("%s during databox download: %s", error_type, exc)
        raise DataboxOperationError(error_type, diagnostics=diagnostics, retryable=is_maintenance) from exc

    logger.error("Unexpected error during databox download: %s", exc)
    raise DataboxOperationError(f"Unexpected error: {exc}", diagnostics=diagnostics) from exc


class DataboxClient:
    """SOAP client for FinanzOnline DataBox operations.

    Provides methods to list databox entries and download documents
    via the BMF DataBox-Download webservice.

    Attributes:
        _timeout: Request timeout in seconds.
        _client: Zeep SOAP client (lazy-initialized).
    """

    def __init__(self, timeout: float = 30.0) -> None:
        """Initialize databox client.

        Args:
            timeout: Request timeout in seconds.
        """
        self._timeout = timeout
        self._client: Client | None = None

    def _get_client(self) -> Client:
        """Get or create SOAP client with configured timeout.

        Returns:
            Zeep Client instance for DataBox service.
        """
        if self._client is None:
            logger.debug("Creating DataBox service client with timeout=%.1fs", self._timeout)
            transport = Transport(timeout=self._timeout)
            self._client = Client(DATABOX_SERVICE_WSDL, transport=transport)
        return self._client

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
            SessionError: If session is invalid or expired (code -1).
            DataboxOperationError: If operation fails.
        """
        logger.debug("Listing databox entries with erltyp=%r", request.erltyp)
        response: Any = None

        try:
            response = self._execute_list_query(session_id, credentials, request)
            return self._process_list_response(session_id, credentials, request, response)
        except Exception as e:
            _handle_list_exception(e, session_id, credentials, request, response)
            raise  # Unreachable but satisfies type checker

    def _execute_list_query(
        self,
        session_id: str,
        credentials: FinanzOnlineCredentials,
        request: DataboxListRequest,
    ) -> Any:
        """Execute the SOAP list query call."""
        client = self._get_client()

        # Build parameters - erltyp is required but can be empty string
        params: dict[str, Any] = {
            "tid": credentials.tid,
            "benid": credentials.benid,
            "id": session_id,
            "erltyp": request.erltyp,  # Required field, empty = all unread
        }

        # Add optional date filters
        if request.ts_zust_von is not None:
            params["ts_zust_von"] = request.ts_zust_von
        if request.ts_zust_bis is not None:
            params["ts_zust_bis"] = request.ts_zust_bis

        logger.debug("DataBox list request params: tid=%s, benid=%s, erltyp=%r", credentials.tid, credentials.benid, request.erltyp)
        response = client.service.getDatabox(**params)
        logger.debug("DataBox list response: rc=%s", getattr(response, "rc", "?"))
        return response

    def _check_session_valid(
        self,
        return_code: int,
        message: str | None,
        session_id: str,
        credentials: FinanzOnlineCredentials,
        request: DataboxListRequest | DataboxDownloadRequest,
        response: Any,
    ) -> None:
        """Raise SessionError if session is invalid."""
        if return_code != RC_SESSION_INVALID:
            return
        if isinstance(request, DataboxListRequest):
            diagnostics = _build_list_diagnostics(session_id, credentials, request, response)
        else:
            diagnostics = _build_download_diagnostics(session_id, credentials, request, response)
        raise SessionError(f"Session invalid or expired: {message}", return_code=return_code, diagnostics=diagnostics)

    def _process_list_response(
        self,
        session_id: str,
        credentials: FinanzOnlineCredentials,
        request: DataboxListRequest,
        response: Any,
    ) -> DataboxListResult:
        """Process SOAP list response and build result."""
        return_code = int(cast(int, response.rc))
        message = _extract_response_message(response)
        logger.debug("List response: rc=%d, msg=%s", return_code, message)

        self._check_session_valid(return_code, message, session_id, credentials, request, response)

        entries: tuple[DataboxEntry, ...] = ()
        if return_code == RC_OK:
            raw_entries = getattr(response, "result", None) or []
            entries = tuple(_parse_databox_entry(e) for e in raw_entries)
            logger.info("Retrieved %d databox entries", len(entries))

        return DataboxListResult(rc=return_code, msg=message, entries=entries, timestamp=local_now())

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
            SessionError: If session is invalid or expired (code -1).
            DataboxOperationError: If operation fails.
        """
        logger.debug("Downloading databox entry with applkey=%s", request.applkey)
        response: Any = None

        try:
            response = self._execute_download_query(session_id, credentials, request)
            return self._process_download_response(session_id, credentials, request, response)
        except Exception as e:
            _handle_download_exception(e, session_id, credentials, request, response)
            raise  # Unreachable but satisfies type checker

    def _execute_download_query(
        self,
        session_id: str,
        credentials: FinanzOnlineCredentials,
        request: DataboxDownloadRequest,
    ) -> Any:
        """Execute the SOAP download query call."""
        client = self._get_client()

        logger.debug("DataBox download request: applkey=%s", request.applkey)
        response = client.service.getDataboxEntry(
            tid=credentials.tid,
            benid=credentials.benid,
            id=session_id,
            applkey=request.applkey,
        )
        logger.debug("DataBox download response: rc=%s", getattr(response, "rc", "?"))
        return response

    def _process_download_response(
        self,
        session_id: str,
        credentials: FinanzOnlineCredentials,
        request: DataboxDownloadRequest,
        response: Any,
    ) -> DataboxDownloadResult:
        """Process SOAP download response and build result."""
        return_code = int(cast(int, response.rc))
        message = _extract_response_message(response)
        logger.debug("Download response: rc=%d, msg=%s", return_code, message)

        self._check_session_valid(return_code, message, session_id, credentials, request, response)

        content = _decode_content(response, request.applkey, session_id, credentials) if return_code == RC_OK else None
        return DataboxDownloadResult(rc=return_code, msg=message, content=content, timestamp=local_now())
