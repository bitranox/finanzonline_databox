"""Behavioral tests for application use cases.

Tests use real fake adapters instead of mocks to verify actual behavior.
Each test reads like plain English and checks exactly one behavior.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

from finanzonline_databox.application.use_cases import (
    DownloadEntryUseCase,
    ListDataboxUseCase,
    SyncDataboxUseCase,
    SyncResult,
    _get_unique_path,  # pyright: ignore[reportPrivateUsage]
)
import errno

from finanzonline_databox.domain.errors import FilesystemError, SessionError
from finanzonline_databox.domain.models import (
    DataboxDownloadResult,
    DataboxListRequest,
    DataboxListResult,
    SessionInfo,
)

if TYPE_CHECKING:
    from tests.fakes import FakeDataboxClient, FakeSessionClient


# =============================================================================
# _get_unique_path Tests
# =============================================================================


@pytest.mark.os_agnostic
class TestGetUniquePath:
    """Tests for _get_unique_path helper function."""

    def test_returns_original_when_file_does_not_exist(self, tmp_path: Path) -> None:
        """Should return original path when file doesn't exist."""
        path = tmp_path / "document.xml"
        result = _get_unique_path(path)
        assert result == path

    def test_adds_suffix_2_when_file_exists(self, tmp_path: Path) -> None:
        """Should add _2 suffix when original file exists."""
        path = tmp_path / "document.xml"
        path.touch()  # Create the file

        result = _get_unique_path(path)
        assert result == tmp_path / "document_2.xml"

    def test_increments_suffix_until_unique(self, tmp_path: Path) -> None:
        """Should increment suffix until finding unique name."""
        # Create document.xml, document_2.xml, document_3.xml
        (tmp_path / "document.xml").touch()
        (tmp_path / "document_2.xml").touch()
        (tmp_path / "document_3.xml").touch()

        path = tmp_path / "document.xml"
        result = _get_unique_path(path)
        assert result == tmp_path / "document_4.xml"

    def test_preserves_file_extension(self, tmp_path: Path) -> None:
        """Should preserve file extension in unique name."""
        path = tmp_path / "report.pdf"
        path.touch()

        result = _get_unique_path(path)
        assert result.suffix == ".pdf"
        assert result.stem == "report_2"

    def test_raises_after_max_attempts_exceeded(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Should raise RuntimeError when max attempts exceeded."""
        from finanzonline_databox.application import use_cases

        # Set a small limit for testing
        monkeypatch.setattr(use_cases, "_MAX_UNIQUE_PATH_ATTEMPTS", 3)

        # Create files to exhaust all unique names
        (tmp_path / "doc.xml").touch()
        (tmp_path / "doc_2.xml").touch()
        (tmp_path / "doc_3.xml").touch()
        (tmp_path / "doc_4.xml").touch()

        with pytest.raises(RuntimeError, match="Could not find unique path after 3 attempts"):
            _get_unique_path(tmp_path / "doc.xml")


# =============================================================================
# SyncResult Tests
# =============================================================================


@pytest.mark.os_agnostic
class TestSyncResultSuccess:
    """Tests for SyncResult.is_success property."""

    def test_success_when_zero_failures(self) -> None:
        """A sync with zero failures is successful."""
        result = SyncResult(
            total_listed=10,
            unread_listed=5,
            downloaded=8,
            skipped=2,
            failed=0,
            total_bytes=1024,
        )

        assert result.is_success is True

    def test_failure_when_any_download_failed(self) -> None:
        """A sync with any failed downloads is not successful."""
        result = SyncResult(
            total_listed=10,
            unread_listed=5,
            downloaded=7,
            skipped=2,
            failed=1,
            total_bytes=1024,
        )

        assert result.is_success is False


@pytest.mark.os_agnostic
class TestSyncResultHasNewDownloads:
    """Tests for SyncResult.has_new_downloads property."""

    def test_has_downloads_when_downloaded_positive(self) -> None:
        """A sync with downloaded files has new downloads."""
        result = SyncResult(
            total_listed=5,
            unread_listed=3,
            downloaded=3,
            skipped=2,
            failed=0,
            total_bytes=100,
        )

        assert result.has_new_downloads is True

    def test_no_downloads_when_all_skipped(self) -> None:
        """A sync with zero downloaded files has no new downloads."""
        result = SyncResult(
            total_listed=5,
            unread_listed=0,
            downloaded=0,
            skipped=5,
            failed=0,
            total_bytes=0,
        )

        assert result.has_new_downloads is False


# =============================================================================
# ListDataboxUseCase Tests
# =============================================================================


@pytest.mark.os_agnostic
class TestListDataboxUseCaseSuccess:
    """Tests for successful list operations."""

    def test_returns_entries_on_successful_login(
        self,
        fake_session_client: FakeSessionClient,
        fake_databox_client: FakeDataboxClient,
        valid_credentials: Any,
        sample_databox_entry: Any,
        successful_session: SessionInfo,
    ) -> None:
        """List use case returns entries when login succeeds."""
        fake_session_client.login_response = successful_session
        fake_databox_client.list_response = DataboxListResult(
            rc=0,
            msg="OK",
            entries=(sample_databox_entry,),
        )

        use_case = ListDataboxUseCase(fake_session_client, fake_databox_client)
        result = use_case.execute(valid_credentials)

        assert result.is_success
        assert result.entry_count == 1

    def test_calls_logout_after_list(
        self,
        fake_session_client: FakeSessionClient,
        fake_databox_client: FakeDataboxClient,
        valid_credentials: Any,
        successful_session: SessionInfo,
    ) -> None:
        """List use case always calls logout after listing."""
        fake_session_client.login_response = successful_session
        fake_databox_client.list_response = DataboxListResult(rc=0, msg="OK", entries=())

        use_case = ListDataboxUseCase(fake_session_client, fake_databox_client)
        use_case.execute(valid_credentials)

        assert fake_session_client.logout_called


@pytest.mark.os_agnostic
class TestListDataboxUseCaseLoginFailure:
    """Tests for list operations when login fails."""

    def test_raises_session_error_on_login_failure(
        self,
        fake_session_client: FakeSessionClient,
        fake_databox_client: FakeDataboxClient,
        valid_credentials: Any,
        failed_session: SessionInfo,
    ) -> None:
        """List use case raises SessionError when login fails."""
        fake_session_client.login_response = failed_session

        use_case = ListDataboxUseCase(fake_session_client, fake_databox_client)

        with pytest.raises(SessionError, match="Login failed"):
            use_case.execute(valid_credentials)

    def test_does_not_list_entries_when_login_fails(
        self,
        fake_session_client: FakeSessionClient,
        fake_databox_client: FakeDataboxClient,
        valid_credentials: Any,
        failed_session: SessionInfo,
    ) -> None:
        """List use case does not call list when login fails."""
        fake_session_client.login_response = failed_session

        use_case = ListDataboxUseCase(fake_session_client, fake_databox_client)

        with pytest.raises(SessionError):
            use_case.execute(valid_credentials)

        assert not fake_databox_client.list_called


@pytest.mark.os_agnostic
class TestListDataboxUseCaseLogoutBehavior:
    """Tests for logout behavior in list operations."""

    def test_logs_out_even_when_list_raises_exception(
        self,
        fake_session_client: FakeSessionClient,
        fake_databox_client: FakeDataboxClient,
        valid_credentials: Any,
        successful_session: SessionInfo,
    ) -> None:
        """Logout is called even when list raises an exception."""
        fake_session_client.login_response = successful_session
        fake_databox_client.list_error = RuntimeError("API error")

        use_case = ListDataboxUseCase(fake_session_client, fake_databox_client)

        with pytest.raises(RuntimeError):
            use_case.execute(valid_credentials)

        assert fake_session_client.logout_called

    def test_logout_failure_does_not_raise(
        self,
        fake_session_client: FakeSessionClient,
        fake_databox_client: FakeDataboxClient,
        valid_credentials: Any,
        successful_session: SessionInfo,
    ) -> None:
        """Logout failure is suppressed and does not raise."""
        fake_session_client.login_response = successful_session
        fake_session_client.logout_error = RuntimeError("Logout failed")
        fake_databox_client.list_response = DataboxListResult(rc=0, msg="OK", entries=())

        use_case = ListDataboxUseCase(fake_session_client, fake_databox_client)
        result = use_case.execute(valid_credentials)

        assert result.is_success


@pytest.mark.os_agnostic
class TestListDataboxUseCaseRequestFiltering:
    """Tests for request filtering in list operations."""

    def test_uses_default_request_when_none_provided(
        self,
        fake_session_client: FakeSessionClient,
        fake_databox_client: FakeDataboxClient,
        valid_credentials: Any,
        successful_session: SessionInfo,
    ) -> None:
        """Uses empty erltyp filter when no request provided."""
        fake_session_client.login_response = successful_session
        fake_databox_client.list_response = DataboxListResult(rc=0, msg="OK", entries=())

        use_case = ListDataboxUseCase(fake_session_client, fake_databox_client)
        use_case.execute(valid_credentials, request=None)

        _, _, request = fake_databox_client.list_calls[0]
        assert request.erltyp == ""

    def test_passes_custom_request_filter(
        self,
        fake_session_client: FakeSessionClient,
        fake_databox_client: FakeDataboxClient,
        valid_credentials: Any,
        successful_session: SessionInfo,
    ) -> None:
        """Custom request filter is passed to databox client."""
        fake_session_client.login_response = successful_session
        fake_databox_client.list_response = DataboxListResult(rc=0, msg="OK", entries=())

        use_case = ListDataboxUseCase(fake_session_client, fake_databox_client)
        use_case.execute(valid_credentials, request=DataboxListRequest(erltyp="B"))

        _, _, request = fake_databox_client.list_calls[0]
        assert request.erltyp == "B"


# =============================================================================
# DownloadEntryUseCase Tests
# =============================================================================


@pytest.mark.os_agnostic
class TestDownloadEntryUseCaseSuccess:
    """Tests for successful download operations."""

    def test_returns_content_on_successful_login(
        self,
        fake_session_client: FakeSessionClient,
        fake_databox_client: FakeDataboxClient,
        valid_credentials: Any,
        successful_session: SessionInfo,
    ) -> None:
        """Download use case returns content when login succeeds."""
        fake_session_client.login_response = successful_session
        fake_databox_client.download_responses = [DataboxDownloadResult(rc=0, msg="OK", content=b"PDF content")]

        use_case = DownloadEntryUseCase(fake_session_client, fake_databox_client)
        result, _ = use_case.execute(valid_credentials, "abc123def456")

        assert result.is_success
        assert result.content == b"PDF content"

    def test_calls_logout_after_download(
        self,
        fake_session_client: FakeSessionClient,
        fake_databox_client: FakeDataboxClient,
        valid_credentials: Any,
        successful_session: SessionInfo,
    ) -> None:
        """Download use case always calls logout."""
        fake_session_client.login_response = successful_session
        fake_databox_client.download_responses = [DataboxDownloadResult(rc=0, msg="OK", content=b"content")]

        use_case = DownloadEntryUseCase(fake_session_client, fake_databox_client)
        use_case.execute(valid_credentials, "abc123def456")

        assert fake_session_client.logout_called


@pytest.mark.os_agnostic
class TestDownloadEntryUseCaseLoginFailure:
    """Tests for download operations when login fails."""

    def test_raises_session_error_on_login_failure(
        self,
        fake_session_client: FakeSessionClient,
        fake_databox_client: FakeDataboxClient,
        valid_credentials: Any,
        failed_session: SessionInfo,
    ) -> None:
        """Download use case raises SessionError when login fails."""
        fake_session_client.login_response = failed_session

        use_case = DownloadEntryUseCase(fake_session_client, fake_databox_client)

        with pytest.raises(SessionError):
            use_case.execute(valid_credentials, "abc123def456")

    def test_does_not_download_when_login_fails(
        self,
        fake_session_client: FakeSessionClient,
        fake_databox_client: FakeDataboxClient,
        valid_credentials: Any,
        failed_session: SessionInfo,
    ) -> None:
        """Download use case does not call download when login fails."""
        fake_session_client.login_response = failed_session

        use_case = DownloadEntryUseCase(fake_session_client, fake_databox_client)

        with pytest.raises(SessionError):
            use_case.execute(valid_credentials, "abc123def456")

        assert not fake_databox_client.download_called


@pytest.mark.os_agnostic
class TestDownloadEntryUseCaseFileSaving:
    """Tests for file saving behavior in download operations."""

    def test_saves_to_file_when_path_provided(
        self,
        fake_session_client: FakeSessionClient,
        fake_databox_client: FakeDataboxClient,
        valid_credentials: Any,
        successful_session: SessionInfo,
        tmp_path: Path,
    ) -> None:
        """Download saves content to file when output path provided."""
        fake_session_client.login_response = successful_session
        fake_databox_client.download_responses = [DataboxDownloadResult(rc=0, msg="OK", content=b"PDF content here")]

        output_file = tmp_path / "document.pdf"
        use_case = DownloadEntryUseCase(fake_session_client, fake_databox_client)
        use_case.execute(valid_credentials, "abc123def456", output_path=output_file)

        assert output_file.exists()
        assert output_file.read_bytes() == b"PDF content here"

    def test_does_not_save_when_download_fails(
        self,
        fake_session_client: FakeSessionClient,
        fake_databox_client: FakeDataboxClient,
        valid_credentials: Any,
        successful_session: SessionInfo,
        tmp_path: Path,
    ) -> None:
        """Download does not save file when download fails."""
        fake_session_client.login_response = successful_session
        fake_databox_client.download_responses = [DataboxDownloadResult(rc=-1, msg="Error", content=None)]

        output_file = tmp_path / "document.pdf"
        use_case = DownloadEntryUseCase(fake_session_client, fake_databox_client)
        use_case.execute(valid_credentials, "abc123def456", output_path=output_file)

        assert not output_file.exists()


@pytest.mark.os_agnostic
class TestDownloadEntryUseCaseLogoutBehavior:
    """Tests for logout behavior in download operations."""

    def test_logs_out_even_when_download_raises_exception(
        self,
        fake_session_client: FakeSessionClient,
        fake_databox_client: FakeDataboxClient,
        valid_credentials: Any,
        successful_session: SessionInfo,
    ) -> None:
        """Logout is called even when download raises an exception."""
        fake_session_client.login_response = successful_session
        fake_databox_client.download_error = RuntimeError("API error")

        use_case = DownloadEntryUseCase(fake_session_client, fake_databox_client)

        with pytest.raises(RuntimeError):
            use_case.execute(valid_credentials, "abc123def456")

        assert fake_session_client.logout_called


# =============================================================================
# SyncDataboxUseCase Tests
# =============================================================================


@pytest.mark.os_agnostic
class TestSyncDataboxUseCaseSuccess:
    """Tests for successful sync operations."""

    def test_syncs_entries_to_directory(
        self,
        fake_session_client: FakeSessionClient,
        fake_databox_client: FakeDataboxClient,
        valid_credentials: Any,
        successful_session: SessionInfo,
        make_databox_entry: Any,
        tmp_path: Path,
    ) -> None:
        """Sync downloads all entries to output directory."""
        fake_session_client.login_response = successful_session
        fake_databox_client.list_response = DataboxListResult(
            rc=0,
            msg="OK",
            entries=(
                make_databox_entry(applkey="key1xxxxxxxxx", filebez="document1.pdf"),
                make_databox_entry(applkey="key2xxxxxxxxx", filebez="document2.pdf"),
            ),
        )
        fake_databox_client.download_responses = [
            DataboxDownloadResult(rc=0, msg="OK", content=b"content1"),
            DataboxDownloadResult(rc=0, msg="OK", content=b"content2"),
        ]

        use_case = SyncDataboxUseCase(fake_session_client, fake_databox_client)
        result = use_case.execute(valid_credentials, tmp_path)

        assert result.total_listed == 2
        assert result.downloaded == 2
        assert result.failed == 0


@pytest.mark.os_agnostic
class TestSyncDataboxUseCaseSkipping:
    """Tests for skipping existing files."""

    def test_skips_existing_files(
        self,
        fake_session_client: FakeSessionClient,
        fake_databox_client: FakeDataboxClient,
        valid_credentials: Any,
        successful_session: SessionInfo,
        make_databox_entry: Any,
        tmp_path: Path,
    ) -> None:
        """Sync skips files that already exist."""
        entry = make_databox_entry(applkey="key1xxxxxxxxx")
        existing_file = tmp_path / entry.suggested_filename
        existing_file.write_bytes(b"existing content")

        fake_session_client.login_response = successful_session
        fake_databox_client.list_response = DataboxListResult(
            rc=0,
            msg="OK",
            entries=(entry,),
        )

        use_case = SyncDataboxUseCase(fake_session_client, fake_databox_client)
        result = use_case.execute(valid_credentials, tmp_path, skip_existing=True)

        assert result.skipped == 1
        assert result.downloaded == 0
        assert not fake_databox_client.download_called


@pytest.mark.os_agnostic
class TestSyncDataboxUseCaseFailure:
    """Tests for sync failure scenarios."""

    def test_returns_empty_result_on_list_failure(
        self,
        fake_session_client: FakeSessionClient,
        fake_databox_client: FakeDataboxClient,
        valid_credentials: Any,
        successful_session: SessionInfo,
        tmp_path: Path,
    ) -> None:
        """Sync returns empty result when listing fails."""
        fake_session_client.login_response = successful_session
        fake_databox_client.list_response = DataboxListResult(
            rc=-1,
            msg="Error",
            entries=(),
        )

        use_case = SyncDataboxUseCase(fake_session_client, fake_databox_client)
        result = use_case.execute(valid_credentials, tmp_path)

        assert result.total_listed == 0
        assert result.downloaded == 0

    def test_counts_failed_downloads(
        self,
        fake_session_client: FakeSessionClient,
        fake_databox_client: FakeDataboxClient,
        valid_credentials: Any,
        successful_session: SessionInfo,
        make_databox_entry: Any,
        tmp_path: Path,
    ) -> None:
        """Sync counts failed downloads."""
        fake_session_client.login_response = successful_session
        fake_databox_client.list_response = DataboxListResult(
            rc=0,
            msg="OK",
            entries=(make_databox_entry(applkey="key1xxxxxxxxx"),),
        )
        fake_databox_client.download_responses = [DataboxDownloadResult(rc=-1, msg="Download failed", content=None)]

        use_case = SyncDataboxUseCase(fake_session_client, fake_databox_client)
        result = use_case.execute(valid_credentials, tmp_path)

        assert result.failed == 1
        assert result.downloaded == 0
        assert result.is_success is False

    def test_handles_download_exception(
        self,
        fake_session_client: FakeSessionClient,
        fake_databox_client: FakeDataboxClient,
        valid_credentials: Any,
        successful_session: SessionInfo,
        make_databox_entry: Any,
        tmp_path: Path,
    ) -> None:
        """Sync catches download exceptions as failures."""
        fake_session_client.login_response = successful_session
        fake_databox_client.list_response = DataboxListResult(
            rc=0,
            msg="OK",
            entries=(make_databox_entry(applkey="key1xxxxxxxxx"),),
        )
        fake_databox_client.download_error = RuntimeError("Connection error")

        use_case = SyncDataboxUseCase(fake_session_client, fake_databox_client)
        result = use_case.execute(valid_credentials, tmp_path)

        assert result.failed == 1
        assert result.is_success is False


@pytest.mark.os_agnostic
class TestSyncDataboxUseCaseDirectoryCreation:
    """Tests for output directory creation."""

    def test_creates_output_directory_if_missing(
        self,
        fake_session_client: FakeSessionClient,
        fake_databox_client: FakeDataboxClient,
        valid_credentials: Any,
        successful_session: SessionInfo,
        tmp_path: Path,
    ) -> None:
        """Sync creates the output directory if it does not exist."""
        fake_session_client.login_response = successful_session
        fake_databox_client.list_response = DataboxListResult(rc=0, msg="OK", entries=())

        output_dir = tmp_path / "new" / "nested" / "dir"
        assert not output_dir.exists()

        use_case = SyncDataboxUseCase(fake_session_client, fake_databox_client)
        use_case.execute(valid_credentials, output_dir)

        assert output_dir.exists()


@pytest.mark.os_agnostic
class TestSyncDataboxUseCaseLogoutBehavior:
    """Tests for logout behavior in sync operations."""

    def test_logs_out_even_when_list_raises_exception(
        self,
        fake_session_client: FakeSessionClient,
        fake_databox_client: FakeDataboxClient,
        valid_credentials: Any,
        successful_session: SessionInfo,
        tmp_path: Path,
    ) -> None:
        """Logout is called even when listing raises an exception."""
        fake_session_client.login_response = successful_session
        fake_databox_client.list_error = RuntimeError("API error")

        use_case = SyncDataboxUseCase(fake_session_client, fake_databox_client)

        with pytest.raises(RuntimeError):
            use_case.execute(valid_credentials, tmp_path)

        assert fake_session_client.logout_called


@pytest.mark.os_agnostic
class TestSyncDataboxUseCaseBytesCalculation:
    """Tests for total bytes calculation."""

    def test_calculates_total_bytes_from_downloaded_content(
        self,
        fake_session_client: FakeSessionClient,
        fake_databox_client: FakeDataboxClient,
        valid_credentials: Any,
        successful_session: SessionInfo,
        make_databox_entry: Any,
        tmp_path: Path,
    ) -> None:
        """Sync calculates total bytes as sum of downloaded content sizes."""
        fake_session_client.login_response = successful_session
        fake_databox_client.list_response = DataboxListResult(
            rc=0,
            msg="OK",
            entries=(
                make_databox_entry(applkey="key1xxxxxxxxx", filebez="doc1.pdf"),
                make_databox_entry(applkey="key2xxxxxxxxx", filebez="doc2.pdf"),
            ),
        )
        fake_databox_client.download_responses = [
            DataboxDownloadResult(rc=0, msg="OK", content=b"A" * 100),
            DataboxDownloadResult(rc=0, msg="OK", content=b"B" * 200),
        ]

        use_case = SyncDataboxUseCase(fake_session_client, fake_databox_client)
        result = use_case.execute(valid_credentials, tmp_path)

        assert result.total_bytes == 300


@pytest.mark.os_agnostic
class TestSyncDataboxUseCaseAnbringenFilter:
    """Tests for anbringen (reference) filtering."""

    def test_filters_entries_by_anbringen(
        self,
        fake_session_client: FakeSessionClient,
        fake_databox_client: FakeDataboxClient,
        valid_credentials: Any,
        successful_session: SessionInfo,
        make_databox_entry: Any,
        tmp_path: Path,
    ) -> None:
        """Sync only downloads entries matching the anbringen filter."""
        fake_session_client.login_response = successful_session
        fake_databox_client.list_response = DataboxListResult(
            rc=0,
            msg="OK",
            entries=(
                make_databox_entry(applkey="key1xxxxxxxxx", anbringen="UID", filebez="uid1.xml"),
                make_databox_entry(applkey="key2xxxxxxxxx", anbringen="E1", filebez="e1.pdf"),
                make_databox_entry(applkey="key3xxxxxxxxx", anbringen="UID", filebez="uid2.xml"),
            ),
        )
        fake_databox_client.download_responses = [
            DataboxDownloadResult(rc=0, msg="OK", content=b"content1"),
            DataboxDownloadResult(rc=0, msg="OK", content=b"content2"),
        ]

        use_case = SyncDataboxUseCase(fake_session_client, fake_databox_client)
        result = use_case.execute(valid_credentials, tmp_path, anbringen_filter="UID")

        # total_listed reflects filtered entries (2 with anbringen="UID")
        assert result.total_listed == 2
        assert result.downloaded == 2
        assert result.skipped == 0
        assert result.failed == 0

    def test_downloads_all_when_no_filter(
        self,
        fake_session_client: FakeSessionClient,
        fake_databox_client: FakeDataboxClient,
        valid_credentials: Any,
        successful_session: SessionInfo,
        make_databox_entry: Any,
        tmp_path: Path,
    ) -> None:
        """Sync downloads all entries when no anbringen filter is set."""
        fake_session_client.login_response = successful_session
        fake_databox_client.list_response = DataboxListResult(
            rc=0,
            msg="OK",
            entries=(
                make_databox_entry(applkey="key1xxxxxxxxx", anbringen="UID", filebez="uid.xml"),
                make_databox_entry(applkey="key2xxxxxxxxx", anbringen="E1", filebez="e1.pdf"),
            ),
        )
        fake_databox_client.download_responses = [
            DataboxDownloadResult(rc=0, msg="OK", content=b"content1"),
            DataboxDownloadResult(rc=0, msg="OK", content=b"content2"),
        ]

        use_case = SyncDataboxUseCase(fake_session_client, fake_databox_client)
        result = use_case.execute(valid_credentials, tmp_path, anbringen_filter="")

        assert result.downloaded == 2

    def test_downloads_zero_when_filter_matches_none(
        self,
        fake_session_client: FakeSessionClient,
        fake_databox_client: FakeDataboxClient,
        valid_credentials: Any,
        successful_session: SessionInfo,
        make_databox_entry: Any,
        tmp_path: Path,
    ) -> None:
        """Sync downloads zero entries when filter matches nothing."""
        fake_session_client.login_response = successful_session
        fake_databox_client.list_response = DataboxListResult(
            rc=0,
            msg="OK",
            entries=(
                make_databox_entry(applkey="key1xxxxxxxxx", anbringen="UID"),
                make_databox_entry(applkey="key2xxxxxxxxx", anbringen="E1"),
            ),
        )

        use_case = SyncDataboxUseCase(fake_session_client, fake_databox_client)
        result = use_case.execute(valid_credentials, tmp_path, anbringen_filter="NONEXISTENT")

        assert result.downloaded == 0
        assert result.skipped == 0
        assert not fake_databox_client.download_called


# =============================================================================
# Filesystem Error Handling Tests
# =============================================================================


@pytest.mark.os_agnostic
class TestDownloadEntryUseCaseFilesystemError:
    """Tests for filesystem error handling in download operations."""

    def test_raises_filesystem_error_on_mkdir_failure(
        self,
        fake_session_client: FakeSessionClient,
        fake_databox_client: FakeDataboxClient,
        valid_credentials: Any,
        successful_session: SessionInfo,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Download raises FilesystemError when directory creation fails."""
        fake_session_client.login_response = successful_session
        fake_databox_client.download_responses = [DataboxDownloadResult(rc=0, msg="OK", content=b"test content")]

        # Mock mkdir to raise PermissionError
        def mock_mkdir(self: Path, **kwargs: Any) -> None:
            raise PermissionError(errno.EACCES, "Permission denied", str(self))

        monkeypatch.setattr(Path, "mkdir", mock_mkdir)

        use_case = DownloadEntryUseCase(fake_session_client, fake_databox_client)
        output_file = tmp_path / "subdir" / "test.pdf"

        with pytest.raises(FilesystemError, match="Permission denied"):
            use_case.execute(valid_credentials, "abc123def456", output_path=output_file)

    def test_raises_filesystem_error_on_write_failure(
        self,
        fake_session_client: FakeSessionClient,
        fake_databox_client: FakeDataboxClient,
        valid_credentials: Any,
        successful_session: SessionInfo,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Download raises FilesystemError when file write fails."""
        fake_session_client.login_response = successful_session
        fake_databox_client.download_responses = [DataboxDownloadResult(rc=0, msg="OK", content=b"test content")]

        # Mock write_bytes to raise disk full error
        def mock_write_bytes(self: Path, data: bytes) -> int:
            raise OSError(errno.ENOSPC, "No space left on device", str(self))

        monkeypatch.setattr(Path, "write_bytes", mock_write_bytes)

        use_case = DownloadEntryUseCase(fake_session_client, fake_databox_client)
        output_file = tmp_path / "test.pdf"

        with pytest.raises(FilesystemError, match="Disk full"):
            use_case.execute(valid_credentials, "abc123def456", output_path=output_file)

    def test_logs_out_even_when_filesystem_error_occurs(
        self,
        fake_session_client: FakeSessionClient,
        fake_databox_client: FakeDataboxClient,
        valid_credentials: Any,
        successful_session: SessionInfo,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Logout is called even when FilesystemError occurs."""
        fake_session_client.login_response = successful_session
        fake_databox_client.download_responses = [DataboxDownloadResult(rc=0, msg="OK", content=b"test content")]

        def mock_write_bytes(self: Path, data: bytes) -> int:
            raise OSError(errno.ENOSPC, "No space left on device", str(self))

        monkeypatch.setattr(Path, "write_bytes", mock_write_bytes)

        use_case = DownloadEntryUseCase(fake_session_client, fake_databox_client)

        with pytest.raises(FilesystemError):
            use_case.execute(valid_credentials, "abc123def456", output_path=tmp_path / "test.pdf")

        assert fake_session_client.logout_called


@pytest.mark.os_agnostic
class TestSyncDataboxUseCaseFilesystemError:
    """Tests for filesystem error handling in sync operations."""

    def test_raises_filesystem_error_on_output_dir_creation_failure(
        self,
        fake_session_client: FakeSessionClient,
        fake_databox_client: FakeDataboxClient,
        valid_credentials: Any,
        successful_session: SessionInfo,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Sync raises FilesystemError when output directory cannot be created."""
        fake_session_client.login_response = successful_session

        def mock_mkdir(self: Path, **kwargs: Any) -> None:
            raise PermissionError(errno.EACCES, "Permission denied", str(self))

        monkeypatch.setattr(Path, "mkdir", mock_mkdir)

        use_case = SyncDataboxUseCase(fake_session_client, fake_databox_client)

        with pytest.raises(FilesystemError, match="Permission denied"):
            use_case.execute(valid_credentials, Path("/readonly/dir"))

    def test_counts_file_write_failure_as_failed(
        self,
        fake_session_client: FakeSessionClient,
        fake_databox_client: FakeDataboxClient,
        valid_credentials: Any,
        successful_session: SessionInfo,
        make_databox_entry: Any,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Sync counts file write failures in failed count and continues."""
        fake_session_client.login_response = successful_session
        fake_databox_client.list_response = DataboxListResult(
            rc=0,
            msg="OK",
            entries=(make_databox_entry(applkey="key1xxxxxxxxx", filebez="doc1.pdf"),),
        )
        fake_databox_client.download_responses = [DataboxDownloadResult(rc=0, msg="OK", content=b"test content")]

        # Make write fail for files
        write_call_count = 0

        def mock_write_bytes(self: Path, data: bytes) -> int:
            nonlocal write_call_count
            write_call_count += 1
            raise OSError(errno.ENOSPC, "No space left on device")

        monkeypatch.setattr(Path, "write_bytes", mock_write_bytes)

        use_case = SyncDataboxUseCase(fake_session_client, fake_databox_client)
        result = use_case.execute(valid_credentials, tmp_path)

        # Write was attempted
        assert write_call_count == 1
        # Failure was counted
        assert result.failed == 1
        assert result.downloaded == 0
        assert result.is_success is False

    def test_continues_after_individual_file_failure(
        self,
        fake_session_client: FakeSessionClient,
        fake_databox_client: FakeDataboxClient,
        valid_credentials: Any,
        successful_session: SessionInfo,
        make_databox_entry: Any,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Sync continues processing remaining entries after a file write failure."""
        fake_session_client.login_response = successful_session
        fake_databox_client.list_response = DataboxListResult(
            rc=0,
            msg="OK",
            entries=(
                make_databox_entry(applkey="key1xxxxxxxxx", filebez="doc1.pdf"),
                make_databox_entry(applkey="key2xxxxxxxxx", filebez="doc2.pdf"),
            ),
        )
        fake_databox_client.download_responses = [
            DataboxDownloadResult(rc=0, msg="OK", content=b"content1"),
            DataboxDownloadResult(rc=0, msg="OK", content=b"content2"),
        ]

        # First write fails, second succeeds
        write_attempts: list[str] = []
        original_write_bytes = Path.write_bytes

        def mock_write_bytes(self: Path, data: bytes) -> int:
            write_attempts.append(self.name)
            if len(write_attempts) == 1:
                raise OSError(errno.ENOSPC, "No space left on device")
            return original_write_bytes(self, data)

        monkeypatch.setattr(Path, "write_bytes", mock_write_bytes)

        use_case = SyncDataboxUseCase(fake_session_client, fake_databox_client)
        result = use_case.execute(valid_credentials, tmp_path)

        # Both files were attempted
        assert len(write_attempts) == 2
        # One failed, one succeeded
        assert result.failed == 1
        assert result.downloaded == 1
        assert result.is_success is False

    def test_logs_out_even_when_output_dir_creation_fails(
        self,
        fake_session_client: FakeSessionClient,
        fake_databox_client: FakeDataboxClient,
        valid_credentials: Any,
        successful_session: SessionInfo,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Logout is NOT called when output dir creation fails (before login)."""
        fake_session_client.login_response = successful_session

        def mock_mkdir(self: Path, **kwargs: Any) -> None:
            raise PermissionError(errno.EACCES, "Permission denied", str(self))

        monkeypatch.setattr(Path, "mkdir", mock_mkdir)

        use_case = SyncDataboxUseCase(fake_session_client, fake_databox_client)

        with pytest.raises(FilesystemError):
            use_case.execute(valid_credentials, Path("/readonly/dir"))

        # mkdir happens before login, so logout should not be called
        assert not fake_session_client.logout_called
