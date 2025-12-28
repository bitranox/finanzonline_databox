# pyright: reportPrivateUsage=false
"""DataBox client adapter: every SOAP interaction a single verse.

Tests verify list/download operations with the FinanzOnline DataBox webservice.
SOAP calls are mocked because the real service requires live credentials and
network access - these are external dependencies we cannot control in tests.
"""

from __future__ import annotations

import base64
from datetime import date, datetime, timezone
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from zeep.exceptions import Fault, TransportError

from finanzonline_databox.adapters.finanzonline.databox_client import (
    DATABOX_SERVICE_WSDL,
    DataboxClient,
    _build_download_diagnostics,
    _build_list_diagnostics,
    _decode_content,
    _extract_response_message,
    _get_str_attr,
    _parse_databox_entry,
    _parse_date,
    _parse_datetime,
)
from finanzonline_databox.domain.errors import DataboxOperationError, SessionError
from finanzonline_databox.domain.models import (
    DataboxDownloadRequest,
    DataboxListRequest,
    FileType,
    ReadStatus,
)

pytestmark = pytest.mark.os_agnostic


# =============================================================================
# Client Initialization
# =============================================================================


class TestClientInitialization:
    """The databox client initializes with sensible defaults."""

    def test_default_timeout_is_thirty_seconds(self) -> None:
        """A fresh client uses 30 seconds as the default timeout."""
        client = DataboxClient()
        assert client._timeout == 30.0

    def test_custom_timeout_is_accepted(self) -> None:
        """Custom timeout values are stored correctly."""
        client = DataboxClient(timeout=60.0)
        assert client._timeout == 60.0

    def test_zeep_client_starts_as_none(self) -> None:
        """The underlying zeep client is lazily initialized."""
        client = DataboxClient()
        assert client._client is None


# =============================================================================
# Lazy Client Creation
# =============================================================================


class TestLazyClientCreation:
    """The zeep client is created on first use and reused thereafter."""

    def test_first_call_creates_zeep_client_with_transport(self) -> None:
        """Calling _get_client creates the zeep Client with configured Transport."""
        client = DataboxClient(timeout=45.0)
        with (
            patch("finanzonline_databox.adapters.finanzonline.databox_client.Transport") as mock_transport,
            patch("finanzonline_databox.adapters.finanzonline.databox_client.Client") as mock_client,
        ):
            mock_transport_instance = MagicMock()
            mock_transport.return_value = mock_transport_instance
            mock_client_instance = MagicMock()
            mock_client.return_value = mock_client_instance

            result = client._get_client()

            mock_transport.assert_called_once_with(timeout=45.0)
            mock_client.assert_called_once_with(DATABOX_SERVICE_WSDL, transport=mock_transport_instance)
            assert result is mock_client_instance

    def test_subsequent_calls_reuse_existing_client(self) -> None:
        """Multiple calls return the same client instance."""
        client = DataboxClient()
        with (
            patch("finanzonline_databox.adapters.finanzonline.databox_client.Transport"),
            patch("finanzonline_databox.adapters.finanzonline.databox_client.Client") as mock_class,
        ):
            mock_instance = MagicMock()
            mock_class.return_value = mock_instance

            first = client._get_client()
            second = client._get_client()

            mock_class.assert_called_once()
            assert first is second


# =============================================================================
# Helper Functions
# =============================================================================


class TestParseDate:
    """Tests for _parse_date helper."""

    def test_date_object_passes_through(self) -> None:
        """Date objects are returned as-is."""
        d = date(2024, 1, 15)
        assert _parse_date(d) == d

    def test_datetime_extracts_date(self) -> None:
        """Datetime objects have date extracted."""
        dt = datetime(2024, 1, 15, 10, 30)
        assert _parse_date(dt) == date(2024, 1, 15)

    def test_string_is_parsed(self) -> None:
        """String dates are parsed."""
        assert _parse_date("2024-01-15") == date(2024, 1, 15)


