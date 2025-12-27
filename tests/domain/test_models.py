"""Tests for domain models.

Tests cover immutability, validation, and property behavior of
all domain model dataclasses.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from finanzonline_databox.domain.models import (
    DataboxDownloadRequest,
    DataboxDownloadResult,
    DataboxEntry,
    DataboxListRequest,
    DataboxListResult,
    Diagnostics,
    FileType,
    FinanzOnlineCredentials,
    NotificationOptions,
    ReadStatus,
    SessionInfo,
)

pytestmark = pytest.mark.os_agnostic


class TestFinanzOnlineCredentials:
    """Tests for FinanzOnlineCredentials dataclass.

    XSD validation rules (from login.xsd):
        - tid: pattern [0-9A-Za-z]{8,12}
        - benid: minLength 5, maxLength 12
        - pin: minLength 5, maxLength 128
        - herstellerid: pattern [0-9A-Za-z]{10,24}
    """

    def test_create_valid_credentials(self) -> None:
        """Should create credentials with valid XSD-compliant values."""
        creds = FinanzOnlineCredentials(
            tid="123456789",
            benid="TESTUSER",
            pin="secretpin",
            herstellerid="ATU12345678",
        )
        assert creds.tid == "123456789"
        assert creds.benid == "TESTUSER"
        assert creds.pin == "secretpin"
        assert creds.herstellerid == "ATU12345678"

    def test_immutability(self) -> None:
        """Should be immutable (frozen dataclass)."""
        creds = FinanzOnlineCredentials(
            tid="123456789",
            benid="TESTUSER",
            pin="secretpin",
            herstellerid="ATU12345678",
        )
        with pytest.raises(AttributeError):
            creds.tid = "456"  # type: ignore[misc]

    def test_empty_tid_raises(self) -> None:
        """Should raise ValueError for empty tid."""
        with pytest.raises(ValueError, match="tid.*required"):
            FinanzOnlineCredentials(tid="", benid="TESTUSER", pin="secretpin", herstellerid="ATU12345678")

    def test_tid_too_short_raises(self) -> None:
        """Should raise ValueError for tid shorter than 8 chars."""
        with pytest.raises(ValueError, match="tid must be 8-12 alphanumeric"):
            FinanzOnlineCredentials(tid="1234567", benid="TESTUSER", pin="secretpin", herstellerid="ATU12345678")

    def test_tid_too_long_raises(self) -> None:
        """Should raise ValueError for tid longer than 12 chars."""
        with pytest.raises(ValueError, match="tid must be 8-12 alphanumeric"):
            FinanzOnlineCredentials(tid="1234567890123", benid="TESTUSER", pin="secretpin", herstellerid="ATU12345678")

    def test_empty_benid_raises(self) -> None:
        """Should raise ValueError for empty benid."""
        with pytest.raises(ValueError, match="benid.*required"):
            FinanzOnlineCredentials(tid="123456789", benid="", pin="secretpin", herstellerid="ATU12345678")

    def test_benid_too_short_raises(self) -> None:
        """Should raise ValueError for benid shorter than 5 chars."""
        with pytest.raises(ValueError, match="benid must be 5-12 characters"):
            FinanzOnlineCredentials(tid="123456789", benid="ABCD", pin="secretpin", herstellerid="ATU12345678")

    def test_empty_pin_raises(self) -> None:
        """Should raise ValueError for empty pin."""
        with pytest.raises(ValueError, match="pin.*required"):
            FinanzOnlineCredentials(tid="123456789", benid="TESTUSER", pin="", herstellerid="ATU12345678")

    def test_pin_too_short_raises(self) -> None:
        """Should raise ValueError for pin shorter than 5 chars."""
        with pytest.raises(ValueError, match="pin must be 5-128 characters"):
            FinanzOnlineCredentials(tid="123456789", benid="TESTUSER", pin="1234", herstellerid="ATU12345678")

    def test_empty_herstellerid_raises(self) -> None:
        """Should raise ValueError for empty herstellerid."""
        with pytest.raises(ValueError, match="herstellerid.*required"):
            FinanzOnlineCredentials(tid="123456789", benid="TESTUSER", pin="secretpin", herstellerid="")

    def test_herstellerid_too_short_raises(self) -> None:
        """Should raise ValueError for herstellerid shorter than 10 chars."""
        with pytest.raises(ValueError, match="herstellerid must be 10-24 alphanumeric"):
            FinanzOnlineCredentials(tid="123456789", benid="TESTUSER", pin="secretpin", herstellerid="ATU123456")


class TestSessionInfo:
    """Tests for SessionInfo dataclass."""

    def test_create_valid_session(self) -> None:
        """Should create session info with valid values."""
        session = SessionInfo(session_id="ABC123", return_code=0, message="OK")
        assert session.session_id == "ABC123"
        assert session.return_code == 0
        assert session.message == "OK"

    def test_is_valid_success(self) -> None:
        """Should return True for successful session."""
        session = SessionInfo(session_id="ABC123", return_code=0, message="OK")
        assert session.is_valid is True

    def test_is_valid_failure_code(self) -> None:
        """Should return False for non-zero return code."""
        session = SessionInfo(session_id="ABC123", return_code=-1, message="Error")
        assert session.is_valid is False

    def test_is_valid_empty_session_id(self) -> None:
        """Should return False for empty session ID even with code 0."""
        session = SessionInfo(session_id="", return_code=0, message="OK")
        assert session.is_valid is False


class TestDiagnostics:
    """Tests for Diagnostics dataclass."""

    def test_create_empty_diagnostics(self) -> None:
        """Should create empty diagnostics."""
        diag = Diagnostics()
        assert diag.operation == ""
        assert diag.is_empty is True

    def test_create_full_diagnostics(self) -> None:
        """Should create diagnostics with all fields."""
        diag = Diagnostics(
            operation="list",
            tid="123***789",
            benid="TEST***",
            applkey="abc***xyz",
            erltyp="B",
            session_id="sess123",
            return_code="-1",
            response_message="Error message",
        )
        assert diag.operation == "list"
        assert diag.tid == "123***789"
        assert diag.applkey == "abc***xyz"
        assert diag.is_empty is False

    def test_items_filters_empty(self) -> None:
        """Should return only non-empty fields via items()."""
        diag = Diagnostics(operation="login", tid="123")
        items = list(diag.items())
        assert items == [("operation", "login"), ("tid", "123")]

    def test_is_empty_true(self) -> None:
        """Should return True for empty diagnostics."""
        assert Diagnostics().is_empty is True

    def test_is_empty_false(self) -> None:
        """Should return False when any field is set."""
        assert Diagnostics(operation="test").is_empty is False


class TestDataboxListRequest:
    """Tests for DataboxListRequest dataclass."""

    def test_create_default_request(self) -> None:
        """Should create request with default values (list all unread)."""
        request = DataboxListRequest()
        assert request.erltyp == ""
        assert request.ts_zust_von is None
        assert request.ts_zust_bis is None

    def test_create_filtered_request(self) -> None:
        """Should create request with document type filter."""
        request = DataboxListRequest(erltyp="B")
        assert request.erltyp == "B"

    def test_create_date_range_request(self) -> None:
        """Should create request with date range."""
        von = datetime(2024, 1, 1, tzinfo=timezone.utc)
        bis = datetime(2024, 1, 7, tzinfo=timezone.utc)
        request = DataboxListRequest(ts_zust_von=von, ts_zust_bis=bis)
        assert request.ts_zust_von == von
        assert request.ts_zust_bis == bis

    def test_date_range_bis_before_von_raises(self) -> None:
        """Should raise ValueError if ts_zust_bis < ts_zust_von."""
        von = datetime(2024, 1, 7, tzinfo=timezone.utc)
        bis = datetime(2024, 1, 1, tzinfo=timezone.utc)
        with pytest.raises(ValueError, match="ts_zust_bis must be >= ts_zust_von"):
            DataboxListRequest(ts_zust_von=von, ts_zust_bis=bis)


class TestDataboxEntry:
    """Tests for DataboxEntry dataclass."""

    def test_create_valid_entry(self, sample_databox_entry: DataboxEntry) -> None:
        """Should create entry with all fields."""
        assert sample_databox_entry.stnr == "12-345/6789"
        assert sample_databox_entry.erltyp == "B"
        assert sample_databox_entry.applkey == "abc123def456xyz"

    def test_is_unread_true(self, sample_databox_entry: DataboxEntry) -> None:
        """Should return True for empty status."""
        assert sample_databox_entry.is_unread is True

    def test_is_unread_false(self) -> None:
        """Should return False for status='1'."""
        entry = DataboxEntry(
            stnr="",
            name="",
            anbringen="E1",
            zrvon="",
            zrbis="",
            datbesch=date(2024, 1, 1),
            erltyp="B",
            fileart=FileType.PDF,
            ts_zust=datetime(2024, 1, 1, tzinfo=timezone.utc),
            applkey="abc123def456xyz",
            filebez="",
            status=ReadStatus.READ,
        )
        assert entry.is_unread is False
        assert entry.is_read is True

    def test_is_pdf(self, sample_databox_entry: DataboxEntry) -> None:
        """Should return True for PDF fileart."""
        assert sample_databox_entry.is_pdf is True
        assert sample_databox_entry.is_xml is False
        assert sample_databox_entry.is_zip is False

    def test_is_xml(self) -> None:
        """Should return True for XML fileart."""
        entry = DataboxEntry(
            stnr="",
            name="",
            anbringen="E1",
            zrvon="",
            zrbis="",
            datbesch=date(2024, 1, 1),
            erltyp="B",
            fileart=FileType.XML,
            ts_zust=datetime(2024, 1, 1, tzinfo=timezone.utc),
            applkey="abc123def456xyz",
            filebez="",
            status=ReadStatus.UNREAD,
        )
        assert entry.is_xml is True
        assert entry.is_pdf is False

    def test_suggested_filename_uses_filebez(self, sample_databox_entry: DataboxEntry) -> None:
        """Should use filebez as filename when available."""
        # sample_databox_entry has filebez="Einkommensteuerbescheid 2024"
        assert sample_databox_entry.suggested_filename == "Einkommensteuerbescheid 2024"

    def test_suggested_filename_fallback_when_filebez_empty(self) -> None:
        """Should generate filename from fields when filebez is empty."""
        entry = DataboxEntry(
            stnr="",
            name="",
            anbringen="E1",
            zrvon="",
            zrbis="",
            datbesch=date(2024, 1, 15),
            erltyp="B",
            fileart=FileType.PDF,
            ts_zust=datetime(2024, 1, 15, tzinfo=timezone.utc),
            applkey="abc123def456xyz",
            filebez="",  # Empty filebez
            status=ReadStatus.UNREAD,
        )
        expected = "2024-01-15_B_E1_abc123def456xyz.pdf"
        assert entry.suggested_filename == expected


class TestDataboxListResult:
    """Tests for DataboxListResult dataclass."""

    def test_create_success_result(self, sample_databox_entries: tuple[DataboxEntry, ...]) -> None:
        """Should create successful result with entries."""
        result = DataboxListResult(rc=0, msg=None, entries=sample_databox_entries)
        assert result.is_success is True
        assert result.entry_count == 2
        assert result.unread_count == 1

    def test_create_error_result(self) -> None:
        """Should create error result."""
        result = DataboxListResult(rc=-1, msg="Session invalid")
        assert result.is_success is False
        assert result.entry_count == 0

    def test_timestamp_default(self) -> None:
        """Should have timestamp set to approximately now."""
        before = datetime.now(timezone.utc)
        result = DataboxListResult(rc=0, msg=None)
        after = datetime.now(timezone.utc)
        assert before <= result.timestamp <= after


class TestDataboxDownloadRequest:
    """Tests for DataboxDownloadRequest dataclass."""

    def test_create_valid_request(self) -> None:
        """Should create request with valid applkey."""
        request = DataboxDownloadRequest(applkey="abc123def456xyz")
        assert request.applkey == "abc123def456xyz"

    def test_empty_applkey_raises(self) -> None:
        """Should raise ValueError for empty applkey."""
        with pytest.raises(ValueError, match="applkey.*required"):
            DataboxDownloadRequest(applkey="")

    def test_applkey_too_short_raises(self) -> None:
        """Should raise ValueError for applkey shorter than 10 chars."""
        with pytest.raises(ValueError, match="applkey must be 10-50 alphanumeric"):
            DataboxDownloadRequest(applkey="abc123456")

    def test_applkey_too_long_raises(self) -> None:
        """Should raise ValueError for applkey longer than 50 chars."""
        with pytest.raises(ValueError, match="applkey must be 10-50 alphanumeric"):
            # 51 characters - longer than max 50
            DataboxDownloadRequest(applkey="abc123def456ghi789jkl012345678901234567890123456789X")


class TestDataboxDownloadResult:
    """Tests for DataboxDownloadResult dataclass."""

    def test_create_success_result(self) -> None:
        """Should create successful result with content."""
        content = b"PDF content here"
        result = DataboxDownloadResult(rc=0, msg=None, content=content)
        assert result.is_success is True
        assert result.content == content
        assert result.content_size == len(content)

    def test_create_error_result(self) -> None:
        """Should create error result."""
        result = DataboxDownloadResult(rc=-1, msg="Document not found")
        assert result.is_success is False
        assert result.content is None
        assert result.content_size == 0

    def test_is_success_requires_content(self) -> None:
        """Should return False for rc=0 but no content."""
        result = DataboxDownloadResult(rc=0, msg=None, content=None)
        assert result.is_success is False

    def test_timestamp_default(self) -> None:
        """Should have timestamp set to approximately now."""
        before = datetime.now(timezone.utc)
        result = DataboxDownloadResult(rc=0, msg=None, content=b"test")
        after = datetime.now(timezone.utc)
        assert before <= result.timestamp <= after


class TestNotificationOptions:
    """Tests for NotificationOptions dataclass."""

    def test_create_default_options(self) -> None:
        """Should create options with default values."""
        opts = NotificationOptions()
        assert opts.enabled is True
        assert opts.recipients == ()

    def test_create_disabled_options(self) -> None:
        """Should create disabled notification options."""
        opts = NotificationOptions(enabled=False)
        assert opts.enabled is False

    def test_create_with_recipients(self) -> None:
        """Should create options with recipients."""
        opts = NotificationOptions(recipients=("user@example.com", "admin@example.com"))
        assert len(opts.recipients) == 2


class TestReadStatusFromString:
    """Tests for ReadStatus.from_string parsing."""

    def test_empty_string_returns_unread(self) -> None:
        """Empty string indicates unread document."""
        assert ReadStatus.from_string("") == ReadStatus.UNREAD

    def test_one_returns_read(self) -> None:
        """String '1' indicates read document."""
        assert ReadStatus.from_string("1") == ReadStatus.READ

    def test_unexpected_value_warns_and_defaults_to_unread(self) -> None:
        """Unexpected values emit a warning and default to UNREAD."""
        import warnings

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            result = ReadStatus.from_string("unexpected")

        assert result == ReadStatus.UNREAD
        assert len(caught) == 1
        assert "Unexpected ReadStatus value" in str(caught[0].message)
        assert "'unexpected'" in str(caught[0].message)


class TestFileTypeFromString:
    """Tests for FileType.from_string parsing."""

    def test_pdf_uppercase(self) -> None:
        """PDF in uppercase is recognized."""
        assert FileType.from_string("PDF") == FileType.PDF

    def test_pdf_lowercase(self) -> None:
        """PDF in lowercase is recognized."""
        assert FileType.from_string("pdf") == FileType.PDF

    def test_xml_uppercase(self) -> None:
        """XML in uppercase is recognized."""
        assert FileType.from_string("XML") == FileType.XML

    def test_xml_lowercase(self) -> None:
        """XML in lowercase is recognized."""
        assert FileType.from_string("xml") == FileType.XML

    def test_zip_uppercase(self) -> None:
        """ZIP in uppercase is recognized."""
        assert FileType.from_string("ZIP") == FileType.ZIP

    def test_zip_lowercase(self) -> None:
        """ZIP in lowercase is recognized."""
        assert FileType.from_string("zip") == FileType.ZIP

    def test_unknown_type_returns_other(self) -> None:
        """Unknown file types return OTHER."""
        assert FileType.from_string("DOC") == FileType.OTHER
        assert FileType.from_string("txt") == FileType.OTHER
        assert FileType.from_string("") == FileType.OTHER
