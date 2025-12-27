"""Shared pytest fixtures for the entire test suite.

Centralizes test infrastructure following clean architecture principles:
- All shared fixtures live here
- Tests import fixtures implicitly via pytest's conftest discovery
- Fixtures use descriptive names that read as plain English

OS-Specific Markers:
    os_agnostic: Tests that run identically on all platforms
    posix_only: Tests requiring POSIX-compliant systems (Linux, macOS)
    windows_only: Tests requiring Windows
    macos_only: Tests requiring macOS

Coverage Configuration:
    When using coverage, always use JSON output to avoid SQL locks.
    Use `coverage json` instead of `coverage report` during parallel execution.
"""

from __future__ import annotations

import re
import sys
from collections.abc import Callable, Iterator
from dataclasses import fields
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import lib_cli_exit_tools
import pytest
from click.testing import CliRunner
from lib_layered_config import Config

# ============================================================================
# ANSI escape code handling
# ============================================================================

ANSI_ESCAPE_PATTERN = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")
CONFIG_FIELDS: tuple[str, ...] = tuple(field.name for field in fields(type(lib_cli_exit_tools.config)))


def _remove_ansi_codes(text: str) -> str:
    """Strip ANSI escape sequences from text.

    Tests compare human-readable CLI output; stripping colour codes keeps
    assertions stable across environments.
    """
    return ANSI_ESCAPE_PATTERN.sub("", text)


# ============================================================================
# pytest configuration
# ============================================================================


