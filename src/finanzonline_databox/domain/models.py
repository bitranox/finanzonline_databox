"""Domain models for FinanzOnline DataBox document retrieval.

Purpose
-------
Immutable dataclasses representing core domain entities for FinanzOnline
DataBox document download operations. These models are pure value objects
with no behavior beyond basic property accessors.

Contents
--------
* :class:`Diagnostics` - Debug/diagnostic information for errors
* :class:`FinanzOnlineCredentials` - Authentication credentials
* :class:`SessionInfo` - Session state after login
* :class:`DataboxListRequest` - Request to list databox entries
* :class:`DataboxEntry` - A single databox document entry
* :class:`DataboxListResult` - Result of listing databox entries
* :class:`DataboxDownloadRequest` - Request to download a document
* :class:`DataboxDownloadResult` - Result of downloading a document

System Role
-----------
Domain layer - pure data structures with no I/O dependencies. Used by
application layer use cases and passed through adapter boundaries.

Examples
--------
>>> creds = FinanzOnlineCredentials(
...     tid="123456789", benid="TESTUSER", pin="secretpin", herstellerid="ATU12345678"
... )
>>> creds.tid
'123456789'

>>> entry = DataboxEntry(
...     stnr="12-345/6789", name="Bescheid", anbringen="E1",
...     zrvon="2024", zrbis="2024", datbesch=date(2024, 1, 15),
...     erltyp="B", fileart=FileType.PDF, ts_zust=datetime(2024, 1, 15, 10, 30),
...     applkey="abc123", filebez="Einkommensteuerbescheid", status=ReadStatus.UNREAD
... )
>>> entry.is_unread
True
"""

from __future__ import annotations

import re
import warnings
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import IntEnum
from typing import TYPE_CHECKING, ClassVar

from finanzonline_databox._datetime_utils import local_now as _local_now

if TYPE_CHECKING:
    pass


class ReadStatus(IntEnum):
    """Document read status in DataBox."""

    UNREAD = 0
    READ = 1

    @classmethod
    def from_string(cls, value: str) -> ReadStatus:
        """Convert FinanzOnline status string to enum.

        Args:
            value: Status string from API ("" = unread, "1" = read).

        Returns:
            Corresponding ReadStatus enum value.
        """
        if value == "1":
            return cls.READ
        if value == "":
            return cls.UNREAD
        warnings.warn(
            f"Unexpected ReadStatus value {value!r}, defaulting to UNREAD",
            UserWarning,
            stacklevel=2,
        )
        return cls.UNREAD


class FileType(IntEnum):
    """Document file type in DataBox."""

    PDF = 1
    XML = 2
    ZIP = 3
    OTHER = 0

    @classmethod
    def from_string(cls, value: str) -> FileType:
        """Convert file type string to enum.

        Args:
            value: File type string (PDF, XML, ZIP, etc.).

        Returns:
            Corresponding FileType enum value.
        """
        upper = value.upper()
        if upper == "PDF":
            return cls.PDF
        if upper == "XML":
            return cls.XML
        if upper == "ZIP":
            return cls.ZIP
        return cls.OTHER


# Well-known FinanzOnline return codes
RC_OK = 0
RC_SESSION_INVALID = -1
RC_MAINTENANCE = -2
RC_TECHNICAL_ERROR = -3
RC_DATE_PARAMS_REQUIRED = -4
RC_DATE_TOO_OLD = -5
RC_DATE_RANGE_TOO_WIDE = -6

# XSD validation patterns (from login.xsd)
_TID_PATTERN = re.compile(r"^[0-9A-Za-z]{8,12}$")
_BENID_MIN_LEN = 5
_BENID_MAX_LEN = 12
_PIN_MIN_LEN = 5
_PIN_MAX_LEN = 128
_HERSTELLERID_PATTERN = re.compile(r"^[0-9A-Za-z]{10,24}$")

# XSD validation patterns (from databox.xsd)
# Note: applkey is xs:string with no length restriction in XSD
# Observed formats: MI1637001755 (12 chars), BMFZOLB202512010123257c5fea5979814cf (37 chars)
_APPLKEY_PATTERN = re.compile(r"^[0-9A-Za-z]{10,50}$")


