"""Punto de entrada de la aplicación.

Antes de importar PySide6/Pillow se verifican las dependencias del
sistema (RF6): si falta algo obligatorio, se informa cómo instalarlo y se
sale sin arrancar Qt; si solo faltan opcionales, se avisa y se continúa.
"""

from __future__ import annotations

import sys

from src.core.dependency_checker import check_dependencies, format_report


def _show_blocking_error(message: str) -> None:
    """Muestra el error de dependencias faltantes por terminal y, si hay
    un entorno gráfico disponible sin PySide6 (p.ej. se lanzó desde un
    icono de escritorio), intenta también un diálogo Tk como respaldo."""
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

    # Import diferido: solo una vez confirmado que PySide6 está disponible.
    from PySide6.QtWidgets import QApplication

    from src.ui.main_window import MainWindow

    app = QApplication(sys.argv)
    app.setApplicationName("Icon Packager KDE")
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
