"""Diálogo para explorar un tema de iconos instalado e importar iconos
puntuales al `IconManager`, como punto de partida para modificarlos.

No copia el tema completo: solo los iconos que el usuario elige entran al
grid editable. El resto seguirá resolviéndose en KDE vía `Inherits=`.
"""

from __future__ import annotations

from src.core.icon_manager import IconManager
from src.core.theme_catalog import (
    CatalogIcon,
    build_catalog,
    discover_installed_themes,
    import_catalog_icon,
    search_catalog,
)
from src.ui.qt_compat import QtCore, QtGui, QtWidgets, Qt, Signal
from src.ui.size_config_panel import CONTEXT_DISPLAY_NAMES

ALL_CONTEXTS_LABEL = "Todos los contextos"


class ThemeImportDialog(QtWidgets.QDialog):
    """Buscador de iconos de un tema instalado localmente, para importar
    solo los que el usuario quiere modificar."""

    icons_imported = Signal(int)  # cuántos iconos se importaron

    def __init__(
        self,
        icon_manager: IconManager,
        parent: QtWidgets.QWidget | None = None,
        preselect_theme_id: str | None = None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Importar iconos de un tema instalado")
        self.resize(560, 480)

        self._icon_manager = icon_manager
        self._catalog: list[CatalogIcon] = []

        layout = QtWidgets.QVBoxLayout(self)

        theme_row = QtWidgets.QHBoxLayout()
        theme_row.addWidget(QtWidgets.QLabel("Tema instalado:"))
        self.theme_combo = QtWidgets.QComboBox()
        theme_row.addWidget(self.theme_combo, stretch=1)
        self.refresh_button = QtWidgets.QPushButton("Actualizar lista")
        self.refresh_button.clicked.connect(self._reload_themes)
        theme_row.addWidget(self.refresh_button)
        layout.addLayout(theme_row)

        self.empty_label = QtWidgets.QLabel(
            "No se encontró ningún tema de iconos instalado (se buscó en\n"
            "~/.local/share/icons, ~/.icons y en las rutas del sistema,\n"
            "p. ej. /usr/share/icons)."
        )
        self.empty_label.setWordWrap(True)
        self.empty_label.hide()
        layout.addWidget(self.empty_label)

        filter_row = QtWidgets.QHBoxLayout()
        self.search_edit = QtWidgets.QLineEdit()
        self.search_edit.setPlaceholderText("Buscar icono por nombre…")
        self.search_edit.textChanged.connect(self._refresh_results)
        filter_row.addWidget(self.search_edit, stretch=1)

        self.context_combo = QtWidgets.QComboBox()
        self.context_combo.addItem(ALL_CONTEXTS_LABEL, userData=None)
        self.context_combo.currentIndexChanged.connect(self._refresh_results)
        filter_row.addWidget(self.context_combo)
        layout.addLayout(filter_row)

        self.result_list = QtWidgets.QListWidget()
        self.result_list.setSelectionMode(
            QtWidgets.QAbstractItemView.ExtendedSelection
        )
        self.result_list.setIconSize(QtCore.QSize(32, 32))
        layout.addWidget(self.result_list, stretch=1)

        self.status_label = QtWidgets.QLabel("")
        layout.addWidget(self.status_label)

        buttons_row = QtWidgets.QHBoxLayout()
        buttons_row.addStretch()
        self.import_button = QtWidgets.QPushButton("Importar seleccionados")
        self.import_button.clicked.connect(self._on_import_clicked)
        buttons_row.addWidget(self.import_button)
        self.close_button = QtWidgets.QPushButton("Cerrar")
        self.close_button.clicked.connect(self.accept)
        buttons_row.addWidget(self.close_button)
        layout.addLayout(buttons_row)

        self.theme_combo.currentIndexChanged.connect(self._on_theme_selected)

        self._reload_themes(preselect_theme_id)

    # -- carga de temas/catálogo -----------------------------------------
    def _reload_themes(self, preselect_theme_id: str | None = None) -> None:
        self.theme_combo.blockSignals(True)
        self.theme_combo.clear()
        themes = discover_installed_themes()
        for theme in themes:
            self.theme_combo.addItem(theme.name, userData=theme)
        self.theme_combo.blockSignals(False)

        has_themes = self.theme_combo.count() > 0
        self.theme_combo.setVisible(has_themes)
        self.empty_label.setVisible(not has_themes)
        self.search_edit.setEnabled(has_themes)
        self.context_combo.setEnabled(has_themes)
        self.result_list.setEnabled(has_themes)
        self.import_button.setEnabled(has_themes)

        if not has_themes:
            self._catalog = []
            self.result_list.clear()
            return

        index = 0
        if preselect_theme_id:
            for i in range(self.theme_combo.count()):
                if self.theme_combo.itemData(i).id == preselect_theme_id:
                    index = i
                    break
        self.theme_combo.setCurrentIndex(index)
        self._on_theme_selected(index)

    def _on_theme_selected(self, _index: int) -> None:
        theme = self.theme_combo.currentData()
        if theme is None:
            return
        self.status_label.setText(f"Cargando catálogo de '{theme.name}'…")
        QtWidgets.QApplication.processEvents()

        self._catalog = build_catalog(theme.path)

        self.context_combo.blockSignals(True)
        self.context_combo.clear()
        self.context_combo.addItem(ALL_CONTEXTS_LABEL, userData=None)
        for context in sorted({c.context for c in self._catalog}):
            self.context_combo.addItem(
                CONTEXT_DISPLAY_NAMES.get(context, context), userData=context
            )
        self.context_combo.blockSignals(False)

        self._refresh_results()

    # -- filtrado/listado --------------------------------------------
    def _refresh_results(self) -> None:
        query = self.search_edit.text()
        context = self.context_combo.currentData()
        results = search_catalog(self._catalog, query=query, context=context)

        self.result_list.clear()
        for catalog_icon in results:
            context_label = CONTEXT_DISPLAY_NAMES.get(
                catalog_icon.context, catalog_icon.context
            )
            label = f"{catalog_icon.name}  [{context_label}]"
            sizes = ", ".join(str(s) for s in sorted(catalog_icon.sizes))
            if catalog_icon.scalable:
                sizes = (sizes + ", escalable") if sizes else "escalable"
            item = QtWidgets.QListWidgetItem(f"{label}  —  {sizes}")
            item.setData(Qt.UserRole, catalog_icon)
            try:
                item.setIcon(QtGui.QIcon(str(catalog_icon.best_source_path())))
            except ValueError:
                pass
            self.result_list.addItem(item)

        total = len(self._catalog)
        shown = len(results)
        self.status_label.setText(
            f"{shown} de {total} iconos" if shown != total else f"{total} iconos"
        )

    # -- importación ---------------------------------------------------
    def _on_import_clicked(self) -> None:
        selected_items = self.result_list.selectedItems()
        if not selected_items:
            QtWidgets.QMessageBox.information(
                self, "Nada seleccionado", "Selecciona al menos un icono para importar."
            )
            return

        imported = 0
        errors: list[str] = []
        for item in selected_items:
            catalog_icon: CatalogIcon = item.data(Qt.UserRole)
            try:
                import_catalog_icon(self._icon_manager, catalog_icon)
                imported += 1
            except (ValueError, FileNotFoundError) as exc:
                errors.append(str(exc))

        if errors:
            QtWidgets.QMessageBox.warning(
                self, "Algunos iconos no se importaron", "\n".join(errors)
            )
        if imported:
            self.status_label.setText(f"{imported} icono(s) importado(s) al tema.")
            self.icons_imported.emit(imported)
