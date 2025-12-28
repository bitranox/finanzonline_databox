"""FinanzOnline DataBox return code definitions.

Purpose
-------
Define return codes from BMF FinanzOnline DataBox Download webservice with
severity classification and human-readable descriptions.

Contents
--------
* :class:`Severity` - Error severity levels
* :class:`ReturnCode` - Enumeration of known return codes
* :class:`ReturnCodeInfo` - Metadata for a return code
* :func:`get_return_code_info` - Lookup return code information

System Role
-----------
Domain layer - pure data definitions based on BMF documentation.
Used by application layer to interpret query results.

Reference
---------
BMF DataBox-Download Webservice documentation (BMF_DataBox_Download_Webservice_2.pdf)

Examples
--------
>>> info = get_return_code_info(0)
>>> info.meaning  # doctest: +SKIP
'Operation successful'
>>> info.severity
<Severity.SUCCESS: 'success'>

>>> info = get_return_code_info(-2)
>>> info.retryable
True
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, IntEnum

from finanzonline_databox.i18n import N_, _


class CliExitCode(IntEnum):
    """CLI exit codes for databox commands.

    Standard exit codes used by the CLI to indicate result status.
    These are distinct from FinanzOnline return codes.
    """

    SUCCESS = 0
    NO_ENTRIES = 1
    CONFIG_ERROR = 2
    AUTH_ERROR = 3
    DOWNLOAD_ERROR = 4
    IO_ERROR = 5


class Severity(Enum):
    """Severity levels for return codes.

    Used to classify the nature of each return code for
    appropriate handling and user notification.
    """

    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ReturnCode(IntEnum):
    """Known FinanzOnline DataBox return codes.

    Values correspond to the 'rc' field in DataBox responses.
    """

    # Success
    OK = 0

    # Session/Auth errors (negative codes)
    SESSION_INVALID = -1
    SYSTEM_MAINTENANCE = -2
    TECHNICAL_ERROR = -3

    # DataBox-specific errors
    DATE_PARAMS_REQUIRED = -4
    DATE_TOO_OLD = -5
    DATE_RANGE_TOO_WIDE = -6


@dataclass(frozen=True, slots=True)
class ReturnCodeInfo:
    """Metadata for a FinanzOnline return code.

    Attributes:
        code: Numeric return code.
        meaning: Human-readable description.
        severity: Error severity level.
        retryable: Whether the operation may succeed if retried later.
    """

    code: int
    meaning: str
    severity: Severity
    retryable: bool = False


# Return code mappings from BMF documentation
# Strings are marked with N_() for extraction and translated at runtime in get_return_code_info()
_RETURN_CODE_INFO: dict[int, ReturnCodeInfo] = {
    # Success
    0: ReturnCodeInfo(code=0, meaning=N_("Operation successful"), severity=Severity.SUCCESS),
    # Session/Auth errors
    -1: ReturnCodeInfo(code=-1, meaning=N_("Session invalid or expired"), severity=Severity.ERROR),
    -2: ReturnCodeInfo(code=-2, meaning=N_("System maintenance"), severity=Severity.WARNING, retryable=True),
    -3: ReturnCodeInfo(code=-3, meaning=N_("Technical error"), severity=Severity.ERROR, retryable=True),
    # DataBox-specific parameter errors
    -4: ReturnCodeInfo(
        code=-4,
        meaning=N_("ts_zust_von and ts_zust_bis must both be specified"),
        severity=Severity.ERROR,
    ),
    -5: ReturnCodeInfo(
        code=-5,
        meaning=N_("ts_zust_von must not be more than 31 days in the past"),
        severity=Severity.ERROR,
    ),
    -6: ReturnCodeInfo(
        code=-6,
        meaning=N_("ts_zust_bis must not be more than 7 days after ts_zust_von"),
        severity=Severity.ERROR,
    ),
}


# Validate dict keys match ReturnCodeInfo.code values at module load time
# This prevents silent bugs if keys and codes are accidentally mismatched
def _validate_return_code_dict() -> None:
    """Validate that dict keys match ReturnCodeInfo.code values."""
    for key, info in _RETURN_CODE_INFO.items():
        if key != info.code:
            raise ValueError(f"Return code dict key {key} does not match ReturnCodeInfo.code {info.code}")


_validate_return_code_dict()


def get_return_code_info(code: int) -> ReturnCodeInfo:
    """Get information about a return code.

    Args:
        code: Numeric return code from FinanzOnline response.

    Returns:
        ReturnCodeInfo with meaning, severity, and retryable flag.
        The meaning is translated to the current language.
        Returns a generic error info for unknown codes.

    Examples:
        >>> info = get_return_code_info(0)
        >>> info.meaning  # doctest: +SKIP
        'Operation successful'
        >>> info.severity == Severity.SUCCESS
        True

        >>> info = get_return_code_info(-2)
        >>> info.retryable
        True

        >>> info = get_return_code_info(9999)
        >>> _("Unknown return code") in info.meaning  # doctest: +SKIP
        True
    """
    if code in _RETURN_CODE_INFO:
        info = _RETURN_CODE_INFO[code]
        # Translate meaning at runtime
        return ReturnCodeInfo(
            code=info.code,
            meaning=_(info.meaning),
            severity=info.severity,
            retryable=info.retryable,
        )

    # Translate unknown code message
    unknown_msg = _("Unknown return code")
    return ReturnCodeInfo(
        code=code,
        meaning=f"{unknown_msg}: {code}",
        severity=Severity.ERROR,
        retryable=False,
    )


def is_success(code: int) -> bool:
    """Check if return code indicates success.

    Args:
        code: Numeric return code.

    Returns:
        True if code is 0 (operation successful).

    Examples:
        >>> is_success(0)
        True
        >>> is_success(-1)
        False
    """
    return code == ReturnCode.OK


def is_retryable(code: int) -> bool:
    """Check if operation with this return code may be retried.

    Args:
        code: Numeric return code.

    Returns:
        True if retry may succeed (e.g., temporary errors, maintenance).

    Examples:
        >>> is_retryable(-2)
        True
        >>> is_retryable(-4)
        False
    """
    return get_return_code_info(code).retryable
