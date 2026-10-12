"""Digit-only ``.env`` values reach every text setting as the text the operator wrote.

lib_layered_config reads an unquoted ``.env`` or environment value as an int whenever that number
reads back as the same text (``123456`` -> ``123456``). A text setting must accept such a number and
keep its digits, otherwise an ordinary ``.env`` line makes the command fail. The credential fields
are covered in ``test_config_digit_credentials``; these tests cover the remaining text settings.

Each test loads a real ``.env`` through the real loader and asserts the library hands over an int
first, so a change in its coercion shows up here rather than on a deployed host.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from lib_layered_config import Config, read_config

from finanzonline_databox import __init__conf__
from finanzonline_databox.config import validate_config
from finanzonline_databox.logging_setup import _build_runtime_config  # pyright: ignore[reportPrivateUsage]
from finanzonline_databox.mail import load_email_config_from_dict

if TYPE_CHECKING:
    from pathlib import Path

pytestmark = pytest.mark.os_agnostic


def _config_from_dotenv(tmp_path: Path, body: str) -> Config:
    env_file = tmp_path / "test.env"
    env_file.write_text(body, encoding="utf-8")
    return read_config(
        vendor=__init__conf__.LAYEREDCONF_VENDOR,
        app=__init__conf__.LAYEREDCONF_APP,
        slug=__init__conf__.LAYEREDCONF_SLUG,
        start_dir=str(tmp_path),
        dotenv_path=str(env_file),
    )


@pytest.mark.parametrize("key", ["smtp_password", "smtp_username"])
def test_a_digit_only_email_text_setting_reaches_the_mail_config_as_its_text(tmp_path: Path, key: str) -> None:
    config = _config_from_dotenv(tmp_path, f"EMAIL__{key.upper()}=123456\n")
    # Premise: the library hands the value over as a number. Without it the test proves nothing.
    assert isinstance(config.get("email", default={})[key], int)

    email = load_email_config_from_dict(config.as_dict())

    assert getattr(email, key) == "123456"


@pytest.mark.parametrize(
    ("section", "key"),
    [("finanzonline", "output_dir"), ("finanzonline", "email_format"), ("app", "language")],
)
def test_a_digit_only_text_setting_is_read_as_its_text(tmp_path: Path, section: str, key: str) -> None:
    config = _config_from_dotenv(tmp_path, f"{section.upper()}__{key.upper()}=2026\n")
    assert isinstance(config.get(section, default={})[key], int)

    schema = validate_config(config)

    assert getattr(getattr(schema, section), key) == "2026"


def test_a_digit_only_logging_service_name_reaches_lib_log_rich_as_its_text(tmp_path: Path) -> None:
    config = _config_from_dotenv(tmp_path, "LIB_LOG_RICH__SERVICE=4711\n")
    assert isinstance(config.get("lib_log_rich", default={})["service"], int)

    assert _build_runtime_config(config).service == "4711"


def test_a_numeric_setting_still_reads_as_a_number(tmp_path: Path) -> None:
    config = _config_from_dotenv(tmp_path, "EMAIL__TIMEOUT=45\n")

    assert load_email_config_from_dict(config.as_dict()).timeout == 45.0


def test_a_boolean_is_still_refused_as_a_text_setting(tmp_path: Path) -> None:
    config = _config_from_dotenv(tmp_path, "EMAIL__SMTP_PASSWORD=true\n")
    assert config.get("email", default={})["smtp_password"] is True

    with pytest.raises(ValueError, match="smtp_password"):
        load_email_config_from_dict(config.as_dict())
