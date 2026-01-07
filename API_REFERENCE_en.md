# Python API Reference

This document describes the Python API for `finanzonline_databox`.

## Public Exports

```python
import finanzonline_databox

# Package metadata
finanzonline_databox.__version__    # "0.0.1"
finanzonline_databox.__title__      # "Python library and CLI..."
finanzonline_databox.__author__     # "bitranox"
finanzonline_databox.__url__        # "https://github.com/bitranox/finanzonline_databox"
```

---

## Configuration

### `get_config()`

Load layered configuration from all sources.

```python
from finanzonline_databox.config import get_config

config = get_config()
# or with profile
config = get_config(profile="production")
# or with custom start directory for .env discovery
config = get_config(start_dir="/path/to/project")
```

**Parameters:**

| Parameter   | Type          | Default | Description                            |
|-------------|---------------|---------|----------------------------------------|
| `profile`   | `str \| None` | `None`  | Profile name for environment isolation |
| `start_dir` | `str \| None` | `None`  | Directory for .env file discovery      |

**Returns:** `Config` - Immutable configuration object

---

### `FinanzOnlineConfig`

Configuration for FinanzOnline connection.

```python
from finanzonline_databox.config import FinanzOnlineConfig, load_finanzonline_config

# Load from layered config
config = get_config()
fo_config = load_finanzonline_config(config)
```

**Attributes:**

| Attribute             | Type                      | Default  | Description                              |
|-----------------------|---------------------------|----------|------------------------------------------|
| `credentials`         | `FinanzOnlineCredentials` | Required | Authentication credentials               |
| `session_timeout`     | `float`                   | `30.0`   | Timeout for session operations (seconds) |
| `query_timeout`       | `float`                   | `30.0`   | Timeout for query/download operations    |
| `default_recipients`  | `list[str] \| None`       | `None`   | Default email recipients                 |
| `email_format`        | `EmailFormat`             | `BOTH`   | Email body format                        |
| `ratelimit_queries`   | `int`                     | `50`     | Max queries in time window               |
| `ratelimit_hours`     | `float`                   | `24.0`   | Sliding window duration in hours         |
| `ratelimit_file`      | `Path \| None`            | `None`   | Path to rate limit tracking file         |

---

## Domain Models

### `FinanzOnlineCredentials`

Authentication credentials for FinanzOnline web services.

```python
from finanzonline_databox.domain.models import FinanzOnlineCredentials

credentials = FinanzOnlineCredentials(
    tid="123456789",      # Participant ID (8-12 alphanumeric)
    benid="WEBUSER",      # User ID (5-12 chars)
    pin="password123",    # Password (5-128 chars)
    herstellerid="ATU12345678"  # Software producer VAT-ID (10-24 alphanumeric)
)
```

**Validation Rules (per login.xsd):**

| Field          | Pattern            | Description                    |
|----------------|--------------------|--------------------------------|
| `tid`          | 8-12 alphanumeric  | Participant ID (Teilnehmer-ID) |
| `benid`        | 5-12 characters    | User ID (Benutzer-ID)          |
| `pin`          | 5-128 characters   | Password/PIN                   |
| `herstellerid` | 10-24 alphanumeric | VAT-ID of software producer    |

---

### `DataboxListRequest`

Request parameters for listing DataBox entries.

```python
from finanzonline_databox.domain.models import DataboxListRequest
from datetime import datetime

# List all unread entries
request = DataboxListRequest()

# List only decisions (Bescheide)
request = DataboxListRequest(erltyp="B")

# List entries in date range (returns both read and unread)
request = DataboxListRequest(
    ts_zust_von=datetime(2024, 1, 1),
    ts_zust_bis=datetime(2024, 1, 7)
)
```

**Attributes:**

| Attribute     | Type               | Default | Description                                        |
|---------------|--------------------|---------|----------------------------------------------------|
| `erltyp`      | `str`              | `""`    | Document type filter (empty = all unread)          |
| `ts_zust_von` | `datetime \| None` | `None`  | Start date filter (max 31 days in past)            |
| `ts_zust_bis` | `datetime \| None` | `None`  | End date filter (max 7 days after ts_zust_von)     |

