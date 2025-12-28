# Configuration

This document describes all configuration options for `finanzonline_databox`.

## Configuration Methods

Configuration can be provided through multiple sources. Later sources override earlier ones:

| Priority | Source      | Description                               |
|----------|-------------|-------------------------------------------|
| 1        | defaults    | Bundled `defaultconfig.toml`              |
| 2        | app         | System-wide application config            |
| 3        | host        | Host-specific config                      |
| 4        | user        | User-specific config                      |
| 5        | .env        | Environment file in current/parent dirs   |
| 6        | env vars    | Environment variables (highest priority)  |

**Environment Variable Naming:**

```bash
# .env file format (no prefix needed)
SECTION__KEY=value

# Shell environment variable format (requires prefix)
FINANZONLINE_DATABOX___SECTION__KEY=value
```

**Configuration File Locations:**

| Target | Linux                                             | macOS                                                          | Windows                                        |
|--------|---------------------------------------------------|----------------------------------------------------------------|------------------------------------------------|
| `user` | `~/.config/finanzonline-databox/`                 | `~/Library/Application Support/bitranox/FinanzOnline DataBox/` | `%APPDATA%\bitranox\FinanzOnline DataBox\`     |
| `app`  | `/etc/xdg/finanzonline-databox/`                  | `/Library/Application Support/bitranox/FinanzOnline DataBox/`  | `%PROGRAMDATA%\bitranox\FinanzOnline DataBox\` |
| `host` | `/etc/finanzonline-databox/hosts/{hostname}.toml` | Same as app                                                    | Same as app                                    |

**Configuration Directory Structure:**

Each configuration directory supports a `config.d/` subdirectory for modular configuration fragments:

```
~/.config/finanzonline-databox/           # User config directory (Linux)
├── config.toml                           # Main configuration file
└── config.d/                             # Fragment directory (loaded in sort order)
    ├── 20-email.toml                     # Email settings
    └── 30-logging.toml                   # Logging settings
```

Fragment files are loaded in alphabetical/numeric order and **deeply merged** with the main config. Use numeric prefixes (e.g., `20-`, `30-`) to control load order. Later files override earlier ones.

**Deep Merge Advantage:**

Settings are deeply merged, so you can override specific values without duplicating entire sections. Create a high-numbered file like `99-myconfig.toml` for your customizations:

```toml
# config.d/99-myconfig.toml - Your personal overrides
[finanzonline]
tid = "123456789"
benid = "MYUSER"
pin = "secretpassword"
herstellerid = "ATU12345678"
default_recipients = ["me@example.com"]

