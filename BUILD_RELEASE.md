# Automatische Desktop-Builds

GitHub Actions baut das KI-Bemessungstool nach jedem Push getrennt auf
macOS und Windows. Der Workflow liegt unter `.github/workflows/build.yml`
und kann zusätzlich manuell gestartet werden.

## Ablauf

Beide Runner verwenden Python 3.12 und installieren die Abhängigkeiten aus
`requirements-dev.txt` und `requirements-build.txt`. Danach wird zuerst die
vollständige Testsuite mit folgendem Befehl ausgeführt:

```bash
python -m pytest
```

Nur bei erfolgreichen Tests ruft der jeweilige Job PyInstaller mit
`KI-Bemessungstool.spec` auf. Die Spec bindet ausschließlich die notwendigen
lokalen Laufzeitdaten ein:

- `assets/logo.png`
- `infopol/materials/timber.json`
- `ai/prompts/stabduebel_system.txt`

Die Python-Module für Berechnung, ÖNORM-Validierung, Optimierung und
Materialverwaltung werden durch PyInstaller analysiert und eingebunden.
`Unterlagen/`, `xxx/`, API-Schlüssel und `.env`-Dateien werden nicht verpackt.

## Build herunterladen

1. Auf GitHub das Repository öffnen.
2. Den Reiter **Actions** wählen.
3. Den Workflow **Desktop-Apps bauen** und den gewünschten erfolgreichen Lauf
   öffnen.
4. Unten unter **Artifacts** eines der Artefakte herunterladen:
   - `KI-Bemessungstool-macOS`
   - `KI-Bemessungstool-Windows`
5. Das heruntergeladene Artefakt und anschließend die darin enthaltene ZIP-Datei
   entpacken.

Das macOS-Paket enthält `KI-Bemessungstool.app`. Das Windows-Paket enthält die
eigenständige Datei `KI-Bemessungstool.exe`.

## Neuen Build auslösen

Ein normaler Push startet beide Builds automatisch:

```bash
git add .github/workflows/build.yml KI-Bemessungstool.spec \
  assets/app_icon.ico BUILD_RELEASE.md .gitignore
git commit -m "Automatische Desktop-Builds einrichten"
git push
```

Alternativ im GitHub-Reiter **Actions** den Workflow öffnen, **Run workflow**
wählen und den gewünschten Branch starten.

## Lokale Builds

macOS:

```bash
python -m pip install -r requirements-build.txt
./build_macos.sh
```

Windows in PowerShell:

```powershell
py -m pip install -r requirements.txt -r requirements-build.txt
py -m PyInstaller --noconfirm --clean KI-Bemessungstool.spec
```

## Signierung und Betriebssystemwarnungen

Die erzeugten Anwendungen sind nicht mit einem Apple Developer ID-Zertifikat
signiert, nicht notarisiert und nicht mit einem Windows-Code-Signing-Zertifikat
signiert. Deshalb können macOS Gatekeeper und Microsoft Defender/SmartScreen
beim ersten Start warnen oder den direkten Start blockieren.

Für eine öffentliche Verteilung sollten später Apple-Code-Signing und
Notarisierung sowie Windows-Code-Signing ergänzt werden. Dafür benötigte
Zertifikate und Passwörter dürfen ausschließlich als geschützte GitHub Secrets
verwaltet und niemals in Repository oder App eingebettet werden.

Die Anwendung enthält keinen persönlichen OpenAI-API-Key. Ohne gesetzten
`OPENAI_API_KEY` verwendet sie weiterhin die lokale Demo-/Fallback-Erkennung.