**Note:** If date range is not provided, only unread entries are returned.

---

### `DataboxEntry`

A single DataBox entry (document metadata).

```python
from finanzonline_databox.domain.models import DataboxEntry
from datetime import date, datetime

entry = DataboxEntry(
    stnr="12-345/6789",
    name="Bescheid",
    anbringen="E1",
    zrvon="2024",
    zrbis="2024",
    datbesch=date(2024, 1, 15),
    erltyp="B",
    fileart="PDF",
    ts_zust=datetime(2024, 1, 15, 10, 30),
    applkey="abc123def456",
    filebez="Einkommensteuerbescheid",
    status=""
)

# Properties
entry.is_unread           # True (status == "")
entry.is_read             # False (status == "1")
entry.is_pdf              # True
entry.is_xml              # False
entry.suggested_filename  # "2024-01-15_B_E1_abc123def456.pdf"
```

**Attributes:**

| Attribute  | Type       | Description                               |
|------------|------------|-------------------------------------------|
| `stnr`     | `str`      | Tax number (Steuernummer)                 |
| `name`     | `str`      | Document name/title                       |
| `anbringen`| `str`      | Document reference code                   |
| `zrvon`    | `str`      | Period from (e.g., "2024")                |
| `zrbis`    | `str`      | Period to (e.g., "2024")                  |
| `datbesch` | `date`     | Document date                             |
| `erltyp`   | `str`      | Document type (B, M, I, P, EU, etc.)      |
| `fileart`  | `str`      | File type (PDF, XML, ZIP)                 |
| `ts_zust`  | `datetime` | Delivery timestamp                        |
| `applkey`  | `str`      | Key for downloading the document          |
| `filebez`  | `str`      | File description                          |
| `status`   | `str`      | Read status ("" = unread, "1" = read)     |

---

### `DataboxListResult`

Result of listing DataBox entries.

```python
from finanzonline_databox.domain.models import DataboxListResult

# Example result
result.rc            # 0 (success)
result.msg           # None or error message
result.entries       # tuple of DataboxEntry
result.timestamp     # datetime (UTC)

# Properties
result.is_success    # True if rc == 0
result.entry_count   # Number of entries
result.unread_count  # Number of unread entries
```

**Attributes:**

| Attribute   | Type                      | Description                        |
|-------------|---------------------------|------------------------------------|
| `rc`        | `int`                     | Return code (0 = success)          |
| `msg`       | `str \| None`             | Response message (if error)        |
| `entries`   | `tuple[DataboxEntry, ...]`| List of DataBox entries            |
| `timestamp` | `datetime`                | When the list was retrieved (UTC)  |

---

### `DataboxDownloadRequest`

Request to download a specific document.

```python
from finanzonline_databox.domain.models import DataboxDownloadRequest

request = DataboxDownloadRequest(applkey="abc123def456xyz")
```

**Attributes:**

| Attribute | Type  | Description                                    |
|-----------|-------|------------------------------------------------|
| `applkey` | `str` | Document key (10-24 alphanumeric chars)        |

---

### `DataboxDownloadResult`

Result of downloading a document.

```python
from finanzonline_databox.domain.models import DataboxDownloadResult

# Example result
result.rc           # 0 (success)
result.msg          # None or error message
result.content      # bytes (decoded document)
result.timestamp    # datetime (UTC)

# Properties
result.is_success   # True if rc == 0 and content is not None
result.content_size # Size in bytes
```

**Attributes:**

| Attribute   | Type            | Description                        |
|-------------|-----------------|------------------------------------|
| `rc`        | `int`           | Return code (0 = success)          |
| `msg`       | `str \| None`   | Response message (if error)        |
| `content`   | `bytes \| None` | Decoded document content           |
| `timestamp` | `datetime`      | When download was performed (UTC)  |

---

## Use Cases

### `ListDataboxUseCase`

Use case for listing DataBox entries.

