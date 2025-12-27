"""Behavioral tests for config_show module."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from finanzonline_databox.config_show import display_config
from finanzonline_databox.enums import OutputFormat

pytestmark = pytest.mark.os_agnostic


def _make_mock_config(data: dict[str, Any]) -> MagicMock:
    """Create a mock Config object."""
    config = MagicMock()
    config.as_dict.return_value = data

    def get_item(key: str, default: Any = None) -> Any:
        return data.get(key, default)

    config.get.side_effect = get_item
    config.to_json.return_value = '{"test": "json"}'
    return config


class TestDisplayConfigHuman:
    """Behavioral tests for human-readable config display."""

    def test_displays_all_sections(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Displays all sections in TOML-like format."""
        config = _make_mock_config(
            {
                "app": {"language": "en"},
                "finanzonline": {"tid": "123"},
            }
        )

        display_config(config, format=OutputFormat.HUMAN)

        captured = capsys.readouterr()
        assert "[app]" in captured.out
        assert "[finanzonline]" in captured.out
        assert "language" in captured.out
        assert "tid" in captured.out

    def test_displays_string_values_quoted(self, capsys: pytest.CaptureFixture[str]) -> None:
        """String values are displayed with quotes."""
        config = _make_mock_config(
            {
                "app": {"language": "en"},
            }
        )

        display_config(config, format=OutputFormat.HUMAN)

        captured = capsys.readouterr()
        assert '"en"' in captured.out

    def test_displays_numeric_values_unquoted(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Numeric values are displayed without quotes."""
        config = _make_mock_config(
            {
                "settings": {"timeout": 30},
            }
        )

        display_config(config, format=OutputFormat.HUMAN)

        captured = capsys.readouterr()
        assert "timeout = 30" in captured.out

    def test_displays_list_as_json(self, capsys: pytest.CaptureFixture[str]) -> None:
        """List values are displayed as JSON."""
        config = _make_mock_config(
            {
                "email": {"recipients": ["a@b.com", "c@d.com"]},
            }
        )

        display_config(config, format=OutputFormat.HUMAN)

        captured = capsys.readouterr()
        assert '["a@b.com", "c@d.com"]' in captured.out

    def test_displays_single_section(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Displays only the requested section."""
        config = _make_mock_config(
            {
                "app": {"language": "de"},
                "finanzonline": {"tid": "123"},
            }
        )

        display_config(config, format=OutputFormat.HUMAN, section="app")

        captured = capsys.readouterr()
        assert "[app]" in captured.out
        assert "language" in captured.out
        assert "[finanzonline]" not in captured.out

    def test_missing_section_exits_with_error(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Missing section raises SystemExit(1)."""
        config = _make_mock_config({"app": {"language": "en"}})

        with pytest.raises(SystemExit) as exc_info:
            display_config(config, format=OutputFormat.HUMAN, section="nonexistent")

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "not found" in captured.err


class TestDisplayConfigJson:
    """Behavioral tests for JSON config display."""

    def test_displays_all_as_json(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Displays all configuration as JSON."""
        config = _make_mock_config({"app": {"language": "en"}})

        display_config(config, format=OutputFormat.JSON)

        captured = capsys.readouterr()
        # Uses config.to_json() for full output
        assert "json" in captured.out.lower()

    def test_displays_single_section_as_json(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Displays single section as JSON."""
        config = _make_mock_config(
            {
                "app": {"language": "de"},
            }
        )

        display_config(config, format=OutputFormat.JSON, section="app")

        captured = capsys.readouterr()
        assert '"app"' in captured.out
        assert '"language"' in captured.out

    def test_missing_section_exits_with_error_json(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Missing section in JSON format raises SystemExit(1)."""
        config = _make_mock_config({"app": {"language": "en"}})

        with pytest.raises(SystemExit) as exc_info:
            display_config(config, format=OutputFormat.JSON, section="nonexistent")

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "not found" in captured.err
