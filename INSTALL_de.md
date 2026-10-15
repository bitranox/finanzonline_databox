# Installationsanleitung

> Der CLI-Stack verwendet `rich-click`, das `rich`-Styling auf click-Ergonomie aufbaut.

Diese Anleitung beschreibt alle unterstützten Methoden zur Installation von `finanzonline_databox`,
einschließlich isolierter Umgebungen und System-Paketmanager. Wählen Sie die Option, die zu Ihrem Workflow passt.


## Wir empfehlen `uv` zur Installation des Pakets

### 🔹 `uv` = Ultraschneller Python-Paketmanager

→ Blitzschneller Ersatz für `pip`, `venv`, `pip-tools` und `poetry`,
geschrieben in Rust, kompatibel mit PEP 621 (`pyproject.toml`)

### 🔹 `uvx` = On-Demand-Tool-Runner

→ Führt Tools temporär in isolierten Umgebungen aus, ohne sie global zu installieren


## ⚙️ Installation

```bash
# empfohlen unter Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
# alternativ
pip install uv
# alternativ
python -m pip install uv
```

---

## 🧠 Grundprinzip

`uv` vereint die Fähigkeiten von:

* **pip** (Paketinstallation)
* **venv** (virtuelle Umgebungen)
* **pip-tools** (Lockfiles)
* **poetry** (Projektverwaltung)
* **pipx** (Tool-Ausführung)

Alles über eine einzige Befehlssuite.

---

## 🧭 Vergleich mit Alternativen

| Tool         | Geschwindigkeit | Lockfile | Tool-Ausführung | pyproject-Unterstützung |
|--------------|-----------------|----------|-----------------|-------------------------|
| pip          | mittel          | ❌       | ❌              | teilweise               |
| poetry       | langsam         | ✅       | ❌              | ✅                      |
| pipx         | mittel          | ❌       | ✅              | ❌                      |
| **uv + uvx** | ⚡ sehr schnell | ✅       | ✅              | ✅                      |

---

## 🪶 Hauptfunktionen

| Funktion                    | Beschreibung                                          |
|-----------------------------|-------------------------------------------------------|
| **Sehr schnell**            | Geschrieben in Rust (10–20× schneller als pip/poetry) |
| **Deterministische Builds** | via `uv.lock`                                         |
| **Isolierte Tools (`uvx`)** | Keine globalen Installationen erforderlich            |
| **PEP-kompatibel**          | Unterstützt `pyproject.toml`, PEP 621                 |
| **Cache-Sharing**           | Wiederverwendung von Paketen aus dem globalen Cache   |
| **Kompatibel**              | Funktioniert mit bestehenden virtuellen Umgebungen    |


---

## 📚 Weitere Ressourcen

