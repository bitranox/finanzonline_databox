"""Tests for domain exceptions.

Tests cover exception hierarchy, attributes, and message handling.
"""

from __future__ import annotations

import pytest

import errno
from pathlib import Path

from finanzonline_databox.domain.errors import (
    AuthenticationError,
    ConfigurationError,
    DataboxError,
    DataboxOperationError,
    FilesystemError,
    SessionError,
    filesystem_error_from_oserror,
)

pytestmark = pytest.mark.os_agnostic


class TestDataboxError:
    """Tests for base DataboxError."""

    def test_message_attribute(self) -> None:
        """Should store message as attribute."""
        err = DataboxError("Test error")
        assert err.message == "Test error"

    def test_str_representation(self) -> None:
        """Should use message in string representation."""
        err = DataboxError("Test error")
        assert str(err) == "Test error"

    def test_is_base_exception(self) -> None:
        """Should inherit from Exception."""
        err = DataboxError("Test")
        assert isinstance(err, Exception)


class TestConfigurationError:
    """Tests for ConfigurationError."""

    def test_inherits_from_base(self) -> None:
        """Should inherit from DataboxError."""
        err = ConfigurationError("Missing config")
        assert isinstance(err, DataboxError)

    def test_can_be_raised(self) -> None:
        """Should be raisable with message."""
        with pytest.raises(ConfigurationError, match="Missing tid"):
            raise ConfigurationError("Missing tid")


class TestAuthenticationError:
    """Tests for AuthenticationError."""

    def test_inherits_from_base(self) -> None:
        """Should inherit from DataboxError."""
        err = AuthenticationError("Login failed")
        assert isinstance(err, DataboxError)

    def test_return_code_optional(self) -> None:
        """Should default return_code to None."""
        err = AuthenticationError("Login failed")
        assert err.return_code is None

    def test_return_code_explicit(self) -> None:
        """Should accept explicit return_code."""
        err = AuthenticationError("Not authorized", return_code=-4)
        assert err.return_code == -4


class TestSessionError:
    """Tests for SessionError."""

    def test_inherits_from_base(self) -> None:
        """Should inherit from DataboxError."""
        err = SessionError("Session expired")
        assert isinstance(err, DataboxError)

    def test_return_code_optional(self) -> None:
        """Should default return_code to None."""
        err = SessionError("Timeout")
        assert err.return_code is None

    def test_return_code_explicit(self) -> None:
        """Should accept explicit return_code."""
        err = SessionError("Invalid session", return_code=-1)
        assert err.return_code == -1


class TestDataboxOperationError:
    """Tests for DataboxOperationError."""

    def test_inherits_from_base(self) -> None:
        """Should inherit from DataboxError."""
        err = DataboxOperationError("Operation failed")
        assert isinstance(err, DataboxError)

    def test_return_code_optional(self) -> None:
        """Should default return_code to None."""
        err = DataboxOperationError("Network error")
        assert err.return_code is None

    def test_retryable_default(self) -> None:
        """Should default retryable to False."""
        err = DataboxOperationError("Error")
        assert err.retryable is False

    def test_retryable_explicit(self) -> None:
        """Should accept explicit retryable."""
        err = DataboxOperationError("Rate limit", return_code=-2, retryable=True)
        assert err.retryable is True
        assert err.return_code == -2


class TestFilesystemError:
    """Tests for FilesystemError."""

    def test_inherits_from_base(self) -> None:
        """Should inherit from DataboxError."""
        err = FilesystemError("Permission denied")
        assert isinstance(err, DataboxError)

    def test_path_as_string(self) -> None:
        """Should convert string path to Path object."""
        err = FilesystemError("Error", path="/tmp/test")
        assert err.path == Path("/tmp/test")

    def test_path_as_path(self) -> None:
        """Should accept Path object directly."""
        p = Path("/tmp/test")
        err = FilesystemError("Error", path=p)
        assert err.path == p

    def test_path_optional(self) -> None:
        """Should default path to None."""
        err = FilesystemError("Error")
        assert err.path is None

    def test_operation_attribute(self) -> None:
        """Should store operation."""
        err = FilesystemError("Error", operation="create directory")
        assert err.operation == "create directory"

    def test_original_error_attribute(self) -> None:
        """Should store original OS error."""
        original = PermissionError(errno.EACCES, "Permission denied")
        err = FilesystemError("Error", original_error=original)
        assert err.original_error is original

    def test_can_be_raised(self) -> None:
        """Should be raisable with message."""
        with pytest.raises(FilesystemError, match="Permission denied"):
            raise FilesystemError("Permission denied")


