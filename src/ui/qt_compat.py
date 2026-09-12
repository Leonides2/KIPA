"""Capa de compatibilidad Qt6 (PySide6) / Qt5 (PySide2).

Se prueba PySide6 primero (recomendado, Plasma 6); si no está instalado,
se usa PySide2 (Plasma 5). El resto del código de `ui/` importa siempre
desde este módulo — nunca directamente de `PySide6`/`PySide2` — y usa
exclusivamente la sintaxis "plana" de enums (`Qt.Horizontal`,
`QDialogButtonBox.Ok`, `Qt.UserRole`...), que ambos bindings soportan, en
vez de la sintaxis con clases anidadas propia de Qt6
(`Qt.Orientation.Horizontal`).

Nota: PySide2 no tiene wheels oficiales para Python 3.11+, así que el
modo Qt5 está pensado para ejecutarse con Python 3.9/3.10 (típico en
distros con Plasma 5). No se ha podido validar visualmente en este
entorno de desarrollo (solo PySide6/Qt6); se recomienda probarlo en una
máquina real con Plasma 5 antes de confiar en él en producción.
"""

from __future__ import annotations

try:
    from PySide6 import QtCore, QtGui, QtWidgets
    from PySide6.QtCore import QThread, Signal, Slot

    QT_API = "PySide6"
    QT_MAJOR = 6
except ImportError:
    from PySide2 import QtCore, QtGui, QtWidgets
    from PySide2.QtCore import QThread, Signal, Slot

    QT_API = "PySide2"
    QT_MAJOR = 5

Qt = QtCore.Qt

__all__ = [
    "QtCore",
    "QtGui",
    "QtWidgets",
    "Qt",
    "QThread",
    "Signal",
    "Slot",
    "QT_API",
    "QT_MAJOR",
    "exec_dialog",
    "exec_app",
]


def exec_dialog(dialog) -> int:
    """`QDialog.exec()` (Qt6) vs `exec_()` (Qt5).

    PySide2 >= 5.14 también expone `exec()`, pero se resuelve
    explícitamente para no depender de la versión exacta instalada.
    """
    return dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()


def exec_app(app) -> int:
    """`QApplication.exec()` (Qt6) vs `exec_()` (Qt5)."""
    return app.exec() if hasattr(app, "exec") else app.exec_()
