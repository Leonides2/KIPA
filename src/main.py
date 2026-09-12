"""Punto de entrada de la aplicación.

Antes de importar Qt (PySide6 o, como alternativa, PySide2)/Pillow se
verifican las dependencias del sistema (RF6): si falta algo obligatorio,
se informa cómo instalarlo y se sale sin arrancar Qt; si solo faltan
opcionales, se avisa y se continúa.
"""

from __future__ import annotations

import sys

from src.core.dependency_checker import check_dependencies, format_report


def _show_blocking_error(message: str) -> None:
    """Muestra el error de dependencias faltantes por terminal y, si hay
    un entorno gráfico disponible sin PySide6/PySide2 (p.ej. se lanzó
    desde un icono de escritorio), intenta también un diálogo Tk como
    respaldo."""
    print(message, file=sys.stderr)
    try:
        import tkinter
        from tkinter import messagebox

        root = tkinter.Tk()
        root.withdraw()
        messagebox.showerror("Icon Packager KDE — Dependencias faltantes", message)
        root.destroy()
    except Exception:
        # Sin Tk disponible (o sin entorno gráfico): el mensaje por
        # terminal ya se mostró arriba, no es un error fatal adicional.
        pass


def main() -> int:
    report = check_dependencies()

    if not report.is_ok:
        message = (
            "Icon Packager KDE no puede iniciarse: faltan dependencias "
            "obligatorias.\n\n" + format_report(report)
        )
        _show_blocking_error(message)
        return 1

    if report.missing_optional:
        print(format_report(report), file=sys.stderr)

    # Import diferido: solo una vez confirmado que hay un binding de Qt
    # disponible (PySide6 o PySide2, ver src/ui/qt_compat.py).
    from src.ui.main_window import MainWindow
    from src.ui.qt_compat import QtGui, QtWidgets, exec_app

    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName("Icon Packager KDE")
    # Icono de la app (barra de tareas/título): se usa uno del tema de
    # iconos activo del sistema, con alternativas por si no existe.
    app.setWindowIcon(
        QtGui.QIcon.fromTheme(
            "preferences-desktop-icons",
            QtGui.QIcon.fromTheme("applications-graphics"),
        )
    )
    window = MainWindow()
    window.show()
    return exec_app(app)


if __name__ == "__main__":
    sys.exit(main())
