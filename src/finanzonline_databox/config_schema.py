"""Pydantic schema models for configuration validation.

Purpose
-------
Provide type-safe validation of configuration dictionaries at the boundary
where untyped config data (from lib_layered_config) enters the application.

Contents
--------
* :class:`AppConfigSchema` - Application settings section
* :class:`FinanzOnlineConfigSchema` - FinanzOnline credentials section
* :class:`EmailConfigSchema` - Email notification settings section
* :class:`ConfigSchema` - Root config schema containing all sections

System Role
-----------
Adapters layer - validates raw config dicts into typed Pydantic models.
Replaces unsafe `cast()` operations with proper Pydantic validation.

Note on Lenient Parsing
-----------------------
These schemas are designed to be lenient - invalid values fall back to defaults
rather than raising validation errors. This matches the previous behavior where
config loading was forgiving of malformed values.

JSON strings (e.g., '["item1", "item2"]') from .env files are automatically
parsed into lists.

Examples
--------
>>> raw_config = {"app": {"language": "de"}, "finanzonline": {"tid": "123"}}
>>> schema = ConfigSchema.model_validate(raw_config)
>>> schema.app.language
'de'
"""

from __future__ import annotations

import json
from typing import Any, cast

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _parse_string_list(value: Any) -> list[str]:
    """Parse a value into a list of strings.

    Handles JSON strings from .env files (e.g., '["item1", "item2"]').
    Invalid values return empty list.
    """
    if isinstance(value, list):
        items = cast(list[object], value)
        return [str(item) for item in items if item]

    if isinstance(value, str) and value.startswith("["):
        try:
            parsed: object = json.loads(value)
            if isinstance(parsed, list):
                parsed_items = cast(list[object], parsed)
                return [str(item) for item in parsed_items if item]
        except json.JSONDecodeError:
            pass

    return []


def _parse_float_lenient(value: Any, default: float) -> float:
    """Parse a float value with fallback to default."""
    if isinstance(value, (int, float)):
        return float(value)
    return default


def _parse_bool_lenient(value: Any, default: bool) -> bool:
    """Parse a boolean value with fallback to default."""
    if isinstance(value, bool):
        return value
    return default


class AppConfigSchema(BaseModel):
    """Schema for [app] configuration section.

    Attributes:
        language: Language code for user-facing messages.
    """

    model_config = ConfigDict(extra="ignore")

    language: str = Field(default="en", description="Language for messages (en, de, es, fr, ru)")


class FinanzOnlineConfigSchema(BaseModel):
    """Schema for [finanzonline] configuration section.

    Attributes:
        tid: Participant ID (Teilnehmer-ID).
        benid: User ID (Benutzer-ID).
        pin: Password/PIN.
        herstellerid: VAT-ID of software producer.
        session_timeout: Timeout for session operations in seconds.
        query_timeout: Timeout for query operations in seconds.
        default_recipients: Default email recipients for sync summaries.
        document_recipients: Default recipients for per-document notifications.
        email_format: Email body format (html, plain, both).
        output_dir: Default output directory for downloads.
    """

    model_config = ConfigDict(extra="ignore")

    tid: str = Field(default="", description="Participant ID")
    benid: str = Field(default="", description="User ID")
    pin: str = Field(default="", description="Password/PIN")
    herstellerid: str = Field(default="", description="VAT-ID of software producer")
    session_timeout: float = Field(default=30.0, description="Session timeout in seconds")
    query_timeout: float = Field(default=30.0, description="Query timeout in seconds")
    default_recipients: list[str] = Field(default_factory=list, description="Default email recipients")
    document_recipients: list[str] = Field(default_factory=list, description="Document notification recipients")
    email_format: str = Field(default="html", description="Email format: html, plain, or both")
    output_dir: str = Field(default="", description="Default output directory")

    @field_validator("session_timeout", "query_timeout", mode="before")
    @classmethod
    def parse_timeout(cls, v: Any) -> float:
        """Parse timeout with lenient fallback to default."""
        return _parse_float_lenient(v, 30.0)

    @field_validator("default_recipients", "document_recipients", mode="before")
    @classmethod
    def parse_recipients(cls, v: Any) -> list[str]:
        """Parse recipients list, handling JSON strings from .env files."""
        return _parse_string_list(v)


