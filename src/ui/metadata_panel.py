"""Formulario de metadata del tema (RF3)."""

from __future__ import annotations

from src.models.theme_metadata import ThemeMetadata
from src.ui.qt_compat import Signal, QtWidgets

COMMON_INHERITS_OPTIONS = ("breeze", "breeze-dark", "oxygen", "hicolor", "")


class MetadataPanel(QtWidgets.QWidget):
    """Panel con el formulario de metadata: nombre, comentario, autor,
    versión y tema base del que heredar (`Inherits=`)."""

    metadata_changed = Signal()
    browse_theme_icons_requested = Signal(str)

    def __init__(self, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent)

        layout = QtWidgets.QFormLayout(self)

        self.name_edit = QtWidgets.QLineEdit()
        self.name_edit.setPlaceholderText("Mi Tema de Iconos")
        layout.addRow("Nombre del tema:", self.name_edit)

        self.comment_edit = QtWidgets.QTextEdit()
        self.comment_edit.setPlaceholderText("Descripción breve del tema…")
        self.comment_edit.setFixedHeight(60)
        layout.addRow("Comentario:", self.comment_edit)

        self.author_edit = QtWidgets.QLineEdit()
        layout.addRow("Autor:", self.author_edit)

        self.version_edit = QtWidgets.QLineEdit("1.0")
        layout.addRow("Versión:", self.version_edit)

        inherits_row = QtWidgets.QHBoxLayout()
        self.inherits_combo = QtWidgets.QComboBox()
        self.inherits_combo.setEditable(True)
        self.inherits_combo.addItems(COMMON_INHERITS_OPTIONS)
        self.inherits_combo.setCurrentText("breeze")
        inherits_row.addWidget(self.inherits_combo, 1)
        self.browse_icons_button = QtWidgets.QPushButton("Examinar iconos…")
        self.browse_icons_button.setToolTip(
            "Importar iconos puntuales del tema indicado para modificarlos "
            "(no hace falta copiar el tema completo: KDE resuelve el resto "
            "automáticamente vía Inherits=)."
        )
        self.browse_icons_button.clicked.connect(
            lambda: self.browse_theme_icons_requested.emit(
                self.inherits_combo.currentText().strip()
            )
        )
        inherits_row.addWidget(self.browse_icons_button)
        layout.addRow("Hereda de (Inherits):", inherits_row)

        for widget in (self.name_edit, self.author_edit, self.version_edit):
            widget.textChanged.connect(self.metadata_changed)
        self.comment_edit.textChanged.connect(self.metadata_changed)
        self.inherits_combo.editTextChanged.connect(self.metadata_changed)

    def get_metadata(self) -> ThemeMetadata:
        return ThemeMetadata(
            name=self.name_edit.text().strip(),
            comment=self.comment_edit.toPlainText().strip()
            or "Generado con Icon Packager",
            author=self.author_edit.text().strip(),
            version=self.version_edit.text().strip() or "1.0",
            inherits=self.inherits_combo.currentText().strip(),
        )

    def set_metadata(self, metadata: ThemeMetadata) -> None:
        self.name_edit.setText(metadata.name)
        self.comment_edit.setPlainText(metadata.comment)
        self.author_edit.setText(metadata.author)
        self.version_edit.setText(metadata.version)
        self.inherits_combo.setCurrentText(metadata.inherits)
