# Claude Code Guidelines for finanzonline_databox

## Project Overview

`finanzonline_databox` is a Python library and CLI for **automated retrieval of documents from the Austrian FinanzOnline DataBox**. It lists, downloads, and syncs tax documents (Bescheide, Mitteilungen, etc.) from the BMF DataBox Download web service. It follows Clean Architecture principles with clear separation between domain, application, and adapter layers.

## Session Initialization

When starting a new session, read and apply the following system prompt files from `/media/srv-main-softdev/projects/softwarestack/systemprompts`:

### Core Guidelines (Always Apply)
- `core_programming_solid.md`

### Bash-Specific Guidelines
When working with Bash scripts:
- `core_programming_solid.md`
- `bash_clean_architecture.md`
- `bash_clean_code.md`
- `bash_small_functions.md`

### Python-Specific Guidelines
When working with Python code:
- `core_programming_solid.md`
- `python_solid_architecture_enforcer.md`
- `python_clean_architecture.md`
- `python_clean_code.md`
- `python_small_functions_style.md`
- `python_libraries_to_use.md`
- `python_structure_template.md`

### Additional Guidelines
- `self_documenting.md`
- `self_documenting_template.md`
- `python_jupyter_notebooks.md`
- `python_testing.md`

## Project Structure

```
finanzonline_databox/
├── .github/workflows/          # GitHub Actions CI/CD workflows
├── .devcontainer/              # Dev container configuration
├── docs/
│   ├── prd/                    # Product requirements (WSDL, XSD specs)
│   └── systemdesign/           # System design documents
├── notebooks/                  # Jupyter notebooks for experiments
├── scripts/                    # Build and automation scripts
│   ├── build.py               # Build wheel/sdist
│   ├── bump*.py               # Version bump scripts
│   ├── clean.py               # Clean build artifacts
│   ├── test.py                # Run tests with coverage
│   ├── push.py                # Git push automation
│   ├── release.py             # Create releases
│   ├── menu.py                # Interactive TUI menu
│   └── _utils.py              # Shared utilities
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

## Common Make Targets

| Target            | Description                                                                     |
|-------------------|---------------------------------------------------------------------------------|
| `build`           | Build wheel/sdist artifacts                                                     |
| `bump`            | Bump version (VERSION=X.Y.Z or PART=major\|minor\|patch) and update changelog  |
| `bump-major`      | Increment major version ((X+1).0.0)                                            |
| `bump-minor`      | Increment minor version (X.Y.Z -> X.(Y+1).0)                                    |
| `bump-patch`      | Increment patch version (X.Y.Z -> X.Y.(Z+1))                                    |
| `clean`           | Remove caches, coverage, and build artifacts (includes `dist/` and `build/`)   |
| `dev`             | Install package with dev extras                                                |
| `help`            | Show make targets                                                              |
| `install`         | Editable install                                                               |
| `menu`            | Interactive TUI menu                                                           |
| `push`            | Commit changes and push to GitHub (no CI monitoring)                           |
| `release`         | Tag vX.Y.Z, push, sync packaging, run gh release if available                  |
| `run`             | Run module entry (`python -m ... --help`)                                      |
| `test`            | Lint, format, type-check, run tests with coverage, upload to Codecov           |
| `version-current` | Print current version from `pyproject.toml`                                    |

## Coding Style & Naming Conventions

Follow the guidelines in `python_clean_code.md` for all Python code.

## Architecture Overview

Apply principles from `python_clean_architecture.md` when designing and implementing features.

## Security & Configuration

- `.env` files are for local tooling only (CodeCov tokens, FinanzOnline credentials for testing)
- **NEVER** commit secrets to version control
- Rich logging should sanitize payloads before rendering
- FinanzOnline credentials (`tid`, `benid`, `pin`) are sensitive - never log them

## CLI Commands

| Command         | Description                                              |
|-----------------|----------------------------------------------------------|
| `list`          | List DataBox documents with optional filters             |
| `download`      | Download a single document by applkey                    |
| `sync`          | Sync all new documents to a local directory              |
| `config`        | Display current configuration                            |
| `config-deploy` | Deploy configuration files to user/app/host              |
| `info`          | Display package information                              |
| `hello`         | Test success path                                        |
| `fail`          | Test error handling                                      |

## Key Dependencies

- `lib_layered_config` - Layered configuration system (TOML + env vars)
- `lib_log_rich` - Rich structured logging
- `lib_cli_exit_tools` - CLI exit code and error handling
- `pydantic` - Config validation at boundaries
- `rich-click` - CLI framework with rich output
- `zeep` - SOAP client for FinanzOnline web services
- `filelock` - File locking for rate limit files

## Commit & Push Policy

### Pre-Push Requirements
- **Always run `make test` before pushing** to avoid lint/test breakage
- Ensure all tests pass and code is properly formatted

### Post-Push Monitoring
- Monitor GitHub Actions for errors after pushing
- Attempt to correct any CI/CD errors that appear

## Claude Code Workflow

When working on this project:
1. Read relevant system prompts at session start
2. Apply appropriate coding guidelines based on file type
3. Run `make test` before commits
4. Follow versioning guidelines for releases
5. Monitor CI after pushing changes

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

| Field | Type | Description |
|-------|------|-------------|
| `total_retrieved` | `int` | Raw count of entries returned by API before filtering |
| `total_listed` | `int` | Entries after filtering (by read status, reference, etc.) |
| `unread_listed` | `int` | Number of unread entries in the filtered list |
| `downloaded` | `int` | Number of entries successfully downloaded |
| `skipped` | `int` | Number of entries skipped (already exist locally) |
| `failed` | `int` | Number of entries that failed to download |
| `total_bytes` | `int` | Total bytes downloaded |
| `downloaded_files` | `tuple` | Tuples of (DataboxEntry, Path) for each downloaded file |

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