[email]
smtp_hosts = ["smtp.mycompany.com:587"]
```

This pattern ensures painless updates - when default configurations (`20-email.toml`, `30-logging.toml`) are updated with new features, your customizations in `99-myconfig.toml` remain intact and override only the specific values you've set.

**Default Fragments (bundled with package):**

| File              | Contents                    |
|-------------------|-----------------------------|
| `20-email.toml`   | SMTP and email settings     |
| `30-logging.toml` | lib_log_rich logging config |

---

## Language Settings

All user-facing messages, CLI output, and email notifications can be displayed in multiple languages.

| Key            | Type  | Default | Description                                      |
|----------------|-------|---------|--------------------------------------------------|
| `app.language` | `str` | `"en"`  | Language code for messages and email content     |

**Supported Languages:**

| Code | Language          |
|------|-------------------|
| `en` | English (default) |
| `de` | German (Deutsch)  |
| `es` | Spanish (Español) |
| `fr` | French (Français) |
| `ru` | Russian (Русский) |

**What gets translated:**
- CLI output (status messages, error messages, prompts)
- Email notifications (subject lines, body content, labels)
- BMF return code descriptions
- All user-facing labels and messages
- Additional languages on request

**Configuration examples:**

```toml
# config.toml
[app]
language = "de"
```

```bash
# .env file
APP__LANGUAGE=de
```

---

## FinanzOnline Settings

Authentication credentials for the FinanzOnline web service.

| Key                               | Type        | Default  | Description                                   |
|-----------------------------------|-------------|----------|-----------------------------------------------|
| `finanzonline.tid`                | `str`       | Required | Participant ID (8-12 alphanumeric)            |
| `finanzonline.benid`              | `str`       | Required | User ID (5-12 chars, must be webservice user) |
| `finanzonline.pin`                | `str`       | Required | Password (5-128 chars)                        |
| `finanzonline.herstellerid`       | `str`       | Required | Software producer VAT-ID (10-24 alphanumeric) |
| `finanzonline.session_timeout`    | `float`     | `30.0`   | Session timeout in seconds                    |
| `finanzonline.query_timeout`      | `float`     | `30.0`   | Query/download timeout in seconds             |
| `finanzonline.output_dir`         | `str`       | `""`     | Default output directory (supports ~ for home)|
| `finanzonline.default_recipients` | `list[str]` | `[]`     | Default email recipients for notifications    |
| `finanzonline.document_recipients`| `list[str]` | `[]`     | Recipients for per-document email attachments |
| `finanzonline.email_format`       | `str`       | `"both"` | Email format: `html`, `plain`, or `both`      |

**.env example:**
```bash
FINANZONLINE__TID=123456789
FINANZONLINE__BENID=WEBUSER
FINANZONLINE__PIN=secretpassword
FINANZONLINE__HERSTELLERID=ATU12345678
FINANZONLINE__SESSION_TIMEOUT=60.0
FINANZONLINE__OUTPUT_DIR=~/Documents/FinanzOnline/DataBox
FINANZONLINE__DEFAULT_RECIPIENTS=["admin@example.com"]
```

**Note on output_dir:**
- When set, this becomes the default directory for `sync` and `download`
- Can be overridden with the `--output` CLI option
- Supports `~` for home directory expansion
- When empty, `sync` uses `./databox` and `download` uses the current directory

---

## Rate Limiting Settings

Built-in rate limit tracking warns when API usage approaches limits. This is a local safeguard - the actual rate limiting is enforced by the BMF servers.

| Key                              | Type    | Default           | Description                                        |
|----------------------------------|---------|-------------------|----------------------------------------------------|
| `finanzonline.ratelimit_queries` | `int`   | `50`              | Max queries in time window (0 = tracking disabled) |
| `finanzonline.ratelimit_hours`   | `float` | `24.0`            | Sliding window duration in hours                   |
| `finanzonline.ratelimit_file`    | `str`   | Platform-specific | Path to rate limit tracking JSON file              |

**Default rate limit file locations:**
- Linux: `~/.cache/finanzonline-databox/rate_limits.json`
- macOS: `~/Library/Caches/finanzonline-databox/rate_limits.json`
- Windows: `%LOCALAPPDATA%/finanzonline-databox/rate_limits.json`

**Behavior when limit exceeded:**
- Logs a warning message
- Sends an email notification
- **Query still proceeds** - BMF handles actual enforcement

**Notes:**
- Both successful and failed API calls are tracked
- Uses file locking for safe concurrent access

**.env example:**
```bash
FINANZONLINE__RATELIMIT_QUERIES=50
FINANZONLINE__RATELIMIT_HOURS=24.0
FINANZONLINE__RATELIMIT_FILE=/shared/network/rate_limits.json
```

---

## Email Settings

SMTP configuration for sending notification emails.

| Key                        | Type          | Default               | Description                   |
|----------------------------|---------------|-----------------------|-------------------------------|
| `email.smtp_hosts`         | `list[str]`   | `[]`                  | SMTP servers (tried in order) |
| `email.from_address`       | `str`         | `"noreply@localhost"` | Sender address                |
| `email.smtp_username`      | `str \| None` | `None`                | SMTP username                 |
| `email.smtp_password`      | `str \| None` | `None`                | SMTP password                 |
| `email.use_starttls`       | `bool`        | `True`                | Enable STARTTLS               |
| `email.timeout`            | `float`       | `30.0`                | Connection timeout            |
| `email.default_recipients` | `list[str]`   | `[]`                  | Default recipients            |

**.env example:**
```bash
EMAIL__SMTP_HOSTS=["smtp.gmail.com:587"]
EMAIL__FROM_ADDRESS=alerts@example.com
EMAIL__SMTP_USERNAME=user@gmail.com
EMAIL__SMTP_PASSWORD=app-password
EMAIL__USE_STARTTLS=true
EMAIL__TIMEOUT=60.0
EMAIL__DEFAULT_RECIPIENTS=["admin@example.com"]
```

---

## Logging Settings

All logging settings use lib_layered_config naming:

| Key                                  | Type  | Default      | Description                              |
|--------------------------------------|-------|--------------|------------------------------------------|
| `lib_log_rich.console_level`         | `str` | `"INFO"`     | Console log level                        |
| `lib_log_rich.console_format_preset` | `str` | `"full"`     | Format: full, short, full_loc, short_loc |
| `lib_log_rich.service`               | `str` | Package name | Service name in logs                     |
| `lib_log_rich.environment`           | `str` | `"prod"`     | Environment label                        |

**.env example:**
```bash
LIB_LOG_RICH__CONSOLE_LEVEL=DEBUG
LIB_LOG_RICH__CONSOLE_FORMAT_PRESET=short
```
