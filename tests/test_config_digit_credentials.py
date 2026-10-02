"""All-digit credentials read from an unquoted ``.env`` value keep their text.

lib_layered_config converts an unquoted ``.env`` value exactly like an environment value, so
``FINANZONLINE__TID=123456789`` reaches the configuration as the int 123456789. A participant ID,
user ID or PIN is an identifier, never a number: the schema turns the int back into its text,
which is lossless because the library only converts a number that reads back as the same text.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from lib_layered_config import Config, read_config

from finanzonline_databox import __init__conf__
from finanzonline_databox.config import load_finanzonline_config

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


def test_unquoted_all_digit_credentials_load_as_text(tmp_path: Path) -> None:
    config = _config_from_dotenv(
        tmp_path,
        "FINANZONLINE__TID=123456789\nFINANZONLINE__BENID=987654321\nFINANZONLINE__PIN=47110815\nFINANZONLINE__HERSTELLERID=ATU12345678\n",
    )

    credentials = load_finanzonline_config(config).credentials

    assert (credentials.tid, credentials.benid, credentials.pin) == ("123456789", "987654321", "47110815")


def test_a_leading_zero_credential_keeps_its_zero(tmp_path: Path) -> None:
    config = _config_from_dotenv(
        tmp_path,
        "FINANZONLINE__TID=012345678\nFINANZONLINE__BENID=USER0001\nFINANZONLINE__PIN=08154711\nFINANZONLINE__HERSTELLERID=ATU12345678\n",
    )

    credentials = load_finanzonline_config(config).credentials

    assert (credentials.tid, credentials.pin) == ("012345678", "08154711")
