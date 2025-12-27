"""Domain layer for finanzonline_databox.

Purpose
-------
Contains pure domain models, value objects, and business rules with no external
dependencies. This layer represents the core business logic for DataBox document
retrieval from FinanzOnline.

Contents
--------
* :mod:`.models` - Immutable dataclasses for domain entities
* :mod:`.errors` - Domain-specific exception hierarchy
* :mod:`.return_codes` - FinanzOnline return code definitions

System Role
-----------
Innermost layer in clean architecture - has no dependencies on application,
adapters, or infrastructure layers. All other layers depend on domain.
"""

from __future__ import annotations

from .errors import (
    AuthenticationError,
    ConfigurationError,
    DataboxError,
    DataboxErrorInfo,
    DataboxOperationError,
    SessionError,
)
from .models import (
    DataboxDownloadRequest,
    DataboxDownloadResult,
    DataboxEntry,
    DataboxListRequest,
    DataboxListResult,
    Diagnostics,
    FinanzOnlineCredentials,
    NotificationOptions,
    SessionInfo,
)
from .return_codes import (
    CliExitCode,
    ReturnCode,
    ReturnCodeInfo,
    Severity,
    get_return_code_info,
    is_retryable,
    is_success,
)

__all__ = [
    # Models
    "DataboxDownloadRequest",
    "DataboxDownloadResult",
    "DataboxEntry",
    "DataboxListRequest",
    "DataboxListResult",
    "Diagnostics",
    "FinanzOnlineCredentials",
    "NotificationOptions",
    "SessionInfo",
    # Errors
    "AuthenticationError",
    "ConfigurationError",
    "DataboxError",
    "DataboxErrorInfo",
    "DataboxOperationError",
    "SessionError",
    # Return codes
    "CliExitCode",
    "ReturnCode",
    "ReturnCodeInfo",
    "Severity",
    "get_return_code_info",
    "is_retryable",
    "is_success",
]
