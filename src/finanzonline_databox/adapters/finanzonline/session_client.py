"""FinanzOnline session management adapter.

Purpose
-------
Implement SessionPort for authentication with BMF FinanzOnline
session webservice using SOAP/zeep.

Contents
--------
* :class:`FinanzOnlineSessionClient` - Session login/logout adapter

System Role
-----------
Adapters layer - SOAP client for FinanzOnline session webservice.

Reference
---------
BMF Session Webservice: https://finanzonline.bmf.gv.at/fon/ws/sessionService.wsdl
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, cast

from zeep import Client
from zeep.exceptions import Fault, TransportError, XMLSyntaxError
from zeep.transports import Transport

from finanzonline_databox._format_utils import mask_credential
from finanzonline_databox.domain.errors import AuthenticationError, SessionError
from finanzonline_databox.domain.models import (
    Diagnostics,
    RC_DATE_PARAMS_REQUIRED,
    SessionInfo,
)

if TYPE_CHECKING:
    from finanzonline_databox.domain.models import FinanzOnlineCredentials


logger = logging.getLogger(__name__)

SESSION_SERVICE_WSDL = "https://finanzonline.bmf.gv.at/fonws/ws/sessionService.wsdl"

# Maximum length of HTML content to include in diagnostics (for email)
_MAX_HTML_CONTENT_LENGTH = 4000


def _is_maintenance_page(content: str | bytes | None) -> bool:
    """Detect if content is a FinanzOnline maintenance page.

    Args:
        content: Raw HTML content (string or bytes).

    Returns:
        True if content appears to be a maintenance page.
    """
    if not content:
        return False
    content_str = content.decode("utf-8", errors="replace") if isinstance(content, bytes) else content
    content_lower = content_str.lower()
    return "/wartung/" in content_lower


def _extract_xml_error_content(exc: XMLSyntaxError) -> str:
    """Extract HTML/XML content from XMLSyntaxError for diagnostics.

    Args:
        exc: The XMLSyntaxError exception.

    Returns:
        Truncated content string for inclusion in error diagnostics.
    """
    content = getattr(exc, "content", None)
    if not content:
        return str(exc)

    content_str = content.decode("utf-8", errors="replace") if isinstance(content, bytes) else str(content)
    if len(content_str) > _MAX_HTML_CONTENT_LENGTH:
        return content_str[:_MAX_HTML_CONTENT_LENGTH] + "\n... [truncated]"
    return content_str


def _format_login_request(credentials: FinanzOnlineCredentials) -> dict[str, str]:
    """Format login request parameters for debug logging (masked)."""
    return {
        "tid": credentials.tid,
        "benid": credentials.benid,
        "pin": mask_credential(credentials.pin),
        "herstellerid": credentials.herstellerid,
    }


def _format_attr_value(attr: str, value: Any) -> Any:
    """Format attribute value, masking session ID."""
    if attr == "id" and value:
        return mask_credential(str(value))
    return value


def _format_response_for_logging(response: Any) -> dict[str, Any]:
    """Format SOAP response object for debug logging."""
    if response is None:
        return {"response": None}
    attrs = ["rc", "msg", "id"]
    return {attr: _format_attr_value(attr, getattr(response, attr)) for attr in attrs if hasattr(response, attr)}


def _extract_login_response_fields(response: Any) -> tuple[str, str, str]:
    """Extract return code, message, and session ID from login response."""
    return_code = str(getattr(response, "rc", ""))
    response_message = str(getattr(response, "msg", "") or "")
    raw_id = str(getattr(response, "id", "") or "") if hasattr(response, "id") else ""
    session_id = mask_credential(raw_id) if raw_id else ""
    return return_code, response_message, session_id


def _build_login_diagnostics(
    credentials: FinanzOnlineCredentials,
    response: Any | None = None,
    error: str | None = None,
) -> Diagnostics:
    """Build diagnostic information for login operation.

    Args:
        credentials: The credentials used (will be masked).
        response: Optional SOAP response object.
        error: Optional error message.

    Returns:
        Diagnostics object with diagnostic information.
    """
    return_code, response_message, session_id = ("", "", "")
    if response is not None:
        return_code, response_message, session_id = _extract_login_response_fields(response)

    return Diagnostics(
        operation="login",
        tid=credentials.tid,
        benid=credentials.benid,
        pin=mask_credential(credentials.pin),
        session_id=session_id,
        return_code=return_code,
        response_message=response_message,
        error_detail=error or "",
    )


def _handle_login_exception(
    exc: Exception,
    credentials: FinanzOnlineCredentials,
    response: Any | None,
) -> None:
    """Handle exceptions during login and raise appropriate domain error.

    Args:
        exc: The exception that occurred.
        credentials: FinanzOnline credentials.
        response: Optional SOAP response.

    Raises:
        AuthenticationError: For authentication errors.
        SessionError: For all other session errors.
    """
    if isinstance(exc, (AuthenticationError, SessionError)):
        raise

    diagnostics = _build_login_diagnostics(credentials, response, error=str(exc))

    if isinstance(exc, Fault):
        logger.error("SOAP fault during login: %s", exc)
        raise SessionError(f"SOAP fault: {exc.message}", diagnostics=diagnostics) from exc

    if isinstance(exc, TransportError):
        logger.error("Transport error during login: %s", exc)
        raise SessionError(f"Connection error: {exc}", diagnostics=diagnostics) from exc

    if isinstance(exc, XMLSyntaxError):
        html_content = getattr(exc, "content", None)
        is_maintenance = _is_maintenance_page(html_content)
        error_type = "DataBox in Wartung" if is_maintenance else "Invalid XML Response"
        error_detail = _extract_xml_error_content(exc)
        diagnostics = _build_login_diagnostics(credentials, response, error=error_detail)
        logger.error("%s during login: %s", error_type, exc)
        raise SessionError(error_type, diagnostics=diagnostics) from exc

    logger.error("Unexpected error during login: %s", exc)
    raise SessionError(f"Unexpected error: {exc}", diagnostics=diagnostics) from exc


class FinanzOnlineSessionClient:
    """SOAP client for FinanzOnline session management.

    Implements SessionPort protocol for login/logout operations
    with the BMF session webservice.

    Attributes:
        _timeout: Request timeout in seconds.
        _client: Zeep SOAP client (lazy-initialized).
    """

    def __init__(self, timeout: float = 30.0) -> None:
        """Initialize session client.

        Args:
            timeout: Request timeout in seconds.
        """
        self._timeout = timeout
        self._client: Client | None = None

    def _get_client(self) -> Client:
        """Get or create SOAP client with configured timeout.

        Returns:
            Zeep Client instance for session service.
        """
        if self._client is None:
            logger.debug("Creating session service client with timeout=%.1fs", self._timeout)
            transport = Transport(timeout=self._timeout)
            self._client = Client(SESSION_SERVICE_WSDL, transport=transport)
        return self._client

    def login(self, credentials: FinanzOnlineCredentials) -> SessionInfo:
        """Authenticate with FinanzOnline and obtain a session.

        Args:
            credentials: FinanzOnline credentials (tid, benid, pin).

        Returns:
            SessionInfo with session_id if successful.

        Raises:
            AuthenticationError: If credentials are invalid (code -4).
            SessionError: If session creation fails for other reasons.
        """
        logger.debug("Attempting login for tid=%s, benid=%s", credentials.tid, credentials.benid)
        response: Any = None

        try:
            response = self._execute_login(credentials)
            return self._process_login_response(credentials, response)
        except Exception as e:
            _handle_login_exception(e, credentials, response)
            raise  # Unreachable but satisfies type checker

    def _execute_login(self, credentials: FinanzOnlineCredentials) -> Any:
        """Execute the SOAP login call."""
        client = self._get_client()
        logger.debug("Login request: %s", _format_login_request(credentials))
        response = client.service.login(
            tid=credentials.tid,
            benid=credentials.benid,
            pin=credentials.pin,
            herstellerid=credentials.herstellerid,
        )
        logger.debug("Login response: %s", _format_response_for_logging(response))
        return response

    def _process_login_response(self, credentials: FinanzOnlineCredentials, response: Any) -> SessionInfo:
        """Process SOAP login response and build result."""
        return_code = int(cast(int, response.rc))
        message = str(cast(str, response.msg) or "")
        session_id = str(cast(str, response.id) or "") if hasattr(response, "id") else ""

        logger.debug("Login response: rc=%d, msg=%s", return_code, message)

        if return_code == RC_DATE_PARAMS_REQUIRED:
            # RC -4: Session service uses this for authorization failures (login validation)
            diagnostics = _build_login_diagnostics(credentials, response)
            raise AuthenticationError(f"Not authorized: {message}", return_code=return_code, diagnostics=diagnostics)

        return SessionInfo(session_id=session_id, return_code=return_code, message=message)

    def logout(self, session_id: str, credentials: FinanzOnlineCredentials) -> bool:
        """End a FinanzOnline session.

        Args:
            session_id: Active session identifier.
            credentials: FinanzOnline credentials.

        Returns:
            True if logout succeeded, False otherwise.
        """
        logout_request = {
            "tid": credentials.tid,
            "benid": credentials.benid,
            "id": mask_credential(session_id) if session_id else "?",
        }
        logger.debug("Logout request: %s", logout_request)

        try:
            client = self._get_client()
            response: Any = client.service.logout(
                tid=credentials.tid,
                benid=credentials.benid,
                id=session_id,
            )

            logger.debug("Logout response: %s", _format_response_for_logging(response))
            return_code = int(cast(int, response.rc)) if hasattr(response, "rc") else -1

            return return_code == 0

        except Exception as e:
            # Logout failures are non-fatal, just log and return False
            logger.warning("Logout failed (non-fatal): %s", e)
            return False
