"""Behavioral tests for i18n module."""

from __future__ import annotations

import pytest

from finanzonline_databox.i18n import (
    DEFAULT_LANGUAGE,
    Language,
    N_,
    _,
    get_current_language,
    setup_locale,
)

pytestmark = pytest.mark.os_agnostic


class TestSetupLocale:
    """Tests for setup_locale function."""

    def test_english_is_default(self) -> None:
        """English is the default language."""
        setup_locale()
        assert get_current_language() == "en"

    def test_english_sets_language(self) -> None:
        """Setting English works."""
        setup_locale("en")
        assert get_current_language() == "en"

    def test_german_sets_language(self) -> None:
        """Setting German works."""
        setup_locale("de")
        assert get_current_language() == "de"

    def test_case_insensitive(self) -> None:
        """Language codes are case insensitive."""
        setup_locale("EN")
        assert get_current_language() == "en"

    def test_strips_whitespace(self) -> None:
        """Whitespace is stripped from language codes."""
        setup_locale("  en  ")
        assert get_current_language() == "en"

    def test_unsupported_falls_back_to_english(self) -> None:
        """Unsupported language falls back to English."""
        setup_locale("invalid")
        assert get_current_language() == "en"

    def test_is_supported_returns_true_for_valid(self) -> None:
        """Language.is_supported returns True for valid codes."""
        assert Language.is_supported("en") is True
        assert Language.is_supported("de") is True
        assert Language.is_supported("es") is True
        assert Language.is_supported("fr") is True
        assert Language.is_supported("ru") is True

    def test_is_supported_returns_false_for_invalid(self) -> None:
        """Language.is_supported returns False for invalid codes."""
        assert Language.is_supported("invalid") is False
        assert Language.is_supported("xx") is False


class TestTranslationFunction:
    """Tests for the _ translation function."""

    def test_returns_original_for_english(self) -> None:
        """Returns original message when using English."""
        setup_locale("en")
        result = _("Hello World")
        assert result == "Hello World"

    def test_returns_original_when_no_translation(self) -> None:
        """Returns original message when translation missing."""
        setup_locale("en")
        result = _("Some unique untranslated string")
        assert result == "Some unique untranslated string"


class TestNFunction:
    """Tests for the N_ marking function."""

    def test_returns_original_unchanged(self) -> None:
        """N_() returns the original string unchanged."""
        result = N_("Hello World")
        assert result == "Hello World"


class TestDefaultLanguage:
    """Tests for DEFAULT_LANGUAGE constant."""

    def test_default_is_english(self) -> None:
        """Default language is English."""
        assert DEFAULT_LANGUAGE == "en"


class TestLanguageEnum:
    """Tests for Language enum."""

    def test_language_values(self) -> None:
        """All language enum values match expected codes."""
        assert Language.ENGLISH.value == "en"
        assert Language.GERMAN.value == "de"
        assert Language.SPANISH.value == "es"
        assert Language.FRENCH.value == "fr"
        assert Language.RUSSIAN.value == "ru"

    def test_from_string_valid_languages(self) -> None:
        """from_string returns correct enum for valid codes."""
        assert Language.from_string("en") == Language.ENGLISH
        assert Language.from_string("de") == Language.GERMAN
        assert Language.from_string("DE") == Language.GERMAN  # case insensitive

    def test_from_string_invalid_language_returns_english(self) -> None:
        """from_string returns ENGLISH for invalid codes."""
        assert Language.from_string("invalid") == Language.ENGLISH
        assert Language.from_string("xx") == Language.ENGLISH

    def test_language_enum_is_string(self) -> None:
        """Language enum extends str, so it can be used as string."""
        assert isinstance(Language.ENGLISH, str)
        assert Language.ENGLISH == "en"

    def test_setup_locale_with_enum(self) -> None:
        """setup_locale accepts Language enum directly."""
        setup_locale(Language.GERMAN)
        assert get_current_language() == Language.GERMAN
