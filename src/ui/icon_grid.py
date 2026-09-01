"""Grid de iconos: preview, nombre editable, contexto y tamaños por icono.

Toda mutación de datos pasa por `IconManager` (RF1) — este widget nunca
escribe en el filesystem por sí mismo, solo lee/valida a través del
manager.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.core.icon_manager import IconManager
from src.models.icon_item import VALID_CONTEXTS, IconItem
from src.ui.size_config_panel import CONTEXT_DISPLAY_NAMES, SizeSelector

SVG_PNG_FILTER = "Iconos (*.svg *.png);;SVG (*.svg);;PNG (*.png);;Todos los archivos (*)"

COL_PREVIEW = 0
COL_NAME = 1
COL_CONTEXT = 2
COL_SIZES = 3
COL_ACTIONS = 4


class IconEditDialog(QDialog):
    """Diálogo de edición de tamaños/contexto para un icono individual."""

    def __init__(self, icon: IconItem, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle(f"Configurar '{icon.name}'")
        self._icon = icon

        layout = QVBoxLayout(self)

        from PySide6.QtWidgets import QComboBox, QFormLayout, QLineEdit

        form = QFormLayout()
        self.name_edit = QLineEdit(icon.name)
        form.addRow("Nombre:", self.name_edit)

        self.context_combo = QComboBox()
        for ctx in VALID_CONTEXTS:
            self.context_combo.addItem(CONTEXT_DISPLAY_NAMES[ctx], userData=ctx)
        idx = self.context_combo.findData(icon.context)
        if idx >= 0:
            self.context_combo.setCurrentIndex(idx)
        form.addRow("Contexto:", self.context_combo)
        layout.addLayout(form)

        self.size_selector = SizeSelector()
        self.size_selector.set_selected_sizes(icon.sizes)
        self.size_selector.set_scalable(icon.scalable)
        if not icon.is_svg:
            self.size_selector.scalable_checkbox.setEnabled(False)
        layout.addWidget(self.size_selector)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def result_name(self) -> str:
        return self.name_edit.text().strip()

    def result_context(self) -> str:
        return self.context_combo.currentData()

    def result_sizes(self) -> set[int]:
        return self.size_selector.selected_sizes()

    def result_scalable(self) -> bool:
        return self.size_selector.is_scalable()


class IconGridWidget(QWidget):
    """Grid principal de iconos con toolbar de añadir/eliminar/reemplazar
    y soporte de drag & drop."""

    icons_changed = Signal()

    def __init__(self, icon_manager: IconManager, parent: QWidget | None = None):
        super().__init__(parent)
        self._icon_manager = icon_manager
        self.setAcceptDrops(True)

        layout = QVBoxLayout(self)

        toolbar = QHBoxLayout()
        self.add_button = QPushButton("Añadir iconos…")
        self.add_button.clicked.connect(self._on_add_clicked)
        toolbar.addWidget(self.add_button)

        self.remove_button = QPushButton("Eliminar seleccionado")
        self.remove_button.clicked.connect(self._on_remove_clicked)
        toolbar.addWidget(self.remove_button)

        self.replace_button = QPushButton("Reemplazar…")
        self.replace_button.clicked.connect(self._on_replace_clicked)
        toolbar.addWidget(self.replace_button)

        toolbar.addStretch()
        layout.addLayout(toolbar)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(
            ["Preview", "Nombre", "Contexto", "Tamaños", ""]
        )
        self.table.setIconSize(QSize(48, 48))
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.horizontalHeader().setSectionResizeMode(
            COL_NAME, QHeaderView.ResizeMode.Stretch
        )
        self.table.itemChanged.connect(self._on_item_changed)
        layout.addWidget(self.table)

        self._suppress_item_changed = False

    # -- API pública --------------------------------------------------
    def refresh(self) -> None:
        """Reconstruye la tabla a partir del estado actual de IconManager."""
        self._suppress_item_changed = True
        self.table.setRowCount(0)
        for icon in self._icon_manager.icons:
            self._append_row(icon)
        self._suppress_item_changed = False

    def selected_icon_name(self) -> str | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, COL_NAME)
        return item.text() if item else None

    # -- drag & drop --------------------------------------------------
    def dragEnterEvent(self, event):  # noqa: N802 (nombre requerido por Qt)
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):  # noqa: N802
        paths = [
            Path(url.toLocalFile())
            for url in event.mimeData().urls()
            if url.isLocalFile()
        ]
        paths = [p for p in paths if p.suffix.lower() in (".svg", ".png")]
        self._add_paths(paths)
        event.acceptProposedAction()

    # -- acciones de toolbar --------------------------------------------
    def _on_add_clicked(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(
            self, "Añadir iconos", str(Path.home()), SVG_PNG_FILTER
        )
        self._add_paths([Path(f) for f in files])

    def _add_paths(self, paths: list[Path]) -> None:
        errors = []
        for path in paths:
            try:
                self._icon_manager.add_icon(path)
            except (FileNotFoundError, ValueError) as exc:
                errors.append(str(exc))
        if errors:
            QMessageBox.warning(self, "Algunos iconos no se añadieron", "\n".join(errors))
        if paths:
            self.refresh()
            self.icons_changed.emit()

    def _on_remove_clicked(self) -> None:
        name = self.selected_icon_name()
        if name is None:
            return
        self._icon_manager.remove_icon(name)
        self.refresh()
        self.icons_changed.emit()

    def _on_replace_clicked(self) -> None:
        name = self.selected_icon_name()
        if name is None:
            return
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Reemplazar icono", str(Path.home()), SVG_PNG_FILTER
        )
        if not file_path:
            return
        try:
            self._icon_manager.replace_icon(name, file_path)
        except (FileNotFoundError, ValueError, KeyError) as exc:
            QMessageBox.warning(self, "No se pudo reemplazar", str(exc))
            return
        self.refresh()
        self.icons_changed.emit()

    def _on_edit_clicked(self, icon_name: str) -> None:
        icon = self._icon_manager.find_by_name(icon_name)
        if icon is None:
            return
        dialog = IconEditDialog(icon, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        new_name = dialog.result_name()
        if new_name and new_name != icon.name:
            if self._icon_manager.find_by_name(new_name):
                QMessageBox.warning(
                    self, "Nombre duplicado", f"Ya existe un icono llamado '{new_name}'."
                )
            else:
                icon.name = new_name

        self._icon_manager.set_context_for_icon(icon.name, dialog.result_context())
        self._icon_manager.set_sizes_for_icon(icon.name, dialog.result_sizes())
        icon.scalable = dialog.result_scalable()

        self.refresh()
        self.icons_changed.emit()

    # -- item changed (rename inline) ------------------------------------
    def _on_item_changed(self, item: QTableWidgetItem) -> None:
        if self._suppress_item_changed or item.column() != COL_NAME:
            return
        row = item.row()
        old_name = item.data(Qt.ItemDataRole.UserRole)
        new_name = item.text().strip()
        if not new_name or new_name == old_name:
            self._suppress_item_changed = True
            item.setText(old_name)
            self._suppress_item_changed = False
            return
        if self._icon_manager.find_by_name(new_name):
            QMessageBox.warning(
                self, "Nombre duplicado", f"Ya existe un icono llamado '{new_name}'."
            )
            self._suppress_item_changed = True
            item.setText(old_name)
            self._suppress_item_changed = False
            return
        icon = self._icon_manager.find_by_name(old_name)
        if icon:
            icon.name = new_name
            item.setData(Qt.ItemDataRole.UserRole, new_name)
        self.icons_changed.emit()

    # -- construcción de filas ------------------------------------------
    def _append_row(self, icon: IconItem) -> None:
        row = self.table.rowCount()
        self.table.insertRow(row)

        preview_item = QTableWidgetItem()
        qicon = QIcon(str(icon.source_path)) if icon.source_path.exists() else QIcon()
        preview_item.setIcon(qicon)
        preview_item.setFlags(preview_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.table.setItem(row, COL_PREVIEW, preview_item)

        name_item = QTableWidgetItem(icon.name)
        name_item.setData(Qt.ItemDataRole.UserRole, icon.name)
        self.table.setItem(row, COL_NAME, name_item)

        context_item = QTableWidgetItem(CONTEXT_DISPLAY_NAMES.get(icon.context, icon.context))
        context_item.setFlags(context_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.table.setItem(row, COL_CONTEXT, context_item)

        sizes_label = ", ".join(str(s) for s in sorted(icon.sizes))
        if icon.scalable:
            sizes_label = (sizes_label + ", escalable") if sizes_label else "escalable"
        sizes_item = QTableWidgetItem(sizes_label or "(sin configurar)")
        sizes_item.setFlags(sizes_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.table.setItem(row, COL_SIZES, sizes_item)

        edit_button = QPushButton("Configurar…")
        edit_button.clicked.connect(lambda _=False, n=icon.name: self._on_edit_clicked(n))
        self.table.setCellWidget(row, COL_ACTIONS, edit_button)
