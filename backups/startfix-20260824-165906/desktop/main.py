from __future__ import annotations

import argparse
import os
from pathlib import Path

import webview

from desktop.bridge import DesktopBridge


ROOT = Path(__file__).resolve().parents[1]
DIST_INDEX = ROOT / "frontend" / "dist" / "index.html"


def frontend_url(dev_url: str | None = None) -> str:
    if dev_url:
        return dev_url
    configured = os.getenv("KI_TOOL_FRONTEND_URL", "").strip()
    if configured:
        return configured
    if not DIST_INDEX.exists():
        raise FileNotFoundError(
            "frontend/dist fehlt. Starte `npm run build` im Ordner frontend "
            "oder verwende `python -m desktop.main --dev-url http://localhost:5173`."
        )
    return DIST_INDEX.as_uri()


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
