"""Gestión en memoria de la lista de iconos del tema."""

from __future__ import annotations

from pathlib import Path

from src.models.icon_item import VALID_CONTEXTS, IconItem


class IconManager:
    """Mantiene la lista de `IconItem` y su configuración.

    La UI y el resto del core solo deben interactuar con los iconos a
    través de esta clase; nunca tocar el filesystem directamente desde la
    UI.
    """

    def __init__(self) -> None:
        self._icons: list[IconItem] = []

    # -- consulta -----------------------------------------------------
    @property
    def icons(self) -> list[IconItem]:
        return list(self._icons)

    def __len__(self) -> int:
        return len(self._icons)

    def is_empty(self) -> bool:
        return not self._icons

    def find_by_name(self, name: str) -> IconItem | None:
        for icon in self._icons:
            if icon.name == name:
                return icon
        return None

    # -- mutación -------------------------------------------------------
    def add_icon(
        self,
        source_path: str | Path,
        name: str | None = None,
        context: str = "apps",
        sizes: set[int] | None = None,
    ) -> IconItem:
        """Añade un icono individual a la lista, tras validarlo."""
        icon = IconItem(
            source_path=Path(source_path),
            name=name or Path(source_path).stem,
            context=context,
            sizes=set(sizes) if sizes else set(),
        )
        icon.validate_source()
        if self.find_by_name(icon.name):
            icon.name = self._unique_name(icon.name)
        self._icons.append(icon)
        return icon

    def add_icons(
        self,
        paths: list[str | Path],
        context: str = "apps",
        sizes: set[int] | None = None,
    ) -> list[IconItem]:
        """Añade varios iconos en lote (para drag & drop o selección múltiple)."""
        added = []
        for path in paths:
            added.append(self.add_icon(path, context=context, sizes=sizes))
        return added

    def remove_icon(self, name: str) -> bool:
        icon = self.find_by_name(name)
        if icon is None:
            return False
        self._icons.remove(icon)
        return True

    def replace_icon(self, name: str, new_source_path: str | Path) -> IconItem:
        icon = self.find_by_name(name)
        if icon is None:
            raise KeyError(f"No existe un icono con nombre '{name}'")
        icon.source_path = Path(new_source_path)
        icon.validate_source()
        icon.scalable = icon.is_svg and not icon.sizes
        return icon

    def clear(self) -> None:
        self._icons.clear()

    # -- configuración global -------------------------------------------
    def set_sizes_for_all(self, sizes: set[int]) -> None:
        for icon in self._icons:
            icon.sizes = set(sizes)

    def set_context_for_all(self, context: str) -> None:
        if context not in VALID_CONTEXTS:
            raise ValueError(f"Contexto inválido: {context}")
        for icon in self._icons:
            icon.context = context

    def set_sizes_for_icon(self, name: str, sizes: set[int]) -> None:
        icon = self.find_by_name(name)
        if icon is None:
            raise KeyError(f"No existe un icono con nombre '{name}'")
        icon.sizes = set(sizes)

    def set_context_for_icon(self, name: str, context: str) -> None:
        icon = self.find_by_name(name)
        if icon is None:
            raise KeyError(f"No existe un icono con nombre '{name}'")
        if context not in VALID_CONTEXTS:
            raise ValueError(f"Contexto inválido: {context}")
        icon.context = context

    # -- validación --------------------------------------------------
    def validate_all(self) -> list[str]:
        """Devuelve una lista de errores encontrados (vacía si todo OK)."""
        errors: list[str] = []
        if self.is_empty():
            errors.append("No se ha añadido ningún icono.")
        for icon in self._icons:
            try:
                icon.validate_source()
            except (FileNotFoundError, ValueError) as exc:
                errors.append(str(exc))
            if not icon.sizes and not icon.scalable:
                errors.append(
                    f"El icono '{icon.name}' no tiene tamaños ni modo escalable "
                    "configurado."
                )
        return errors

    # -- privado ----------------------------------------------------
    def _unique_name(self, base_name: str) -> str:
        i = 2
        candidate = f"{base_name}-{i}"
        while self.find_by_name(candidate):
            i += 1
            candidate = f"{base_name}-{i}"
        return candidate