class TestParseDatetime:
    """Tests for _parse_datetime helper."""

    def test_aware_datetime_passes_through(self) -> None:
        """Aware datetimes are returned as-is."""
        dt = datetime(2024, 1, 15, 10, 30, tzinfo=timezone.utc)
        assert _parse_datetime(dt) == dt

    def test_naive_datetime_gets_local_timezone(self) -> None:
        """Naive datetimes get local timezone."""
        dt = datetime(2024, 1, 15, 10, 30)
        result = _parse_datetime(dt)
        assert result.tzinfo is not None

    def test_iso_string_is_parsed(self) -> None:
        """ISO format strings are parsed."""
        result = _parse_datetime("2024-01-15T10:30:00")
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15


class TestGetStrAttr:
    """Tests for _get_str_attr helper."""

    def test_returns_attribute_value(self) -> None:
        """Returns string value of attribute."""
        obj = MagicMock()
        obj.name = "Test"
        assert _get_str_attr(obj, "name") == "Test"

    def test_returns_empty_for_missing(self) -> None:
        """Returns empty string for missing attribute."""
        obj = MagicMock(spec=[])
        assert _get_str_attr(obj, "name") == ""

    def test_returns_empty_for_none(self) -> None:
        """Returns empty string for None value."""
        obj = MagicMock()
        obj.name = None
        assert _get_str_attr(obj, "name") == ""


class TestExtractResponseMessage:
    """Tests for _extract_response_message helper."""

    def test_returns_message_value(self) -> None:
        """Returns message from response."""
        response = MagicMock()
        response.msg = "Success"
        assert _extract_response_message(response) == "Success"

    def test_returns_none_for_missing_attr(self) -> None:
        """Returns None when msg attribute missing."""
        response = MagicMock(spec=[])
        assert _extract_response_message(response) is None

    def test_returns_empty_string_for_none_value(self) -> None:
        """Returns empty string when msg is None."""
        response = MagicMock()
        response.msg = None
        assert _extract_response_message(response) == ""


class TestDecodeContent:
    """Tests for _decode_content helper."""

    def test_decodes_base64_content(self, valid_credentials: Any) -> None:
        """Base64 content is decoded."""
        response = MagicMock()
        response.result = base64.b64encode(b"PDF content").decode("ascii")
        result = _decode_content(response, "key123def456", "SESSION123", valid_credentials)
        assert result == b"PDF content"

    def test_returns_none_for_empty_result(self, valid_credentials: Any) -> None:
        """Returns None when result is empty."""
        response = MagicMock()
        response.result = ""
        assert _decode_content(response, "key123def456", "SESSION123", valid_credentials) is None

    def test_returns_none_for_missing_result(self, valid_credentials: Any) -> None:
        """Returns None when result attribute is missing."""
        response = MagicMock(spec=["rc", "msg"])
        assert _decode_content(response, "key123def456", "SESSION123", valid_credentials) is None

    def test_invalid_base64_raises_operation_error(self, valid_credentials: Any) -> None:
        """Invalid base64 content raises DataboxOperationError."""
        response = MagicMock()
        response.result = "!!!not-valid-base64!!!"
        response.rc = 0
        response.msg = None

        with pytest.raises(DataboxOperationError) as exc_info:
            _decode_content(response, "key123def456", "SESSION123", valid_credentials)

        assert "invalid base64" in str(exc_info.value).lower()
        assert exc_info.value.diagnostics is not None


class TestParseDataboxEntry:
    """Tests for _parse_databox_entry helper."""

    def test_parses_complete_entry(self) -> None:
        """Complete SOAP entry is parsed to DataboxEntry."""
        mock_entry = MagicMock()
        mock_entry.stnr = "12-345/6789"
        mock_entry.name = "Bescheid"
        mock_entry.anbringen = "E1"
        mock_entry.zrvon = "2024"
        mock_entry.zrbis = "2024"
        mock_entry.datbesch = date(2024, 1, 15)
        mock_entry.erltyp = "B"
        mock_entry.fileart = "PDF"
        mock_entry.ts_zust = datetime(2024, 1, 15, 10, 30, tzinfo=timezone.utc)
        mock_entry.applkey = "abc123def456xyz"
        mock_entry.filebez = "Document description"
        mock_entry.status = "1"

        result = _parse_databox_entry(mock_entry)

        assert result.stnr == "12-345/6789"
        assert result.erltyp == "B"
        assert result.fileart == FileType.PDF
        assert result.status == ReadStatus.READ


