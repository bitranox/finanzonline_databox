"""Internationalization support using gettext.

Purpose:
    Provide multi-language support for user-facing messages using Python's
    built-in gettext module. Supports English (default), German, Spanish,
    French, and Russian.

Contents:
    * :class:`Language` - Enum of supported languages
    * :func:`setup_locale` - Initialize translations for a language
    * :func:`_` - Translate a message string
    * :func:`get_current_language` - Get the currently active language

System Role:
    Infrastructure module providing i18n capabilities. Called early in
    application initialization to configure translations before any
    user-facing output is generated.

Examples:
    >>> setup_locale(Language.GERMAN)
    >>> _("Show full Python traceback on errors")
    'Vollständige Python-Fehlerrückverfolgung bei Fehlern anzeigen'
"""

from __future__ import annotations

import gettext
import logging
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)


class Language(str, Enum):
    """Supported languages for i18n.

    Extends str so values can be used directly as language codes.

    Attributes:
        ENGLISH: English (en) - default/source language.
        GERMAN: German (de).
        SPANISH: Spanish (es).
        FRENCH: French (fr).
        RUSSIAN: Russian (ru).
    """

    ENGLISH = "en"
    GERMAN = "de"
    SPANISH = "es"
    FRENCH = "fr"
    RUSSIAN = "ru"

    @classmethod
    def from_string(cls, value: str) -> Language:
        """Parse language code string to enum.

        Args:
            value: Language code (e.g., "en", "de", "DE", "german").

        Returns:
            Matching Language enum member, or ENGLISH for invalid values.
        """
        normalized = value.lower().strip()
        for member in cls:
            if member.value == normalized:
                return member
        return cls.ENGLISH

    @classmethod
    def is_supported(cls, value: str) -> bool:
        """Check if a language code is supported.

        Args:
            value: Language code to check.

        Returns:
            True if the language is supported, False otherwise.
        """
        normalized = value.lower().strip()
        return any(member.value == normalized for member in cls)


DEFAULT_LANGUAGE = Language.ENGLISH

# Module-level state for current translation
_current_translation: gettext.GNUTranslations | gettext.NullTranslations | None = None
_current_language: Language = DEFAULT_LANGUAGE


def _get_locale_dir() -> Path:
    """Return the path to the locales directory."""
    return Path(__file__).parent / "locales"


def setup_locale(language: Language | str = DEFAULT_LANGUAGE) -> None:
    """Initialize gettext with the specified language.

    Args:
        language: Language enum or code string (en, de, es, fr, ru).
                  Defaults to English. If the language is not supported
                  or translation files are missing, falls back to English.

    Side Effects:
        Sets the module-level translation object used by _() function.
        Logs a debug message indicating the active language.
    """
    global _current_translation, _current_language

    # Convert string to Language enum if needed
    lang: Language
    if isinstance(language, Language):
        lang = language
    else:
        if not Language.is_supported(language):
            logger.warning(
                "Unsupported language '%s', falling back to '%s'",
                language,
                DEFAULT_LANGUAGE.value,
            )
            lang = DEFAULT_LANGUAGE
        else:
            lang = Language.from_string(language)

    _current_language = lang

    # English is the source language, no translation needed
    if lang == Language.ENGLISH:
        _current_translation = gettext.NullTranslations()
        logger.debug("Locale initialized: en (source language)")
        return

    # Try to load translation for the requested language
    locale_dir = _get_locale_dir()
    try:
        _current_translation = gettext.translation(
            "messages",
            localedir=str(locale_dir),
            languages=[lang.value],
        )
        logger.debug("Locale initialized: %s", lang.value)
    except FileNotFoundError:
        logger.warning(
            "Translation files not found for '%s', falling back to '%s'",
            lang.value,
            DEFAULT_LANGUAGE.value,
        )
        _current_translation = gettext.NullTranslations()
        _current_language = DEFAULT_LANGUAGE


def _(message: str) -> str:
    """Translate a message string.

    Args:
        message: The message to translate (in English).

    Returns:
        Translated message if available, otherwise the original message.

    Examples:
        >>> from finanzonline_databox.i18n import setup_locale, _
        >>> setup_locale("en")
        >>> _("UID is valid")
        'UID is valid'
    """
    if _current_translation is None:
        return message
    return _current_translation.gettext(message)


def N_(message: str) -> str:  # noqa: N802 - Standard gettext convention
    """Mark a string for translation extraction without translating.

    Use this for strings that are defined at module level (like dictionary
    values) but translated at runtime via _().

    Args:
        message: The message to mark for extraction.

    Returns:
        The original message unchanged.

    Examples:
        >>> N_("UID is valid")
        'UID is valid'
    """
    return message


def get_current_language() -> Language:
    """Return the currently active language.

    Returns:
        The Language enum member for the active language.
    """
    return _current_language


__all__ = [
    "DEFAULT_LANGUAGE",
    "Language",
    "N_",
    "_",
    "get_current_language",
    "setup_locale",
]