class EmailConfigSchema(BaseModel):
    """Schema for [email] configuration section.

    Attributes:
        smtp_hosts: List of SMTP hosts (host:port format).
        from_address: Sender email address.
        smtp_username: Optional SMTP authentication username.
        smtp_password: Optional SMTP authentication password.
        use_starttls: Whether to use STARTTLS.
        timeout: SMTP connection timeout in seconds.
        raise_on_missing_attachments: Raise error if attachment file missing.
        raise_on_invalid_recipient: Raise error on invalid recipient.
        default_recipients: Default email recipients.
    """

    model_config = ConfigDict(extra="ignore")

    smtp_hosts: list[str] = Field(default_factory=list, description="SMTP hosts (host:port)")
    from_address: str = Field(default="noreply@localhost", description="Sender address")
    smtp_username: str | None = Field(default=None, description="SMTP username")
    smtp_password: str | None = Field(default=None, description="SMTP password")
    use_starttls: bool = Field(default=True, description="Use STARTTLS")
    timeout: float = Field(default=30.0, description="Connection timeout")
    raise_on_missing_attachments: bool = Field(default=True, description="Error on missing attachments")
    raise_on_invalid_recipient: bool = Field(default=True, description="Error on invalid recipient")
    default_recipients: list[str] = Field(default_factory=list, description="Default recipients")

    @field_validator("smtp_hosts", "default_recipients", mode="before")
    @classmethod
    def parse_list_fields(cls, v: Any) -> list[str]:
        """Parse list fields, handling JSON strings from .env files."""
        return _parse_string_list(v)

    @field_validator("timeout", mode="before")
    @classmethod
    def parse_timeout(cls, v: Any) -> float:
        """Parse timeout with lenient fallback to default."""
        return _parse_float_lenient(v, 30.0)

    @field_validator("use_starttls", "raise_on_missing_attachments", "raise_on_invalid_recipient", mode="before")
    @classmethod
    def parse_bool_fields(cls, v: Any, info: Any) -> bool:
        """Parse boolean fields with lenient fallback to default."""
        defaults = {
            "use_starttls": True,
            "raise_on_missing_attachments": True,
            "raise_on_invalid_recipient": True,
        }
        return _parse_bool_lenient(v, defaults.get(info.field_name, True))


class LibLogRichConfigSchema(BaseModel):
    """Schema for [lib_log_rich] configuration section.

    Accepts any fields since lib_log_rich has its own validation.
    """

    model_config = ConfigDict(extra="allow")


class ConfigSchema(BaseModel):
    """Root schema for complete configuration.

    Validates the full config dict from lib_layered_config.as_dict().
    Unknown sections are ignored (extra="ignore").

    Attributes:
        app: Application settings.
        finanzonline: FinanzOnline credentials and settings.
        email: Email notification settings.
        lib_log_rich: Logging configuration (passed through).
    """

    model_config = ConfigDict(extra="ignore")

    app: AppConfigSchema = Field(default_factory=AppConfigSchema)
    finanzonline: FinanzOnlineConfigSchema = Field(default_factory=FinanzOnlineConfigSchema)
    email: EmailConfigSchema = Field(default_factory=EmailConfigSchema)
    lib_log_rich: LibLogRichConfigSchema = Field(default_factory=LibLogRichConfigSchema)


__all__ = [
    "AppConfigSchema",
    "ConfigSchema",
    "EmailConfigSchema",
    "FinanzOnlineConfigSchema",
    "LibLogRichConfigSchema",
]
