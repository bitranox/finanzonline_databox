# CLI-Referenz

Dieses Dokument beschreibt alle CLI-Befehle und Optionen für `finanzonline_databox`.

## Globale Optionen

Diese Optionen gelten für alle Befehle:

| Option                         | Standard         | Beschreibung                                                           |
|--------------------------------|------------------|------------------------------------------------------------------------|
| `--traceback / --no-traceback` | `--no-traceback` | Vollständigen Python-Traceback bei Fehlern anzeigen                    |
| `--profile NAME`               | `None`           | Konfiguration aus benanntem Profil laden (z.B. 'production', 'test')   |
| `--version`                    | -                | Version anzeigen und beenden                                           |
| `-h, --help`                   | -                | Hilfe anzeigen und beenden                                             |

## Befehle

Der CLI-Befehl ist unter `finanzonline-databox` und `finanzonline_databox` registriert - Sie können beide verwenden.

---

### `list` - DataBox-Dokumente auflisten

```bash
finanzonline-databox list [OPTIONEN]
```

Listet alle Dokumente in der FinanzOnline DataBox mit optionalen Filtern auf.

**Optionen:**

| Option        | Kurz | Standard   | Beschreibung                                                              |
|---------------|------|------------|---------------------------------------------------------------------------|
| `--erltyp`    | `-t` | `""`       | Dokumenttyp-Filter: B, M, I, P, EU (leer = alle)                          |
| `--reference` | `-r` | `""`       | Referenz-Filter (Anbringen, z.B. UID, E1)                                 |
| `--from`      | -    | `None`     | Startdatum (YYYY-MM-DD, max. 31 Tage in der Vergangenheit)                |
| `--to`        | -    | `None`     | Enddatum (YYYY-MM-DD, max. 7 Tage nach Startdatum)                        |
| `--days`      | `-d` | `None`     | Dokumente der letzten N Tage (überschreibt --from/--to, max. 31)          |
| `--unread`    | `-u` | `--unread` | Nur ungelesene Dokumente anzeigen **(Standard)**                          |
| `--read`      | -    | -          | Nur gelesene Dokumente anzeigen                                           |
| `--all`       | `-a` | -          | Alle Dokumente anzeigen (gelesen und ungelesen)                           |
| `--format`    | -    | `human`    | Ausgabeformat: `human` oder `json`                                        |

> **Hinweis:** Die Optionen `--unread`, `--read` und `--all` schließen sich gegenseitig aus. Standard ist `--unread`.
>
> **Automatischer Datumsbereich:** Bei Verwendung von `--all` oder `--read` ohne `--days` oder `--from/--to` wird automatisch `--days 31` gesetzt, da die BMF-API gelesene Dokumente nur mit Datumsbereich zurückgibt.
>
> **Implementierungsdetail:** Die BMF-API erlaubt pro Anfrage maximal 7 Tage. Bei größeren Zeiträumen teilt die CLI die Anfrage automatisch auf und aggregiert die Ergebnisse.

**API-Einschränkungen (BMF DataBox-Webservice):**

| Einschränkung                    | Wert                        |
|----------------------------------|-----------------------------|
| `--from` (ts_zust_von)           | Max. 31 Tage in der Vergangenheit |
| `--to` - `--from` (Zeitspanne)   | Max. 7 Tage                 |
| Ohne Datumsfilter                | Nur ungelesene Dokumente    |
| Mit Datumsfilter                 | Gelesene + ungelesene Dokumente |

> **Hinweis:** Nach dem Download wird ein Dokument serverseitig als "gelesen" markiert und erscheint nicht mehr in der Standardliste.

**Dokumenttypen (erltyp):**

| Code | Beschreibung                     |
|------|----------------------------------|
| `B`  | Bescheide, Ergänzungsersuchen    |
| `M`  | Mitteilungen                     |
| `I`  | Informationen                    |
| `P`  | Protokolle                       |
| `EU` | EU-Erledigungen                  |

**Exit-Codes:**

| Code | Bedeutung                |
|------|--------------------------|
| 0    | Erfolg                   |
| 2    | Konfigurationsfehler     |
| 3    | Authentifizierungsfehler |
| 4    | Operationsfehler         |

**Beispiele:**

