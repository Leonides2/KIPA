"""Diálogo de exportación: selección de modo (A/B), destino y progreso (RF4/RF5)."""

from __future__ import annotations

import shutil
from pathlib import Path

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
)

from src.core.icon_manager import IconManager
from src.core.packager import Packager, PackagerError
from src.core.theme_builder import ThemeBuildError, ThemeBuilder
from src.models.theme_metadata import ThemeMetadata

MODE_A = "a"
MODE_B = "b"


class ExportWorker(QThread):
    """Ejecuta ThemeBuilder + Packager en un hilo aparte para no bloquear la UI."""

    progress = Signal(int, str)
    finished_ok = Signal(str)
    failed = Signal(str)

    def __init__(self, metadata: ThemeMetadata, icons, mode: str, output_path: Path):
        super().__init__()
        self.metadata = metadata
        self.icons = icons
        self.mode = mode
        self.output_path = output_path
        self._tmp_theme_root: Path | None = None

    def run(self) -> None:
        try:
            self.progress.emit(10, "Construyendo estructura del tema…")
            builder = ThemeBuilder(self.metadata, self.icons)
            theme_root = builder.build()
            self._tmp_theme_root = theme_root.parent

            self.progress.emit(60, "Empaquetando…")
            packager = Packager(theme_root, self.metadata)
            if self.mode == MODE_A:
                packager.export_mode_a(self.output_path)
            else:
                packager.export_mode_b(self.output_path)

            self.progress.emit(100, "Completado")
            self.finished_ok.emit(str(self.output_path))
        except (ThemeBuildError, PackagerError, ValueError, OSError) as exc:
            self.failed.emit(str(exc))
        finally:
            if self._tmp_theme_root and self._tmp_theme_root.exists():
                shutil.rmtree(self._tmp_theme_root, ignore_errors=True)


class ExportDialog(QDialog):
    """Diálogo que valida, selecciona modo/destino y lanza la exportación."""

    def __init__(
        self,
        icon_manager: IconManager,
        metadata_provider,
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Exportar tema de iconos")
        self.setMinimumWidth(480)
        self._icon_manager = icon_manager
        self._metadata_provider = metadata_provider
        self._worker: ExportWorker | None = None

        layout = QVBoxLayout(self)

        mode_group = QGroupBox("Modo de exportación")
        mode_layout = QVBoxLayout(mode_group)
        self.mode_a_radio = QRadioButton(
            "Modo A — Distribución privada (.tar.gz + install.sh)"
        )
        self.mode_a_radio.setChecked(True)
        mode_layout.addWidget(self.mode_a_radio)
        mode_layout.addWidget(
            QLabel(
                "    El usuario descomprime el .tar.gz y ejecuta install.sh\n"
                "    para instalar el tema en ~/.local/share/icons/"
            )
        )
        self.mode_b_radio = QRadioButton(
            "Modo B — Paquete KDE (instalable con kpackagetool6 -t Icons)"
        )
        mode_layout.addWidget(self.mode_b_radio)
        mode_layout.addWidget(
            QLabel(
                "    Genera un paquete con metadata.json compatible con\n"
                "    KPackage, instalable con un único comando."
            )
        )
        layout.addWidget(mode_group)

        dest_group = QGroupBox("Destino")
        dest_layout = QHBoxLayout(dest_group)
        self.dest_edit = QLineEdit()
        dest_layout.addWidget(self.dest_edit)
        browse_button = QPushButton("Examinar…")
        browse_button.clicked.connect(self._on_browse)
        dest_layout.addWidget(browse_button)
        layout.addWidget(dest_group)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        self.status_label = QLabel("")
        layout.addWidget(self.status_label)

        buttons_row = QHBoxLayout()
        buttons_row.addStretch()
        self.export_button = QPushButton("Exportar")
        self.export_button.clicked.connect(self._on_export_clicked)
        buttons_row.addWidget(self.export_button)
        self.close_button = QPushButton("Cerrar")
        self.close_button.clicked.connect(self.reject)
        buttons_row.addWidget(self.close_button)
        layout.addLayout(buttons_row)

    # -- helpers ----------------------------------------------------
    def _selected_mode(self) -> str:
        return MODE_A if self.mode_a_radio.isChecked() else MODE_B

    def _default_filename(self) -> str:
        metadata = self._metadata_provider()
        suffix = "" if self._selected_mode() == MODE_A else "-kpkg"
        return f"{metadata.slug}{suffix}.tar.gz"

    def _on_browse(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar paquete como",
            str(Path.home() / self._default_filename()),
            "Archivo tar.gz (*.tar.gz)",
        )
        if path:
            if not path.endswith(".tar.gz"):
                path += ".tar.gz"
            self.dest_edit.setText(path)

    def _validate(self, metadata: ThemeMetadata) -> list[str]:
        errors = self._icon_manager.validate_all()
        try:
            metadata.validate()
        except ValueError as exc:
            errors.append(str(exc))
        if not self.dest_edit.text().strip():
            errors.append("Selecciona una ubicación de destino.")
        return errors

    # -- exportación --------------------------------------------------
    def _on_export_clicked(self) -> None:
        metadata = self._metadata_provider()
        errors = self._validate(metadata)
        if errors:
            QMessageBox.warning(
                self, "No se puede exportar", "\n".join(f"• {e}" for e in errors)
            )
            return

        self.export_button.setEnabled(False)
        self.progress_bar.setValue(0)
        self.status_label.setText("Iniciando exportación…")

        output_path = Path(self.dest_edit.text().strip())
        self._worker = ExportWorker(
            metadata, self._icon_manager.icons, self._selected_mode(), output_path
        )
        self._worker.progress.connect(self._on_progress)
        self._worker.finished_ok.connect(self._on_finished_ok)
        self._worker.failed.connect(self._on_failed)
        self._worker.start()

    def _on_progress(self, value: int, message: str) -> None:
        self.progress_bar.setValue(value)
        self.status_label.setText(message)

    def _on_finished_ok(self, output_path: str) -> None:
        self.export_button.setEnabled(True)
        self.status_label.setText(f"Exportado correctamente: {output_path}")
        QMessageBox.information(
            self, "Exportación completada", f"Tema exportado en:\n{output_path}"
        )

    def _on_failed(self, message: str) -> None:
        self.export_button.setEnabled(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("Error durante la exportación.")
        QMessageBox.critical(self, "Error al exportar", message)
