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

> [English version available (README_en.md)](README_en.md)

`finanzonline_databox` ist eine Python-Bibliothek und CLI zum **automatisierten Abrufen von Dokumenten aus der FinanzOnline DataBox**. Bescheide, Mitteilungen, Bestätigungen und andere steuerrelevante Dokumente werden automatisch heruntergeladen und lokal gespeichert.

## Warum finanzonline_databox?

Das manuelle Abrufen von Dokumenten aus der FinanzOnline DataBox erfordert Anmeldung, Navigation durch Menüs und einzelne Downloads - mühsam und nicht automatisierbar. Mit `finanzonline_databox`:

- **Kein Browser erforderlich** - läuft vollständig über die Kommandozeile
- **Automatischer Download** - alle neuen Dokumente mit einem Befehl synchronisieren
- **Vollständig skriptfähig** - Integration in Backup-Prozesse, Archivierungssysteme oder CI-Pipelines
- **E-Mail-Benachrichtigungen** - automatische Benachrichtigungen bei neuen Dokumenten
- **Ratenlimit-Schutz** - integriertes Tracking zum Schutz vor API-Überlastung
- **Dokumenttyp-Filter** - nur bestimmte Dokumentarten (Bescheide, Mitteilungen, etc.) abrufen
- **FREIE SOFTWARE** - diese Software ist und bleibt kostenlos

**Funktionen:**
- Auflisten aller Dokumente in der DataBox (mit Filtern)
- Download einzelner Dokumente per `applkey`
- Synchronisation aller neuen Dokumente in ein lokales Verzeichnis
- **Bis zu 31 Tage abrufen** - `list` und `sync` unterstützen bis zu 31 Tage Rückblick
- CLI-Einstiegspunkt mit rich-click (rich-Ausgabe + click-Ergonomie)
- Automatische E-Mail-Benachrichtigungen bei neuen Dokumenten
- **Per-Dokument E-Mails** - jedes heruntergeladene Dokument als Anhang an separate Empfänger
- **Mehrsprachige Unterstützung** - Englisch, Deutsch, Spanisch, Französisch, Russisch
- Menschenlesbare und JSON-Ausgabeformate
- Ratenlimit-Tracking mit Warn-E-Mails
- Mehrschichtiges Konfigurationssystem mit lib_layered_config
- Strukturiertes Logging mit lib_log_rich

**Unterstützte Dokumenttypen (erltyp):**
- `B` - Bescheide (Decisions/Decrees)
- `M` - Mitteilungen (Notifications)
- `I` - Informationen (Information)
- `P` - Protokolle (Protocols)
- `EU` - EU-Erledigungen
- und weitere...

**Beispiele:**
```bash
# Alle ungelesenen Dokumente auflisten (Standard)
finanzonline-databox list

# Nur Bescheide auflisten
finanzonline-databox list --erltyp B

# Alle Dokumente auflisten (bis zu 31 Tage)
finanzonline-databox list --all

# Nur gelesene Dokumente auflisten (bis zu 31 Tage)
finanzonline-databox list --read

# Alle Dokumente der letzten 3 Tage
finanzonline-databox list --days 3 --all

# Ein bestimmtes Dokument herunterladen
finanzonline-databox download abc123def456xyz --output ./downloads

# Alle neuen Dokumente synchronisieren (nur ungelesene, Standard)
finanzonline-databox sync --output ./databox-archiv

# Alle Dokumente synchronisieren (gelesen und ungelesen)
finanzonline-databox sync --output ./databox-archiv --all

# Dokumente der letzten 31 Tage synchronisieren
finanzonline-databox sync --days 31 --all

# Nur Protokolle mit Referenz UID synchronisieren
finanzonline-databox sync -t P -r UID

# Dokumente synchronisieren und als E-Mail-Anhang versenden
finanzonline-databox sync --document-recipient archiv@firma.at

# UID-Bestätigungen an Vertrieb, restliche Dokumente an Buchhaltung
finanzonline-databox sync -r UID --document-recipient sales@firma.at
finanzonline-databox sync --document-recipient buchhaltung@firma.at
```

---

## Aufbewahrungspflichten

