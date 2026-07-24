# Python-API-Referenz

Dieses Dokument beschreibt die Python-API für `finanzonline_databox`.

## Öffentliche Exporte

```python
import finanzonline_databox

# Paket-Metadaten
finanzonline_databox.__version__  # "0.0.1"
finanzonline_databox.__title__  # "Python library and CLI..."
finanzonline_databox.__author__  # "bitranox"
finanzonline_databox.__url__  # "https://github.com/bitranox/finanzonline_databox"
```

---

## Konfiguration

### `get_config()`

Lädt die mehrschichtige Konfiguration aus allen Quellen.

```python
from finanzonline_databox.config import get_config

config = get_config()
# oder mit Profil
config = get_config(profile="production")
# oder mit benutzerdefiniertem Startverzeichnis für .env-Erkennung
config = get_config(start_dir="/path/to/project")
```

**Parameter:**

| Parameter   | Typ           | Standard | Beschreibung                              |
|-------------|---------------|----------|-------------------------------------------|
| `profile`   | `str \| None` | `None`   | Profilname für Umgebungsisolierung        |
| `start_dir` | `str \| None` | `None`   | Verzeichnis für .env-Dateierkennung       |

**Rückgabe:** `Config` - Unveränderliches Konfigurationsobjekt

---

### `FinanzOnlineConfig`

Konfiguration für die FinanzOnline-Verbindung.

```python
from finanzonline_databox.config import FinanzOnlineConfig, load_finanzonline_config

# Aus mehrschichtiger Konfiguration laden
config = get_config()
fo_config = load_finanzonline_config(config)
```

**Attribute:**

| Attribut              | Typ                       | Standard     | Beschreibung                                |
|-----------------------|---------------------------|--------------|---------------------------------------------|
| `credentials`         | `FinanzOnlineCredentials` | Erforderlich | Authentifizierungsdaten                     |
| `session_timeout`     | `float`                   | `30.0`       | Timeout für Session-Operationen (Sekunden)  |
| `query_timeout`       | `float`                   | `30.0`       | Timeout für Abfrage/Download (Sekunden)     |
| `default_recipients`  | `list[str] \| None`       | `None`       | Standard-E-Mail-Empfänger                   |
| `email_format`        | `EmailFormat`             | `BOTH`       | E-Mail-Body-Format                          |
| `ratelimit_queries`   | `int`                     | `50`         | Max. Abfragen im Zeitfenster                |
| `ratelimit_hours`     | `float`                   | `24.0`       | Gleitendes Zeitfenster in Stunden           |
| `ratelimit_file`      | `Path \| None`            | `None`       | Pfad zur Ratenlimit-Tracking-Datei          |

---

## Domain-Modelle

### `FinanzOnlineCredentials`

Authentifizierungsdaten für FinanzOnline-Webservices.

```python
from finanzonline_databox.domain.models import FinanzOnlineCredentials

credentials = FinanzOnlineCredentials(
    tid="123456789",  # Teilnehmer-ID (8-12 alphanumerisch)
    benid="WEBUSER",  # Benutzer-ID (5-12 Zeichen)
    pin="password123",  # Passwort (5-128 Zeichen)
    herstellerid="ATU12345678",  # Software-Hersteller UID (10-24 alphanumerisch)
)
```

**Validierungsregeln (gemäß login.xsd):**

| Feld           | Muster              | Beschreibung                   |
|----------------|---------------------|--------------------------------|
| `tid`          | 8-12 alphanumerisch | Teilnehmer-ID                  |
| `benid`        | 5-12 Zeichen        | Benutzer-ID                    |
| `pin`          | 5-128 Zeichen       | Passwort/PIN                   |
| `herstellerid` | 10-24 alphanumerisch| UID des Software-Herstellers   |

---

### `DataboxListRequest`

Anfrageparameter zum Auflisten von DataBox-Einträgen.

