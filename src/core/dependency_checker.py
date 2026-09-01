"""Verificación de dependencias del sistema operativo antes de arrancar.

Se ejecuta antes de importar PySide6/Pillow, para poder informar con un
mensaje claro (por terminal, y por diálogo Tk si está disponible) de qué
falta y cómo instalarlo, en vez de fallar con un `ImportError` críptico.
"""

from __future__ import annotations

import ctypes.util
import importlib.util
import os
import platform
import shutil
import sys
from dataclasses import dataclass, field

MIN_PYTHON = (3, 11)

# Familias de distribuciones Linux soportadas para sugerir el comando de
# instalación correcto (best-effort, basado en /etc/os-release).
_INSTALL_CMD = {
    "debian": "sudo apt install {pkgs}",
    "fedora": "sudo dnf install {pkgs}",
    "arch": "sudo pacman -S {pkgs}",
    "opensuse": "sudo zypper install {pkgs}",
}

_DISTRO_TO_FAMILY = {
    "ubuntu": "debian",
    "debian": "debian",
    "neon": "debian",  # KDE neon
    "kubuntu": "debian",
    "linuxmint": "debian",
    "pop": "debian",
    "fedora": "fedora",
    "nobara": "fedora",
    "rhel": "fedora",
    "centos": "fedora",
    "arch": "arch",
    "manjaro": "arch",
    "endeavouros": "arch",
    "garuda": "arch",
    "opensuse-leap": "opensuse",
    "opensuse-tumbleweed": "opensuse",
}

# paquete del sistema por familia de distro, para cada dependencia lógica.
_SYSTEM_PACKAGES = {
    "pyside6": {
        "debian": "python3-pyside6.qtcore python3-pyside6.qtgui python3-pyside6.qtwidgets",
        "fedora": "python3-pyside6",
        "arch": "pyside6",
        "opensuse": "python3-PySide6",
    },
    "pillow": {
        "debian": "python3-pil",
        "fedora": "python3-pillow",
        "arch": "python-pillow",
        "opensuse": "python3-Pillow",
    },
    "cairosvg": {
        "debian": "python3-cairosvg",
        "fedora": "python3-cairosvg",
        "arch": "python-cairosvg",
        "opensuse": "python3-cairosvg",
    },
    "xcb": {
        "debian": "libxcb-cursor0 libxkbcommon-x11-0",
        "fedora": "xcb-util-cursor libxkbcommon-x11",
        "arch": "xcb-util-cursor libxkbcommon-x11",
        "opensuse": "libxcb-cursor0 libxkbcommon-x11-0",
    },
    "kpackagetool6": {
        "debian": "kpackagetool6",
        "fedora": "kf6-kpackage",
        "arch": "kpackage",
        "opensuse": "kf6-kpackage",
    },
}

# Fallback vía pip cuando no se reconoce la distro o no aplica paquete de
# sistema (p.ej. dentro de un venv).
_PIP_PACKAGE = {
    "pyside6": "PySide6",
    "pillow": "Pillow",
    "cairosvg": "cairosvg",
}


@dataclass
class DependencyCheck:
    name: str
    required: bool
    ok: bool
    detail: str = ""
    install_hint: str = ""


@dataclass
class DependencyReport:
    checks: list[DependencyCheck] = field(default_factory=list)

    @property
    def missing_required(self) -> list[DependencyCheck]:
        return [c for c in self.checks if c.required and not c.ok]

    @property
    def missing_optional(self) -> list[DependencyCheck]:
        return [c for c in self.checks if not c.required and not c.ok]

    @property
    def is_ok(self) -> bool:
        return not self.missing_required


def _distro_id() -> str:
    """Lee /etc/os-release para identificar la distro (best-effort)."""
    try:
        data: dict[str, str] = {}
        with open("/etc/os-release", encoding="utf-8") as fh:
            for line in fh:
                if "=" in line:
                    key, _, value = line.strip().partition("=")
                    data[key] = value.strip('"')
        return data.get("ID", "").lower()
    except OSError:
        return ""


def _distro_family(distro_id: str) -> str:
    return _DISTRO_TO_FAMILY.get(distro_id, "")