```python
from finanzonline_databox.application.use_cases import ListDataboxUseCase
from finanzonline_databox.adapters.finanzonline import (
    FinanzOnlineSessionClient,
    DataboxClient
)
from finanzonline_databox.domain.models import (
    FinanzOnlineCredentials,
    DataboxListRequest
)

# Create clients
session_client = FinanzOnlineSessionClient(timeout=30.0)
databox_client = DataboxClient(timeout=30.0)

# Create use case
use_case = ListDataboxUseCase(session_client, databox_client)

# Execute listing
credentials = FinanzOnlineCredentials(
    tid="123456789",
    benid="WEBUSER",
    pin="password",
    herstellerid="ATU12345678"
)

# List all unread
result = use_case.execute(credentials)

# List only decisions
request = DataboxListRequest(erltyp="B")
result = use_case.execute(credentials, request)

print(f"Found {result.entry_count} entries ({result.unread_count} unread)")
```

**Parameters for `execute()`:**

| Parameter     | Type                            | Description                |
|---------------|---------------------------------|----------------------------|
| `credentials` | `FinanzOnlineCredentials`       | Authentication credentials |
| `request`     | `DataboxListRequest \| None`    | Optional filters           |

**Returns:** `DataboxListResult`

**Raises:**
- `SessionError` - Login or session management failed
- `DataboxOperationError` - List operation failed

---

### `DownloadEntryUseCase`

Use case for downloading a single document.

```python
from finanzonline_databox.application.use_cases import DownloadEntryUseCase
from pathlib import Path

# Create use case
use_case = DownloadEntryUseCase(session_client, databox_client)

# Download to memory
result = use_case.execute(credentials, applkey="abc123def456xyz")

# Download and save to file
result = use_case.execute(
    credentials,
    applkey="abc123def456xyz",
    output_path=Path("./document.pdf")
)

if result.is_success:
    print(f"Downloaded {result.content_size} bytes")
```

**Parameters for `execute()`:**

| Parameter     | Type                      | Description                   |
|---------------|---------------------------|-------------------------------|
| `credentials` | `FinanzOnlineCredentials` | Authentication credentials    |
| `applkey`     | `str`                     | Document key to download      |
| `output_path` | `Path \| None`            | Optional path to save file    |

**Returns:** `DataboxDownloadResult`

**Raises:**
- `SessionError` - Login or session management failed
- `DataboxOperationError` - Download operation failed
- `OSError` - File write failed (if output_path specified)

---

### `SyncDataboxUseCase`

Use case for syncing all new documents to local storage.

```python
from finanzonline_databox.application.use_cases import SyncDataboxUseCase
from pathlib import Path

# Create use case
use_case = SyncDataboxUseCase(session_client, databox_client)

# Sync all unread documents (default)
result = use_case.execute(
    credentials,
    output_dir=Path("./databox-archive")
)

# Sync only decisions
request = DataboxListRequest(erltyp="B")
result = use_case.execute(
    credentials,
    output_dir=Path("./decisions"),
    request=request
)

# Sync only protocols with reference UID
request = DataboxListRequest(erltyp="P")
result = use_case.execute(
    credentials,
    output_dir=Path("./uid-protocols"),
    request=request,
    anbringen_filter="UID"
)

# Sync only unread documents (explicit)
result = use_case.execute(
    credentials,
    output_dir=Path("./unread-only"),
    read_filter="unread"
)

# Sync only read documents
result = use_case.execute(
    credentials,
    output_dir=Path("./read-only"),
    read_filter="read"
)

# Sync all documents (both read and unread)
result = use_case.execute(
    credentials,
    output_dir=Path("./all-documents"),
    read_filter="all"
)

print(f"Downloaded: {result.downloaded}")
print(f"Skipped: {result.skipped}")
print(f"Failed: {result.failed}")
print(f"Total bytes: {result.total_bytes}")
```

**Parameters for `execute()`:**

| Parameter          | Type                         | Default | Description                                         |
|--------------------|------------------------------|---------|-----------------------------------------------------|
| `credentials`      | `FinanzOnlineCredentials`    | Required| Authentication credentials                          |
| `output_dir`       | `Path`                       | Required| Directory to save downloaded files                  |
| `request`          | `DataboxListRequest \| None` | `None`  | Optional filters                                    |
| `skip_existing`    | `bool`                       | `True`  | Skip files that already exist                       |
| `anbringen_filter` | `str`                        | `""`    | Only sync entries with this reference               |
| `read_filter`      | `str`                        | `"all"` | Read status filter: `"unread"`, `"read"`, or `"all"`|

