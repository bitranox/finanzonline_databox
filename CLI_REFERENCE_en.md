# CLI Reference

This document describes all CLI commands and options for `finanzonline_databox`.

## Global Options

These options apply to all commands:

| Option                         | Default          | Description                                                          |
|--------------------------------|------------------|----------------------------------------------------------------------|
| `--traceback / --no-traceback` | `--no-traceback` | Show full Python traceback on errors                                 |
| `--profile NAME`               | `None`           | Load configuration from a named profile (e.g., 'production', 'test') |
| `--version`                    | -                | Show version and exit                                                |
| `-h, --help`                   | -                | Show help and exit                                                   |

## Commands

The CLI command is registered under `finanzonline-databox` and `finanzonline_databox` - so you can use both.

---

### `list` - List DataBox Documents

```bash
finanzonline-databox list [OPTIONS]
```

Lists all documents in the FinanzOnline DataBox with optional filters.

**Options:**

| Option        | Short | Default    | Description                                                           |
|---------------|-------|------------|-----------------------------------------------------------------------|
| `--erltyp`    | `-t`  | `""`       | Document type filter: B, M, I, P, EU (empty = all)                    |
| `--reference` | `-r`  | `""`       | Reference filter (anbringen, e.g., UID, E1)                           |
| `--from`      | -     | `None`     | Start date filter (YYYY-MM-DD, max 31 days ago)                       |
| `--to`        | -     | `None`     | End date filter (YYYY-MM-DD, max 7 days after start)                  |
| `--days`      | `-d`  | `None`     | List documents from last N days (overrides --from/--to, max 31)       |
| `--unread`    | `-u`  | `--unread` | Show only unread documents **(default)**                              |
| `--read`      | -     | -          | Show only read documents                                              |
| `--all`       | `-a`  | -          | Show all documents (both read and unread)                             |
| `--format`    | -     | `human`    | Output format: `human` or `json`                                      |

> **Note:** The `--unread`, `--read`, and `--all` options are mutually exclusive. Default is `--unread`.
>
> **Auto-date range:** When using `--all` or `--read` without specifying `--days` or `--from/--to`, the CLI automatically uses `--days 31` because the BMF API only returns read documents when a date range is provided.
>
> **Implementation note:** The BMF API limits each request to a 7-day window. For ranges > 7 days, the CLI automatically splits the request into multiple chunks and aggregates results.

**API Constraints (BMF DataBox Webservice):**

| Constraint                       | Value                             |
|----------------------------------|-----------------------------------|
| `--from` (ts_zust_von)           | Max 31 days in the past           |
| `--to` - `--from` (date range)   | Max 7 days                        |
| Without date filter              | Only unread documents returned    |
| With date filter                 | Both read + unread documents      |

> **Note:** After downloading, a document is marked as "read" on the server and no longer appears in the default list.

**Document Types (erltyp):**

| Code | Description                      |
|------|----------------------------------|
| `B`  | Bescheide (Decisions/Decrees)    |
| `M`  | Mitteilungen (Notifications)     |
| `I`  | Informationen (Information)      |
| `P`  | Protokolle (Protocols)           |
| `EU` | EU-Erledigungen (EU completions) |

**Exit Codes:**

| Code | Meaning              |
|------|----------------------|
| 0    | Success              |
| 2    | Configuration error  |
| 3    | Authentication error |
| 4    | Operation error      |

**Examples:**

```bash
# List all unread documents (default)
finanzonline-databox list

# List only decisions (Bescheide)
finanzonline-databox list --erltyp B

# List only protocols with reference UID
finanzonline-databox list -t P -r UID

# List all documents (up to 31 days)
finanzonline-databox list --all

# List only read documents (up to 31 days)
finanzonline-databox list --read

# List documents from the last 31 days
finanzonline-databox list --days 31

# List all documents from the last 3 days
finanzonline-databox list --days 3 --all

# Custom date range (max 7 day span)
finanzonline-databox list --from 2024-12-01 --to 2024-12-07

# Fetch older documents (up to 31 days back)
finanzonline-databox list --from 2024-11-22 --to 2024-11-29

# JSON output for scripting
finanzonline-databox list --format json
```

---

### `download` - Download a Single Document

```bash
finanzonline-databox download [OPTIONS] APPLKEY
```

Downloads a specific document from the DataBox by its application key.

**Arguments:**

| Argument  | Required | Description                                    |
|-----------|----------|------------------------------------------------|
| `APPLKEY` | Yes      | Document application key (from `list` command) |

**Options:**

| Option       | Short | Default         | Description                              |
|--------------|-------|-----------------|------------------------------------------|
| `--output`   | `-o`  | `.` (current)   | Output directory (or from config `output_dir`) |
| `--filename` | `-f`  | Auto-generated  | Override output filename                 |

**Exit Codes:**

| Code | Meaning              |
|------|----------------------|
| 0    | Success              |
| 2    | Configuration error  |
| 3    | Authentication error |
| 4    | Operation error      |

**Examples:**

```bash
# Download with auto-generated filename
finanzonline-databox download abc123def456xyz

# Download to specific directory
finanzonline-databox download abc123def456xyz --output ./downloads

# Download with custom filename
finanzonline-databox download abc123def456xyz -f my_document.pdf
```

---