```bash
# Alle ungelesenen Dokumente auflisten (Standard)
finanzonline-databox list

# Nur Bescheide auflisten
finanzonline-databox list --erltyp B

# Nur Protokolle mit Referenz UID auflisten
finanzonline-databox list -t P -r UID

# Alle Dokumente auflisten (bis zu 31 Tage)
finanzonline-databox list --all

# Nur gelesene Dokumente auflisten (bis zu 31 Tage)
finanzonline-databox list --read

# Dokumente der letzten 31 Tage
finanzonline-databox list --days 31

# Alle Dokumente der letzten 3 Tage
finanzonline-databox list --days 3 --all

# Benutzerdefinierter Datumsbereich (max. 7 Tage Spanne)
finanzonline-databox list --from 2024-12-01 --to 2024-12-07

# Ältere Dokumente abrufen (bis 31 Tage zurück)
finanzonline-databox list --from 2024-11-22 --to 2024-11-29

# JSON-Ausgabe für Skripte
finanzonline-databox list --format json
```

---

### `download` - Ein Dokument herunterladen

```bash
finanzonline-databox download [OPTIONEN] APPLKEY
```

Lädt ein bestimmtes Dokument aus der DataBox über seinen Anwendungsschlüssel herunter.

**Argumente:**

| Argument  | Erforderlich | Beschreibung                                       |
|-----------|--------------|----------------------------------------------------|
| `APPLKEY` | Ja           | Dokument-Anwendungsschlüssel (vom `list`-Befehl)   |

**Optionen:**

| Option       | Kurz | Standard        | Beschreibung                                       |
|--------------|------|-----------------|----------------------------------------------------|
| `--output`   | `-o` | `.` (aktuell)   | Ausgabeverzeichnis (oder aus Konfig `output_dir`)  |
| `--filename` | `-f` | Auto-generiert  | Ausgabedateiname überschreiben                     |

**Exit-Codes:**

| Code | Bedeutung                |
|------|--------------------------|
| 0    | Erfolg                   |
| 2    | Konfigurationsfehler     |
| 3    | Authentifizierungsfehler |
| 4    | Operationsfehler         |

**Beispiele:**

```bash
# Download mit auto-generiertem Dateinamen
finanzonline-databox download abc123def456xyz

# Download in bestimmtes Verzeichnis
finanzonline-databox download abc123def456xyz --output ./downloads

# Download mit benutzerdefiniertem Dateinamen
finanzonline-databox download abc123def456xyz -f mein_bescheid.pdf
```

---

### `sync` - Alle neuen Dokumente synchronisieren

```bash
finanzonline-databox sync [OPTIONEN]
```

Synchronisiert alle Dokumente in ein lokales Verzeichnis. Sendet optional E-Mail-Benachrichtigungen bei neuen Downloads.

**Optionen:**

| Option                             | Kurz | Standard        | Beschreibung                                          |
|------------------------------------|------|-----------------|-------------------------------------------------------|
| `--output`                         | `-o` | `./databox`     | Verzeichnis zum Speichern heruntergeladener Dokumente |
| `--erltyp`                         | `-t` | `""`            | Dokumenttyp-Filter: B, M, I, P, EU                    |
| `--reference`                      | `-r` | `""`            | Referenz-Filter (Anbringen, z.B. UID, E1)             |
| `--days`                           | -    | `31`            | Dokumente der letzten N Tage synchronisieren (max. 31)|
| `--unread`                         | `-u` | `--unread`      | Nur ungelesene Dokumente synchronisieren **(Standard)**|
| `--read`                           | -    | -               | Nur gelesene Dokumente synchronisieren                |
| `--all`                            | `-a` | -               | Alle Dokumente synchronisieren (gelesen und ungelesen)|
| `--skip-existing/--no-skip-existing` | -  | `--skip-existing` | Vorhandene Dateien überspringen                     |
| `--no-email`                       | -    | `False`         | E-Mail-Benachrichtigung deaktivieren                  |
| `--recipient`                      | -    | Konfig-Standard | E-Mail-Empfänger für Zusammenfassung (mehrfach möglich)|
| `--document-recipient`             | -    | `[]`            | E-Mail-Empfänger für Per-Dokument-E-Mails mit Anhang  |
| `--format`                         | -    | `human`         | Ausgabeformat: `human` oder `json`                    |

> **Hinweis:** Die Optionen `--unread`, `--read` und `--all` schließen sich gegenseitig aus. Standard ist `--unread`.
>
> **Implementierungsdetail:** Die BMF-API erlaubt pro Anfrage maximal 7 Tage. Bei größeren Zeiträumen teilt die CLI die Anfrage automatisch auf und aggregiert die Ergebnisse.
>
> **output_dir Konfiguration:** Wenn `finanzonline.output_dir` in der Konfiguration gesetzt ist, wird dieses als Standard verwendet statt `./databox`.

**Exit-Codes:**

