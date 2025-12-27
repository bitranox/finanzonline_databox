"""Tests for domain exceptions.

Tests cover exception hierarchy, attributes, and message handling.
"""

from __future__ import annotations

import pytest

from finanzonline_databox.domain.errors import (
    AuthenticationError,
    ConfigurationError,
    DataboxError,
    DataboxOperationError,
    SessionError,
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


class TestExceptionHierarchy:
    """Tests for exception hierarchy behavior."""

    def test_catch_all_with_base_class(self) -> None:
        """Should catch all specific errors with DataboxError."""
        errors = [
            ConfigurationError("config"),
            AuthenticationError("auth"),
            SessionError("session"),
            DataboxOperationError("operation"),
        ]
        for err in errors:
            try:
                raise err
            except DataboxError as caught:
                assert caught.message in ["config", "auth", "session", "operation"]

    def test_specific_catch_first(self) -> None:
        """Should allow catching specific exceptions first."""
        try:
            raise DataboxOperationError("rate limit", return_code=-2, retryable=True)
        except DataboxOperationError as err:
            assert err.retryable is True
        except DataboxError:
            pytest.fail("Should have caught DataboxOperationError specifically")
