# Changelog

All notable changes to this project will be documented in this file following
the [Keep a Changelog](https://keepachangelog.com/) format.



## [1.0.1] - 2025-12-28

### Fixed

- Fixed `config-deploy --force` showing misleading "Use --force" message when files already have identical content. Now shows "All configuration files are already up to date" instead.
- Fixed Windows CI test failure in `test_output_dir_expands_tilde` - path comparison now uses `Path.name` and `Path.parent.name` instead of string with forward slashes.
- Fixed `_parse_date()` in databox_client to correctly extract date from datetime objects (datetime is a subclass of date, so order of isinstance checks matters).
- Fixed `isinstance()` checks in `_check_session_valid()` by moving `DataboxListRequest` and `DataboxDownloadRequest` imports out of `TYPE_CHECKING` block.

## [1.0.0] - 2025-12-27

Initial release
