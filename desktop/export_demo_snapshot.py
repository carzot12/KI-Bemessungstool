from __future__ import annotations

import json
from pathlib import Path

from desktop.bridge import DesktopBridge


def main() -> None:
    target = Path(__file__).resolve().parents[1] / "frontend" / "public" / "demo-snapshot.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(DesktopBridge(demo_enabled=True).bootstrap(), ensure_ascii=False),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
