"""Formulario de metadata del tema (RF3)."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QComboBox, QFormLayout, QLineEdit, QTextEdit, QWidget

from src.models.theme_metadata import ThemeMetadata

COMMON_INHERITS_OPTIONS = ("breeze", "breeze-dark", "oxygen", "hicolor", "")


class MetadataPanel(QWidget):
    """Panel con el formulario de metadata: nombre, comentario, autor,
    versión y tema base del que heredar (`Inherits=`)."""

    metadata_changed = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)

        layout = QFormLayout(self)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Mi Tema de Iconos")
        layout.addRow("Nombre del tema:", self.name_edit)

        self.comment_edit = QTextEdit()
        self.comment_edit.setPlaceholderText("Descripción breve del tema…")
        self.comment_edit.setFixedHeight(60)
        layout.addRow("Comentario:", self.comment_edit)

        self.author_edit = QLineEdit()
        layout.addRow("Autor:", self.author_edit)

        self.version_edit = QLineEdit("1.0")
        layout.addRow("Versión:", self.version_edit)

        self.inherits_combo = QComboBox()
        self.inherits_combo.setEditable(True)
        self.inherits_combo.addItems(COMMON_INHERITS_OPTIONS)
        self.inherits_combo.setCurrentText("breeze")
        layout.addRow("Hereda de (Inherits):", self.inherits_combo)

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
