"""Domain exceptions for FinanzOnline DataBox operations.

Purpose
-------
Define a hierarchy of domain-specific exceptions that represent
business error conditions in the DataBox document retrieval process.

Contents
--------
* :class:`DataboxError` - Base exception for all DataBox errors
* :class:`ConfigurationError` - Missing or invalid configuration
* :class:`AuthenticationError` - Login/credentials failure
* :class:`SessionError` - Session management errors
* :class:`DataboxOperationError` - DataBox operation execution errors
* :class:`FilesystemError` - Filesystem operation failures
* :func:`filesystem_error_from_oserror` - Create FilesystemError from OSError

System Role
-----------
Domain layer - pure exception definitions with no I/O dependencies.
Application layer catches and handles these exceptions appropriately.

Examples
--------
>>> raise ConfigurationError("Missing tid credential")
Traceback (most recent call last):
    ...
finanzonline_databox.domain.errors.ConfigurationError: Missing tid credential

>>> from finanzonline_databox.domain.models import Diagnostics
>>> diag = Diagnostics(operation="list", return_code="-3")
>>> err = DataboxOperationError("Technical error", return_code=-3, retryable=True, diagnostics=diag)
>>> err.retryable
True
"""

from __future__ import annotations

import errno
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from finanzonline_databox.domain.models import Diagnostics
from finanzonline_databox.i18n import _

if TYPE_CHECKING:
    from finanzonline_databox.domain.return_codes import CliExitCode


@dataclass(frozen=True, slots=True)
class DataboxErrorInfo:
    """Consolidated error information for databox command error handling.

    Groups all error-related data that would otherwise be passed as
    separate parameters, reducing parameter list length and improving
    code clarity.

    Attributes:
        error_type: Type label for display (e.g., "Authentication Error").
        message: Human-readable error description.
        exit_code: CLI exit code to return.
        return_code: Optional FinanzOnline return code.
        retryable: Whether the error is temporary/retryable.
        diagnostics: Optional diagnostics for debugging.
    """

    error_type: str
    message: str
    exit_code: CliExitCode
    return_code: int | None = None
    retryable: bool = False
    diagnostics: Diagnostics | None = None


class DataboxError(Exception):
    """Base exception for all DataBox errors.

    All domain-specific exceptions inherit from this class to enable
    catching all DataBox errors with a single except clause.

    Attributes:
        message: Human-readable error description.
    """

    def __init__(self, message: str) -> None:
        """Initialize with error message.

        Args:
            message: Human-readable error description.
        """
        self.message = message
        super().__init__(message)


class ConfigurationError(DataboxError):
    """Configuration is missing or invalid.

    Raised when required configuration values are missing or when
    configuration validation fails.

    Examples:
        - Missing FinanzOnline credentials (tid, benid, pin)
        - Invalid download directory path
        - Missing email configuration when notifications enabled
    """


class AuthenticationError(DataboxError):
    """Authentication with FinanzOnline failed.

    Raised when login fails due to invalid credentials or when
    the account is not authorized for DataBox access.

    Attributes:
        message: Human-readable error description.
        return_code: FinanzOnline return code (if available).
        diagnostics: Diagnostics object with request/response details.
    """

    def __init__(
        self,
        message: str,
        *,
        return_code: int | None = None,
        diagnostics: Diagnostics | None = None,
    ) -> None:
        """Initialize with error details.

        Args:
            message: Human-readable error description.
            return_code: Optional FinanzOnline return code.
            diagnostics: Optional Diagnostics object with masked credentials.
        """
        super().__init__(message)
        self.return_code = return_code
        self.diagnostics = diagnostics or Diagnostics()