**Returns:** `SyncResult`

**Raises:**
- `SessionError` - Login or session management failed
- `DataboxOperationError` - List or download operation failed

---

### `SyncResult`

Result of a sync operation.

```python
result.total_retrieved   # Raw count from API before filtering
result.total_listed      # Entries after filtering
result.unread_listed     # Unread entries in filtered list
result.downloaded        # Successfully downloaded
result.skipped           # Skipped (file already exists locally)
result.failed            # Failed to download
result.total_bytes       # Total bytes downloaded
result.downloaded_files  # Tuple of (DataboxEntry, Path) for downloaded files
result.applied_filters   # Tuple of applied filter names (e.g., ("Unread", "UID:E1"))

# Properties
result.is_success        # True if failed == 0
result.has_new_downloads # True if downloaded > 0
```

**Attributes:**

| Attribute          | Type                                   | Description                                      |
|--------------------|----------------------------------------|--------------------------------------------------|
| `total_retrieved`  | `int`                                  | Raw count from API before filtering              |
| `total_listed`     | `int`                                  | Number of entries after filtering                |
| `unread_listed`    | `int`                                  | Number of unread entries in filtered list        |
| `downloaded`       | `int`                                  | Number of successfully downloaded files          |
| `skipped`          | `int`                                  | Number of skipped files (already exist locally)  |
| `failed`           | `int`                                  | Number of failed downloads                       |
| `total_bytes`      | `int`                                  | Total bytes downloaded                           |
| `downloaded_files` | `tuple[tuple[DataboxEntry, Path], ...]`| Downloaded files with their paths                |
| `applied_filters`  | `tuple[str, ...]`                      | Applied filter names for display                 |

**Statistics Output Example:**

When `SyncDataboxUseCase.execute()` completes, the formatted output shows aligned statistics:

```
Retrieved                       : 7
After Filter [Unread, UID:E1]   : 3
Downloaded                      : 2
Skipped (exists)                : 1
Failed                          : 0
Total Size                      : 125.4 KB
```

---

## Email Functions

### `EmailConfig`

Email configuration container.

```python
from finanzonline_databox.mail import EmailConfig

config = EmailConfig(
    smtp_hosts=["smtp.example.com:587"],
    from_address="alerts@example.com",
    smtp_username="user@example.com",  # Optional
    smtp_password="password",           # Optional
    use_starttls=True,
    timeout=30.0,
    raise_on_missing_attachments=True,
    raise_on_invalid_recipient=True,
    default_recipients=["admin@example.com"]
)
```

**Attributes:**

| Attribute                      | Type          | Default               | Description                        |
|--------------------------------|---------------|-----------------------|------------------------------------|
| `smtp_hosts`                   | `list[str]`   | `[]`                  | SMTP servers in 'host:port' format |
| `from_address`                 | `str`         | `"noreply@localhost"` | Default sender address             |
| `smtp_username`                | `str \| None` | `None`                | SMTP authentication username       |
| `smtp_password`                | `str \| None` | `None`                | SMTP authentication password       |
| `use_starttls`                 | `bool`        | `True`                | Enable STARTTLS                    |
| `timeout`                      | `float`       | `30.0`                | Socket timeout (seconds)           |
| `raise_on_missing_attachments` | `bool`        | `True`                | Raise on missing files             |
| `raise_on_invalid_recipient`   | `bool`        | `True`                | Raise on invalid addresses         |
| `default_recipients`           | `list[str]`   | `[]`                  | Default recipients                 |

---

### `send_email()`

Send an email using configured SMTP settings.

```python
from finanzonline_databox.mail import EmailConfig, send_email
from pathlib import Path

config = EmailConfig(
    smtp_hosts=["smtp.example.com:587"],
    from_address="alerts@example.com"
)

send_email(
    config=config,
    recipients=["user@example.com"],
    subject="Test Email",
    body="Plain text body",
    body_html="<h1>HTML body</h1>",  # Optional
    from_address="override@example.com",  # Optional
    attachments=[Path("report.pdf")]  # Optional
)
```

