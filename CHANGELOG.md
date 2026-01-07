# Changelog

All notable changes to this project will be documented in this file following
the [Keep a Changelog](https://keepachangelog.com/) format.



## [1.2.6] - 2026-01-07

### Added

- Added `total_retrieved` field to `SyncResult` to track raw API count before filtering

### Changed

- Sync log now shows date range: `Starting databox sync (2026-01-01 to 2026-01-07) to /path`
- Chunk progress now shows both raw API count and filtered count: `Chunk 1 (days 0-7): 5 from API, 3 after filter - 2 unread`
- `_sum_sync_stats()` and `_aggregate_sync_results()` now aggregate `total_retrieved` across chunks

## [1.2.5] - 2026-01-07

### Added

- Added `unread_listed` field to `SyncResult` dataclass to track unread entry count per sync operation
- Added chunk progress logging during sync: `Chunk N (days X-Y): Retrieved N entries - N unread`

### Changed

- Sync operations now display per-chunk progress with entry counts and unread status
- `_sum_sync_stats()` and `_aggregate_sync_results()` now aggregate unread counts across chunks

## [1.2.4] - 2026-01-07

### Changed

- Error emails now render the HTML server response as formatted content (readable maintenance message) in addition to showing the source code in a collapsible section
- Renamed i18n keys: "Server Response (HTML)" → "Server Message" and added "HTML Source Code" for the collapsible source section

## [1.2.3] - 2026-01-07

### Added

- Added `XMLSyntaxError` handling in SOAP clients to detect when FinanzOnline returns HTML instead of XML
- Added maintenance page detection: when HTML response contains `/wartung/`, error type is set to "DataBox in Wartung"
- Added HTML content display in error notification emails - server response is shown in a collapsible section
- Added `_is_maintenance_page()` and `_extract_xml_error_content()` helpers in databox_client.py and session_client.py

### Changed

- Error emails now include the full HTML server response in diagnostics when XML parsing fails
- Email subject shows "DataBox ERROR: sync - DataBox in Wartung" when maintenance page is detected
- Maintenance errors are now marked as retryable
- Diagnostic values in HTML emails are now properly HTML-escaped to prevent rendering issues

## [1.2.2] - 2025-12-28

### Added

- Added tests for `_normalize_path_string()` helper with Windows/Linux path conversion coverage

### Changed

- Updated `defaultconfig.toml` documentation with cross-platform path examples for UNC paths

## [1.2.1] - 2025-12-28

### Added

- Added cross-platform path support: forward slashes (Linux-style) now work on Windows for all path settings like `output_dir`. This is especially useful for UNC paths which would otherwise require escaped backslashes (e.g., `//server/share/folder` instead of `\\\\server\\share\\folder`).

### Changed

- Changed default email format from `both` to `html`

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
