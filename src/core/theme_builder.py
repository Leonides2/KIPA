"""Construcción de la estructura de carpetas de un tema de iconos KDE."""

from __future__ import annotations

import configparser
import shutil
import tempfile
from pathlib import Path

from PIL import Image

from src.models.icon_item import IconItem
from src.models.theme_metadata import ThemeMetadata

# Tamaño de referencia usado en la sección [scalable/<contexto>] del
# index.theme cuando hay iconos escalables (valor habitual en temas KDE).
_SCALABLE_NOMINAL_SIZE = 48
_SCALABLE_MIN_SIZE = 16
_SCALABLE_MAX_SIZE = 512

# Nombre del contexto freedesktop -> nombre "humano" usado en index.theme.
CONTEXT_LABELS = {
    "apps": "Applications",
    "actions": "Actions",
    "mimetypes": "MimeTypes",
    "places": "Places",
    "status": "Status",
}


class ThemeBuildError(Exception):
    """Error durante la construcción del tema."""


class ThemeBuilder:
    """Genera en disco la estructura de un tema de iconos a partir de los
    `IconItem` y el `ThemeMetadata` configurados por el usuario.

    El resultado se escribe en un directorio temporal (o uno indicado
    explícitamente), listo para ser tomado por `Packager`.
    """

    def __init__(self, metadata: ThemeMetadata, icons: list[IconItem]):
        self.metadata = metadata
        self.icons = icons

    def build(self, dest_dir: str | Path | None = None) -> Path:
        """Construye la estructura del tema y devuelve la carpeta raíz.

        Si `dest_dir` no se indica, se crea un directorio temporal con
        `tempfile.mkdtemp()`. La carpeta raíz del tema es
        `<dest_dir>/<slug-del-tema>/`.
        """
        self.metadata.validate()
        if not self.icons:
            raise ThemeBuildError("No hay iconos para construir el tema.")

        base_dir = Path(dest_dir) if dest_dir else Path(tempfile.mkdtemp(prefix="icon-packager-"))
        theme_root = base_dir / self.metadata.slug
        theme_root.mkdir(parents=True, exist_ok=True)

        directories = self._generate_icon_files(theme_root)
        self._write_index_theme(theme_root, directories)
        return theme_root

    # -- generación de archivos ------------------------------------------
    def _generate_icon_files(self, theme_root: Path) -> list[str]:
        """Genera los PNG rasterizados y copia los SVG escalables.

        Devuelve la lista ordenada de subcarpetas creadas (p.ej.
        "16x16/apps", "scalable/apps"), usada luego para `Directories=`.
        """
        directories: set[str] = set()

        for icon in self.icons:
            icon.validate_source()

            for size in sorted(icon.effective_sizes()):
                subdir = f"{size}x{size}/{icon.context}"
                target_dir = theme_root / subdir
                target_dir.mkdir(parents=True, exist_ok=True)
                target_path = target_dir / f"{icon.name}.png"
                self._render_png(icon, size, target_path)
                directories.add(subdir)

            if icon.scalable:
                if not icon.is_svg:
                    raise ThemeBuildError(
                        f"El icono '{icon.name}' está marcado como escalable "
                        "pero no es un SVG."
                    )
                subdir = f"scalable/{icon.context}"
                target_dir = theme_root / subdir
                target_dir.mkdir(parents=True, exist_ok=True)
                shutil.copy2(icon.source_path, target_dir / f"{icon.name}.svg")
                directories.add(subdir)

        return sorted(directories, key=self._directory_sort_key)

    @staticmethod
    def _directory_sort_key(directory: str) -> tuple[int, str]:
        size_part = directory.split("/", 1)[0]
        if size_part == "scalable":
            return (1, directory)
        try:
            size = int(size_part.split("x", 1)[0])
        except ValueError:
            size = 0
        return (0, f"{size:05d}-{directory}")

    def _render_png(self, icon: IconItem, size: int, target_path: Path) -> None:
        """Genera un PNG de `size`x`size` a partir del icono fuente.

        - Si la fuente es SVG, se rasteriza con Pillow (requiere soporte
          de rlottie/cairosvg no disponible por defecto en Pillow, por lo
          que en la práctica se espera que el usuario suba PNG para
          tamaños fijos; si la fuente es PNG se redimensiona directamente).
        """
        if icon.is_png:
            with Image.open(icon.source_path) as img:
                img = img.convert("RGBA")
                resized = img.resize((size, size), Image.LANCZOS)
                resized.save(target_path, format="PNG")
            return

        if icon.is_svg:
            self._render_svg_to_png(icon.source_path, size, target_path)
            return

        raise ThemeBuildError(f"Formato no soportado para '{icon.source_path}'.")

    def _render_svg_to_png(self, svg_path: Path, size: int, target_path: Path) -> None:
        """Rasteriza un SVG a PNG. Usa cairosvg si está disponible; si no,
        lanza un error claro indicando que se necesita PNG o cairosvg."""
        try:
            import cairosvg  # type: ignore
        except ImportError as exc:
            raise ThemeBuildError(
                f"No se puede rasterizar '{svg_path.name}' a {size}x{size}px: "
                "falta la dependencia opcional 'cairosvg'. Instálala "
                "(`pip install cairosvg`) o sube también una versión PNG "
                "de este icono para los tamaños fijos."
            ) from exc

        cairosvg.svg2png(
            url=str(svg_path),
            write_to=str(target_path),
            output_width=size,
            output_height=size,
        )

    # -- index.theme --------------------------------------------------
    def _write_index_theme(self, theme_root: Path, directories: list[str]) -> None:
        config = configparser.ConfigParser()
        config.optionxform = str  # preservar mayúsculas de las claves

        section = "Icon Theme"
        config.add_section(section)
        config.set(section, "Name", self.metadata.name)
        config.set(section, "Comment", self.metadata.comment)
        if self.metadata.author:
            config.set(section, "X-KDE-AuthorName", self.metadata.author)
        config.set(section, "Version", self.metadata.version)
        if self.metadata.inherits:
            config.set(section, "Inherits", self.metadata.inherits)
        config.set(section, "Directories", ",".join(directories))

        for directory in directories:
            config.add_section(directory)
            size_part, context = directory.split("/", 1)
            context_label = CONTEXT_LABELS.get(context, context.capitalize())
            if size_part == "scalable":
                config.set(directory, "Size", str(_SCALABLE_NOMINAL_SIZE))
                config.set(directory, "MinSize", str(_SCALABLE_MIN_SIZE))
                config.set(directory, "MaxSize", str(_SCALABLE_MAX_SIZE))
                config.set(directory, "Type", "Scalable")
            else:
                size = size_part.split("x", 1)[0]
                config.set(directory, "Size", size)
                config.set(directory, "Type", "Fixed")
            config.set(directory, "Context", context_label)

        index_path = theme_root / "index.theme"
        with open(index_path, "w", encoding="utf-8") as fh:
            config.write(fh, space_around_delimiters=False)
