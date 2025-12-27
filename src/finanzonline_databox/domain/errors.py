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

from dataclasses import dataclass
from typing import TYPE_CHECKING

from finanzonline_databox.domain.models import Diagnostics

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
