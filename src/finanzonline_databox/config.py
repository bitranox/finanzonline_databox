"""Configuration management using lib_layered_config.

Provides a centralized configuration loader that merges defaults, application
configs, host configs, user configs, .env files, and environment variables
following a deterministic precedence order.

Contents:
    * :func:`get_config` – loads configuration with lib_layered_config
    * :func:`get_default_config_path` – returns path to bundled default config
    * :func:`load_finanzonline_config` – loads FinanzOnline credentials and settings

    Configuration identifiers (vendor, app, slug) are imported from
    :mod:`finanzonline_databox.__init__conf__` as LAYEREDCONF_* constants.

System Role:
    Acts as the configuration adapter layer, bridging lib_layered_config with the
    application's runtime needs while keeping domain logic decoupled from
    configuration mechanics.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from lib_layered_config import Config, read_config

from . import __init__conf__
from .config_schema import ConfigSchema
from .domain.errors import ConfigurationError
from .domain.models import FinanzOnlineCredentials
from .enums import EmailFormat

if TYPE_CHECKING:
    from .i18n import Language

# =============================================================================
# Configuration Parsing Helpers
# =============================================================================


def parse_string_list(raw: object) -> list[str]:
    """Parse a string list from config, handling JSON strings from .env files."""
    import json

    if isinstance(raw, list):
        return [str(item) for item in cast(list[object], raw) if item]

    if isinstance(raw, str) and raw.startswith("["):
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                return [str(item) for item in cast(list[object], parsed) if item]
        except json.JSONDecodeError:
            pass

    return []


def _parse_email_format(raw: Any, default: EmailFormat) -> EmailFormat:
    """Parse email format from config value.

    Args:
        raw: Raw config value (string or EmailFormat).
        default: Default value if parsing fails.

    Returns:
        EmailFormat enum value.
    """
    if isinstance(raw, EmailFormat):
        return raw

    if isinstance(raw, str):
        normalized = raw.lower().strip()
        try:
            return EmailFormat(normalized)
        except ValueError:
            pass

    return default


def _normalize_path_string(path_str: str) -> str:
    """Normalize path string to use OS-appropriate separators.

    Allows users to use forward slashes (Linux-style) on all platforms,
    including Windows. This is especially useful for UNC paths which
    would otherwise require escaped backslashes in TOML config files.

    Args:
        path_str: Path string, possibly with forward slashes.

    Returns:
        Normalized path string with OS-appropriate separators.

    Examples:
        On Windows:
            "//server/share/folder" -> "\\\\server\\share\\folder"
            "/home/user/docs" -> "\\home\\user\\docs"

        On Linux/macOS:
            "//server/share/folder" -> "//server/share/folder" (unchanged)
            "C:\\Users\\docs" -> "C:\\Users\\docs" (unchanged)
    """
    import os

    if os.name == "nt":  # Windows
        # Replace forward slashes with backslashes for Windows
        return path_str.replace("/", "\\")

    # On Linux/macOS, leave path unchanged
    return path_str


@lru_cache(maxsize=1)
def get_default_config_path() -> Path:
    """Return the path to the bundled default configuration file.

    The default configuration ships with the package and needs to be
    locatable at runtime regardless of how the package is installed.
    Uses __file__ to locate the defaultconfig.toml file relative to this
    module.

    Returns:
        Absolute path to defaultconfig.toml.

    Note:
        This function is cached since the path never changes during runtime.

    Example:
        >>> path = get_default_config_path()
        >>> path.name
        'defaultconfig.toml'
        >>> path.exists()
        True
    """
    return Path(__file__).parent / "defaultconfig.toml"


# Cache configuration to avoid redundant file I/O and parsing.
# Trade-offs:
#   ✅ Future-proof if config is read from multiple places
#   ✅ Near-zero overhead (single cache entry)
#   ❌ Prevents dynamic config reloading (if ever needed)
#   ❌ start_dir/profile parameter variations would bypass cache
@lru_cache(maxsize=4)
def get_config(*, profile: str | None = None, start_dir: str | None = None) -> Config:
    """Load layered configuration with application defaults.

    Centralizes configuration loading so all entry points use the same
    precedence rules and default values without duplicating the discovery
    logic. Uses lru_cache to avoid redundant file reads when called from
    multiple modules.

    Loads configuration from multiple sources in precedence order:
    defaults → app → host → user → dotenv → env

    The vendor, app, and slug identifiers determine platform-specific paths:
    - Linux: Uses XDG directories with slug
    - macOS: Uses Library/Application Support with vendor/app
    - Windows: Uses ProgramData/AppData with vendor/app

    When a profile is specified, configuration is loaded from profile-specific
    subdirectories (e.g., ~/.config/slug/profile/<name>/config.toml).

    Args:
        profile: Optional profile name for environment isolation. When specified,
            a ``profile/<name>/`` subdirectory is inserted into all configuration
            paths. Valid names: alphanumeric, hyphens, underscores. Examples:
            'test', 'production', 'staging-v2'. Defaults to None (no profile).
        start_dir: Optional directory that seeds .env discovery. Defaults to current
            working directory when None.

    Returns:
        Immutable configuration object with provenance tracking.

    Note:
        This function is cached (maxsize=4). The first call loads and parses all
        configuration files; subsequent calls with the same parameters return the
        cached Config instance immediately.

    Example:
        >>> config = get_config()
        >>> isinstance(config.as_dict(), dict)
        True
        >>> config.get("nonexistent", default="fallback")
        'fallback'

        >>> # Load production profile
        >>> prod_config = get_config(profile="production")  # doctest: +SKIP

    See Also:
        lib_layered_config.read_config: Underlying configuration loader.
    """
    return read_config(
        vendor=__init__conf__.LAYEREDCONF_VENDOR,
        app=__init__conf__.LAYEREDCONF_APP,
        slug=__init__conf__.LAYEREDCONF_SLUG,
        profile=profile,
        default_file=get_default_config_path(),
        start_dir=start_dir,
    )


def validate_config(config: Config) -> ConfigSchema:
    """Validate config dict against Pydantic schema.

    Converts the untyped config dictionary from lib_layered_config into
    a validated Pydantic model. This is the boundary where untyped config
    data becomes typed.

    Args:
        config: Loaded layered configuration object.

    Returns:
        Validated ConfigSchema with typed sections.

    Raises:
        ConfigurationError: If config validation fails.

    Example:
        >>> config = get_config()  # doctest: +SKIP
        >>> schema = validate_config(config)  # doctest: +SKIP
        >>> schema.app.language  # doctest: +SKIP
        'en'
    """
    try:
        return ConfigSchema.model_validate(config.as_dict())
    except Exception as e:
        raise ConfigurationError(f"Configuration validation failed: {e}") from e


def _default_language() -> Language:
    """Return default language (avoids circular import at module load)."""
    from .i18n import Language

    return Language.ENGLISH


@dataclass(frozen=True, slots=True)
class AppConfig:
    """General application configuration.

    Attributes:
        language: Language for user-facing messages.
    """

    language: Language = field(default_factory=_default_language)


def load_app_config(config: Config) -> AppConfig:
    """Load application configuration from layered config.

    Args:
        config: Loaded layered configuration object.

    Returns:
        AppConfig with language setting.

    Example:
        >>> config = get_config()  # doctest: +SKIP
        >>> app_config = load_app_config(config)  # doctest: +SKIP
        >>> app_config.language  # doctest: +SKIP
        Language.ENGLISH
    """
    from .i18n import Language

    # Validate config at boundary using Pydantic schema
    schema = validate_config(config)

    # Parse language with validation (from_string handles invalid values)
    raw_language = schema.app.language
    language = Language.from_string(raw_language) if raw_language else Language.ENGLISH

    return AppConfig(language=language)


@dataclass(frozen=True, slots=True)
class FinanzOnlineConfig:
    """Configuration for FinanzOnline DataBox connection.

    Attributes:
        credentials: Authentication credentials (tid, benid, pin, herstellerid).
        session_timeout: Timeout for session operations in seconds.
        query_timeout: Timeout for query operations in seconds.
        default_recipients: Default email recipients for sync summary notifications.
        document_recipients: Default email recipients for per-document notifications with attachments.
        email_format: Email body format (html, text, or both).
        output_dir: Default output directory for downloaded files.
    """

    credentials: FinanzOnlineCredentials
    session_timeout: float = 30.0
    query_timeout: float = 30.0
    default_recipients: list[str] | None = None
    document_recipients: list[str] | None = None
    email_format: EmailFormat = EmailFormat.BOTH
    output_dir: Path | None = None


def load_finanzonline_config(config: Config) -> FinanzOnlineConfig:
    """Load FinanzOnline configuration from layered config.

    Args:
        config: Loaded layered configuration object.

    Returns:
        FinanzOnlineConfig with validated credentials and settings.

    Raises:
        ConfigurationError: If required configuration values are missing.

    Example:
        >>> config = get_config()  # doctest: +SKIP
        >>> fo_config = load_finanzonline_config(config)  # doctest: +SKIP
    """
    # Validate config at boundary using Pydantic schema
    schema = validate_config(config)
    fo_section = schema.finanzonline

    # Required credentials (typed access from schema)
    tid = fo_section.tid
    benid = fo_section.benid
    pin = fo_section.pin
    herstellerid = fo_section.herstellerid

    # Validate required fields
    missing: list[str] = []
    if not tid:
        missing.append("finanzonline.tid")
    if not benid:
        missing.append("finanzonline.benid")
    if not pin:
        missing.append("finanzonline.pin")
    if not herstellerid:
        missing.append("finanzonline.herstellerid")

    if missing:
        raise ConfigurationError(f"Missing required FinanzOnline configuration: {', '.join(missing)}. Configure via config file or environment variables.")

    # Create credentials (validation happens in __post_init__)
    try:
        credentials = FinanzOnlineCredentials(
            tid=tid,
            benid=benid,
            pin=pin,
            herstellerid=herstellerid,
        )
    except ValueError as e:
        raise ConfigurationError(f"Invalid credentials: {e}") from e

    # Optional settings with defaults (already validated by Pydantic)
    session_timeout = fo_section.session_timeout
    query_timeout = fo_section.query_timeout

    # Recipients are already validated as list[str] by Pydantic
    default_recipients = fo_section.default_recipients
    document_recipients = fo_section.document_recipients

    # Parse email_format - defaults to "html"
    email_format = _parse_email_format(fo_section.email_format, EmailFormat.HTML)

    # Parse output_dir - default output directory for downloaded files
    # Normalize path separators to allow Linux-style paths on Windows (e.g., UNC paths)
    output_dir_raw = fo_section.output_dir
    output_dir: Path | None = None
    if output_dir_raw and output_dir_raw.strip():
        normalized_path = _normalize_path_string(output_dir_raw.strip())
        output_dir = Path(normalized_path).expanduser()

    return FinanzOnlineConfig(
        credentials=credentials,
        session_timeout=session_timeout,
        query_timeout=query_timeout,
        default_recipients=default_recipients if default_recipients else None,
        document_recipients=document_recipients if document_recipients else None,
        email_format=email_format,
        output_dir=output_dir,
    )


__all__ = [
    "AppConfig",
    "FinanzOnlineConfig",
    "get_config",
    "get_default_config_path",
    "load_app_config",
    "load_finanzonline_config",
    "parse_string_list",
    "validate_config",
]
