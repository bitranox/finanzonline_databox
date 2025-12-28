# Changelog

All notable changes to this project will be documented in this file following
the [Keep a Changelog](https://keepachangelog.com/) format.



## [1.2.0] - 2025-12-28

### Added

- Added Pydantic config schema models (`config_schema.py`) for type-safe configuration validation at boundaries
- Added lenient validators for JSON string parsing from .env files (handles `'["item1", "item2"]'` format)
- Added `validate_config()` function for config boundary validation
- Added `ErrorTypeInfo` dataclass for structured error type mapping in CLI
- Added `FilesystemErrorHint` dataclass replacing raw dict for filesystem error hints
- Added module-level validation for return code dict consistency

### Changed

- Changed `read_filter` parameter from `str` to `ReadFilter` enum in use cases and CLI
- Replaced magic number `-4` with `RC_DATE_PARAMS_REQUIRED` domain constant in session_client.py
- Updated config.py and mail.py to use Pydantic validation instead of unsafe `cast()` operations
- Documented enum serialization contract in formatters.py (`_entry_to_dict()`)

### Fixed

- Fixed string/enum type mismatch where `read_filter` was typed as `str` but compared against `ReadFilter` enum
- Fixed unsafe cast operations in config loading that could silently fail
- Fixed timeout not being applied to zeep SOAP clients - `_timeout` parameter is now passed to `Transport` in both `FinanzOnlineSessionClient` and `DataboxClient`
- Fixed implicit base64 error handling in `_decode_content()` - now catches `binascii.Error` and raises `DataboxOperationError` with full diagnostics

## [1.1.0] - 2025-12-28

### Added

- Added `FilesystemError` exception class with user-friendly error messages for filesystem operations (permission denied, disk full, read-only filesystem, path too long, etc.)
- Added `filesystem_error_from_oserror()` helper to convert `OSError` to localized `FilesystemError` with actionable hints
- Added filesystem error handling in `DownloadEntryUseCase` and `SyncDataboxUseCase` for `mkdir()` and `write_bytes()` operations
- Added CLI hints for filesystem errors (e.g., "Use --output to specify a different directory")
- Added translations for filesystem error messages in German, Spanish, French, and Russian

## [1.0.1] - 2025-12-28

### Fixed

- Fixed `config-deploy --force` showing misleading "Use --force" message when files already have identical content. Now shows "All configuration files are already up to date" instead.
- Fixed Windows CI test failure in `test_output_dir_expands_tilde` - path comparison now uses `Path.name` and `Path.parent.name` instead of string with forward slashes.
- Fixed `_parse_date()` in databox_client to correctly extract date from datetime objects (datetime is a subclass of date, so order of isinstance checks matters).
- Fixed `isinstance()` checks in `_check_session_valid()` by moving `DataboxListRequest` and `DataboxDownloadRequest` imports out of `TYPE_CHECKING` block.

## [1.0.0] - 2025-12-27

Initial release