| Code | Bedeutung                             |
|------|---------------------------------------|
| 0    | Erfolg (alle synchronisiert)          |
| 1    | Teilerfolg (einige fehlgeschlagen)    |
| 2    | Konfigurationsfehler                  |
| 3    | Authentifizierungsfehler              |
| 4    | Operationsfehler                      |

**Beispiele:**

```bash
# Alle ungelesenen Dokumente nach ./databox synchronisieren (Standard)
finanzonline-databox sync

# In ein bestimmtes Verzeichnis synchronisieren
finanzonline-databox sync --output ./archiv/databox

# Nur Bescheide synchronisieren
finanzonline-databox sync --erltyp B --output ./bescheide

# Nur Protokolle mit Referenz UID synchronisieren
finanzonline-databox sync -t P -r UID

# Dokumente der letzten 7 Tage synchronisieren (nur ungelesene, Standard)
finanzonline-databox sync --days 7

# Dokumente der letzten 7 Tage, nur gelesene
finanzonline-databox sync --days 7 --read

# Alle Dokumente der letzten 7 Tage (gelesen und ungelesen)
finanzonline-databox sync --days 7 --all

# Sync mit JSON-Ausgabe (für Skripte)
finanzonline-databox sync --format json --no-email

# Mit benutzerdefinierten Empfängern
finanzonline-databox sync --recipient admin@beispiel.at --recipient finanzen@beispiel.at

# Dokumente der letzten 31 Tage synchronisieren
finanzonline-databox sync --days 31 --all

# Jedes Dokument als E-Mail-Anhang an separate Empfänger senden
finanzonline-databox sync --document-recipient archiv@beispiel.at

# Kombiniert: Zusammenfassung + Per-Dokument-E-Mails
finanzonline-databox sync --recipient admin@beispiel.at --document-recipient archiv@beispiel.at

# Vorhandene Dateien erneut herunterladen
finanzonline-databox sync --no-skip-existing
```

---

### `config` - Konfiguration anzeigen

```bash
finanzonline-databox config [OPTIONEN]
```

**Optionen:**

| Option      | Standard | Beschreibung                                                                    |
|-------------|----------|---------------------------------------------------------------------------------|
| `--format`  | `human`  | Ausgabeformat: `human` oder `json`                                              |
| `--section` | `None`   | Nur bestimmten Abschnitt anzeigen (z.B. 'finanzonline', 'email', 'lib_log_rich')|
| `--profile` | `None`   | Profil vom Root-Befehl überschreiben                                            |

**Beispiele:**

```bash
# Alle Konfigurationen anzeigen
finanzonline-databox config

# JSON-Ausgabe für Skripte
finanzonline-databox config --format json

# Nur E-Mail-Abschnitt anzeigen
finanzonline-databox config --section email

# Produktionsprofil anzeigen
finanzonline-databox config --profile production
```

---

### `config-deploy` - Konfigurationsdateien bereitstellen

```bash
finanzonline-databox config-deploy [OPTIONEN]
```

**Optionen:**

| Option      | Erforderlich | Standard | Beschreibung                                                    |
|-------------|--------------|----------|-----------------------------------------------------------------|
| `--target`  | Ja           | -        | Zielebene: `user`, `app` oder `host` (kann mehrfach angegeben werden) |
| `--force`   | Nein         | `False`  | Bestehende Konfigurationsdateien überschreiben                  |
| `--profile` | Nein         | `None`   | In bestimmtes Profilverzeichnis bereitstellen                   |

**Beispiele:**

```bash
# Benutzerkonfiguration bereitstellen
finanzonline-databox config-deploy --target user

# Systemweit bereitstellen (erfordert Berechtigungen)
sudo finanzonline-databox config-deploy --target app

# Mehrere Ziele bereitstellen
finanzonline-databox config-deploy --target user --target host

# Bestehende überschreiben
finanzonline-databox config-deploy --target user --force

# In Produktionsprofil bereitstellen
finanzonline-databox config-deploy --target user --profile production
```

---

### `info` - Paketinformationen anzeigen

```bash
finanzonline-databox info
```

Zeigt Paketname, Version, Homepage, Autor und andere Metadaten an.

---

### `hello` - Erfolgspfad testen

```bash
finanzonline-databox hello
```

Gibt eine Begrüßungsmeldung aus, um zu verifizieren, dass die CLI funktioniert.

---

### `fail` - Fehlerbehandlung testen

```bash
finanzonline-databox fail
finanzonline-databox --traceback fail  # Mit vollständigem Traceback
```

Löst absichtlich einen Fehler aus, um die Fehlerbehandlung zu testen.
