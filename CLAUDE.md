# Claude Code Guidelines for finanzonline_databox

## Project Overview

`finanzonline_databox` is a Python library and CLI for **automated retrieval of documents from the Austrian FinanzOnline DataBox**. It lists, downloads, and syncs tax documents (Bescheide, Mitteilungen, etc.) from the BMF DataBox Download web service. It follows Clean Architecture principles with clear separation between domain, application, and adapter layers.

## Project Structure

```
finanzonline_databox/
├── .github/workflows/          # GitHub Actions CI/CD workflows
├── .devcontainer/              # Dev container configuration
├── docs/
│   ├── prd/                    # Product requirements (WSDL, XSD specs)
│   └── systemdesign/           # System design documents
├── notebooks/                  # Jupyter notebooks for experiments
├── src/finanzonline_databox/      # Main Python package
│   ├── adapters/              # Infrastructure adapters (Clean Architecture)
│   │   ├── finanzonline/      # FinanzOnline SOAP clients
│   │   │   ├── session_client.py   # Login/logout handling
│   │   │   └── databox_client.py   # DataBox list/download operations
│   │   ├── notification/      # Email notification adapter
│   │   ├── output/            # Output formatters (human, JSON)
│   │   └── ratelimit/         # API rate limit tracking
│   ├── application/           # Use cases (Clean Architecture)
│   │   ├── ports.py           # Abstract interfaces (SessionPort, DataboxPort)
│   │   └── use_cases.py       # ListDataboxUseCase, DownloadEntryUseCase, SyncDataboxUseCase
│   ├── domain/                # Domain models (Clean Architecture)
│   │   ├── errors.py          # Domain exceptions (DataboxError, SessionError, etc.)
│   │   ├── models.py          # FinanzOnlineCredentials, DataboxEntry, DataboxListResult, etc.
│   │   └── return_codes.py    # BMF DataBox return code definitions
│   ├── defaultconfig.d/       # Layered config fragments
│   ├── __init__.py            # Package initialization
│   ├── __init__conf__.py      # Generated metadata constants
│   ├── __main__.py            # CLI entry point
│   ├── cli.py                 # CLI implementation (rich-click)
│   ├── config.py              # Configuration loading
│   ├── config_schema.py       # Pydantic config validation schemas
│   ├── mail.py                # Email utilities
│   └── py.typed               # PEP 561 marker
├── tests/                     # Test suite (mirrors src structure)
├── .env.example               # Example environment variables
├── CLAUDE.md                  # Claude Code guidelines (this file)
├── CHANGELOG.md               # Version history
├── CONTRIBUTING.md            # Contribution guidelines
├── DEVELOPMENT.md             # Development setup guide
├── INSTALL_en.md              # Installation instructions (English)
├── INSTALL_de.md              # Installation instructions (German)
├── Makefile                   # Make targets for common tasks
├── pyproject.toml             # Project metadata & dependencies
└── README.md                  # Project overview (German)
```

## Versioning & Releases

- **Single Source of Truth**: Package version is in `pyproject.toml` (`[project].version`)
- **Version Bumps**: update `pyproject.toml` , `CHANGELOG.md` and update the constants in `src/../__init__conf__.py` according to `pyproject.toml`
    - Automation rewrites `src/finanzonline_databox/__init__conf__.py` from `pyproject.toml`, so runtime code imports generated constants instead of querying `importlib.metadata`.
    - After updating project metadata (version, summary, URLs, authors) run `make test` (or `python -m scripts.test`) to regenerate the metadata module before committing.
- **Release Tags**: Format is `vX.Y.Z` (push tags for CI to build and publish)

## Make targets specific to this repo

- `make run` - Run module entry (`python -m ... --help`)

Everything else is the generated bmk list: run `make help`.

## Architecture Overview

use skill `bitranox:coding-python-clean-architecture` when designing and implementing features.

## Security & Configuration specific to this repo

