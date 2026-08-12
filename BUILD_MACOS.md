# macOS-App bauen

Der Build erzeugt eine eigenständige Apple-Silicon-App unter
`dist/KI-Bemessungstool.app`.

## Vorbereitung

```bash
python -m pip install -r requirements.txt
python -m pip install -r requirements-build.txt
```

## Build

```bash
./build_macos.sh
```

Alternativ kann die versionierte Spec-Datei direkt verwendet werden:

```bash
python -m PyInstaller --noconfirm --clean KI-Bemessungstool.spec
```

Die Verzeichnisse `build/` und `dist/` sind lokale Build-Artefakte und werden
nicht in Git aufgenommen. Die Spec-Datei, das Build-Skript und alle benötigten
Quelldaten bleiben versioniert. Der lokale Build kann auf dem Build-Mac direkt
gestartet werden. Für die Weitergabe an andere Macs wären zusätzlich eine
Apple-Developer-Signatur und Notarisierung erforderlich.

## API-Key

Es wird kein API-Key in die App oder in den Build eingebettet. Ohne gesetzten
`OPENAI_API_KEY` startet die Anwendung im vorhandenen lokalen Demo-Modus.
Soll das OpenAI-LLM verwendet werden, muss der Schlüssel außerhalb des
Repositories in der Benutzerumgebung von macOS bereitgestellt werden.

Für einen Start per Finder kann der Schlüssel sicher im macOS-Schlüsselbund
unter dem Dienstnamen `KI-Bemessungstool OpenAI` gespeichert werden:

```bash
security add-generic-password -U -s "KI-Bemessungstool OpenAI" \
  -a "$USER" -w
```

Der Befehl fragt den Wert verdeckt ab. Die App prüft zuerst
`OPENAI_API_KEY`, danach diesen Schlüsselbund-Eintrag. Der Schlüssel wird
weder in Git noch in das App-Bundle geschrieben.

Die normale Entwicklung bleibt unverändert möglich:

```bash
python app.py
```