def _validate_required(value: str, field_name: str, display_name: str) -> None:
    """Validate that a required field is not empty."""
    if not value:
        raise ValueError(f"{field_name} ({display_name}) is required")


def _validate_length_range(value: str, field_name: str, min_len: int, max_len: int) -> None:
    """Validate that a field length is within the specified range."""
    if not (min_len <= len(value) <= max_len):
        raise ValueError(f"{field_name} must be {min_len}-{max_len} characters, got {len(value)}")


def _validate_pattern(value: str, field_name: str, pattern: re.Pattern[str], description: str) -> None:
    """Validate that a field matches the specified pattern."""
    if not pattern.match(value):
        raise ValueError(f"{field_name} must be {description}, got: {value!r}")


@dataclass(frozen=True, slots=True)
class Diagnostics:
    """Debug/diagnostic information for error reporting.

    Captures request and response details for troubleshooting errors.
    All sensitive data (credentials) should be masked before storing.

    Attributes:
        operation: The operation being performed (e.g., 'login', 'list', 'download').
        tid: Masked participant ID (if applicable).
        benid: Masked user ID (if applicable).
        pin: Masked PIN/password (if applicable).
        applkey: Document key (if applicable).
        erltyp: Document type filter (if applicable).
        session_id: Session ID (if applicable).
        return_code: Return code from response (if applicable).
        response_message: Response message from service (if applicable).
        error_detail: Additional error details (if applicable).

    Examples:
        >>> diag = Diagnostics(operation="login", tid="123***789", benid="TEST***", pin="sec***pin")
        >>> list(diag.items())
        [('operation', 'login'), ('tid', '123***789'), ('benid', 'TEST***'), ('pin', 'sec***pin')]
    """

    operation: str = ""
    tid: str = ""
    benid: str = ""
    pin: str = ""
    applkey: str = ""
    erltyp: str = ""
    session_id: str = ""
    return_code: str = ""
    response_message: str = ""
    error_detail: str = ""

    _FIELD_NAMES: ClassVar[tuple[str, ...]] = (
        "operation",
        "tid",
        "benid",
        "pin",
        "applkey",
        "erltyp",
        "session_id",
        "return_code",
        "response_message",
        "error_detail",
    )

    def items(self) -> Iterator[tuple[str, str]]:
        """Iterate over non-empty diagnostic fields.

        Yields:
            Tuples of (field_name, value) for non-empty fields.

        Examples:
            >>> diag = Diagnostics(operation="login", tid="123***789")
            >>> list(diag.items())
            [('operation', 'login'), ('tid', '123***789')]
        """
        for name in self._FIELD_NAMES:
            value = getattr(self, name)
            if value:
                yield (name, value)

    @property
    def is_empty(self) -> bool:
        """Check if diagnostics contain no information."""
        return not any(getattr(self, name) for name in self._FIELD_NAMES)


@dataclass(frozen=True, slots=True)
class FinanzOnlineCredentials:
    """Authentication credentials for FinanzOnline web services.

    Validation rules per login.xsd:
        - tid: 8-12 alphanumeric characters
        - benid: 5-12 characters
        - pin: 5-128 characters
        - herstellerid: 10-24 alphanumeric characters (VAT-ID of software producer)

    Attributes:
        tid: Participant ID (Teilnehmer-ID) - 8-12 alphanumeric chars.
        benid: User ID (Benutzer-ID) - 5-12 chars.
        pin: Password/PIN for authentication - 5-128 chars.
        herstellerid: VAT-ID of software producer - 10-24 alphanumeric chars.
    """

    tid: str
    benid: str
    pin: str
    herstellerid: str

    def __post_init__(self) -> None:
        """Validate credentials according to login.xsd schema."""
        _validate_required(self.tid, "tid", "Participant ID")
        _validate_pattern(self.tid, "tid", _TID_PATTERN, "8-12 alphanumeric characters")

        _validate_required(self.benid, "benid", "User ID")
        _validate_length_range(self.benid, "benid", _BENID_MIN_LEN, _BENID_MAX_LEN)

        _validate_required(self.pin, "pin", "Password")
        _validate_length_range(self.pin, "pin", _PIN_MIN_LEN, _PIN_MAX_LEN)

        _validate_required(self.herstellerid, "herstellerid", "Software Producer VAT-ID")
        _validate_pattern(self.herstellerid, "herstellerid", _HERSTELLERID_PATTERN, "10-24 alphanumeric characters")