```python
from finanzonline_databox.domain.models import DataboxListRequest
from datetime import datetime

# Alle ungelesenen Einträge auflisten
request = DataboxListRequest()

# Nur Bescheide auflisten
request = DataboxListRequest(erltyp="B")

# Einträge im Datumsbereich auflisten (gibt gelesene und ungelesene zurück)
request = DataboxListRequest(ts_zust_von=datetime(2024, 1, 1), ts_zust_bis=datetime(2024, 1, 7))
```

**Attribute:**

| Attribut      | Typ                | Standard | Beschreibung                                     |
|---------------|--------------------|---------|-------------------------------------------------|
| `erltyp`      | `str`              | `""`    | Dokumenttyp-Filter (leer = alle ungelesenen)    |
| `ts_zust_von` | `datetime \| None` | `None`  | Startdatum-Filter (max. 31 Tage zurück)         |
| `ts_zust_bis` | `datetime \| None` | `None`  | Enddatum-Filter (max. 7 Tage nach ts_zust_von)  |

**Hinweis:** Wenn kein Datumsbereich angegeben ist, werden nur ungelesene Einträge zurückgegeben.

---

### `DataboxEntry`

Ein einzelner DataBox-Eintrag (Dokumentmetadaten).

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
    status="",
)

# Properties
entry.is_unread  # True (status == "")
entry.is_read  # False (status == "1")
entry.is_pdf  # True
entry.is_xml  # False
entry.suggested_filename  # "2024-01-15_B_E1_abc123def456.pdf"
```

**Attribute:**

| Attribut   | Typ        | Beschreibung                               |
|------------|------------|-------------------------------------------|
| `stnr`     | `str`      | Steuernummer                              |
| `name`     | `str`      | Dokumentname/Titel                        |
| `anbringen`| `str`      | Dokument-Referenzcode                     |
| `zrvon`    | `str`      | Zeitraum von (z.B. "2024")                |
| `zrbis`    | `str`      | Zeitraum bis (z.B. "2024")                |
| `datbesch` | `date`     | Dokumentdatum                             |
| `erltyp`   | `str`      | Dokumenttyp (B, M, I, P, EU, etc.)        |
| `fileart`  | `str`      | Dateityp (PDF, XML, ZIP)                  |
| `ts_zust`  | `datetime` | Zustellungszeitstempel                    |
| `applkey`  | `str`      | Schlüssel zum Herunterladen des Dokuments |
| `filebez`  | `str`      | Dateibeschreibung                         |
| `status`   | `str`      | Lesestatus ("" = ungelesen, "1" = gelesen)|

---

### `DataboxListResult`

Ergebnis des Auflistens von DataBox-Einträgen.

```python
from finanzonline_databox.domain.models import DataboxListResult

# Beispiel-Ergebnis
result.rc  # 0 (Erfolg)
result.msg  # None oder Fehlermeldung
result.entries  # Tupel von DataboxEntry
result.timestamp  # datetime (UTC)

# Properties
result.is_success  # True wenn rc == 0
result.entry_count  # Anzahl der Einträge
result.unread_count  # Anzahl der ungelesenen Einträge
```

**Attribute:**

| Attribut    | Typ                       | Beschreibung                       |
|-------------|---------------------------|------------------------------------|
| `rc`        | `int`                     | Rückgabecode (0 = Erfolg)          |
| `msg`       | `str \| None`             | Antwortnachricht (bei Fehler)      |
| `entries`   | `tuple[DataboxEntry, ...]`| Liste der DataBox-Einträge         |
| `timestamp` | `datetime`                | Wann die Liste abgerufen wurde (UTC)|

---

### `DataboxDownloadRequest`

Anfrage zum Herunterladen eines bestimmten Dokuments.

```python
from finanzonline_databox.domain.models import DataboxDownloadRequest

request = DataboxDownloadRequest(applkey="abc123def456xyz")
```

**Attribute:**

| Attribut  | Typ   | Beschreibung                                    |
|-----------|-------|------------------------------------------------|
| `applkey` | `str` | Dokumentschlüssel (10-24 alphanumerische Zeichen)|

---

### `DataboxDownloadResult`

Ergebnis des Herunterladens eines Dokuments.

```python
from finanzonline_databox.domain.models import DataboxDownloadResult

