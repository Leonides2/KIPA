"""Panel de configuración de tamaños y contextos, y widget reutilizable
`SizeSelector` (usado también en el diálogo de edición por-icono del grid)."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.core.icon_manager import IconManager
from src.models.icon_item import STANDARD_SIZES, VALID_CONTEXTS

CONTEXT_DISPLAY_NAMES = {
    "apps": "Aplicaciones (apps)",
    "actions": "Acciones (actions)",
    "mimetypes": "Tipos MIME (mimetypes)",
    "places": "Lugares (places)",
    "status": "Estado (status)",
}


class SizeSelector(QWidget):
    """Checkboxes para los tamaños estándar + opción "Escalable (SVG)".

    Widget reutilizable: se usa tanto en el panel global como en el
    diálogo de edición individual de un icono.
    """

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._checkboxes: dict[int, QCheckBox] = {}

        layout = QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        columns = 4
        for i, size in enumerate(STANDARD_SIZES):
            checkbox = QCheckBox(f"{size}x{size}")
            self._checkboxes[size] = checkbox
            layout.addWidget(checkbox, i // columns, i % columns)

        self.scalable_checkbox = QCheckBox("Escalable (SVG)")
        row = (len(STANDARD_SIZES) - 1) // columns + 1
        layout.addWidget(self.scalable_checkbox, row, 0, 1, columns)

    def selected_sizes(self) -> set[int]:
        return {size for size, cb in self._checkboxes.items() if cb.isChecked()}

    def set_selected_sizes(self, sizes: set[int]) -> None:
        for size, cb in self._checkboxes.items():
            cb.setChecked(size in sizes)

    def is_scalable(self) -> bool:
        return self.scalable_checkbox.isChecked()

    def set_scalable(self, value: bool) -> None:
        self.scalable_checkbox.setChecked(value)


class SizeConfigPanel(QWidget):
    """Panel de configuración global: tamaños y contexto por defecto,
    aplicables a todos los iconos de una vez."""

    configuration_changed = Signal()

    def __init__(self, icon_manager: IconManager, parent: QWidget | None = None):
        super().__init__(parent)
        self._icon_manager = icon_manager

        layout = QVBoxLayout(self)

        sizes_group = QGroupBox("Tamaños a generar")
        sizes_layout = QVBoxLayout(sizes_group)
        self.size_selector = SizeSelector()
        sizes_layout.addWidget(self.size_selector)

        apply_sizes_row = QHBoxLayout()
        apply_sizes_row.addStretch()
        self.apply_sizes_button = QPushButton("Aplicar tamaños a todos los iconos")
        self.apply_sizes_button.clicked.connect(self._apply_sizes_to_all)
        apply_sizes_row.addWidget(self.apply_sizes_button)
        sizes_layout.addLayout(apply_sizes_row)
        layout.addWidget(sizes_group)

        context_group = QGroupBox("Contexto")
        context_layout = QVBoxLayout(context_group)
        context_row = QHBoxLayout()
        context_row.addWidget(QLabel("Contexto por defecto:"))
        self.context_combo = QComboBox()
        for ctx in VALID_CONTEXTS:
            self.context_combo.addItem(CONTEXT_DISPLAY_NAMES[ctx], userData=ctx)
        context_row.addWidget(self.context_combo)
        context_layout.addLayout(context_row)

        apply_context_row = QHBoxLayout()
        apply_context_row.addStretch()
        self.apply_context_button = QPushButton("Aplicar contexto a todos los iconos")
        self.apply_context_button.clicked.connect(self._apply_context_to_all)
        apply_context_row.addWidget(self.apply_context_button)
        context_layout.addLayout(apply_context_row)
        layout.addWidget(context_group)

        layout.addStretch()

    def selected_context(self) -> str:
        return self.context_combo.currentData()

    def _apply_sizes_to_all(self) -> None:
        sizes = self.size_selector.selected_sizes()
        self._icon_manager.set_sizes_for_all(sizes)
        if self.size_selector.is_scalable():
            for icon in self._icon_manager.icons:
                icon.scalable = True
        self.configuration_changed.emit()

    def _apply_context_to_all(self) -> None:
        self._icon_manager.set_context_for_all(self.selected_context())
        self.configuration_changed.emit()
