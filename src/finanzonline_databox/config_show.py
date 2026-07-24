"""Configuration display functionality for CLI config command.

Provides the business logic for displaying merged configuration from all
sources in human-readable or JSON format. Keeps CLI layer thin by handling
all formatting and display logic here.

Contents:
    * :func:`display_config` - displays configuration in requested format

System Role:
    Lives in the behaviors layer. The CLI command delegates to this module for
    all configuration display logic, keeping presentation concerns separate from
    command-line argument parsing.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any, cast

import click

from .enums import OutputFormat

if TYPE_CHECKING:
    from lib_layered_config import Config


def display_config(
    config: Config,
    *,
    output_format: OutputFormat = OutputFormat.HUMAN,
    section: str | None = None,
) -> None:
    """Display the provided configuration in the requested format.

    Users need visibility into the effective configuration loaded from
    defaults, app configs, host configs, user configs, .env files, and
    environment variables. Outputs the provided Config object in the
    requested format.

    Args:
        config: Already-loaded layered configuration object to display.
        output_format: Output format: OutputFormat.HUMAN for TOML-like display or
            OutputFormat.JSON for JSON. Defaults to OutputFormat.HUMAN.
        section: Optional section name to display only that section. When None,
            displays all configuration.

    Side Effects:
        Writes formatted configuration to stdout via click.echo().
        Raises SystemExit(1) if requested section doesn't exist.

    Note:
        The human-readable format mimics TOML syntax for consistency with the
        configuration file format. JSON format provides machine-readable output
        suitable for parsing by other tools.

    Example:
        >>> from finanzonline_databox.config import get_config
        >>> config = get_config()  # doctest: +SKIP
        >>> display_config(config)  # doctest: +SKIP
        [lib_log_rich]
          service = "finanzonline_databox"
          environment = "prod"

        >>> display_config(config, output_format=OutputFormat.JSON)  # doctest: +SKIP
        {
          "lib_log_rich": {
            "service": "finanzonline_databox",
            "environment": "prod"
          }
        }
    """
    if output_format == OutputFormat.JSON:
        _display_json(config, section=section)
    else:
        _display_human(config, section=section)


def _echo_missing_section(section: str) -> None:
    """Report a requested section that has no data and abort the command."""
    click.echo(f"Section '{section}' not found or empty", err=True)
    raise SystemExit(1)


def _display_json(config: Config, *, section: str | None) -> None:
    """Print configuration as JSON, optionally scoped to a single section."""
    if not section:
        # Use lib_layered_config's built-in to_json method
        click.echo(config.to_json(indent=2))
        return

    section_data = config.get(section, default={})
    if not section_data:
        _echo_missing_section(section)
        return
    click.echo(json.dumps({section: section_data}, indent=2))


def _display_human(config: Config, *, section: str | None) -> None:
    """Print configuration in TOML-like format, optionally scoped to a single section."""
    if not section:
        # Show all configuration
        data: dict[str, Any] = config.as_dict()
        for section_name, section_data in data.items():
            _echo_section(section_name, section_data)
        return

    section_data = config.get(section, default={})
    if not section_data:
        _echo_missing_section(section)
        return
    _echo_section(section, section_data)


def _echo_section(section_name: str, section_data: Any) -> None:
    """Print a single ``[section]`` header followed by its key/value lines."""
    click.echo(f"\n[{section_name}]")
    if not isinstance(section_data, dict):
        click.echo(f"  {section_data}")
        return
    dict_data = cast("dict[str, Any]", section_data)
    for key, value in dict_data.items():
        _echo_value_line(key, value)


def _echo_value_line(key: str, value: Any) -> None:
    """Print a single ``key = value`` line, formatting the value TOML-style."""
    if isinstance(value, (list, dict)):
        click.echo(f"  {key} = {json.dumps(value)}")
    elif isinstance(value, str):
        click.echo(f'  {key} = "{value}"')
    else:
        click.echo(f"  {key} = {value}")


__all__ = [
    "display_config",
]