### `sync` - Sync All New Documents

```bash
finanzonline-databox sync [OPTIONS]
```

Synchronizes all documents to a local directory. Optionally sends email notifications on new downloads.

**Options:**

| Option                             | Short | Default           | Description                                     |
|------------------------------------|-------|-------------------|-------------------------------------------------|
| `--output`                         | `-o`  | `./databox`       | Directory to save downloaded documents          |
| `--erltyp`                         | `-t`  | `""`              | Document type filter: B, M, I, P, EU            |
| `--reference`                      | `-r`  | `""`              | Reference filter (anbringen, e.g., UID, E1)     |
| `--days`                           | -     | `31`              | Sync documents from the last N days (max 31)    |
| `--unread`                         | `-u`  | `--unread`        | Sync only unread documents **(default)**        |
| `--read`                           | -     | -                 | Sync only read documents                        |
| `--all`                            | `-a`  | -                 | Sync all documents (both read and unread)       |
| `--skip-existing/--no-skip-existing` | -   | `--skip-existing` | Skip files that already exist                   |
| `--no-email`                       | -     | `False`           | Disable email notification                      |
| `--recipient`                      | -     | Config default    | Email recipient for summary (can specify multiple)|
| `--document-recipient`             | -     | `[]`              | Email recipient for per-document emails with attachment |
| `--format`                         | -     | `human`           | Output format: `human` or `json`                |

> **Note:** The `--unread`, `--read`, and `--all` options are mutually exclusive. Default is `--unread`.
>
> **Implementation note:** The BMF API limits each request to a 7-day window. For ranges > 7 days, the CLI automatically splits the request into multiple chunks and aggregates results.
>
> **output_dir config:** When `finanzonline.output_dir` is set in the configuration, it's used as the default instead of `./databox`.

**Exit Codes:**

| Code | Meaning                        |
|------|--------------------------------|
| 0    | Success (all synced)           |
| 1    | Partial success (some failed)  |
| 2    | Configuration error            |
| 3    | Authentication error           |
| 4    | Operation error                |

**Examples:**

```bash
# Sync all unread documents to ./databox (default)
finanzonline-databox sync

# Sync to a specific directory
finanzonline-databox sync --output ./archive/databox

# Sync only decisions (Bescheide)
finanzonline-databox sync --erltyp B --output ./bescheide

# Sync only protocols with reference UID
finanzonline-databox sync -t P -r UID

# Sync documents from the last 7 days (unread only, default)
finanzonline-databox sync --days 7

# Sync documents from the last 7 days, read only
finanzonline-databox sync --days 7 --read

# Sync all documents from the last 7 days (both read and unread)
finanzonline-databox sync --days 7 --all

# Sync with JSON output (for scripting)
finanzonline-databox sync --format json --no-email

# With custom recipients
finanzonline-databox sync --recipient admin@example.com --recipient finance@example.com

# Sync documents from the last 31 days
finanzonline-databox sync --days 31 --all

# Send each document as email attachment to separate recipients
finanzonline-databox sync --document-recipient archive@example.com

# Combined: summary + per-document emails
finanzonline-databox sync --recipient admin@example.com --document-recipient archive@example.com

# Re-download existing files
finanzonline-databox sync --no-skip-existing
```

---

### `config` - Display Configuration

```bash
finanzonline-databox config [OPTIONS]
```

**Options:**

| Option      | Default | Description                                                                  |
|-------------|---------|------------------------------------------------------------------------------|
| `--format`  | `human` | Output format: `human` or `json`                                             |
| `--section` | `None`  | Show only a specific section (e.g., 'finanzonline', 'email', 'lib_log_rich') |
| `--profile` | `None`  | Override profile from root command                                           |

**Examples:**

```bash
# Show all configuration
finanzonline-databox config

# JSON output for scripting
finanzonline-databox config --format json

# Show only email section
finanzonline-databox config --section email

# Show production profile
finanzonline-databox config --profile production
```

---

### `config-deploy` - Deploy Configuration Files

```bash
finanzonline-databox config-deploy [OPTIONS]
```

**Options:**

| Option      | Required | Default | Description                                                   |
|-------------|----------|---------|---------------------------------------------------------------|
| `--target`  | Yes      | -       | Target layer: `user`, `app`, or `host` (can specify multiple) |
| `--force`   | No       | `False` | Overwrite existing configuration files                        |
| `--profile` | No       | `None`  | Deploy to a specific profile directory                        |

**Examples:**

```bash
# Deploy user configuration
finanzonline-databox config-deploy --target user

# Deploy system-wide (requires privileges)
sudo finanzonline-databox config-deploy --target app

# Deploy multiple targets
finanzonline-databox config-deploy --target user --target host

# Overwrite existing
finanzonline-databox config-deploy --target user --force

# Deploy to production profile
finanzonline-databox config-deploy --target user --profile production
```

---

### `info` - Display Package Information

```bash
finanzonline-databox info
```

Shows package name, version, homepage, author, and other metadata.

---

### `hello` - Test Success Path

```bash
finanzonline-databox hello
```

Emits a greeting message to verify the CLI is working.

---

### `fail` - Test Error Handling

```bash
finanzonline-databox fail
finanzonline-databox --traceback fail  # With full traceback
```

Triggers an intentional error to test error handling.
