"""Descubrimiento de temas de iconos instalados y catálogo de sus iconos.

Permite "heredar visualmente" de un tema ya instalado: se escanean sus
directorios (según su `index.theme`) para poder buscar/elegir iconos
puntuales y traerlos al `IconManager` como punto de partida para
modificarlos, sin necesidad de copiar el tema completo (freedesktop ya
resuelve en tiempo de ejecución, vía `Inherits=`, cualquier icono que no
se sobrescriba).

Se buscan tanto en rutas de usuario como del sistema (no hacen falta
permisos especiales para *leer* `/usr/share/icons`): temas como Breeze,
Oxygen o Adwaita casi siempre están instalados a nivel de sistema, nunca
en `~/.local/share/icons`, así que limitarse a rutas de usuario dejaría
esta función sin encontrar nada en la mayoría de instalaciones KDE
reales.
"""

from __future__ import annotations

import configparser
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

from src.core.icon_manager import IconManager
from src.core.theme_builder import CONTEXT_LABELS
from src.models.icon_item import VALID_CONTEXTS, IconItem

# Tamaño al inicio de un segmento de carpeta, en cualquiera de las formas
# que se ven en temas reales: "16", "16x16", "16@2x", "16x16@2x"...
_SIZE_TOKEN_RE = re.compile(r"^(\d+)(?:x\d+)?(?:@\d+x?)?$")

_LABEL_TO_CONTEXT = {label: slug for slug, label in CONTEXT_LABELS.items()}


def default_icon_search_dirs() -> list[Path]:
    """Todas las rutas donde freedesktop busca temas de iconos, en orden
    de prioridad: `XDG_DATA_HOME`/usuario primero (para que un tema propio
    con el mismo id que uno del sistema gane), luego `XDG_DATA_DIRS`
    (por defecto `/usr/local/share` y `/usr/share`)."""
    home = Path.home()
    dirs = [
        Path(os.environ.get("XDG_DATA_HOME", str(home / ".local/share"))) / "icons",
        home / ".icons",
    ]

    xdg_data_dirs = os.environ.get("XDG_DATA_DIRS", "/usr/local/share:/usr/share")
    for base in xdg_data_dirs.split(":"):
        if base:
            dirs.append(Path(base) / "icons")

    # Deduplicar preservando el orden (p.ej. si XDG_DATA_HOME coincide con
    # el valor por defecto ya añadido).
    seen: set[Path] = set()
    unique_dirs: list[Path] = []
    for d in dirs:
        if d not in seen:
            seen.add(d)
            unique_dirs.append(d)
    return unique_dirs


@dataclass
class InstalledTheme:
    """Un tema de iconos instalado localmente."""

    id: str
    name: str
    path: Path


@dataclass
class CatalogIcon:
    """Un icono disponible dentro de un tema catalogado, con las fuentes
    (PNG por tamaño y/o SVG) encontradas en disco para ese nombre+contexto."""

    name: str
    context: str
    sizes: set[int] = field(default_factory=set)
    scalable: bool = False
    svg_source: Path | None = None
    png_sources: dict[int, Path] = field(default_factory=dict)

    def best_source_path(self) -> Path:
        """Archivo a usar como fuente si se importa este icono: se
        prefiere el SVG (mejor calidad para regenerar cualquier tamaño);
        si no hay, el PNG de mayor resolución disponible."""
        if self.svg_source is not None:
            return self.svg_source
        if self.png_sources:
            return self.png_sources[max(self.png_sources)]
        raise ValueError(f"El icono '{self.name}' no tiene ningún archivo fuente.")


def discover_installed_themes(search_dirs: list[Path] | None = None) -> list[InstalledTheme]:
    """Busca temas de iconos instalados (con `index.theme` válido y no
    `Hidden=true`) en las carpetas dadas (por defecto, las de usuario y
    del sistema — ver `default_icon_search_dirs`)."""
    dirs = search_dirs if search_dirs is not None else default_icon_search_dirs()
    themes: list[InstalledTheme] = []
    seen_ids: set[str] = set()

    for base in dirs:
        if not base.is_dir():
            continue
        for entry in sorted(base.iterdir()):
            if not entry.is_dir() or entry.name in seen_ids:
                continue
            index_theme = entry / "index.theme"
            if not index_theme.is_file():
                continue

            config = configparser.ConfigParser()
            config.optionxform = str
            try:
                config.read(index_theme, encoding="utf-8")
            except configparser.Error:
                continue
            if "Icon Theme" not in config:
                continue

            section = config["Icon Theme"]
            if section.get("Hidden", "false").strip().lower() == "true":
                continue

            seen_ids.add(entry.name)
            themes.append(
                InstalledTheme(
                    id=entry.name,
                    name=section.get("Name", entry.name),
                    path=entry,
                )
            )

    return themes


def _looks_like_size_segment(segment: str) -> bool:
    return bool(_SIZE_TOKEN_RE.match(segment)) or segment in ("scalable", "symbolic")


