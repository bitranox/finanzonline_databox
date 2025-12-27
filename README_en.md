# finanzonline_databox

<!-- Badges -->
[![CI](https://github.com/bitranox/finanzonline_databox/actions/workflows/ci.yml/badge.svg)](https://github.com/bitranox/finanzonline_databox/actions/workflows/ci.yml)
[![CodeQL](https://github.com/bitranox/finanzonline_databox/actions/workflows/codeql.yml/badge.svg)](https://github.com/bitranox/finanzonline_databox/actions/workflows/codeql.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Open in Codespaces](https://img.shields.io/badge/Codespaces-Open-blue?logo=github&logoColor=white&style=flat-square)](https://codespaces.new/bitranox/finanzonline_databox?quickstart=1)
[![PyPI](https://img.shields.io/pypi/v/finanzonline_databox.svg)](https://pypi.org/project/finanzonline_databox/)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/finanzonline_databox.svg)](https://pypi.org/project/finanzonline_databox/)
[![Code Style: Ruff](https://img.shields.io/badge/Code%20Style-Ruff-46A3FF?logo=ruff&labelColor=000)](https://docs.astral.sh/ruff/)
[![codecov](https://codecov.io/gh/bitranox/finanzonline_databox/graph/badge.svg?token=UFBaUDIgRk)](https://codecov.io/gh/bitranox/finanzonline_databox)
[![Maintainability](https://qlty.sh/badges/041ba2c1-37d6-40bb-85a0-ec5a8a0aca0c/maintainability.svg)](https://qlty.sh/gh/bitranox/projects/finanzonline_databox)
[![Known Vulnerabilities](https://snyk.io/test/github/bitranox/finanzonline_databox/badge.svg)](https://snyk.io/test/github/bitranox/finanzonline_databox)
[![security: bandit](https://img.shields.io/badge/security-bandit-yellow.svg)](https://github.com/PyCQA/bandit)

> [Deutsche Version verfügbar (README.md)](README.md)

`finanzonline_databox` is a Python library and CLI for **automated retrieval of documents from the FinanzOnline DataBox**. Tax decisions, notifications, confirmations, and other tax-relevant documents are automatically downloaded and stored locally.

## Why finanzonline_databox?

Manually retrieving documents from the FinanzOnline DataBox requires logging in, navigating through menus, and downloading files one by one - tedious and impossible to automate. With `finanzonline_databox`:

- **No browser required** - runs entirely from the command line
- **Automatic download** - sync all new documents with a single command
- **Fully scriptable** - integrate into backup processes, archiving systems, or CI pipelines
- **Email notifications** - automatic notifications when new documents arrive
- **Rate limit protection** - built-in tracking to protect against API overload
- **Document type filters** - retrieve only specific document types (decisions, notifications, etc.)
- **FREE SOFTWARE** - this software is and always will be free of charge

**Features:**
- List all documents in the DataBox (with filters)
- Download individual documents by `applkey`
- Sync all new documents to a local directory
- **Up to 31 days lookback** - `list` and `sync` support up to 31 days of history
- CLI entry point styled with rich-click (rich output + click ergonomics)
- Automatic email notifications for new documents
- **Per-document emails** - each downloaded document as attachment to separate recipients
- **Multi-language support** - English, German, Spanish, French, Russian
- Human-readable and JSON output formats
- Rate limit tracking with warning emails
- Layered configuration system with lib_layered_config
- Rich structured logging with lib_log_rich

**Supported Document Types (erltyp):**
- `B` - Bescheide (Decisions/Decrees)
- `M` - Mitteilungen (Notifications)
- `I` - Informationen (Information)
- `P` - Protokolle (Protocols)
- `EU` - EU-Erledigungen (EU completions)
- and more...

**Examples:**
```bash
# List all unread documents (default)
finanzonline-databox list

# List only decisions (Bescheide)
finanzonline-databox list --erltyp B

# List all documents (up to 31 days)
finanzonline-databox list --all

# List only read documents (up to 31 days)
finanzonline-databox list --read

# List all documents from the last 3 days
finanzonline-databox list --days 3 --all

# Download a specific document
finanzonline-databox download abc123def456xyz --output ./downloads

# Sync all new documents (unread only, default)
finanzonline-databox sync --output ./databox-archive

# Sync all documents (both read and unread)
finanzonline-databox sync --output ./databox-archive --all

# Sync documents from the last 31 days
finanzonline-databox sync --days 31 --all

# Sync only protocols with reference UID
finanzonline-databox sync -t P -r UID

# Sync documents and send each as email attachment
finanzonline-databox sync --document-recipient archive@company.com

# UID confirmations to sales, all other documents to accounting
finanzonline-databox sync -r UID --document-recipient sales@company.com
finanzonline-databox sync --document-recipient accounting@company.com
```

---

## Document Retention Requirements (Aufbewahrungspflichten)

> **IMPORTANT:** Documents from the FinanzOnline DataBox must be retained according to § 132 BAO (Bundesabgabenordnung - Austrian Federal Tax Code).
>
> These documents serve as official documentation for tax audits and must be retained according to Austrian retention requirements (typically 7 years).

With `finanzonline_databox sync`, you can automatically download all documents to a local archive and fulfill your retention obligations.

---

## BMF Rate Limits

The FinanzOnline web service has rate limits. This tool includes built-in rate limit tracking (default: 50 queries per 24 hours) that:
- Warns you before you approach BMF limits
- Sends email notifications when exceeded
- Does NOT block queries - BMF handles actual enforcement

Configure via `finanzonline.ratelimit_queries` and `finanzonline.ratelimit_hours`.

### FinanzOnline Webservice User

> **IMPORTANT:** The user (BENID) must be configured as a **webservice user** in FinanzOnline user administration.
>
> Common errors:
> - `-1` = Session invalid or expired
> - `-2` = System under maintenance
> - `-3` = Technical error
> - `-4` = Date parameters required
> - `-5` = Date too old (max. 31 days)
> - `-6` = Date range too wide (max. 7 days)

---

## Table of Contents

- [Document Retention Requirements](#document-retention-requirements-aufbewahrungspflichten)
- [BMF Rate Limits](#bmf-rate-limits)
- [Quick Start](#quick-start)
- [Usage](#usage)
- [BMF Return Codes](#bmf-return-codes)
- [Further Documentation](#further-documentation)

---

## Quick Start

Your IT staff should be perfectly able to install this application easily. If you need support, you can contact the author for paid support.


### Recommended: Run via uvx to automatically get the latest version

UV - the ultrafast installer - written in Rust (10-20x faster than pip/poetry)

```bash
# Install Python (Requires >= **Python 3.10+**)
# Install UV
pip install --upgrade uv
# Create configuration files
uvx finanzonline_databox@latest config-deploy --target user
```

Create your personal config file in the `config.d/` directory (settings are deeply merged, so updates to default configs won't affect your settings):

```bash
# Linux:   ~/.config/finanzonline-databox/config.d/99-myconfig.toml
# macOS:   ~/Library/Application Support/bitranox/FinanzOnline DataBox/config.d/99-myconfig.toml
# Windows: %APPDATA%\bitranox\FinanzOnline DataBox\config.d\99-myconfig.toml
```

```toml
# 99-myconfig.toml - Your personal settings
[finanzonline]
tid = "123456789"           # Participant ID (Teilnehmer-ID)
benid = "WEBUSER"           # User ID (Benutzer-ID) - must be webservice user!
pin = "yourpassword"        # Password/PIN
herstellerid = "ATU12345678" # Software producer VAT-ID (put your Austrian UID)
output_dir = "~/Documents/FinanzOnline/DataBox"  # Default output directory
default_recipients = ["accounting@yourcompany.com"]  # Recipients for sync summary
document_recipients = ["archive@yourcompany.com"]  # Recipients for document attachments
email_format = "both"       # "html", "plain" or "both"

[email]
smtp_hosts = ["smtp.example.com:587"]
from_address = "databox@yourcompany.com"
```

```bash
# List all unread documents
uvx finanzonline_databox@latest list

# Download all new documents
uvx finanzonline_databox@latest sync --output ./archive
```

For alternative install paths (pip, pipx, uvx, source builds), see [INSTALL_en.md](INSTALL_en.md).

---

## Usage

```bash
# List all unread documents (default)
finanzonline-databox list

# List only decisions (Bescheide)
finanzonline-databox list --erltyp B

# List only protocols with reference UID
finanzonline-databox list -t P -r UID

# List documents from the last 31 days
finanzonline-databox list --days 31

# Show only unread documents from the last 7 days
finanzonline-databox list --days 7 --unread

# Show only read documents from the last 31 days
finanzonline-databox list --days 31 --read

# Show all documents from the last 31 days (both read and unread)
finanzonline-databox list --days 31 --all

# Download a specific document
finanzonline-databox download abc123def456xyz --output ./downloads

# Sync all new documents to a directory (unread only, default)
finanzonline-databox sync --output ./databox-archive

# Sync all documents (both read and unread)
finanzonline-databox sync --output ./databox-archive --all

# Sync only decisions
finanzonline-databox sync --output ./decisions --erltyp B

# Sync only protocols with reference UID
finanzonline-databox sync -t P -r UID

# Sync documents from the last 31 days
finanzonline-databox sync --days 31 --all

# Sync documents and send each as email attachment
finanzonline-databox sync --document-recipient archive@company.com

# JSON output for scripting
finanzonline-databox list --format json
```

Results are displayed and optionally an email with the results is sent to configured email addresses.

### Email Notifications

```bash
# Summary to default recipients (from configuration)
finanzonline-databox sync --output ./archive

# Summary to specific recipients
finanzonline-databox sync --recipient admin@company.com --recipient accounting@company.com

# Each document as email attachment to separate recipients
finanzonline-databox sync --document-recipient archive@company.com

# Combine both
finanzonline-databox sync --recipient admin@company.com --document-recipient archive@company.com
```

---

## BMF Return Codes

| Code | Meaning |
|------|---------|
| `0` | Success |
| `-1` | Session invalid or expired |
| `-2` | System under maintenance (retry later) |
| `-3` | Technical error (retry later) |
| `-4` | Date parameters required (ts_zust_von/bis) |
| `-5` | ts_zust_von too old (max. 31 days in the past) |
| `-6` | Date range too wide (max. 7 days between von and bis) |

---

## Further Documentation

- [Installation Guide (EN)](INSTALL_en.md) | [Installationsanleitung (DE)](INSTALL_de.md)
- [Configuration Reference (EN)](CONFIGURATION_en.md) | [Konfigurationsreferenz (DE)](CONFIGURATION_de.md)
- [CLI Reference (EN)](CLI_REFERENCE_en.md) | [CLI-Referenz (DE)](CLI_REFERENCE_de.md)
- [Python API Reference (EN)](API_REFERENCE_en.md) | [Python-API-Referenz (DE)](API_REFERENCE_de.md)
- [BMF Return Codes (EN)](RETURNCODES_en.md) | [BMF-Rückgabecodes (DE)](RETURNCODES_de.md)
- [Development Handbook](DEVELOPMENT.md)
- [Contributor Guide](CONTRIBUTING.md)
- [Changelog](CHANGELOG.md)
- [Module Reference](docs/systemdesign/module_reference.md)
- [License](LICENSE)
- **[Deutsche Dokumentation (README.md)](README.md)**
