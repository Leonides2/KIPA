"""Empaquetado del tema construido por `ThemeBuilder`.

Modo A: `.tar.gz` de distribución privada, con `install.sh` incluido.
Modo B: paquete compatible con `kpackagetool6 -t Icons` (formato KPackage).
"""

from __future__ import annotations

import json
import os
import stat
import tarfile
import tempfile
from pathlib import Path

from src.models.theme_metadata import ThemeMetadata

INSTALL_SH_TEMPLATE = """#!/bin/bash
set -e
DEST="$HOME/.local/share/icons/{slug}"
mkdir -p "$DEST"
cp -r ./* "$DEST"
rm -f "$DEST/install.sh"
kbuildsycoca6 --noincremental 2>/dev/null || true
echo "Tema instalado en $DEST"
"""


class PackagerError(Exception):
    """Error durante el empaquetado."""


class Packager:
    """Toma la carpeta de un tema ya construido (`ThemeBuilder.build()`) y
    produce el artefacto final en el modo solicitado."""

    def __init__(self, theme_root: Path, metadata: ThemeMetadata):
        self.theme_root = Path(theme_root)
        self.metadata = metadata

    def validate_theme_dir(self) -> None:
        if not self.theme_root.is_dir():
            raise PackagerError(f"No existe la carpeta del tema: {self.theme_root}")
        index_theme = self.theme_root / "index.theme"
        if not index_theme.is_file():
            raise PackagerError(
                "La carpeta del tema no contiene un 'index.theme'. "
                "Genera el tema con ThemeBuilder antes de empaquetar."
            )
        has_content = any(
            p.is_file() and p.suffix.lower() in (".png", ".svg")
            for p in self.theme_root.rglob("*")
        )
        if not has_content:
            raise PackagerError(
                "El tema no contiene ningún icono generado (PNG/SVG). "
                "Se requiere al menos un tamaño generado."
            )

    # -- Modo A: distribución privada ------------------------------------
    def export_mode_a(self, output_path: str | Path) -> Path:
        """Genera `<output_path>` como .tar.gz con install.sh incluido."""
        self.validate_theme_dir()
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with tempfile.TemporaryDirectory(prefix="icon-packager-installsh-") as tmp:
            install_sh_path = Path(tmp) / "install.sh"
            install_sh_path.write_text(
                INSTALL_SH_TEMPLATE.format(slug=self.metadata.slug),
                encoding="utf-8",
            )
            # Permisos de ejecución antes de añadirlo al tar.
            st = os.stat(install_sh_path)
            os.chmod(
                install_sh_path,
                st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH,
            )

            with tarfile.open(output_path, "w:gz") as tar:
                arcroot = self.metadata.slug
                for item in sorted(self.theme_root.rglob("*")):
                    arcname = f"{arcroot}/{item.relative_to(self.theme_root)}"
                    tar.add(item, arcname=arcname, recursive=False)
                tar.add(
                    install_sh_path,
                    arcname=f"{arcroot}/install.sh",
                    recursive=False,
                )

        return output_path

    # -- Modo B: paquete KPackage (kpackagetool6 -t Icons) ---------------
    def export_mode_b(self, output_path: str | Path) -> Path:
        """Genera `<output_path>` como .tar.gz instalable vía
        `kpackagetool6 -t Icons -i <output_path>`.

        La estructura sigue el formato KPackage: `metadata.json` en la
        raíz del paquete (KPackage moderno usa metadata.json en lugar del
        antiguo metadata.desktop) junto con la estructura habitual del
        tema de iconos dentro de `contents/`... en la práctica, para el
        tipo de servicio "Icons" de Plasma, `kpackagetool6` espera la
        estructura del tema directamente en la raíz del paquete más un
        `metadata.json` describiendo el paquete. Se genera esa variante,
        más compatible con instalaciones reales de temas de iconos KDE.
        """
        self.validate_theme_dir()
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        metadata_json = self._build_kpackage_metadata()

        with tempfile.TemporaryDirectory(prefix="icon-packager-kpkg-") as tmp:
            metadata_path = Path(tmp) / "metadata.json"
            metadata_path.write_text(
                json.dumps(metadata_json, indent=4, ensure_ascii=False),
                encoding="utf-8",
            )

            with tarfile.open(output_path, "w:gz") as tar:
                for item in sorted(self.theme_root.rglob("*")):
                    arcname = str(item.relative_to(self.theme_root))
                    tar.add(item, arcname=arcname, recursive=False)
                tar.add(metadata_path, arcname="metadata.json", recursive=False)

        return output_path

    def _build_kpackage_metadata(self) -> dict:
        return {
            "KPackageStructure": "Icons",
            "KPlugin": {
                "Id": self.metadata.slug,
                "Name": self.metadata.name,
                "Description": self.metadata.comment,
                "Version": self.metadata.version,
                "Authors": (
                    [{"Name": self.metadata.author}] if self.metadata.author else []
                ),
            },
        }