def _resolve_context(raw_context: str, directory: str) -> str | None:
    """Contexto del icono: se prefiere el `Context=` del propio
    index.theme (p.ej. 'Applications' -> 'apps'); si no hay sección o no
    trae `Context=`, se infiere del nombre de carpeta, soportando tanto
    "tamaño/contexto" (hicolor: "16x16/apps") como "contexto/tamaño"
    (Breeze: "actions/16")."""
    if raw_context:
        if raw_context in _LABEL_TO_CONTEXT:
            return _LABEL_TO_CONTEXT[raw_context]
        if raw_context.lower() in VALID_CONTEXTS:
            return raw_context.lower()

    parts = directory.split("/", 1)
    if len(parts) != 2:
        return None
    first, second = parts
    return second if _looks_like_size_segment(first) else first


def _resolve_size(raw_size: str, directory: str) -> int | None:
    """Tamaño nominal fijo: se prefiere el `Size=` del index.theme; si no
    está disponible, se infiere del segmento de carpeta que parezca un
    tamaño (en cualquiera de los dos órdenes posibles)."""
    if raw_size.isdigit():
        return int(raw_size)
    for segment in directory.split("/"):
        match = _SIZE_TOKEN_RE.match(segment)
        if match:
            return int(match.group(1))
    return None


def build_catalog(theme_path: Path) -> list[CatalogIcon]:
    """Recorre las carpetas de un tema y agrupa sus archivos por icono
    (nombre + contexto). Solo incluye los contextos que esta app entiende
    (`apps`, `actions`, `mimetypes`, `places`, `status`).

    El nombre de carpeta es una cadena arbitraria según la spec — cada
    tema la organiza a su manera (hicolor: `16x16/apps`; Breeze:
    `actions/16`) — así que el contexto/tamaño de cada carpeta se leen de
    su propia sección `[directorio]` en `index.theme` (`Context=`,
    `Size=`), no del nombre de la carpeta; el nombre solo se usa como
    respaldo si esa sección faltara.
    """
    index_theme = theme_path / "index.theme"
    directories: list[str] = []
    config = configparser.ConfigParser(strict=False)
    config.optionxform = str

    if index_theme.is_file():
        try:
            config.read(index_theme, encoding="utf-8")
            raw = config.get("Icon Theme", "Directories", fallback="")
            directories = [d.strip() for d in raw.split(",") if d.strip()]
        except configparser.Error:
            directories = []

    if not directories:
        # index.theme ausente/incompleto: recorrer subcarpetas de 2 niveles.
        directories = [
            str(p.relative_to(theme_path)) for p in theme_path.glob("*/*") if p.is_dir()
        ]

    icons: dict[tuple[str, str], CatalogIcon] = {}

    for directory in directories:
        dir_path = theme_path / directory
        if not dir_path.is_dir():
            continue

        section = config[directory] if config.has_section(directory) else {}

        # Variantes HiDPI (Scale=2/3, p.ej. Breeze "actions/16@2x"): mismo
        # icono a otra escala, no un tamaño nuevo que ofrecer.
        if section.get("Scale", "1") != "1":
            continue

        context = _resolve_context(section.get("Context", ""), directory)
        if context not in VALID_CONTEXTS:
            continue

        size = _resolve_size(section.get("Size", ""), directory)

        for file in dir_path.iterdir():
            if not file.is_file() or file.suffix.lower() not in (".png", ".svg"):
                continue

            key = (context, file.stem)
            catalog_icon = icons.setdefault(
                key, CatalogIcon(name=file.stem, context=context)
            )

            if file.suffix.lower() == ".svg":
                catalog_icon.scalable = True
                if catalog_icon.svg_source is None:
                    catalog_icon.svg_source = file
            elif size is not None:
                catalog_icon.sizes.add(size)
                catalog_icon.png_sources.setdefault(size, file)

    return sorted(icons.values(), key=lambda c: (c.context, c.name))


def search_catalog(
    catalog: list[CatalogIcon], query: str = "", context: str | None = None
) -> list[CatalogIcon]:
    """Filtra un catálogo ya construido por texto (substring en el
    nombre) y/o contexto — usado por el buscador de la UI."""
    results = catalog
    if context:
        results = [c for c in results if c.context == context]
    query = query.strip().lower()
    if query:
        results = [c for c in results if query in c.name.lower()]
    return results


def import_catalog_icon(icon_manager: IconManager, catalog_icon: CatalogIcon) -> IconItem:
    """Copia un icono del catálogo (aún en la carpeta del tema instalado)
    al `IconManager` como un `IconItem` normal, listo para modificar y
    exportar como parte de un tema nuevo."""
    item = icon_manager.add_icon(
        catalog_icon.best_source_path(),
        name=catalog_icon.name,
        context=catalog_icon.context,
        sizes=set(catalog_icon.sizes),
    )
    item.scalable = catalog_icon.scalable and item.is_svg
    return item
