from __future__ import annotations

import base64
from io import BytesIO

import pytest
from PIL import Image


@pytest.fixture
def technical_drawings() -> dict[str, dict[str, object]]:
    """Small valid PNG payloads for report integration tests."""
    image = Image.new("RGB", (320, 160), "white")
    stream = BytesIO()
    image.save(stream, format="PNG")
    data_url = "data:image/png;base64," + base64.b64encode(stream.getvalue()).decode("ascii")
    return {
        view: {"dataUrl": data_url, "width": 320, "height": 160}
        for view in ("side", "top", "section", "isometric")
    }
