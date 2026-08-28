from __future__ import annotations

import argparse
import base64
import os
import sys
import time
from pathlib import Path

import webview

from desktop.bridge import DesktopBridge


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SPLASH_MINIMUM_SECONDS = 1.8


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


def splash_html() -> str:
    """Return the lightweight startup document for the separate splash window."""
    logo_data = base64.b64encode(resource_path("assets/logo.png").read_bytes()).decode()
    return f"""<!doctype html>
<html lang="de"><head><meta charset="utf-8"><style>
  :root {{ color-scheme: light; font-family: -apple-system, BlinkMacSystemFont, sans-serif; }}
  * {{ box-sizing: border-box; }}
  html, body {{ width: 100%; height: 100%; margin: 0; overflow: hidden; }}
  body {{ display: grid; place-content: center; background: #fff; color: #20242a; text-align: center; }}
  main {{ width: 640px; height: 390px; padding: 48px 72px 42px; border: 1px solid #e3e6ea; }}
  img {{ display: block; width: 390px; height: 76px; margin: 0 auto 24px; object-fit: contain; }}
  h1 {{ margin: 0; font-size: 27px; line-height: 1.2; letter-spacing: -.3px; }}
  p {{ margin: 6px 0 28px; color: #6b7280; font-size: 14px; }}
  span {{ display: block; margin-bottom: 11px; color: #6b7280; font-size: 12px; }}
  .track {{ position: relative; width: 400px; height: 8px; margin: auto; overflow: hidden;
            border-radius: 999px; background: #f0d9df; }}
  i {{ position: absolute; inset: 0 auto 0 -35%; width: 35%; border-radius: inherit;
       background: #b20d30; animation: progress 1.15s ease-in-out infinite; }}
  @keyframes progress {{ to {{ left: 100%; }} }}
</style></head><body><main>
  <img src="data:image/png;base64,{logo_data}" alt="holz.bau forschungs gmbh">
  <h1>KI-Bemessungstool</h1>
  <p>KI-gestützte Bemessung von Holzbauverbindungen</p>
  <span>KI-Bemessungstool wird gestartet …</span>
  <div class="track"><i></i></div>
</main></body></html>"""


def launch(dev_url: str | None = None) -> None:
    """Start the shared React/pywebview shell."""
    bridge = DesktopBridge()
    splash = webview.create_window(
        "KI-Bemessungstool",
        html=splash_html(),
        width=640,
        height=390,
        min_size=(640, 390),
        resizable=False,
        frameless=True,
        easy_drag=True,
        on_top=True,
        background_color="#FFFFFF",
    )
    main_window = webview.create_window(
        "KI-Bemessungstool",
        frontend_url(dev_url),
        js_api=bridge,
        width=1500,
        height=940,
        min_size=(1100, 700),
        hidden=True,
        background_color="#F3F4F6",
    )

    def complete_startup() -> None:
        # Both windows share pywebview's single Cocoa event loop. This worker
        # only coordinates readiness and never starts a second GUI toolkit.
        splash.events.loaded.wait()
        splash_visible_since = time.monotonic()
        main_window.events.loaded.wait()
        ready_deadline = time.monotonic() + 10
        while True:
            try:
                ready = bool(main_window.evaluate_js("Boolean(window.__KI_APP_READY__)"))
            except Exception:
                ready = False
            if ready or time.monotonic() >= ready_deadline:
                if not ready:
                    print(
                        "Warnung: React-Readiness wurde nicht innerhalb von 10 Sekunden "
                        "bestätigt; Hauptfenster wird trotzdem geöffnet.",
                        file=sys.stderr,
                        flush=True,
                    )
                break
            time.sleep(0.05)
        remaining = SPLASH_MINIMUM_SECONDS - (time.monotonic() - splash_visible_since)
        if remaining > 0:
            time.sleep(remaining)
        # On Cocoa, destroying pywebview's primary window also terminates the
        # shared event loop. Keep it hidden until the visible main window
        # closes, then destroy it as part of normal application shutdown.
        splash.hide()
        main_window.show()

    def close_primary_window() -> None:
        splash.destroy()

    main_window.events.closed += close_primary_window

    webview.start(
        complete_startup,
        debug=bool(dev_url or os.getenv("KI_TOOL_WEB_DEBUG")),
    )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dev-url")
    args = parser.parse_args(argv)
    launch(args.dev_url)


if __name__ == "__main__":
    main()
