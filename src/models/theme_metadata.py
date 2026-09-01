"""Modelo de datos para la metadata de un tema de iconos."""

from __future__ import annotations

import re
from dataclasses import dataclass

_SLUG_RE = re.compile(r"[^a-z0-9]+")


@dataclass
class ThemeMetadata:
    """Metadata del tema, usada para generar `index.theme` y los paquetes."""

    name: str
    comment: str = "Generado con Icon Packager"
    author: str = ""
    version: str = "1.0"
    inherits: str = "breeze"

    def validate(self) -> None:
        if not self.name or not self.name.strip():
            raise ValueError("El nombre del tema no puede estar vacío.")

    @property
    def slug(self) -> str:
        """Nombre normalizado apto como nombre de carpeta/paquete."""
        slug = _SLUG_RE.sub("-", self.name.strip().lower()).strip("-")
        return slug or "mi-tema"