@dataclass(frozen=True, slots=True)
class SessionInfo:
    """Session information returned after successful login.

    Attributes:
        session_id: Session identifier for subsequent requests.
        return_code: Login return code (0 = success).
        message: Human-readable status message.
    """

    session_id: str
    return_code: int
    message: str

    @property
    def is_valid(self) -> bool:
        """Check if session was created successfully."""
        return self.return_code == RC_OK and bool(self.session_id)


@dataclass(frozen=True, slots=True)
class DataboxListRequest:
    """Request parameters for listing databox entries.

    Attributes:
        erltyp: Document type filter (empty = all unread).
            Common types: B (Bescheide), M (Mitteilungen), I (Informationen), P (Protokolle).
        ts_zust_von: Start date for filtering (max 31 days in the past).
        ts_zust_bis: End date for filtering (max 7 days after ts_zust_von).

    Note:
        If ts_zust_von/bis are not provided, only unread entries are returned.
        If provided, both read and unread entries in the date range are returned.
    """

    erltyp: str = ""
    ts_zust_von: datetime | None = None
    ts_zust_bis: datetime | None = None

    def __post_init__(self) -> None:
        """Validate date range constraints."""
        if self.ts_zust_von is not None and self.ts_zust_bis is not None and self.ts_zust_bis < self.ts_zust_von:
            raise ValueError("ts_zust_bis must be >= ts_zust_von")


@dataclass(frozen=True, slots=True)
class DataboxEntry:
    """A single databox entry (document metadata).

    Represents one document in the FinanzOnline databox that can be downloaded.

    Attributes:
        stnr: Tax number (Steuernummer).
        name: Name/title of the document.
        anbringen: Document reference code.
        zrvon: Period from (e.g., "2024").
        zrbis: Period to (e.g., "2024").
        datbesch: Document date.
        erltyp: Document type code (B, M, I, P, EU, etc.).
        fileart: File type (PDF, XML, ZIP).
        ts_zust: Delivery timestamp.
        applkey: Key for downloading the document.
        filebez: File description.
        status: Read status (ReadStatus.UNREAD or ReadStatus.READ).

    Examples:
        >>> entry = DataboxEntry(
        ...     stnr="12-345/6789", name="Bescheid", anbringen="E1",
        ...     zrvon="2024", zrbis="2024", datbesch=date(2024, 1, 15),
        ...     erltyp="B", fileart=FileType.PDF, ts_zust=datetime(2024, 1, 15, 10, 30),
        ...     applkey="abc123def456", filebez="Einkommensteuerbescheid", status=ReadStatus.UNREAD
        ... )
        >>> entry.is_unread
        True
        >>> entry.is_pdf
        True
    """

    stnr: str
    name: str
    anbringen: str
    zrvon: str
    zrbis: str
    datbesch: date
    erltyp: str
    fileart: FileType
    ts_zust: datetime
    applkey: str
    filebez: str
    status: ReadStatus

    @property
    def is_unread(self) -> bool:
        """Check if this entry has not been read yet."""
        return self.status == ReadStatus.UNREAD

    @property
    def is_read(self) -> bool:
        """Check if this entry has been read."""
        return self.status == ReadStatus.READ

    @property
    def is_pdf(self) -> bool:
        """Check if this is a PDF document."""
        return self.fileart == FileType.PDF

    @property
    def is_xml(self) -> bool:
        """Check if this is an XML document."""
        return self.fileart == FileType.XML

    @property
    def is_zip(self) -> bool:
        """Check if this is a ZIP archive."""
        return self.fileart == FileType.ZIP

    @property
    def suggested_filename(self) -> str:
        """Generate a suggested filename for this document.

        Uses the filebez (file description) field from the API if available.
        Falls back to a generated name if filebez is empty.

        Returns:
            Filename from filebez, or format: YYYY-MM-DD_erltyp_anbringen_applkey.ext

        Examples:
            >>> entry = DataboxEntry(
            ...     stnr="", name="", anbringen="UID", zrvon="", zrbis="",
            ...     datbesch=date(2024, 1, 15), erltyp="P", fileart=FileType.XML,
            ...     ts_zust=datetime(2024, 1, 15), applkey="MI1639230524",
            ...     filebez="MIUID_ATU62139135_20240115.xml", status=ReadStatus.UNREAD
            ... )
            >>> entry.suggested_filename
            'MIUID_ATU62139135_20240115.xml'
            >>> entry_empty = DataboxEntry(
            ...     stnr="", name="", anbringen="E1", zrvon="", zrbis="",
            ...     datbesch=date(2024, 1, 15), erltyp="B", fileart=FileType.PDF,
            ...     ts_zust=datetime(2024, 1, 15), applkey="abc123def456", filebez="", status=ReadStatus.UNREAD
            ... )
            >>> entry_empty.suggested_filename
            '2024-01-15_B_E1_abc123def456.pdf'
        """
        if self.filebez:
            return self.filebez
        # Fallback for empty filebez
        date_str = self.datbesch.strftime("%Y-%m-%d")
        ext = self.fileart.name.lower()
        return f"{date_str}_{self.erltyp}_{self.anbringen}_{self.applkey}.{ext}"


