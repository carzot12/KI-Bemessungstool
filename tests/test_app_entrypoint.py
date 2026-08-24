from __future__ import annotations

from unittest.mock import patch

import pytest

import app


def test_default_entrypoint_launches_react_desktop() -> None:
    with patch("desktop.main.launch") as launch:
        app.main([])
    launch.assert_called_once_with(None)


def test_legacy_flag_launches_customtkinter_entrypoint() -> None:
    with patch.object(app, "legacy_main") as legacy, patch("desktop.main.launch") as launch:
        app.main(["--legacy"])
    legacy.assert_called_once_with()
    launch.assert_not_called()


def test_dev_flag_checks_vite_and_passes_url() -> None:
    with patch.object(app, "_require_vite_server") as check, patch("desktop.main.launch") as launch:
        app.main(["--dev"])
    check.assert_called_once_with("http://127.0.0.1:5173")
    launch.assert_called_once_with("http://127.0.0.1:5173")


def test_dev_flag_explains_missing_vite_server() -> None:
    with patch("urllib.request.urlopen", side_effect=OSError("offline")):
        with pytest.raises(SystemExit, match="npm --prefix frontend run dev"):
            app._require_vite_server("http://127.0.0.1:5173")
