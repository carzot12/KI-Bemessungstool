from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import webview

from desktop.bridge import DesktopBridge


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def resource_path(relative_path: str | Path) -> Path:
    """Resolve bundled and development resources from one central place."""
    relative = Path(relative_path)
    candidates: list[Path] = []

    if getattr(sys, "frozen", False):
        bundle_root = getattr(sys, "_MEIPASS", None)
        if bundle_root:
            candidates.append(Path(bundle_root))

        # Defensive macOS bundle fallbacks. Depending on the PyInstaller
        # version, collected data can live below Resources or Frameworks.
        executable = Path(sys.executable).resolve()
        if executable.parent.name == "MacOS":
            contents = executable.parent.parent
            candidates.extend((contents / "Resources", contents / "Frameworks"))

    candidates.append(PROJECT_ROOT)
    for base in candidates:
        resolved = base / relative
        if resolved.exists():
            return resolved

    # Return the canonical expected location for a useful error message.
    return candidates[0] / relative


def frontend_index_path() -> Path:
    return resource_path(Path("frontend") / "dist" / "index.html")


def frontend_url(dev_url: str | None = None) -> str:
    if dev_url:
        return dev_url
    configured = os.getenv("KI_TOOL_FRONTEND_URL", "").strip()
    if configured:
        return configured
    dist_index = frontend_index_path()
    if not dist_index.is_file():
        raise FileNotFoundError(
            "frontend/dist/index.html fehlt. Starte `npm run build` im Ordner "
            "frontend oder verwende `python -m desktop.main --dev-url "
            f"http://localhost:5173`. Gesuchter Pfad: {dist_index}"
        )
    return dist_index.as_uri()


def launch(dev_url: str | None = None) -> None:
    """Start the shared React/pywebview shell."""
    bridge = DesktopBridge()
    webview.create_window(
        "KI-Bemessungstool",
        frontend_url(dev_url),
        js_api=bridge,
        width=1500,
        height=940,
        min_size=(1100, 700),
        background_color="#F3F4F6",
    )
    webview.start(debug=bool(dev_url or os.getenv("KI_TOOL_WEB_DEBUG")))


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dev-url")
    args = parser.parse_args(argv)
    launch(args.dev_url)


if __name__ == "__main__":
    main()