class TestBuildListDiagnostics:
    """Tests for _build_list_diagnostics helper."""

    def test_creates_diagnostics_from_request(self, valid_credentials: Any) -> None:
        """Creates diagnostics with masked values."""
        request = DataboxListRequest(erltyp="B")
        diag = _build_list_diagnostics("SESSION123456", valid_credentials, request)

        assert diag.operation == "getDatabox"
        assert diag.erltyp == "B"
        assert "..." in diag.session_id  # Masked

    def test_includes_response_info(self, valid_credentials: Any) -> None:
        """Includes response info when provided."""
        request = DataboxListRequest()
        response = MagicMock()
        response.rc = 0
        response.msg = "Success"

        diag = _build_list_diagnostics("SESSION123", valid_credentials, request, response=response)

        assert diag.return_code == "0"
        assert diag.response_message == "Success"


class TestBuildDownloadDiagnostics:
    """Tests for _build_download_diagnostics helper."""

    def test_creates_diagnostics_from_request(self, valid_credentials: Any) -> None:
        """Creates diagnostics with masked values."""
        request = DataboxDownloadRequest(applkey="abc123def456")
        diag = _build_download_diagnostics("SESSION123456", valid_credentials, request)

        assert diag.operation == "getDataboxEntry"
        assert diag.applkey == "abc123def456"


# =============================================================================
# List Entries
# =============================================================================


class TestListEntriesSuccess:
    """Tests for successful list operations."""

    def test_returns_entries_on_success(
        self,
        valid_credentials: Any,
        mock_soap_list_response: MagicMock,
    ) -> None:
        """Successful list returns entries."""
        client = DataboxClient()
        request = DataboxListRequest()

        with patch.object(client, "_get_client") as mock_get:
            mock_zeep = MagicMock()
            mock_zeep.service.getDatabox.return_value = mock_soap_list_response
            mock_get.return_value = mock_zeep

            result = client.list_entries("SESSION123", valid_credentials, request)

            assert result.is_success
            assert result.entry_count > 0

    def test_passes_credentials_to_soap_service(
        self,
        valid_credentials: Any,
        mock_soap_list_response: MagicMock,
    ) -> None:
        """Credentials are forwarded to the SOAP call."""
        client = DataboxClient()
        request = DataboxListRequest(erltyp="B")

        with patch.object(client, "_get_client") as mock_get:
            mock_zeep = MagicMock()
            mock_zeep.service.getDatabox.return_value = mock_soap_list_response
            mock_get.return_value = mock_zeep

            client.list_entries("SESSION123", valid_credentials, request)

            mock_zeep.service.getDatabox.assert_called_once()
            call_kwargs = mock_zeep.service.getDatabox.call_args.kwargs
            assert call_kwargs["tid"] == valid_credentials.tid
            assert call_kwargs["erltyp"] == "B"


class TestListEntriesFailure:
    """Tests for list operation failures."""

    def test_session_invalid_raises_session_error(self, valid_credentials: Any) -> None:
        """Session invalid code raises SessionError."""
        client = DataboxClient()
        request = DataboxListRequest()
        response = MagicMock()
        response.rc = -1
        response.msg = "Session invalid"

        with patch.object(client, "_get_client") as mock_get:
            mock_zeep = MagicMock()
            mock_zeep.service.getDatabox.return_value = response
            mock_get.return_value = mock_zeep

            with pytest.raises(SessionError) as exc_info:
                client.list_entries("SESSION123", valid_credentials, request)

            assert exc_info.value.return_code == -1

    def test_soap_fault_raises_operation_error(self, valid_credentials: Any) -> None:
        """SOAP faults are wrapped in DataboxOperationError."""
        client = DataboxClient()
        request = DataboxListRequest()

        with patch.object(client, "_get_client") as mock_get:
            mock_zeep = MagicMock()
            mock_zeep.service.getDatabox.side_effect = Fault("SOAP error")
            mock_get.return_value = mock_zeep

            with pytest.raises(DataboxOperationError) as exc_info:
                client.list_entries("SESSION123", valid_credentials, request)

            assert "SOAP fault" in str(exc_info.value)

    def test_transport_error_raises_retryable_error(self, valid_credentials: Any) -> None:
        """Transport errors are marked as retryable."""
        client = DataboxClient()
        request = DataboxListRequest()

        with patch.object(client, "_get_client") as mock_get:
            mock_zeep = MagicMock()
            mock_zeep.service.getDatabox.side_effect = TransportError("Connection failed")
            mock_get.return_value = mock_zeep

            with pytest.raises(DataboxOperationError) as exc_info:
                client.list_entries("SESSION123", valid_credentials, request)

            assert exc_info.value.retryable is True


