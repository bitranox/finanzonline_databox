# BMF Return Codes

> [Deutsche Version verfügbar (RETURNCODES_de.md)](RETURNCODES_de.md)

This document describes all return codes from the Austrian BMF (Federal Ministry of Finance) FinanzOnline DataBox Download web service.

---

## Overview

The FinanzOnline DataBox web service returns numeric codes to indicate the result of operations. Code `0` indicates success; negative codes indicate errors.

---

## Success Code

| Code | Meaning              | Severity | Retryable |
|------|----------------------|----------|-----------|
| 0    | Operation successful | success  | -         |

---

## Session/Authentication Codes

These codes are returned during login and session management.

| Code | Meaning                                     | Severity | Retryable |
|------|---------------------------------------------|----------|-----------|
| -1   | Session invalid or expired                  | error    | No        |
| -2   | System maintenance                          | warning  | Yes       |
| -3   | Technical error                             | error    | Yes       |

### Common Authentication Issues

- **Code -1 (Session invalid):** The session has expired or was never established. Re-authenticate and try again.
- **Code -2 (System maintenance):** The BMF servers are under maintenance. Wait a few minutes and retry.
- **Code -3 (Technical error):** Temporary server issue. Retry later.

---

## DataBox-Specific Codes

These codes are returned during DataBox list and download operations.

| Code | Meaning                                                          | Severity | Retryable |
|------|------------------------------------------------------------------|----------|-----------|
| -4   | Date parameters required (ts_zust_von and ts_zust_bis)           | error    | No        |
| -5   | ts_zust_von must not be more than 31 days in the past            | error    | No        |
| -6   | ts_zust_bis must not be more than 7 days after ts_zust_von       | error    | No        |

### Date Parameter Rules

When filtering by date range, both parameters must be provided:

- **ts_zust_von** (start date): Maximum 31 days in the past
- **ts_zust_bis** (end date): Maximum 7 days after ts_zust_von

**Examples of valid date ranges:**
```
ts_zust_von = 2024-01-01, ts_zust_bis = 2024-01-07  (7 days - OK)
ts_zust_von = 2024-01-01, ts_zust_bis = 2024-01-05  (4 days - OK)
```

**Examples of invalid date ranges:**
```
ts_zust_von = 2024-01-01, ts_zust_bis = 2024-01-10  (9 days - ERROR: max 7 days)
ts_zust_von = 2023-01-01  (more than 31 days ago - ERROR)
```

---

## CLI Exit Codes

The CLI uses its own exit codes distinct from FinanzOnline return codes:

| Exit Code | Meaning              |
|-----------|----------------------|
| 0         | Success              |
| 1         | No entries found     |
| 2         | Configuration error  |
| 3         | Authentication error |
| 4         | Download error       |
| 5         | I/O error            |

---

## Severity Levels

| Severity   | Description                                          |
|------------|------------------------------------------------------|
| `success`  | Operation completed successfully                     |
| `warning`  | Warning - action may be required                     |
| `error`    | Error - request could not be processed               |
| `critical` | Critical - check configuration or permissions        |

---

## Retryable Errors

Errors with "Retryable: Yes" can be retried after a waiting period:

- **Code -2 (System maintenance):** Wait a few minutes and try again.
- **Code -3 (Technical error):** Temporary issue, retry later.

---

## BMF Rate Limits

The FinanzOnline DataBox web service may have rate limits. The tool includes built-in rate limit tracking (default: 50 queries per 24 hours) that:

- Warns you before you approach BMF limits
- Sends email notifications when exceeded
- Does NOT block queries - BMF handles actual enforcement

Configure via `finanzonline.ratelimit_queries` and `finanzonline.ratelimit_hours`.
