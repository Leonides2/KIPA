"""Fixtures compartidas para los tests."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from PIL import Image

# Permite ejecutar `pytest` desde la raíz del proyecto importando `src.*`.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SAMPLE_SVG = """<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 48 48">
  <circle cx="24" cy="24" r="20" fill="#3daee9"/>
</svg>
"""


@pytest.fixture
def sample_png(tmp_path: Path) -> Path:
    path = tmp_path / "sample-icon.png"
    img = Image.new("RGBA", (64, 64), (61, 174, 233, 255))
    img.save(path, format="PNG")
    return path


@pytest.fixture
def sample_svg(tmp_path: Path) -> Path:
    path = tmp_path / "sample-icon.svg"
    path.write_text(SAMPLE_SVG, encoding="utf-8")
    return path