@dataclass(frozen=True, slots=True)
class DataboxListResult:
    """Result of listing databox entries.

    Attributes:
        rc: Return code (0 = success).
        msg: Response message (if error).
        entries: List of databox entries.
        timestamp: When the list was retrieved (local timezone).
    """

    rc: int
    msg: str | None
    entries: tuple[DataboxEntry, ...] = ()
    timestamp: datetime = field(default_factory=_local_now)

    @property
    def is_success(self) -> bool:
        """Check if the list operation succeeded."""
        return self.rc == RC_OK

    @property
    def entry_count(self) -> int:
        """Return the number of entries."""
        return len(self.entries)

    @property
    def unread_count(self) -> int:
        """Return the number of unread entries."""
        return sum(1 for e in self.entries if e.is_unread)


@dataclass(frozen=True, slots=True)
class DataboxDownloadRequest:
    """Request to download a specific document.

    Attributes:
        applkey: Document key from DataboxEntry (10-50 alphanumeric chars).
    """

    applkey: str

    def __post_init__(self) -> None:
        """Validate applkey format."""
        _validate_required(self.applkey, "applkey", "Document Key")
        _validate_pattern(self.applkey, "applkey", _APPLKEY_PATTERN, "10-50 alphanumeric characters")


@dataclass(frozen=True, slots=True)
class DataboxDownloadResult:
    """Result of downloading a document.

    Attributes:
        rc: Return code (0 = success).
        msg: Response message (if error).
        content: Decoded document content (bytes).
        timestamp: When the download was performed (local timezone).
    """

    rc: int
    msg: str | None
    content: bytes | None = None
    timestamp: datetime = field(default_factory=_local_now)

    @property
    def is_success(self) -> bool:
        """Check if the download succeeded."""
        return self.rc == RC_OK and self.content is not None

    @property
    def content_size(self) -> int:
        """Return the size of the downloaded content in bytes."""
        return len(self.content) if self.content else 0


@dataclass(frozen=True, slots=True)
class NotificationOptions:
    """Options for notification handling in CLI commands.

    Groups notification-related options that travel together to reduce
    parameter list length.

    Attributes:
        enabled: Whether notifications should be sent.
        recipients: Explicit recipients (empty list uses config defaults).
    """

    enabled: bool = True
    recipients: tuple[str, ...] = ()