* 🔗 [https://docs.astral.sh/uv](https://docs.astral.sh/uv)
* 🔗 [https://astral.sh/blog/uv](https://astral.sh/blog/uv)
* 🔗 [https://github.com/astral-sh/uv](https://github.com/astral-sh/uv)

---


## Warum wir uv empfehlen: Schutz vor Supply-Chain-Angriffen

Dieses Repository enthält eine `uv.lock`. Sie legt jedes Paket, das das Projekt braucht,
einschließlich der transitiven Abhängigkeiten, auf eine exakte Version und auf die Hashes der
Dateien dieser Version fest. Die Einstellung `exclude-newer` unter `[tool.uv]` in `pyproject.toml`
fügt eine Wartezeit hinzu: uv nimmt keine Version in die Lock-Datei auf, die jünger ist als diese
Wartezeit. Die CI installiert aus der Lock-Datei. Eine gekaperte Version, die innerhalb der
Wartezeit wieder zurückgezogen wird, erreicht unsere Builds deshalb nie, und eine Datei mit
abweichendem Hash wird abgelehnt.

Dieser Schutz bleibt in diesem Repository. Das installierbare Paket gibt für seine Abhängigkeiten
nur Untergrenzen (`>=`) an. Ein einfaches `pip install` nimmt deshalb von jeder transitiven
Abhängigkeit die neueste Version, die es im Moment der Installation gibt. Wurde eine davon eine
Stunde vorher gekapert, bekommen Sie die gekaperte Version. `pipx install` und `uv tool install`
ohne Optionen verhalten sich genauso.

So installieren Sie das Kommandozeilenwerkzeug mit einer eigenen Wartezeit (uv überspringt dann
jede Version, die jünger als 7 Tage ist, auch transitive), oder führen genau den Stand aus, den
unsere CI testet:

```bash
uv tool install --exclude-newer "7 days" finanzonline_databox
git clone https://github.com/bitranox/finanzonline_databox.git && cd finanzonline_databox && uv sync --locked && uv run finanzonline-databox --help
```

Wenn Ihr eigenes Projekt von finanzonline_databox abhängt, geben Sie ihm dieselbe Wartezeit (hier als Beispiel
7 Tage) und committen Sie die `uv.lock`, die `uv add finanzonline_databox` schreibt:

```toml
[tool.uv]
exclude-newer = "7 days"
```

## 1. Installation via uv

```bash
# Virtuelle Umgebung erstellen und aktivieren (optional, aber empfohlen)
uv venv
# macOS/Linux
source .venv/bin/activate
# Windows (PowerShell)
.venv\Scripts\Activate.ps1

# Installation via uv von PyPI
uv pip install finanzonline_databox
# optionale Installation von GitHub
uv pip install "git+https://github.com/bitranox/finanzonline_databox"
# Upgrade
uv tool upgrade --all
```

## 2. Einmalige Ausführung via uvx

Einmalige/Ad-hoc-Nutzung ermöglicht die Ausführung des Tools, ohne es dem Projekt hinzuzufügen.
Mehrere Projekte mit unterschiedlichen Tool-Versionen bleiben isoliert, sodass jedes "seine" uvx-Version ohne Konflikte verwenden kann.

```bash
# Ausführung von PyPI
uvx finanzonline_databox
# Ausführung von GitHub
uvx --from git+https://github.com/bitranox/finanzonline_databox.git finanzonline_databox

```

---

## 3. Installation via pip

```bash
# optional, Installation in einer venv (empfohlen)
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
# Installation von PyPI
pip install finanzonline_databox
# optionale Installation von GitHub
pip install "git+https://github.com/bitranox/finanzonline_databox"
# optionale Entwicklungsinstallation von lokal
pip install -e .[dev]
# optionale Installation von lokal (nur Runtime):
pip install .
```

## 4. Benutzer-Installation (ohne Virtualenv) - von lokal

```bash
# Installation von PyPI
pip install --user finanzonline_databox
# optionale Installation von GitHub
pip install --user "git+https://github.com/bitranox/finanzonline_databox"
# optionale Installation von lokal
pip install --user .
```

> Hinweis: Dies respektiert PEP 668. Vermeiden Sie die Verwendung bei System-Python-Builds,
> die als "externally managed" gekennzeichnet sind. Stellen Sie sicher, dass `~/.local/bin` (POSIX)
> in Ihrem PATH ist, damit die CLI verfügbar ist.

## 5. pipx (Isolierte CLI-freundliche Umgebung)

```bash
# pipx via pip installieren
python -m pip install pipx
# optional pipx via apt installieren
sudo apt install python-pipx
# Installation via pipx von PyPI
pipx install finanzonline_databox
# optionale Installation via pipx von GitHub
pipx install "git+https://github.com/bitranox/finanzonline_databox"
# optionale Installation von lokal
pipx install .
pipx upgrade finanzonline_databox
```

## 6. Aus Build-Artefakten

```bash
python -m build
pip install dist/finanzonline_databox-*.whl
pip install dist/finanzonline_databox-*.tar.gz   # sdist
```

## 7. Poetry oder PDM verwaltete Umgebungen

```bash
# Poetry
poetry add finanzonline_databox     # als Abhängigkeit
poetry install                   # für lokale Entwicklung

# PDM
pdm add finanzonline_databox
pdm install
```

## 8. Direkte Installation von Git

```bash
pip install "git+https://github.com/bitranox/finanzonline_databox#egg=finanzonline_databox"
```

## 9. System-Paketmanager (optionale Vertriebskanäle)

- Deb/RPM: Paketierung mit `fpm` für OS-native Bereitstellung

Alle Methoden registrieren sowohl den Befehl `finanzonline_databox` als auch
`finanzonline-databox` in Ihrem PATH.

---

## Zugangsdaten-Konfiguration

Nach der Installation müssen Sie Ihre FinanzOnline-Zugangsdaten konfigurieren.

### Option A: Konfigurationsdateien bereitstellen (Empfohlen)

Stellen Sie eine benutzerspezifische Konfigurationsdatei mit allen dokumentierten Einstellungen bereit:

```bash
# Benutzerkonfigurationsvorlage bereitstellen
finanzonline-databox config-deploy --target user

# Die generierte Konfigurationsdatei bearbeiten
# Linux:   ~/.config/finanzonline-databox/config.toml
# macOS:   ~/Library/Application Support/bitranox/FinanzOnline DataBox/config.toml
# Windows: %APPDATA%\bitranox\FinanzOnline DataBox\config.toml
```

Für systemweite Konfiguration (erfordert Berechtigungen):

```bash
# Systemweite Konfigurationsvorlage bereitstellen
sudo finanzonline-databox config-deploy --target app

# Die generierte Konfigurationsdatei bearbeiten
# Linux:   /etc/xdg/finanzonline-databox/config.toml
# macOS:   /Library/Application Support/bitranox/FinanzOnline DataBox/config.toml
# Windows: %PROGRAMDATA%\bitranox\FinanzOnline DataBox\config.toml
```

### Option B: Eine .env-Datei verwenden (Optional)

Alternativ erstellen Sie eine `.env`-Datei in Ihrem Arbeitsverzeichnis (siehe [.env.example](.env.example) für eine vollständige Vorlage):

```bash
# FinanzOnline-Zugangsdaten (ERFORDERLICH)
FINANZONLINE__TID=123456789           # Teilnehmer-ID (8-12 alphanumerisch)
FINANZONLINE__BENID=WEBUSER           # Benutzer-ID (5-12 Zeichen, muss als Webservice-Benutzer in FinanzOnline angelegt sein!)
FINANZONLINE__PIN=yourpassword        # Passwort (5-128 Zeichen)
FINANZONLINE__HERSTELLERID=ATU12345678  # Software-Hersteller UID (Ihre österreichische UID)
FINANZONLINE__DEFAULT_RECIPIENTS=["admin@ihrfirma.at","buchhaltung@ihrfirma.at"]

# E-Mail-Konfiguration (für Benachrichtigungen)
EMAIL__SMTP_HOSTS=["smtp.beispiel.at:587"]
EMAIL__FROM_ADDRESS=alerts@beispiel.at
```

### Option C: Umgebungsvariablen verwenden

Umgebungsvariablen direkt setzen (mit App-Präfix):

```bash
export FINANZONLINE_DATABOX___FINANZONLINE__TID=123456789
export FINANZONLINE_DATABOX___FINANZONLINE__BENID=WEBUSER
export FINANZONLINE_DATABOX___FINANZONLINE__PIN=yourpassword
export FINANZONLINE_DATABOX___FINANZONLINE__HERSTELLERID=ATU12345678
```

### Installation überprüfen

```bash
# wenn installiert - alle ungelesenen DataBox-Dokumente auflisten
finanzonline-databox list
# mit uvx, neueste Version ohne Installation ausführen
uvx finanzonline_databox@latest list
```

Für detaillierte Konfigurationsoptionen siehe [CONFIGURATION_de.md](CONFIGURATION_de.md).