> **WICHTIG:** Dokumente aus der FinanzOnline DataBox müssen gemäß § 132 BAO (Bundesabgabenordnung) aufbewahrt werden.
>
> Die Dokumente dienen als offizielle Dokumentation für Steuerprüfungen und müssen gemäß den österreichischen Aufbewahrungsvorschriften aufbewahrt werden (üblicherweise 7 Jahre).

Mit `finanzonline_databox sync` können Sie alle Dokumente automatisch in ein lokales Archiv herunterladen und so Ihre Aufbewahrungspflichten erfüllen.

---

## BMF-Ratenlimits

Der FinanzOnline-Webservice hat Ratenlimits. Dieses Tool enthält integriertes Ratenlimit-Tracking (Standard: 50 Abfragen pro 24 Stunden), das:
- Warnt, bevor Sie BMF-Limits erreichen
- E-Mail-Benachrichtigungen bei Überschreitung sendet
- Abfragen werden NICHT blockiert - das BMF führt die eigentliche Durchsetzung durch

Konfiguration über `finanzonline.ratelimit_queries` und `finanzonline.ratelimit_hours`.

### FinanzOnline Webservice-Benutzer

> **WICHTIG:** Der Benutzer (BENID) muss in der FinanzOnline-Benutzerverwaltung als **Webservice-Benutzer** konfiguriert sein.
>
> Häufige Fehler:
> - `-1` = Session ungültig oder abgelaufen
> - `-2` = System in Wartung
> - `-3` = Technischer Fehler
> - `-4` = Datumsparameter erforderlich
> - `-5` = Datum zu alt (max. 31 Tage)
> - `-6` = Datumsbereich zu groß (max. 7 Tage)

---

## Inhaltsverzeichnis