def _install_hint(logical_name: str) -> str:
    """Sugerencia de instalación: paquete del sistema (según distro
    detectada) y, si aplica, alternativa vía pip."""
    family = _distro_family(_distro_id())
    hints: list[str] = []

    system_pkgs = _SYSTEM_PACKAGES.get(logical_name, {}).get(family)
    if system_pkgs and family in _INSTALL_CMD:
        hints.append(_INSTALL_CMD[family].format(pkgs=system_pkgs))

    pip_pkg = _PIP_PACKAGE.get(logical_name)
    if pip_pkg:
        hints.append(f"pip install {pip_pkg}")

    return "  o  ".join(hints) if hints else ""


def check_dependencies() -> DependencyReport:
    """Comprueba todas las dependencias necesarias/opcionales.

    No importa PySide6 ni Pillow (usa `importlib.util.find_spec`), para
    poder ejecutarse aunque falten y poder informar del problema en vez
    de morir con un ImportError sin contexto.
    """
    report = DependencyReport()

    py_ok = sys.version_info[:2] >= MIN_PYTHON
    report.checks.append(
        DependencyCheck(
            name="Python >= 3.11",
            required=True,
            ok=py_ok,
            detail=f"Detectado: Python {platform.python_version()}",
            install_hint="Instala Python 3.11+ con tu gestor de paquetes o "
            "desde https://www.python.org/downloads/",
        )
    )

    report.checks.append(
        DependencyCheck(
            name="PySide6",
            required=True,
            ok=importlib.util.find_spec("PySide6") is not None,
            detail="Biblioteca de interfaz gráfica (Qt para Python).",
            install_hint=_install_hint("pyside6"),
        )
    )

    report.checks.append(
        DependencyCheck(
            name="Pillow",
            required=True,
            ok=importlib.util.find_spec("PIL") is not None,
            detail="Redimensionado de iconos PNG.",
            install_hint=_install_hint("pillow"),
        )
    )

    report.checks.append(
        DependencyCheck(
            name="cairosvg (opcional)",
            required=False,
            ok=importlib.util.find_spec("cairosvg") is not None,
            detail="Necesario solo para rasterizar SVG a tamaños PNG fijos "
            "(los tamaños 'scalable' no lo necesitan).",
            install_hint=_install_hint("cairosvg"),
        )
    )

    if platform.system() == "Linux" and not os.environ.get("WAYLAND_DISPLAY"):
        # Best-effort: no garantiza el resultado (find_library depende de
        # que ldconfig conozca la biblioteca), pero cubre el error más
        # común al abrir la app ("could not load the Qt platform plugin
        # xcb") en instalaciones mínimas de Linux bajo X11.
        xcb_ok = any(
            ctypes.util.find_library(lib) for lib in ("xcb-cursor", "xkbcommon-x11")
        )
        report.checks.append(
            DependencyCheck(
                name="Librerías Qt/XCB del sistema (X11)",
                required=False,
                ok=xcb_ok,
                detail="Necesarias para mostrar la interfaz gráfica bajo X11. "
                "Si la app no abre ninguna ventana, instala esto primero.",
                install_hint=_install_hint("xcb"),
            )
        )

    report.checks.append(
        DependencyCheck(
            name="kpackagetool6 (opcional)",
            required=False,
            ok=shutil.which("kpackagetool6") is not None,
            detail="Solo necesario para instalar paquetes exportados en "
            "Modo B (kpackagetool6 -t Icons -i ...).",
            install_hint=_install_hint("kpackagetool6"),
        )
    )

    return report


def format_report(report: DependencyReport) -> str:
    lines: list[str] = []

    if report.missing_required:
        lines.append("Faltan dependencias obligatorias:")
        for c in report.missing_required:
            lines.append(f"  ✗ {c.name} — {c.detail}")
            if c.install_hint:
                lines.append(f"    → Instálala con: {c.install_hint}")
        lines.append("")

    if report.missing_optional:
        lines.append("Dependencias opcionales no encontradas (funcionalidad reducida):")
        for c in report.missing_optional:
            lines.append(f"  ⚠ {c.name} — {c.detail}")
            if c.install_hint:
                lines.append(f"    → Instálala con: {c.install_hint}")

    return "\n".join(lines)