# Beispiel-Ergebnis
result.rc  # 0 (Erfolg)
result.msg  # None oder Fehlermeldung
result.content  # bytes (decodiertes Dokument)
result.timestamp  # datetime (UTC)

# Properties
result.is_success  # True wenn rc == 0 und content ist nicht None
result.content_size  # Größe in Bytes
```

**Attribute:**

| Attribut    | Typ             | Beschreibung                       |
|-------------|-----------------|------------------------------------|
| `rc`        | `int`           | Rückgabecode (0 = Erfolg)          |
| `msg`       | `str \| None`   | Antwortnachricht (bei Fehler)      |
| `content`   | `bytes \| None` | Decodierter Dokumentinhalt         |
| `timestamp` | `datetime`      | Wann der Download durchgeführt wurde (UTC)|

---

## Use Cases

### `ListDataboxUseCase`

Use Case zum Auflisten von DataBox-Einträgen.

```python
from finanzonline_databox.application.use_cases import ListDataboxUseCase
from finanzonline_databox.adapters.finanzonline import FinanzOnlineSessionClient, DataboxClient
from finanzonline_databox.domain.models import FinanzOnlineCredentials, DataboxListRequest

# Clients erstellen
session_client = FinanzOnlineSessionClient(timeout=30.0)
databox_client = DataboxClient(timeout=30.0)

# Use Case erstellen
use_case = ListDataboxUseCase(session_client, databox_client)

# Auflistung ausführen
credentials = FinanzOnlineCredentials(tid="123456789", benid="WEBUSER", pin="password", herstellerid="ATU12345678")

# Alle ungelesenen auflisten
result = use_case.execute(credentials)

# Nur Bescheide auflisten
request = DataboxListRequest(erltyp="B")
result = use_case.execute(credentials, request)

print(f"Gefunden: {result.entry_count} Einträge ({result.unread_count} ungelesen)")
```

**Parameter für `execute()`:**

| Parameter     | Typ                            | Beschreibung                 |
|---------------|--------------------------------|------------------------------|
| `credentials` | `FinanzOnlineCredentials`      | Authentifizierungsdaten      |
| `request`     | `DataboxListRequest \| None`   | Optionale Filter             |

**Rückgabe:** `DataboxListResult`

**Wirft:**
- `SessionError` - Login oder Session-Verwaltung fehlgeschlagen
- `DataboxOperationError` - Auflistungsoperation fehlgeschlagen

---

### `DownloadEntryUseCase`

Use Case zum Herunterladen eines einzelnen Dokuments.

```python
from finanzonline_databox.application.use_cases import DownloadEntryUseCase
from pathlib import Path

# Use Case erstellen
use_case = DownloadEntryUseCase(session_client, databox_client)

# In den Speicher herunterladen
result = use_case.execute(credentials, applkey="abc123def456xyz")

# Herunterladen und in Datei speichern
result = use_case.execute(credentials, applkey="abc123def456xyz", output_path=Path("./dokument.pdf"))

if result.is_success:
    print(f"Heruntergeladen: {result.content_size} Bytes")
```

**Parameter für `execute()`:**

| Parameter     | Typ                       | Beschreibung                       |
|---------------|---------------------------|-------------------------------------|
| `credentials` | `FinanzOnlineCredentials` | Authentifizierungsdaten            |
| `applkey`     | `str`                     | Dokumentschlüssel zum Herunterladen|
| `output_path` | `Path \| None`            | Optionaler Pfad zum Speichern      |

**Rückgabe:** `DataboxDownloadResult`

**Wirft:**
- `SessionError` - Login oder Session-Verwaltung fehlgeschlagen
- `DataboxOperationError` - Download-Operation fehlgeschlagen
- `OSError` - Schreiben der Datei fehlgeschlagen (wenn output_path angegeben)

---

### `SyncDataboxUseCase`

Use Case zum Synchronisieren aller neuen Dokumente in den lokalen Speicher.

```python
from finanzonline_databox.application.use_cases import SyncDataboxUseCase
from pathlib import Path