class SessionError(DataboxError):
    """Session management error.

    Raised when session operations fail, such as:
    - Session creation timeout
    - Session expired during operation
    - Logout failure

    Attributes:
        message: Human-readable error description.
        return_code: FinanzOnline return code (if available).
        diagnostics: Diagnostics object with request/response details.
    """

    def __init__(
        self,
        message: str,
        *,
        return_code: int | None = None,
        diagnostics: Diagnostics | None = None,
    ) -> None:
        """Initialize with error details.

        Args:
            message: Human-readable error description.
            return_code: Optional FinanzOnline return code.
            diagnostics: Optional Diagnostics object with masked credentials.
        """
        super().__init__(message)
        self.return_code = return_code
        self.diagnostics = diagnostics or Diagnostics()


class DataboxOperationError(DataboxError):
    """DataBox operation execution failed.

    Raised when a DataBox operation cannot be completed, such as:
    - Network/connectivity issues
    - Service unavailable (maintenance)
    - Invalid date range parameters
    - Document download failure

    Attributes:
        message: Human-readable error description.
        return_code: FinanzOnline return code (if available).
        retryable: Whether the operation may succeed if retried later.
        diagnostics: Diagnostics object with request/response details.
    """

    def __init__(
        self,
        message: str,
        *,
        return_code: int | None = None,
        retryable: bool = False,
        diagnostics: Diagnostics | None = None,
    ) -> None:
        """Initialize with error details.

        Args:
            message: Human-readable error description.
            return_code: Optional FinanzOnline return code.
            retryable: Whether retry may succeed.
            diagnostics: Optional Diagnostics object with masked credentials.
        """
        super().__init__(message)
        self.return_code = return_code
        self.retryable = retryable
        self.diagnostics = diagnostics or Diagnostics()


class FilesystemError(DataboxError):
    """Filesystem operation failed.

    Raised when file or directory operations fail, such as:
    - Permission denied when creating directories or writing files
    - Disk full when saving downloaded content
    - Read-only filesystem
    - Invalid path or path too long

    Attributes:
        message: Human-readable error description.
        path: Path that caused the error (if available).
        operation: Operation that failed (e.g., "create directory", "write file").
        original_error: The underlying OS error.
    """

    def __init__(
        self,
        message: str,
        *,
        path: Path | str | None = None,
        operation: str | None = None,
        original_error: OSError | None = None,
    ) -> None:
        """Initialize with error details.

        Args:
            message: Human-readable error description.
            path: Optional path that caused the error.
            operation: Optional operation name that failed.
            original_error: Optional underlying OSError.
        """
        super().__init__(message)
        self.path = Path(path) if isinstance(path, str) else path
        self.operation = operation
        self.original_error = original_error


def filesystem_error_from_oserror(
    exc: OSError,
    *,
    path: Path | str | None = None,
    operation: str = "write",
) -> FilesystemError:
    """Create a FilesystemError from an OSError with user-friendly message.

    Maps common errno values to localized, user-friendly error messages.

    Args:
        exc: The original OSError.
        path: Path that caused the error.
        operation: Operation that failed (e.g., "create directory", "write file").

    Returns:
        FilesystemError with user-friendly message.

    Examples:
        >>> import errno
        >>> exc = PermissionError(errno.EACCES, "Permission denied", "/tmp/test")
        >>> err = filesystem_error_from_oserror(exc, path="/tmp/test", operation="write file")
        >>> "Permission denied" in err.message
        True
    """
    path_str = str(path) if path else _("unknown")

    # Classify by errno for specific messages
    error_messages: dict[int, str] = {
        errno.EACCES: _("Permission denied: Cannot {operation} '{path}'"),
        errno.ENOSPC: _("Disk full: Cannot {operation} '{path}'"),
        errno.EROFS: _("Read-only filesystem: Cannot {operation} '{path}'"),
        errno.ENAMETOOLONG: _("Path too long: '{path}'"),
        errno.ENOENT: _("Directory does not exist: '{path}'"),
        errno.ENOTDIR: _("Not a directory: '{path}'"),
    }

    default_template = _("Filesystem error ({operation}): {error}")
    template = error_messages.get(exc.errno, default_template) if exc.errno is not None else default_template
    message = template.format(operation=operation, path=path_str, error=str(exc))

    return FilesystemError(
        message,
        path=path,
        operation=operation,
        original_error=exc,
    )