# =============================================================================
# Download Entry
# =============================================================================


class TestDownloadEntrySuccess:
    """Tests for successful download operations."""

    def test_returns_content_on_success(
        self,
        valid_credentials: Any,
        mock_soap_download_response: MagicMock,
    ) -> None:
        """Successful download returns content."""
        client = DataboxClient()
        request = DataboxDownloadRequest(applkey="abc123def456")

        with patch.object(client, "_get_client") as mock_get:
            mock_zeep = MagicMock()
            mock_zeep.service.getDataboxEntry.return_value = mock_soap_download_response
            mock_get.return_value = mock_zeep

            result = client.download_entry("SESSION123", valid_credentials, request)

            assert result.is_success
            assert result.content is not None

    def test_passes_applkey_to_soap_service(
        self,
        valid_credentials: Any,
        mock_soap_download_response: MagicMock,
    ) -> None:
        """Applkey is forwarded to the SOAP call."""
        client = DataboxClient()
        request = DataboxDownloadRequest(applkey="abc123def456")

        with patch.object(client, "_get_client") as mock_get:
            mock_zeep = MagicMock()
            mock_zeep.service.getDataboxEntry.return_value = mock_soap_download_response
            mock_get.return_value = mock_zeep

            client.download_entry("SESSION123", valid_credentials, request)

            mock_zeep.service.getDataboxEntry.assert_called_once()
            call_kwargs = mock_zeep.service.getDataboxEntry.call_args.kwargs
            assert call_kwargs["applkey"] == "abc123def456"


class TestDownloadEntryFailure:
    """Tests for download operation failures."""

    def test_session_invalid_raises_session_error(self, valid_credentials: Any) -> None:
        """Session invalid code raises SessionError."""
        client = DataboxClient()
        request = DataboxDownloadRequest(applkey="abc123def456")
        response = MagicMock()
        response.rc = -1
        response.msg = "Session invalid"

        with patch.object(client, "_get_client") as mock_get:
            mock_zeep = MagicMock()
            mock_zeep.service.getDataboxEntry.return_value = response
            mock_get.return_value = mock_zeep

            with pytest.raises(SessionError) as exc_info:
                client.download_entry("SESSION123", valid_credentials, request)

            assert exc_info.value.return_code == -1

    def test_soap_fault_raises_operation_error(self, valid_credentials: Any) -> None:
        """SOAP faults are wrapped in DataboxOperationError."""
        client = DataboxClient()
        request = DataboxDownloadRequest(applkey="abc123def456")

        with patch.object(client, "_get_client") as mock_get:
            mock_zeep = MagicMock()
            mock_zeep.service.getDataboxEntry.side_effect = Fault("SOAP error")
            mock_get.return_value = mock_zeep

            with pytest.raises(DataboxOperationError) as exc_info:
                client.download_entry("SESSION123", valid_credentials, request)

            assert "SOAP fault" in str(exc_info.value)

    def test_transport_error_raises_retryable_error(self, valid_credentials: Any) -> None:
        """Transport errors are marked as retryable."""
        client = DataboxClient()
        request = DataboxDownloadRequest(applkey="abc123def456")

        with patch.object(client, "_get_client") as mock_get:
            mock_zeep = MagicMock()
            mock_zeep.service.getDataboxEntry.side_effect = TransportError("Connection failed")
            mock_get.return_value = mock_zeep

            with pytest.raises(DataboxOperationError) as exc_info:
                client.download_entry("SESSION123", valid_credentials, request)

            assert exc_info.value.retryable is True