def pytest_configure(config: pytest.Config) -> None:
    """Register custom markers for OS-specific tests."""
    config.addinivalue_line("markers", "os_agnostic: tests that run on all platforms")
    config.addinivalue_line("markers", "posix_only: tests requiring POSIX systems (Linux, macOS)")
    config.addinivalue_line("markers", "windows_only: tests requiring Windows")
    config.addinivalue_line("markers", "macos_only: tests requiring macOS")


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Skip tests based on current platform."""
    is_windows = sys.platform == "win32"
    is_macos = sys.platform == "darwin"
    is_posix = sys.platform != "win32"

    skip_windows = pytest.mark.skip(reason="Windows-only test")
    skip_posix = pytest.mark.skip(reason="POSIX-only test")
    skip_macos = pytest.mark.skip(reason="macOS-only test")

    for item in items:
        if "windows_only" in item.keywords and not is_windows:
            item.add_marker(skip_windows)
        if "posix_only" in item.keywords and not is_posix:
            item.add_marker(skip_posix)
        if "macos_only" in item.keywords and not is_macos:
            item.add_marker(skip_macos)


# ============================================================================
# Internationalization setup
# ============================================================================


@pytest.fixture(scope="session", autouse=True)
def ensure_english_locale() -> None:
    """Set English locale at session start for consistent test output.

    Many tests expect English strings (e.g., 'SUCCESS', 'Timestamp:').
    This ensures the i18n system starts in English before any tests run.
    """
    from finanzonline_databox.i18n import setup_locale

    setup_locale("en")


# ============================================================================
# Environment setup
# ============================================================================


def _load_dotenv() -> None:
    """Load .env file when it exists for integration test configuration."""
    try:
        from dotenv import load_dotenv

        env_file = Path(__file__).parent.parent / ".env"
        if env_file.exists():
            load_dotenv(env_file)
    except ImportError:
        pass


@pytest.fixture(scope="session", autouse=True)
def load_dotenv_session() -> None:
    """Load .env file at session start for integration tests."""
    _load_dotenv()


# ============================================================================
# CLI testing fixtures
# ============================================================================


@pytest.fixture
def cli_runner() -> CliRunner:
    """Provide a Click test runner for CLI tests."""
    return CliRunner()


@pytest.fixture
def strip_ansi() -> Callable[[str], str]:
    """Return a helper that strips ANSI escape sequences from a string."""
    return _remove_ansi_codes


@pytest.fixture
def isolated_cli_runner(cli_runner: CliRunner, tmp_path: Path) -> Iterator[CliRunner]:
    """Provide an isolated runner in a temp directory.

    Yields:
        Click CliRunner within a temporary directory context.
    """
    with cli_runner.isolated_filesystem(temp_dir=tmp_path):
        yield cli_runner


@pytest.fixture(autouse=True)
def reset_traceback_state() -> Iterator[None]:
    """Reset lib_cli_exit_tools traceback state between tests."""
    original_traceback = getattr(lib_cli_exit_tools.config, "traceback", False)
    original_color = getattr(lib_cli_exit_tools.config, "traceback_force_color", False)
    yield
    lib_cli_exit_tools.config.traceback = original_traceback
    lib_cli_exit_tools.config.traceback_force_color = original_color


# ============================================================================
# Configuration fixtures
# ============================================================================


@pytest.fixture
def config_dict() -> dict[str, Any]:
    """Provide a basic configuration dictionary for tests."""
    return {
        "finanzonline": {
            "tid": "123456789",
            "benid": "TESTUSER",
            "pin": "secretpin",
            "herstellerid": "ATU12345678",
            "session_timeout": 30.0,
            "query_timeout": 60.0,
        }
    }


@pytest.fixture
def mock_config(config_dict: dict[str, Any]) -> Config:
    """Provide a mock Config object for tests."""
    mock = MagicMock(spec=Config)
    mock.as_dict.return_value = config_dict
    return mock


# ============================================================================
# Domain model fixtures - Credentials & Session
# ============================================================================


@pytest.fixture
def valid_credentials() -> Any:
    """Provide valid FinanzOnline credentials for tests."""
    from finanzonline_databox.domain.models import FinanzOnlineCredentials

    return FinanzOnlineCredentials(
        tid="123456789",
        benid="TESTUSER",
        pin="testpin123",
        herstellerid="ATU12345678",
    )


@pytest.fixture
def valid_session_info() -> Any:
    """Provide a valid session info for tests."""
    from finanzonline_databox.domain.models import SessionInfo

    return SessionInfo(
        session_id="TEST_SESSION_123",
        return_code=0,
        message="Login successful",
    )


# ============================================================================
# Domain model fixtures - DataBox
# ============================================================================


@pytest.fixture
def sample_databox_entry() -> Any:
    """Provide a sample DataBox entry for tests."""
    from finanzonline_databox.domain.models import DataboxEntry, FileType, ReadStatus

    return DataboxEntry(
        stnr="12-345/6789",
        name="Bescheid",
        anbringen="E1",
        zrvon="2024",
        zrbis="2024",
        datbesch=date(2024, 1, 15),
        erltyp="B",
        fileart=FileType.PDF,
        ts_zust=datetime(2024, 1, 15, 10, 30, tzinfo=timezone.utc),
        applkey="abc123def456xyz",
        filebez="Einkommensteuerbescheid 2024",
        status=ReadStatus.UNREAD,
    )


@pytest.fixture
def sample_databox_entries() -> Any:
    """Provide multiple sample DataBox entries for tests."""
    from finanzonline_databox.domain.models import DataboxEntry, FileType, ReadStatus

    return [
        DataboxEntry(
            stnr="12-345/6789",
            name="Bescheid",
            anbringen="E1",
            zrvon="2024",
            zrbis="2024",
            datbesch=date(2024, 1, 15),
            erltyp="B",
            fileart=FileType.PDF,
            ts_zust=datetime(2024, 1, 15, 10, 30, tzinfo=timezone.utc),
            applkey="abc123def456xyz",
            filebez="Einkommensteuerbescheid 2024",
            status=ReadStatus.UNREAD,
        ),
        DataboxEntry(
            stnr="12-345/6789",
            name="Mitteilung",
            anbringen="M1",
            zrvon="2024",
            zrbis="2024",
            datbesch=date(2024, 1, 20),
            erltyp="M",
            fileart=FileType.PDF,
            ts_zust=datetime(2024, 1, 20, 14, 0, tzinfo=timezone.utc),
            applkey="def456ghi789abc",
            filebez="Mitteilung zur Steuererklärung",
            status=ReadStatus.READ,
        ),
    ]


@pytest.fixture
def valid_list_result(sample_databox_entries: Any) -> Any:
    """Provide a successful DataBox list result for tests."""
    from finanzonline_databox.domain.models import DataboxListResult

    return DataboxListResult(
        rc=0,
        msg=None,
        entries=tuple(sample_databox_entries),
        timestamp=datetime(2024, 1, 25, 12, 0, 0, tzinfo=timezone.utc),
    )


@pytest.fixture
def empty_list_result() -> Any:
    """Provide an empty DataBox list result for tests."""
    from finanzonline_databox.domain.models import DataboxListResult

    return DataboxListResult(
        rc=0,
        msg=None,
        entries=(),
        timestamp=datetime(2024, 1, 25, 12, 0, 0, tzinfo=timezone.utc),
    )


@pytest.fixture
def error_list_result() -> Any:
    """Provide an error DataBox list result for tests."""
    from finanzonline_databox.domain.models import DataboxListResult

    return DataboxListResult(
        rc=-1,
        msg="Session invalid or expired",
        entries=(),
    )


@pytest.fixture
def valid_download_result() -> Any:
    """Provide a successful download result for tests."""
    from finanzonline_databox.domain.models import DataboxDownloadResult

    return DataboxDownloadResult(
        rc=0,
        msg=None,
        content=b"%PDF-1.4 test content",
        timestamp=datetime(2024, 1, 25, 12, 0, 0, tzinfo=timezone.utc),
    )


@pytest.fixture
def error_download_result() -> Any:
    """Provide an error download result for tests."""
    from finanzonline_databox.domain.models import DataboxDownloadResult

    return DataboxDownloadResult(
        rc=-3,
        msg="Technical error",
        content=None,
    )


@pytest.fixture
def valid_email_config() -> Any:
    """Provide a valid email configuration for tests."""
    from finanzonline_databox.mail import EmailConfig

    return EmailConfig(
        smtp_hosts=["smtp.test.com:587"],
        from_address="sender@test.com",
    )


# ============================================================================
# FinanzOnline configuration fixtures
# ============================================================================


@pytest.fixture
def finanzonline_config_dict() -> dict[str, Any]:
    """Provide a valid FinanzOnline configuration dictionary."""
    return {
        "finanzonline": {
            "tid": "123456789",
            "benid": "TESTUSER",
            "pin": "secretpin",
            "herstellerid": "ATU12345678",
            "session_timeout": 45.0,
            "query_timeout": 60.0,
            "default_recipients": ["test@example.com", "admin@example.com"],
        }
    }


@pytest.fixture
def minimal_finanzonline_config_dict() -> dict[str, Any]:
    """Provide minimal required FinanzOnline configuration."""
    return {
        "finanzonline": {
            "tid": "123456789",
            "benid": "TESTUSER",
            "pin": "secretpin",
            "herstellerid": "ATU12345678",
        }
    }


@pytest.fixture
def mock_fo_config(valid_credentials: Any) -> MagicMock:
    """Provide a mock FinanzOnline configuration object."""
    mock = MagicMock()
    mock.credentials = valid_credentials
    mock.session_timeout = 30.0
    mock.query_timeout = 30.0
    mock.default_recipients = []
    return mock


# ============================================================================
# SOAP client fixtures
# ============================================================================


@pytest.fixture
def mock_soap_login_response() -> MagicMock:
    """Provide a mock successful SOAP login response."""
    response = MagicMock()
    response.rc = 0
    response.msg = "Login successful"
    response.id = "SESSION123456"
    return response


@pytest.fixture
def mock_soap_list_response(sample_databox_entries: Any) -> MagicMock:
    """Provide a mock successful SOAP getDatabox response."""
    response = MagicMock()
    response.rc = 0
    response.msg = None

    # Create mock entry objects
    mock_entries: list[MagicMock] = []
    for entry in sample_databox_entries:
        mock_entry = MagicMock()
        mock_entry.stnr = entry.stnr
        mock_entry.name = entry.name
        mock_entry.anbringen = entry.anbringen
        mock_entry.zrvon = entry.zrvon
        mock_entry.zrbis = entry.zrbis
        mock_entry.datbesch = entry.datbesch
        mock_entry.erltyp = entry.erltyp
        mock_entry.fileart = entry.fileart
        mock_entry.ts_zust = entry.ts_zust
        mock_entry.applkey = entry.applkey
        mock_entry.filebez = entry.filebez
        mock_entry.status = entry.status
        mock_entries.append(mock_entry)

    response.result = mock_entries
    return response


@pytest.fixture
def mock_soap_download_response() -> MagicMock:
    """Provide a mock successful SOAP getDataboxEntry response."""
    import base64

    response = MagicMock()
    response.rc = 0
    response.msg = None
    response.result = base64.b64encode(b"%PDF-1.4 test content").decode("ascii")
    return response


# ============================================================================
# Email/SMTP fixtures
# ============================================================================


@pytest.fixture
def smtp_config_from_env() -> Any:
    """Load SMTP configuration from environment for integration tests.

    Returns None and marks skip if environment is not configured.
    """
    import os

    from finanzonline_databox.mail import EmailConfig

    smtp_server = os.getenv("TEST_SMTP_SERVER")
    email_address = os.getenv("TEST_EMAIL_ADDRESS")

    if not smtp_server or not email_address:
        pytest.skip("TEST_SMTP_SERVER or TEST_EMAIL_ADDRESS not configured in .env")

    return EmailConfig(
        smtp_hosts=[smtp_server],
        from_address=email_address,
        timeout=10.0,
    )


# ============================================================================
# Test data factories
# ============================================================================


@pytest.fixture
def make_databox_entry() -> Callable[..., Any]:
    """Factory for creating DataboxEntry with custom parameters."""
    from finanzonline_databox.domain.models import DataboxEntry, FileType, ReadStatus

    def _factory(
        stnr: str = "12-345/6789",
        name: str = "Test Document",
        anbringen: str = "E1",
        zrvon: str = "2024",
        zrbis: str = "2024",
        datbesch: date | None = None,
        erltyp: str = "B",
        fileart: FileType = FileType.PDF,
        ts_zust: datetime | None = None,
        applkey: str = "abc123def456xyz",
        filebez: str = "Test document description",
        status: ReadStatus = ReadStatus.UNREAD,
    ) -> DataboxEntry:
        return DataboxEntry(
            stnr=stnr,
            name=name,
            anbringen=anbringen,
            zrvon=zrvon,
            zrbis=zrbis,
            datbesch=datbesch or date(2024, 1, 15),
            erltyp=erltyp,
            fileart=fileart,
            ts_zust=ts_zust or datetime(2024, 1, 15, 10, 0, tzinfo=timezone.utc),
            applkey=applkey,
            filebez=filebez,
            status=status,
        )

    return _factory


@pytest.fixture
def make_list_result() -> Callable[..., Any]:
    """Factory for creating DataboxListResult with custom parameters."""
    from finanzonline_databox.domain.models import DataboxListResult

    def _factory(
        rc: int = 0,
        msg: str | None = None,
        entries: tuple[Any, ...] = (),
    ) -> DataboxListResult:
        return DataboxListResult(
            rc=rc,
            msg=msg,
            entries=entries,
            timestamp=datetime(2024, 1, 25, 12, 0, 0, tzinfo=timezone.utc),
        )

    return _factory


@pytest.fixture
def make_download_result() -> Callable[..., Any]:
    """Factory for creating DataboxDownloadResult with custom parameters."""
    from finanzonline_databox.domain.models import DataboxDownloadResult

    def _factory(
        rc: int = 0,
        msg: str | None = None,
        content: bytes | None = b"%PDF-1.4 test content",
    ) -> DataboxDownloadResult:
        return DataboxDownloadResult(
            rc=rc,
            msg=msg,
            content=content,
            timestamp=datetime(2024, 1, 25, 12, 0, 0, tzinfo=timezone.utc),
        )

    return _factory


# ============================================================================
# Fake adapters for behavioral testing (prefer over mocks)
# ============================================================================


@pytest.fixture
def fake_session_client() -> Any:
    """Provide an in-memory fake session client.

    Prefer this over MagicMock for testing use cases.
    """
    from tests.fakes import FakeSessionClient

    return FakeSessionClient()


@pytest.fixture
def fake_databox_client() -> Any:
    """Provide an in-memory fake databox client.

    Prefer this over MagicMock for testing use cases.
    """
    from tests.fakes import FakeDataboxClient

    return FakeDataboxClient()


@pytest.fixture
def successful_session() -> Any:
    """Provide a successful session info for fakes."""
    from finanzonline_databox.domain.models import SessionInfo

    return SessionInfo(
        session_id="FAKE_SESSION_SUCCESS",
        return_code=0,
        message="OK",
    )


@pytest.fixture
def failed_session() -> Any:
    """Provide a failed session info for fakes."""
    from finanzonline_databox.domain.models import SessionInfo

    return SessionInfo(
        session_id="",
        return_code=-1,
        message="Login failed",
    )
