"""Fake session client for testing.

Provides a real in-memory implementation of SessionPort.
Preferred over mocks because it tests actual behavior.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from finanzonline_databox.domain.models import FinanzOnlineCredentials, SessionInfo


@dataclass
class FakeSessionClient:
    """In-memory fake implementation of SessionPort.

    Configurable to return success or failure responses.
    Tracks calls for verification without mock assertions.
    """

    login_response: SessionInfo | None = None
    login_error: Exception | None = None
    logout_response: bool = True
    logout_error: Exception | None = None

    login_calls: list[FinanzOnlineCredentials] = field(
        default_factory=lambda: []  # type: ignore[arg-type]
    )
    logout_calls: list[tuple[str, FinanzOnlineCredentials]] = field(
        default_factory=lambda: []  # type: ignore[arg-type]
    )

    def login(self, credentials: FinanzOnlineCredentials) -> SessionInfo:
        """Record login call and return configured response."""
        self.login_calls.append(credentials)

        if self.login_error:
            raise self.login_error

        if self.login_response:
            return self.login_response

        # Default success response
        from finanzonline_databox.domain.models import SessionInfo as SI

        return SI(
            session_id="FAKE_SESSION_123",
            return_code=0,
            message="Login successful",
        )

    def logout(self, session_id: str, credentials: FinanzOnlineCredentials) -> bool:
        """Record logout call and return configured response."""
        self.logout_calls.append((session_id, credentials))

        if self.logout_error:
            raise self.logout_error

        return self.logout_response

    @property
    def login_called(self) -> bool:
        """Check if login was called."""
        return len(self.login_calls) > 0

    @property
    def logout_called(self) -> bool:
        """Check if logout was called."""
        return len(self.logout_calls) > 0

    def reset(self) -> None:
        """Clear all recorded calls."""
        self.login_calls.clear()
        self.logout_calls.clear()