class TestFilesystemErrorFromOSError:
    """Tests for filesystem_error_from_oserror helper."""

    def test_permission_denied(self) -> None:
        """Should create user-friendly message for EACCES."""
        original = PermissionError(errno.EACCES, "Permission denied", "/tmp/test")
        err = filesystem_error_from_oserror(original, path="/tmp/test", operation="write file")
        assert "Permission denied" in err.message
        assert "write file" in err.message
        assert "/tmp/test" in err.message

    def test_disk_full(self) -> None:
        """Should create user-friendly message for ENOSPC."""
        original = OSError(errno.ENOSPC, "No space left on device")
        err = filesystem_error_from_oserror(original, path="/tmp/test", operation="write file")
        assert "Disk full" in err.message

    def test_read_only_filesystem(self) -> None:
        """Should create user-friendly message for EROFS."""
        original = OSError(errno.EROFS, "Read-only file system")
        err = filesystem_error_from_oserror(original, path="/mnt/cdrom/test", operation="write file")
        assert "Read-only filesystem" in err.message

    def test_path_too_long(self) -> None:
        """Should create user-friendly message for ENAMETOOLONG."""
        original = OSError(errno.ENAMETOOLONG, "File name too long")
        err = filesystem_error_from_oserror(original, path="/tmp/" + "x" * 300, operation="write file")
        assert "Path too long" in err.message

    def test_directory_not_exist(self) -> None:
        """Should create user-friendly message for ENOENT."""
        original = FileNotFoundError(errno.ENOENT, "No such file or directory")
        err = filesystem_error_from_oserror(original, path="/nonexistent/dir", operation="create directory")
        assert "does not exist" in err.message

    def test_not_a_directory(self) -> None:
        """Should create user-friendly message for ENOTDIR."""
        original = OSError(errno.ENOTDIR, "Not a directory")
        err = filesystem_error_from_oserror(original, path="/tmp/file.txt/subdir", operation="create directory")
        assert "Not a directory" in err.message

    def test_generic_error(self) -> None:
        """Should create generic message for unknown errno."""
        original = OSError(999, "Unknown error")
        err = filesystem_error_from_oserror(original, path="/tmp/test", operation="write file")
        assert "Filesystem error" in err.message

    def test_preserves_original_error(self) -> None:
        """Should store the original OSError."""
        original = PermissionError(errno.EACCES, "Permission denied")
        err = filesystem_error_from_oserror(original, path="/tmp/test")
        assert err.original_error is original

    def test_preserves_path(self) -> None:
        """Should store the path."""
        original = PermissionError(errno.EACCES, "Permission denied")
        err = filesystem_error_from_oserror(original, path=Path("/tmp/test"))
        assert err.path == Path("/tmp/test")

    def test_preserves_operation(self) -> None:
        """Should store the operation."""
        original = PermissionError(errno.EACCES, "Permission denied")
        err = filesystem_error_from_oserror(original, path="/tmp/test", operation="create directory")
        assert err.operation == "create directory"


class TestExceptionHierarchy:
    """Tests for exception hierarchy behavior."""

    def test_catch_all_with_base_class(self) -> None:
        """Should catch all specific errors with DataboxError."""
        errors = [
            ConfigurationError("config"),
            AuthenticationError("auth"),
            SessionError("session"),
            DataboxOperationError("operation"),
            FilesystemError("filesystem"),
        ]
        for err in errors:
            try:
                raise err
            except DataboxError as caught:
                assert caught.message in ["config", "auth", "session", "operation", "filesystem"]

    def test_specific_catch_first(self) -> None:
        """Should allow catching specific exceptions first."""
        try:
            raise DataboxOperationError("rate limit", return_code=-2, retryable=True)
        except DataboxOperationError as err:
            assert err.retryable is True
        except DataboxError:
            pytest.fail("Should have caught DataboxOperationError specifically")
