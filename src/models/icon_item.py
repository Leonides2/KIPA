"""Modelo de datos para un icono gestionado por la aplicación."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

# Contextos definidos por la especificación freedesktop Icon Theme.
VALID_CONTEXTS = ("apps", "actions", "mimetypes", "places", "status")

# Tamaños estándar sugeridos por la spec (además de "scalable").
STANDARD_SIZES = (16, 22, 24, 32, 48, 64, 128, 256)


@dataclass
class IconItem:
    """Representa un icono añadido por el usuario, en memoria.

    No toca el filesystem por sí mismo: `source_path` apunta al archivo
    original (SVG o PNG) que el usuario seleccionó/arrastró; el resto de
    campos describen cómo debe tratarse al construir el tema.
    """

    source_path: Path
    name: str
    context: str = "apps"
    sizes: set[int] = field(default_factory=set)
    scalable: bool = False

    def __post_init__(self) -> None:
        self.source_path = Path(self.source_path)
        if not self.name:
            self.name = self.source_path.stem
        if self.context not in VALID_CONTEXTS:
            raise ValueError(
                f"Contexto inválido '{self.context}'. "
                f"Debe ser uno de: {', '.join(VALID_CONTEXTS)}"
            )
        # Un SVG puede usarse tanto rasterizado como escalable; se marca
        # como scalable automáticamente si es la única fuente disponible.
        if self.is_svg and not self.sizes:
            self.scalable = True

    @property
    def is_svg(self) -> bool:
        return self.source_path.suffix.lower() == ".svg"

    @property
    def is_png(self) -> bool:
        return self.source_path.suffix.lower() == ".png"

    def validate_source(self) -> None:
        """Valida que el archivo fuente exista y tenga un formato soportado."""
        if not self.source_path.exists():
            raise FileNotFoundError(f"No existe el archivo: {self.source_path}")
        if not (self.is_svg or self.is_png):
            raise ValueError(
                f"Formato no soportado '{self.source_path.suffix}'. "
                "Solo se admiten SVG y PNG."
            )

    def effective_sizes(self) -> set[int]:
        """Tamaños rasterizados que se generarán para este icono."""
        return set(self.sizes)