# Use Case erstellen
use_case = SyncDataboxUseCase(session_client, databox_client)

# Alle ungelesenen Dokumente synchronisieren
result = use_case.execute(credentials, output_dir=Path("./databox-archiv"))

# Nur Bescheide synchronisieren
request = DataboxListRequest(erltyp="B")
result = use_case.execute(credentials, output_dir=Path("./bescheide"), request=request)

# Nur Protokolle mit Referenz UID synchronisieren
request = DataboxListRequest(erltyp="P")
result = use_case.execute(credentials, output_dir=Path("./uid-protokolle"), request=request, anbringen_filter="UID")

# Nur ungelesene Dokumente synchronisieren
result = use_case.execute(credentials, output_dir=Path("./ungelesene"), read_filter="unread")

# Nur gelesene Dokumente erneut herunterladen
result = use_case.execute(credentials, output_dir=Path("./gelesene"), read_filter="read", skip_existing=False)

# Alle Dokumente synchronisieren (gelesen und ungelesen)
result = use_case.execute(credentials, output_dir=Path("./alle-dokumente"), read_filter="all")

print(f"Heruntergeladen: {result.downloaded}")
print(f"Übersprungen: {result.skipped}")
print(f"Fehlgeschlagen: {result.failed}")
print(f"Gesamt Bytes: {result.total_bytes}")
```

**Parameter für `execute()`:**

| Parameter          | Typ                          | Standard | Beschreibung                                            |
|--------------------|------------------------------|----------|---------------------------------------------------------|
| `credentials`      | `FinanzOnlineCredentials`    | Pflicht  | Authentifizierungsdaten                                 |
| `output_dir`       | `Path`                       | Pflicht  | Verzeichnis zum Speichern der Downloads                 |
| `request`          | `DataboxListRequest \| None` | `None`   | Optionale Filter                                        |
| `skip_existing`    | `bool`                       | `True`   | Bereits existierende Dateien überspringen               |
| `anbringen_filter` | `str`                        | `""`     | Nur Einträge mit dieser Referenz synchronisieren        |
| `read_filter`      | `str`                        | `"all"`  | Lesestatus-Filter: `"unread"`, `"read"` oder `"all"`    |

**`read_filter` Werte:**

| Wert       | Beschreibung                              |
|------------|-------------------------------------------|
| `"unread"` | Nur ungelesene Dokumente synchronisieren  |
| `"read"`   | Nur gelesene Dokumente synchronisieren    |
| `"all"`    | Alle Dokumente synchronisieren (Standard) |

**Rückgabe:** `SyncResult`

**Wirft:**
- `SessionError` - Login oder Session-Verwaltung fehlgeschlagen
- `DataboxOperationError` - Auflistungs- oder Download-Operation fehlgeschlagen

---

### `SyncResult`

Ergebnis einer Sync-Operation.

```python
result.total_retrieved  # Rohanzahl von API vor Filterung
result.total_listed  # Einträge nach Filterung
result.unread_listed  # Ungelesene Einträge in gefilterter Liste
result.downloaded  # Erfolgreich heruntergeladen
result.skipped  # Übersprungen (Datei existiert bereits lokal)
result.failed  # Fehlgeschlagen beim Herunterladen
result.total_bytes  # Gesamt heruntergeladene Bytes
result.downloaded_files  # Tupel von (DataboxEntry, Path) für heruntergeladene Dateien
result.applied_filters  # Tupel von angewendeten Filternamen (z.B. ("Unread", "UID:E1"))

