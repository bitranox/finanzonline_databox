# BMF-Rückgabecodes

> [English version available (RETURNCODES_en.md)](RETURNCODES_en.md)

Dieses Dokument beschreibt alle Rückgabecodes des österreichischen BMF (Bundesministerium für Finanzen) FinanzOnline DataBox-Download-Webservices.

---

## Übersicht

Der FinanzOnline DataBox-Webservice gibt numerische Codes zurück, um das Ergebnis von Operationen anzuzeigen. Code `0` bedeutet Erfolg; negative Codes zeigen Fehler an.

---

## Erfolgscode

| Code | Bedeutung            | Schweregrad | Wiederholbar |
|------|----------------------|-------------|--------------|
| 0    | Operation erfolgreich| success     | -            |

---

## Session-/Authentifizierungscodes

Diese Codes werden bei der Anmeldung und Session-Verwaltung zurückgegeben.

| Code | Bedeutung                          | Schweregrad | Wiederholbar |
|------|------------------------------------|-------------|--------------|
| -1   | Session ungültig oder abgelaufen   | error       | Nein         |
| -2   | Systemwartung                      | warning     | Ja           |
| -3   | Technischer Fehler                 | error       | Ja           |

### Häufige Authentifizierungsprobleme

- **Code -1 (Session ungültig):** Die Session ist abgelaufen oder wurde nie aufgebaut. Erneut authentifizieren und nochmal versuchen.
- **Code -2 (Systemwartung):** Die BMF-Server sind in Wartung. Einige Minuten warten und erneut versuchen.
- **Code -3 (Technischer Fehler):** Temporäres Server-Problem. Später erneut versuchen.

---

## DataBox-spezifische Codes

Diese Codes werden bei DataBox-Auflistungs- und Download-Operationen zurückgegeben.

| Code | Bedeutung                                                           | Schweregrad | Wiederholbar |
|------|---------------------------------------------------------------------|-------------|--------------|
| -4   | Datumsparameter erforderlich (ts_zust_von und ts_zust_bis)          | error       | Nein         |
| -5   | ts_zust_von darf nicht mehr als 31 Tage in der Vergangenheit liegen | error       | Nein         |
| -6   | ts_zust_bis darf nicht mehr als 7 Tage nach ts_zust_von liegen      | error       | Nein         |

### Datumsparameter-Regeln

Bei der Filterung nach Datumsbereich müssen beide Parameter angegeben werden:

- **ts_zust_von** (Startdatum): Maximal 31 Tage in der Vergangenheit
- **ts_zust_bis** (Enddatum): Maximal 7 Tage nach ts_zust_von

**Beispiele für gültige Datumsbereiche:**
```
ts_zust_von = 2024-01-01, ts_zust_bis = 2024-01-07  (7 Tage - OK)
ts_zust_von = 2024-01-01, ts_zust_bis = 2024-01-05  (4 Tage - OK)
```

**Beispiele für ungültige Datumsbereiche:**
```
ts_zust_von = 2024-01-01, ts_zust_bis = 2024-01-10  (9 Tage - FEHLER: max. 7 Tage)
ts_zust_von = 2023-01-01  (mehr als 31 Tage her - FEHLER)
```

---

## CLI-Exit-Codes

Die CLI verwendet eigene Exit-Codes, die sich von den FinanzOnline-Rückgabecodes unterscheiden:

| Exit-Code | Bedeutung              |
|-----------|------------------------|
| 0         | Erfolg                 |
| 1         | Keine Einträge gefunden|
| 2         | Konfigurationsfehler   |
| 3         | Authentifizierungsfehler|
| 4         | Download-Fehler        |
| 5         | I/O-Fehler             |

---

## Schweregrade

| Schweregrad | Beschreibung                                          |
|-------------|-------------------------------------------------------|
| `success`   | Operation erfolgreich abgeschlossen                   |
| `warning`   | Warnung - Aktion möglicherweise erforderlich          |
| `error`     | Fehler - Anfrage konnte nicht verarbeitet werden      |
| `critical`  | Kritisch - Konfiguration oder Berechtigung prüfen     |

---

## Wiederholbare Fehler

Fehler mit "Wiederholbar: Ja" können nach einer Wartezeit erneut versucht werden:

- **Code -2 (Systemwartung):** Einige Minuten warten und erneut versuchen.
- **Code -3 (Technischer Fehler):** Temporäres Problem, später erneut versuchen.

---

## BMF-Ratenlimits

Der FinanzOnline DataBox-Webservice kann Ratenlimits haben. Das Tool enthält integriertes Ratenlimit-Tracking (Standard: 50 Abfragen pro 24 Stunden), das:

- Warnt, bevor Sie BMF-Limits erreichen
- E-Mail-Benachrichtigungen bei Überschreitung sendet
- Abfragen NICHT blockiert - das BMF führt die eigentliche Durchsetzung durch

Konfiguration über `finanzonline.ratelimit_queries` und `finanzonline.ratelimit_hours`.