**Parameters:**

| Parameter      | Type                     | Default  | Description           |
|----------------|--------------------------|----------|-----------------------|
| `config`       | `EmailConfig`            | Required | Email configuration   |
| `recipients`   | `str \| Sequence[str]`   | Required | Recipient address(es) |
| `subject`      | `str`                    | Required | Email subject         |
| `body`         | `str`                    | `""`     | Plain-text body       |
| `body_html`    | `str`                    | `""`     | HTML body             |
| `from_address` | `str \| None`            | `None`   | Override sender       |
| `attachments`  | `Sequence[Path] \| None` | `None`   | File paths to attach  |

**Returns:** `bool` - True on success

**Raises:**
- `ValueError` - No valid recipients
- `FileNotFoundError` - Missing attachment
- `RuntimeError` - All SMTP hosts failed

---

### `send_notification()`

Send a simple plain-text notification email.

```python
from finanzonline_databox.mail import EmailConfig, send_notification

config = EmailConfig(
    smtp_hosts=["smtp.example.com:587"],
    from_address="alerts@example.com"
)

send_notification(
    config=config,
    recipients="admin@example.com",
    subject="System Alert",
    message="Backup completed successfully"
)
```

**Parameters:**

| Parameter    | Type                   | Default  | Description           |
|--------------|------------------------|----------|-----------------------|
| `config`     | `EmailConfig`          | Required | Email configuration   |
| `recipients` | `str \| Sequence[str]` | Required | Recipient address(es) |
| `subject`    | `str`                  | Required | Subject line          |
| `message`    | `str`                  | Required | Notification message  |

**Returns:** `bool` - True on success

---

### `load_email_config_from_dict()`

Load EmailConfig from a configuration dictionary.

```python
from finanzonline_databox.mail import load_email_config_from_dict
from finanzonline_databox.config import get_config

config = get_config()
email_config = load_email_config_from_dict(config.as_dict())
```

---

## Exceptions

All domain exceptions inherit from `DataboxError`:

```python
from finanzonline_databox.domain.errors import (
    DataboxError,            # Base exception
    ConfigurationError,      # Missing or invalid configuration
    AuthenticationError,     # Login/credentials failure
    SessionError,            # Session management errors
    DataboxOperationError,   # DataBox operation execution errors
)
```

| Exception              | Attributes                                           | Description                              |
|------------------------|------------------------------------------------------|------------------------------------------|
| `DataboxError`         | `message`                                            | Base exception for all DataBox errors    |
| `ConfigurationError`   | `message`                                            | Missing or invalid configuration         |
| `AuthenticationError`  | `message`, `return_code`, `diagnostics`              | Login failed                             |
| `SessionError`         | `message`, `return_code`, `diagnostics`              | Session management failed                |
| `DataboxOperationError`| `message`, `return_code`, `retryable`, `diagnostics` | DataBox operation failed                 |

---

## Return Code Utilities

```python
from finanzonline_databox.domain.return_codes import (
    get_return_code_info,
    is_success,
    is_retryable,
    Severity,
    ReturnCodeInfo
)

# Get info about a return code
info = get_return_code_info(0)
print(info.code)       # 0
print(info.meaning)    # "Success"
print(info.severity)   # Severity.SUCCESS
print(info.retryable)  # False

# Quick checks
is_success(0)      # True
is_retryable(-2)   # True (maintenance)
is_retryable(-3)   # True (technical error)
```

**DataBox Return Codes:**

| Code | Meaning                                              |
|------|------------------------------------------------------|
| `0`  | Success                                              |
| `-1` | Session invalid or expired                           |
| `-2` | System under maintenance (retryable)                 |
| `-3` | Technical error (retryable)                          |
| `-4` | Date parameters required (ts_zust_von/bis)           |
| `-5` | ts_zust_von too old (max 31 days in past)            |
| `-6` | Date range too wide (max 7 days between von and bis) |