# Properties
result.is_success  # True wenn failed == 0
result.has_new_downloads  # True wenn downloaded > 0
```

**Attribute:**

| Attribut           | Typ                                    | Beschreibung                                       |
|--------------------|----------------------------------------|----------------------------------------------------|
| `total_retrieved`  | `int`                                  | Rohanzahl von API vor Filterung                    |
| `total_listed`     | `int`                                  | Anzahl der Einträge nach Filterung                 |
| `unread_listed`    | `int`                                  | Anzahl der ungelesenen Einträge in gefilterter Liste|
| `downloaded`       | `int`                                  | Anzahl erfolgreich heruntergeladener Dateien       |
| `skipped`          | `int`                                  | Anzahl übersprungener Dateien (existieren bereits) |
| `failed`           | `int`                                  | Anzahl fehlgeschlagener Downloads                  |
| `total_bytes`      | `int`                                  | Gesamt heruntergeladene Bytes                      |
| `downloaded_files` | `tuple[tuple[DataboxEntry, Path], ...]`| Heruntergeladene Dateien mit ihren Pfaden          |
| `applied_filters`  | `tuple[str, ...]`                      | Angewendete Filternamen für Anzeige                |

**Beispiel Statistik-Ausgabe:**

Wenn `SyncDataboxUseCase.execute()` abgeschlossen ist, zeigt die formatierte Ausgabe ausgerichtete Statistiken:

```
Abgerufen                           : 7
Nach Filter [Unread, UID:E1]        : 3
Heruntergeladen                     : 2
Übersprungen (vorhanden)            : 1
Fehlgeschlagen                      : 0
Gesamtgröße                         : 125,4 KB
```

---

## E-Mail-Funktionen

### `EmailConfig`

E-Mail-Konfigurationscontainer.

```python
from finanzonline_databox.mail import EmailConfig

config = EmailConfig(
    smtp_hosts=["smtp.beispiel.at:587"],
    from_address="alerts@beispiel.at",
    smtp_username="benutzer@beispiel.at",  # Optional
    smtp_password="passwort",  # Optional
    use_starttls=True,
    timeout=30.0,
    raise_on_missing_attachments=True,
    raise_on_invalid_recipient=True,
    default_recipients=["admin@beispiel.at"],
)
```

**Attribute:**

| Attribut                       | Typ           | Standard              | Beschreibung                         |
|--------------------------------|---------------|-----------------------|--------------------------------------|
| `smtp_hosts`                   | `list[str]`   | `[]`                  | SMTP-Server im 'host:port'-Format    |
| `from_address`                 | `str`         | `"noreply@localhost"` | Standard-Absenderadresse             |
| `smtp_username`                | `str \| None` | `None`                | SMTP-Authentifizierungsbenutzername  |
| `smtp_password`                | `str \| None` | `None`                | SMTP-Authentifizierungspasswort      |
| `use_starttls`                 | `bool`        | `True`                | STARTTLS aktivieren                  |
| `timeout`                      | `float`       | `30.0`                | Socket-Timeout (Sekunden)            |
| `raise_on_missing_attachments` | `bool`        | `True`                | Exception bei fehlenden Dateien      |
| `raise_on_invalid_recipient`   | `bool`        | `True`                | Exception bei ungültigen Adressen    |
| `default_recipients`           | `list[str]`   | `[]`                  | Standard-Empfänger                   |

---

### `send_email()`

Sendet eine E-Mail mit konfigurierten SMTP-Einstellungen.

```python
from finanzonline_databox.mail import EmailConfig, send_email
from pathlib import Path

config = EmailConfig(smtp_hosts=["smtp.beispiel.at:587"], from_address="alerts@beispiel.at")

send_email(
    config=config,
    recipients=["benutzer@beispiel.at"],
    subject="Test-E-Mail",
    body="Klartext-Inhalt",
    body_html="<h1>HTML-Inhalt</h1>",  # Optional
    from_address="override@beispiel.at",  # Optional
    attachments=[Path("bericht.pdf")],  # Optional
)
```

**Parameter:**

| Parameter      | Typ                      | Standard     | Beschreibung           |
|----------------|--------------------------|--------------|------------------------|
| `config`       | `EmailConfig`            | Erforderlich | E-Mail-Konfiguration   |
| `recipients`   | `str \| Sequence[str]`   | Erforderlich | Empfängeradresse(n)    |
| `subject`      | `str`                    | Erforderlich | E-Mail-Betreff         |
| `body`         | `str`                    | `""`         | Klartext-Body          |
| `body_html`    | `str`                    | `""`         | HTML-Body              |
| `from_address` | `str \| None`            | `None`       | Absender überschreiben |
| `attachments`  | `Sequence[Path] \| None` | `None`       | Dateipfade für Anhänge |

**Rückgabe:** `bool` - True bei Erfolg

**Wirft:**
- `ValueError` - Keine gültigen Empfänger
- `FileNotFoundError` - Fehlender Anhang
- `RuntimeError` - Alle SMTP-Hosts fehlgeschlagen

---

### `send_notification()`

Sendet eine einfache Klartext-Benachrichtigungs-E-Mail.

```python
from finanzonline_databox.mail import EmailConfig, send_notification