- [Aufbewahrungspflichten](#aufbewahrungspflichten)
- [BMF-Ratenlimits](#bmf-ratenlimits)
- [Schnellstart](#schnellstart)
- [Verwendung](#verwendung)
- [BMF-Rückgabecodes](#bmf-rückgabecodes)
- [Weitere Dokumentation](#weitere-dokumentation)

---

## Schnellstart

Ihr IT-Personal sollte diese Anwendung problemlos installieren können. Bei Bedarf an Support können Sie den Autor für bezahlten Support kontaktieren.


### Empfohlen: Ausführung via uvx für automatisch die neueste Version

UV - der ultraschnelle Installer - geschrieben in Rust (10-20x schneller als pip/poetry)

```bash
# Python installieren (erfordert >= **Python 3.10+**)
# UV installieren
pip install --upgrade uv
# Konfigurationsdateien erstellen
uvx finanzonline_databox@latest config-deploy --target user
```

Erstellen Sie Ihre persönliche Konfigurationsdatei im `config.d/`-Verzeichnis (Einstellungen werden tief zusammengeführt, sodass Updates der Standardkonfigurationen Ihre Einstellungen nicht beeinflussen):

```bash
# Linux:   ~/.config/finanzonline-databox/config.d/99-myconfig.toml
# macOS:   ~/Library/Application Support/bitranox/FinanzOnline DataBox/config.d/99-myconfig.toml
# Windows: %APPDATA%\bitranox\FinanzOnline DataBox\config.d\99-myconfig.toml
```

```toml
# 99-myconfig.toml - Ihre persönlichen Einstellungen
[finanzonline]
tid = "123456789"           # Teilnehmer-ID
benid = "WEBUSER"           # Benutzer-ID - muss Webservice-Benutzer sein!
pin = "yourpassword"        # Passwort/PIN
herstellerid = "ATU12345678" # Software-Hersteller UID (Ihre österreichische UID eintragen)
output_dir = "~/Documents/FinanzOnline/DataBox"  # Standard-Ausgabeverzeichnis
default_recipients = ["buchhaltung@ihre-firma.at"]  # Empfänger für Sync-Zusammenfassung
document_recipients = ["archiv@ihre-firma.at"]  # Empfänger für Dokument-Anhänge
email_format = "both"       # "html", "plain" oder "both"

[email]
smtp_hosts = ["smtp.beispiel.at:587"]
from_address = "databox@ihre-firma.at"
```

```bash
# Alle ungelesenen Dokumente auflisten
uvx finanzonline_databox@latest list

# Alle neuen Dokumente herunterladen
uvx finanzonline_databox@latest sync --output ./archiv
```

Für alternative Installationswege (pip, pipx, uvx, Source-Builds) siehe [INSTALL_de.md](INSTALL_de.md).

---

## Verwendung

```bash
# Alle ungelesenen Dokumente auflisten (Standard)
finanzonline-databox list

# Nur Bescheide auflisten
finanzonline-databox list --erltyp B

# Nur Protokolle mit Referenz UID auflisten
finanzonline-databox list -t P -r UID

# Dokumente der letzten 31 Tage auflisten
finanzonline-databox list --days 31

# Nur ungelesene Dokumente der letzten 7 Tage
finanzonline-databox list --days 7 --unread

# Nur gelesene Dokumente der letzten 31 Tage
finanzonline-databox list --days 31 --read

# Alle Dokumente der letzten 31 Tage (gelesen und ungelesen)
finanzonline-databox list --days 31 --all

# Ein bestimmtes Dokument herunterladen
finanzonline-databox download abc123def456xyz --output ./downloads

# Alle neuen Dokumente in ein Verzeichnis synchronisieren (nur ungelesene, Standard)
finanzonline-databox sync --output ./databox-archiv

# Alle Dokumente synchronisieren (gelesen und ungelesen)
finanzonline-databox sync --output ./databox-archiv --all

# Nur Bescheide synchronisieren
finanzonline-databox sync --output ./bescheide --erltyp B

# Nur Protokolle mit Referenz UID synchronisieren
finanzonline-databox sync -t P -r UID

# Dokumente der letzten 31 Tage synchronisieren
finanzonline-databox sync --days 31 --all

# Dokumente synchronisieren und als E-Mail-Anhang versenden
finanzonline-databox sync --document-recipient archiv@firma.at

# JSON-Ausgabe für Scripting
finanzonline-databox list --format json
```

Die Ergebnisse werden angezeigt und optional eine E-Mail mit den Ergebnissen an die konfigurierten E-Mail-Adressen gesendet.

### E-Mail-Benachrichtigungen

```bash
# Zusammenfassung an Standard-Empfänger (aus Konfiguration)
finanzonline-databox sync --output ./archiv

# Zusammenfassung an spezifische Empfänger
finanzonline-databox sync --recipient admin@firma.at --recipient buchhaltung@firma.at

# Jedes Dokument als E-Mail-Anhang an separate Empfänger
finanzonline-databox sync --document-recipient archiv@firma.at

# Beides kombinieren
finanzonline-databox sync --recipient admin@firma.at --document-recipient archiv@firma.at
```

---

## BMF-Rückgabecodes

| Code | Bedeutung |
|------|-----------|
| `0` | Erfolg |
| `-1` | Session ungültig oder abgelaufen |
| `-2` | System in Wartung (retry später) |
| `-3` | Technischer Fehler (retry später) |
| `-4` | Datumsparameter erforderlich (ts_zust_von/bis) |
| `-5` | ts_zust_von zu alt (max. 31 Tage in der Vergangenheit) |
| `-6` | Datumsbereich zu groß (max. 7 Tage zwischen von und bis) |

---

## Weitere Dokumentation

- [Installationsanleitung (DE)](INSTALL_de.md) | [Installation Guide (EN)](INSTALL_en.md)
- [Konfigurationsreferenz (DE)](CONFIGURATION_de.md) | [Configuration Reference (EN)](CONFIGURATION_en.md)
- [CLI-Referenz (DE)](CLI_REFERENCE_de.md) | [CLI Reference (EN)](CLI_REFERENCE_en.md)
- [Python-API-Referenz (DE)](API_REFERENCE_de.md) | [Python API Reference (EN)](API_REFERENCE_en.md)
- [BMF-Rückgabecodes (DE)](RETURNCODES_de.md) | [BMF Return Codes (EN)](RETURNCODES_en.md)
- [Entwicklungshandbuch](DEVELOPMENT.md)
- [Contributor-Leitfaden](CONTRIBUTING.md)
- [Changelog](CHANGELOG.md)
- [Modulreferenz](docs/systemdesign/module_reference.md)
- [Lizenz](LICENSE)
