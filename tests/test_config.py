"""Tests for config module."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from finanzonline_databox.config import (
    AppConfig,
    _normalize_path_string,  # pyright: ignore[reportPrivateUsage]
    _parse_email_format,  # pyright: ignore[reportPrivateUsage]
    parse_string_list,
    get_default_config_path,
    load_app_config,
    load_finanzonline_config,
)
from finanzonline_databox.domain.errors import ConfigurationError
from finanzonline_databox.enums import EmailFormat
from finanzonline_databox.i18n import Language

pytestmark = pytest.mark.os_agnostic


class TestParseStringList:
    """Tests for parse_string_list helper."""

    def test_parses_list(self) -> None:
        """List of strings passes through."""
        result = parse_string_list(["a", "b", "c"])
        assert result == ["a", "b", "c"]

    def test_filters_empty_items(self) -> None:
        """Empty items are filtered out."""
        result = parse_string_list(["a", "", "b", None])
        assert result == ["a", "b"]

    def test_parses_json_string(self) -> None:
        """JSON array strings are parsed."""
        result = parse_string_list('["foo", "bar"]')
        assert result == ["foo", "bar"]

    def test_invalid_json_returns_empty(self) -> None:
        """Invalid JSON returns empty list."""
        result = parse_string_list("[not valid json")
        assert result == []

    def test_non_list_json_returns_empty(self) -> None:
        """JSON non-array returns empty list."""
        result = parse_string_list('{"key": "value"}')
        assert result == []

    def test_plain_string_returns_empty(self) -> None:
        """Plain string without brackets returns empty."""
        result = parse_string_list("just a string")
        assert result == []

    def test_none_returns_empty(self) -> None:
        """None returns empty list."""
        result = parse_string_list(None)
        assert result == []

    def test_converts_non_strings(self) -> None:
        """Non-string items are converted to strings."""
        result = parse_string_list([1, 2, 3])
        assert result == ["1", "2", "3"]


class TestParseEmailFormat:
    """Tests for _parse_email_format helper."""

    def test_parses_enum_directly(self) -> None:
        """EmailFormat enum passes through."""
        result = _parse_email_format(EmailFormat.HTML, EmailFormat.BOTH)
        assert result == EmailFormat.HTML

    def test_parses_valid_string(self) -> None:
        """Valid string values are parsed."""
        assert _parse_email_format("html", EmailFormat.BOTH) == EmailFormat.HTML
        assert _parse_email_format("plain", EmailFormat.BOTH) == EmailFormat.PLAIN
        assert _parse_email_format("both", EmailFormat.HTML) == EmailFormat.BOTH

    def test_normalizes_case(self) -> None:
        """String case is normalized."""
        assert _parse_email_format("HTML", EmailFormat.BOTH) == EmailFormat.HTML
        assert _parse_email_format("PLAIN", EmailFormat.BOTH) == EmailFormat.PLAIN

    def test_strips_whitespace(self) -> None:
        """Whitespace is stripped."""
        assert _parse_email_format("  html  ", EmailFormat.BOTH) == EmailFormat.HTML

    def test_invalid_string_returns_default(self) -> None:
        """Invalid strings return default."""
        result = _parse_email_format("invalid", EmailFormat.BOTH)
        assert result == EmailFormat.BOTH

    def test_none_returns_default(self) -> None:
        """None returns default."""
        result = _parse_email_format(None, EmailFormat.PLAIN)
        assert result == EmailFormat.PLAIN

    def test_number_returns_default(self) -> None:
        """Numbers return default."""
        result = _parse_email_format(42, EmailFormat.HTML)
        assert result == EmailFormat.HTML


class TestNormalizePathString:
    """Tests for _normalize_path_string helper."""

    def test_linux_path_unchanged_on_linux(self) -> None:
        """Linux paths are unchanged on Linux/macOS."""
        from unittest.mock import patch

        with patch.object(__import__("os"), "name", "posix"):
            result = _normalize_path_string("/home/user/Documents")
            assert result == "/home/user/Documents"

    def test_unc_path_unchanged_on_linux(self) -> None:
        """UNC-style paths are unchanged on Linux/macOS."""
        from unittest.mock import patch

        with patch.object(__import__("os"), "name", "posix"):
            result = _normalize_path_string("//server/share/folder")
            assert result == "//server/share/folder"

    def test_forward_slashes_converted_on_windows(self) -> None:
        """Forward slashes are converted to backslashes on Windows."""
        from unittest.mock import patch

        with patch.object(__import__("os"), "name", "nt"):
            result = _normalize_path_string("/home/user/Documents")
            assert result == "\\home\\user\\Documents"

    def test_unc_path_converted_on_windows(self) -> None:
        """UNC paths with forward slashes are converted on Windows."""
        from unittest.mock import patch

        with patch.object(__import__("os"), "name", "nt"):
            result = _normalize_path_string("//server/share/folder")
            assert result == "\\\\server\\share\\folder"

    def test_mixed_slashes_on_windows(self) -> None:
        """Mixed slashes are all converted to backslashes on Windows."""
        from unittest.mock import patch

        with patch.object(__import__("os"), "name", "nt"):
            result = _normalize_path_string("//server/share\\folder/subfolder")
            assert result == "\\\\server\\share\\folder\\subfolder"


class TestGetDefaultConfigPath:
    """Tests for get_default_config_path function."""

    def test_returns_path(self) -> None:
        """Returns a Path object."""
        result = get_default_config_path()
        assert isinstance(result, Path)

    def test_points_to_toml_file(self) -> None:
        """Path points to defaultconfig.toml."""
        result = get_default_config_path()
        assert result.name == "defaultconfig.toml"

    def test_file_exists(self) -> None:
        """The config file actually exists."""
        result = get_default_config_path()
        assert result.exists()

    def test_is_cached(self) -> None:
        """Function returns same object on repeated calls."""
        result1 = get_default_config_path()
        result2 = get_default_config_path()
        assert result1 is result2


class TestLoadAppConfig:
    """Tests for load_app_config function."""

    def test_loads_default_language(self) -> None:
        """Default language is English."""
        mock_config = MagicMock()
        mock_config.as_dict.return_value = {}
        result = load_app_config(mock_config)
        assert result.language == "en"

    def test_loads_configured_language(self) -> None:
        """Configured language is used."""
        mock_config = MagicMock()
        mock_config.as_dict.return_value = {"app": {"language": "de"}}
        result = load_app_config(mock_config)
        assert result.language == "de"

    def test_invalid_language_uses_default(self) -> None:
        """Invalid language falls back to default."""
        mock_config = MagicMock()
        mock_config.as_dict.return_value = {"app": {"language": "invalid"}}
        result = load_app_config(mock_config)
        assert result.language == "en"

    def test_normalizes_language_case(self) -> None:
        """Language is normalized to lowercase."""
        mock_config = MagicMock()
        mock_config.as_dict.return_value = {"app": {"language": "DE"}}
        result = load_app_config(mock_config)
        assert result.language == "de"


class TestLoadFinanzOnlineConfig:
    """Tests for load_finanzonline_config function."""

    def test_loads_valid_config(self) -> None:
        """Valid configuration loads successfully."""
        mock_config = MagicMock()
        mock_config.as_dict.return_value = {
            "finanzonline": {
                "tid": "12345678",
                "benid": "TESTUSER",
                "pin": "secret123",
                "herstellerid": "ATU12345678",
            }
        }
        result = load_finanzonline_config(mock_config)
        assert result.credentials.tid == "12345678"
        assert result.credentials.benid == "TESTUSER"
        assert result.session_timeout == 30.0
        assert result.query_timeout == 30.0

    def test_raises_on_missing_tid(self) -> None:
        """Missing tid raises ConfigurationError."""
        mock_config = MagicMock()
        mock_config.as_dict.return_value = {
            "finanzonline": {
                "benid": "TESTUSER",
                "pin": "secret",
                "herstellerid": "ATU12345678",
            }
        }
        with pytest.raises(ConfigurationError, match="tid"):
            load_finanzonline_config(mock_config)

    def test_raises_on_missing_benid(self) -> None:
        """Missing benid raises ConfigurationError."""
        mock_config = MagicMock()
        mock_config.as_dict.return_value = {
            "finanzonline": {
                "tid": "12345678",
                "pin": "secret",
                "herstellerid": "ATU12345678",
            }
        }
        with pytest.raises(ConfigurationError, match="benid"):
            load_finanzonline_config(mock_config)

    def test_raises_on_missing_pin(self) -> None:
        """Missing pin raises ConfigurationError."""
        mock_config = MagicMock()
        mock_config.as_dict.return_value = {
            "finanzonline": {
                "tid": "12345678",
                "benid": "TESTUSER",
                "herstellerid": "ATU12345678",
            }
        }
        with pytest.raises(ConfigurationError, match="pin"):
            load_finanzonline_config(mock_config)

    def test_raises_on_missing_herstellerid(self) -> None:
        """Missing herstellerid raises ConfigurationError."""
        mock_config = MagicMock()
        mock_config.as_dict.return_value = {
            "finanzonline": {
                "tid": "12345678",
                "benid": "TESTUSER",
                "pin": "secret",
            }
        }
        with pytest.raises(ConfigurationError, match="herstellerid"):
            load_finanzonline_config(mock_config)

    def test_loads_optional_timeouts(self) -> None:
        """Custom timeouts are loaded."""
        mock_config = MagicMock()
        mock_config.as_dict.return_value = {
            "finanzonline": {
                "tid": "12345678",
                "benid": "TESTUSER",
                "pin": "secret123",
                "herstellerid": "ATU12345678",
                "session_timeout": 60.0,
                "query_timeout": 90.0,
            }
        }
        result = load_finanzonline_config(mock_config)
        assert result.session_timeout == 60.0
        assert result.query_timeout == 90.0

    def test_loads_default_recipients(self) -> None:
        """Default recipients list is loaded."""
        mock_config = MagicMock()
        mock_config.as_dict.return_value = {
            "finanzonline": {
                "tid": "12345678",
                "benid": "TESTUSER",
                "pin": "secret123",
                "herstellerid": "ATU12345678",
                "default_recipients": ["admin@example.com"],
            }
        }
        result = load_finanzonline_config(mock_config)
        assert result.default_recipients == ["admin@example.com"]

    def test_loads_email_format(self) -> None:
        """Email format is loaded."""
        mock_config = MagicMock()
        mock_config.as_dict.return_value = {
            "finanzonline": {
                "tid": "12345678",
                "benid": "TESTUSER",
                "pin": "secret123",
                "herstellerid": "ATU12345678",
                "email_format": "html",
            }
        }
        result = load_finanzonline_config(mock_config)
        assert result.email_format == EmailFormat.HTML

    def test_empty_recipients_becomes_none(self) -> None:
        """Empty recipients list becomes None."""
        mock_config = MagicMock()
        mock_config.as_dict.return_value = {
            "finanzonline": {
                "tid": "12345678",
                "benid": "TESTUSER",
                "pin": "secret123",
                "herstellerid": "ATU12345678",
                "default_recipients": [],
            }
        }
        result = load_finanzonline_config(mock_config)
        assert result.default_recipients is None

    def test_loads_output_dir(self) -> None:
        """Output directory is loaded."""
        mock_config = MagicMock()
        mock_config.as_dict.return_value = {
            "finanzonline": {
                "tid": "12345678",
                "benid": "TESTUSER",
                "pin": "secret123",
                "herstellerid": "ATU12345678",
                "output_dir": "/var/databox",
            }
        }
        result = load_finanzonline_config(mock_config)
        assert result.output_dir == Path("/var/databox")

    def test_output_dir_expands_tilde(self) -> None:
        """Output directory expands ~ to home directory."""
        mock_config = MagicMock()
        mock_config.as_dict.return_value = {
            "finanzonline": {
                "tid": "12345678",
                "benid": "TESTUSER",
                "pin": "secret123",
                "herstellerid": "ATU12345678",
                "output_dir": "~/Documents/DataBox",
            }
        }
        result = load_finanzonline_config(mock_config)
        assert result.output_dir is not None
        assert not str(result.output_dir).startswith("~")
        assert result.output_dir.name == "DataBox"
        assert result.output_dir.parent.name == "Documents"

    def test_empty_output_dir_becomes_none(self) -> None:
        """Empty output_dir becomes None."""
        mock_config = MagicMock()
        mock_config.as_dict.return_value = {
            "finanzonline": {
                "tid": "12345678",
                "benid": "TESTUSER",
                "pin": "secret123",
                "herstellerid": "ATU12345678",
                "output_dir": "",
            }
        }
        result = load_finanzonline_config(mock_config)
        assert result.output_dir is None

    def test_whitespace_output_dir_becomes_none(self) -> None:
        """Whitespace-only output_dir becomes None."""
        mock_config = MagicMock()
        mock_config.as_dict.return_value = {
            "finanzonline": {
                "tid": "12345678",
                "benid": "TESTUSER",
                "pin": "secret123",
                "herstellerid": "ATU12345678",
                "output_dir": "   ",
            }
        }
        result = load_finanzonline_config(mock_config)
        assert result.output_dir is None

    def test_default_output_dir_is_none(self) -> None:
        """Default output_dir is None when not configured."""
        mock_config = MagicMock()
        mock_config.as_dict.return_value = {
            "finanzonline": {
                "tid": "12345678",
                "benid": "TESTUSER",
                "pin": "secret123",
                "herstellerid": "ATU12345678",
            }
        }
        result = load_finanzonline_config(mock_config)
        assert result.output_dir is None


class TestAppConfig:
    """Tests for AppConfig dataclass."""

    def test_default_language(self) -> None:
        """Default language is English."""
        config = AppConfig()
        assert config.language == Language.ENGLISH

    def test_custom_language(self) -> None:
        """Custom language can be set."""
        config = AppConfig(language=Language.GERMAN)
        assert config.language == Language.GERMAN

    def test_is_frozen(self) -> None:
        """AppConfig is immutable."""
        config = AppConfig()
        with pytest.raises(AttributeError):
            config.language = Language.GERMAN  # type: ignore[misc]