config = EmailConfig(smtp_hosts=["smtp.beispiel.at:587"], from_address="alerts@beispiel.at")

send_notification(config=config, recipients="admin@beispiel.at", subject="Systemwarnung", message="Backup erfolgreich abgeschlossen")
```

**Parameter:**

| Parameter    | Typ                    | Standard     | Beschreibung           |
|--------------|------------------------|--------------|------------------------|
| `config`     | `EmailConfig`          | Erforderlich | E-Mail-Konfiguration   |
| `recipients` | `str \| Sequence[str]` | Erforderlich | Empfängeradresse(n)    |
| `subject`    | `str`                  | Erforderlich | Betreffzeile           |
| `message`    | `str`                  | Erforderlich | Benachrichtigungstext  |

**Rückgabe:** `bool` - True bei Erfolg

---

### `load_email_config_from_dict()`

Lädt EmailConfig aus einem Konfigurations-Dictionary.

```python
from finanzonline_databox.mail import load_email_config_from_dict
from finanzonline_databox.config import get_config

config = get_config()
email_config = load_email_config_from_dict(config.as_dict())
```

---

## Exceptions

Alle Domain-Exceptions erben von `DataboxError`:

```python
from finanzonline_databox.domain.errors import (
    DataboxError,  # Basis-Exception
    ConfigurationError,  # Fehlende oder ungültige Konfiguration
    AuthenticationError,  # Login/Zugangsdaten-Fehler
    SessionError,  # Session-Verwaltungsfehler
    DataboxOperationError,  # DataBox-Operationsfehler
)
```

| Exception              | Attribute                                            | Beschreibung                               |
|------------------------|------------------------------------------------------|--------------------------------------------|
| `DataboxError`         | `message`                                            | Basis-Exception für alle DataBox-Fehler    |
| `ConfigurationError`   | `message`                                            | Fehlende oder ungültige Konfiguration      |
| `AuthenticationError`  | `message`, `return_code`, `diagnostics`              | Login fehlgeschlagen                       |
| `SessionError`         | `message`, `return_code`, `diagnostics`              | Session-Verwaltung fehlgeschlagen          |
| `DataboxOperationError`| `message`, `return_code`, `retryable`, `diagnostics` | DataBox-Operation fehlgeschlagen           |

---

## Rückgabecode-Hilfsfunktionen

```python
from finanzonline_databox.domain.return_codes import get_return_code_info, is_success, is_retryable, Severity, ReturnCodeInfo

# Informationen über einen Rückgabecode abrufen
info = get_return_code_info(0)
print(info.code)  # 0
print(info.meaning)  # "Erfolg"
print(info.severity)  # Severity.SUCCESS
print(info.retryable)  # False

# Schnellprüfungen
is_success(0)  # True
is_retryable(-2)  # True (Wartung)
is_retryable(-3)  # True (Technischer Fehler)
```

**DataBox-Rückgabecodes:**

| Code | Bedeutung                                                 |
|------|-----------------------------------------------------------|
| `0`  | Erfolg                                                    |
| `-1` | Session ungültig oder abgelaufen                          |
| `-2` | System in Wartung (wiederholbar)                          |
| `-3` | Technischer Fehler (wiederholbar)                         |
| `-4` | Datumsparameter erforderlich (ts_zust_von/bis)            |
| `-5` | ts_zust_von zu alt (max. 31 Tage in der Vergangenheit)    |
| `-6` | Datumsbereich zu groß (max. 7 Tage zwischen von und bis)  |