- `.env` files are for local tooling only (CodeCov tokens, FinanzOnline credentials for testing)
- **NEVER** commit secrets to version control
- Rich logging should sanitize payloads before rendering
- FinanzOnline credentials (`tid`, `benid`, `pin`) are sensitive - never log them

## CLI Commands

| Command         | Description                                  |
|-----------------|----------------------------------------------|
| `list`          | List DataBox documents with optional filters |
| `download`      | Download a single document by applkey        |
| `sync`          | Sync all new documents to a local directory  |
| `config`        | Display current configuration                |
| `config-deploy` | Deploy configuration files to user/app/host  |
| `info`          | Display package information                  |
| `hello`         | Test success path                            |
| `fail`          | Test error handling                          |

## Key Dependencies

- `lib_layered_config` - Layered configuration system (TOML + env vars)
- `lib_log_rich` - Rich structured logging
- `lib_cli_exit_tools` - CLI exit code and error handling
- `pydantic` - Config validation at boundaries
- `rich-click` - CLI framework with rich output
- `zeep` - SOAP client for FinanzOnline web services
- `filelock` - File locking for rate limit files
- `btx_lib_mail` - SMTP delivery for notification emails; its `Transport` port is the
  seam the mail tests inject a double into, so they never patch `smtplib`
- `orjson` - Fast JSON serialization

## Commit & Push Policy

### Pre-Push Requirements
- **Always run `make test` before pushing** to avoid lint/test breakage
- Ensure all tests pass and code is properly formatted

### Post-Push Monitoring
- Monitor GitHub Actions for errors after pushing
- Attempt to correct any CI/CD errors that appear

## Domain Models

Key domain models for the DataBox service:

- `FinanzOnlineCredentials` - Authentication (tid, benid, pin, herstellerid)
- `DataboxListRequest` - List filters (erltyp, ts_zust_von, ts_zust_bis)
- `DataboxEntry` - Document metadata (stnr, name, erltyp, applkey, status, etc.)
- `DataboxListResult` - List operation result
- `DataboxDownloadRequest` - Download request (applkey)
- `DataboxDownloadResult` - Downloaded content (bytes)
- `SyncResult` - Sync operation statistics (see below)

### SyncResult Fields

| Field              | Type              | Description                                               |
|--------------------|-------------------|-----------------------------------------------------------|
| `total_retrieved`  | `int`             | Raw count of entries returned by API before filtering     |
| `total_listed`     | `int`             | Entries after filtering (by read status, reference, etc.) |
| `unread_listed`    | `int`             | Number of unread entries in the filtered list             |
| `downloaded`       | `int`             | Number of entries successfully downloaded                 |
| `skipped`          | `int`             | Number of entries skipped (already exist locally)         |
| `failed`           | `int`             | Number of entries that failed to download                 |
| `total_bytes`      | `int`             | Total bytes downloaded                                    |
| `downloaded_files` | `tuple`           | Tuples of (DataboxEntry, Path) for each downloaded file   |
| `applied_filters`  | `tuple[str, ...]` | Names of filters applied (e.g., "Unread", "UID:123")      |

### Sync Statistics Output

The sync command displays statistics with aligned colons:

```
Statistics
------------------------------
Retrieved                  : 7
After Filter [Unread]      : 0
Downloaded                 : 0
Skipped (exists)           : 0
Failed                     : 0
Total Size                 : 0 B
```

- **Retrieved**: Total entries from API (`total_retrieved`)
- **After Filter [filters]**: Entries after filtering, shows applied filter names
- **Skipped (exists)**: Files skipped because they already exist locally

## DataBox Return Codes

| Code | Meaning                                              |
|------|------------------------------------------------------|
| `0`  | Success                                              |
| `-1` | Session invalid or expired                           |
| `-2` | System under maintenance (retryable)                 |
| `-3` | Technical error (retryable)                          |
| `-4` | Date parameters required (ts_zust_von/bis)           |
| `-5` | ts_zust_von too old (max 31 days in past)            |
| `-6` | Date range too wide (max 7 days between von and bis) |
