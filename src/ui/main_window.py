"""Ventana principal: layout de 3 paneles + exportación (RF5)."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QMainWindow,
    QSplitter,
    QStatusBar,
    QToolBar,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import Qt

from src.core.icon_manager import IconManager
from src.ui.export_dialog import ExportDialog
from src.ui.icon_grid import IconGridWidget
from src.ui.metadata_panel import MetadataPanel
from src.ui.size_config_panel import SizeConfigPanel


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Icon Packager KDE")
        self.resize(1000, 640)

        self.icon_manager = IconManager()

        self.icon_grid = IconGridWidget(self.icon_manager)
        self.size_config_panel = SizeConfigPanel(self.icon_manager)
        self.metadata_panel = MetadataPanel()

        side_panel = QWidget()
        side_layout = QVBoxLayout(side_panel)
        side_layout.addWidget(self.size_config_panel)
        side_layout.addWidget(self.metadata_panel)
        side_layout.addStretch()

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.icon_grid)
        splitter.addWidget(side_panel)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 1)
        self.setCentralWidget(splitter)

        self._build_toolbar()

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self._update_status()

        self.icon_grid.icons_changed.connect(self._update_status)
        self.size_config_panel.configuration_changed.connect(self.icon_grid.refresh)
        self.size_config_panel.configuration_changed.connect(self._update_status)

    def _build_toolbar(self) -> None:
        toolbar = QToolBar("Principal")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        export_action = toolbar.addAction("Exportar…")
        export_action.triggered.connect(self._open_export_dialog)

    def _update_status(self) -> None:
        count = len(self.icon_manager)
        plural = "icono" if count == 1 else "iconos"
        self.status_bar.showMessage(f"{count} {plural} en el tema.")

    def _open_export_dialog(self) -> None:
        dialog = ExportDialog(self.icon_manager, self.metadata_panel.get_metadata, self)
        dialog.exec()
