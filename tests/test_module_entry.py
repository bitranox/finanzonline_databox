"""Module entry stories ensuring `python -m` mirrors the CLI."""

from __future__ import annotations

import importlib
import runpy
import sys
from typing import TYPE_CHECKING

import lib_cli_exit_tools
import pytest

from finanzonline_databox import cli as cli_mod

if TYPE_CHECKING:
    from collections.abc import Callable


def _run_module_entry(monkeypatch: pytest.MonkeyPatch, argv: list[str]) -> int:
    """Run ``python -m finanzonline_databox`` in-process and return its exit code."""
    monkeypatch.setattr(sys, "argv", ["finanzonline_databox", *argv])
    with pytest.raises(SystemExit) as exc:
        runpy.run_module("finanzonline_databox.__main__", run_name="__main__")
    assert isinstance(exc.value.code, int)
    return exc.value.code


@pytest.mark.os_agnostic
@pytest.mark.parametrize("argv", [["--bogus-flag"], ["no-such-command"], ["--help"], ["hello"]], ids=["bad-flag", "unknown-command", "help", "hello"])
def test_module_entry_exits_with_the_code_the_console_script_gives(monkeypatch: pytest.MonkeyPatch, argv: list[str]) -> None:
    script_code = cli_mod.main(argv)

    assert _run_module_entry(monkeypatch, argv) == script_code


@pytest.mark.os_agnostic
@pytest.mark.parametrize("argv", [["--bogus-flag"], ["no-such-command"]], ids=["bad-flag", "unknown-command"])
def test_module_entry_reports_a_usage_error_with_click_usage_exit_code(monkeypatch: pytest.MonkeyPatch, argv: list[str]) -> None:
    assert _run_module_entry(monkeypatch, argv) == 2


@pytest.mark.os_agnostic
def test_when_traceback_flag_is_used_via_module_entry_the_full_poem_is_printed(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    strip_ansi: Callable[[str], str],
) -> None:
    monkeypatch.setattr(lib_cli_exit_tools.config, "traceback", False, raising=False)
    monkeypatch.setattr(lib_cli_exit_tools.config, "traceback_force_color", False, raising=False)

    exit_code = _run_module_entry(monkeypatch, ["--traceback", "fail"])

    plain_err = strip_ansi(capsys.readouterr().err)
    assert exit_code != 0
    assert "Traceback (most recent call last)" in plain_err
    assert "RuntimeError: I should fail" in plain_err
    assert "[TRUNCATED" not in plain_err
    assert lib_cli_exit_tools.config.traceback is False
    assert lib_cli_exit_tools.config.traceback_force_color is False


@pytest.mark.os_agnostic
def test_when_the_module_is_imported_it_runs_nothing() -> None:
    # Left imported, every later runpy of finanzonline_databox.__main__ warns that it is already loaded.
    previous = sys.modules.pop("finanzonline_databox.__main__", None)
    try:
        module = importlib.import_module("finanzonline_databox.__main__")

        assert module.cli is cli_mod
    finally:
        sys.modules.pop("finanzonline_databox.__main__", None)
        if previous is not None:
            sys.modules["finanzonline_databox.__main__"] = previous
