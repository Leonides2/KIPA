from __future__ import annotations

from pathlib import Path

from PIL import Image

from src.core.icon_manager import IconManager
from src.core.theme_catalog import (
    build_catalog,
    default_icon_search_dirs,
    discover_installed_themes,
    import_catalog_icon,
    search_catalog,
)


def _make_fake_theme(base: Path, theme_id: str, name: str, hidden: bool = False) -> Path:
    theme_dir = base / theme_id
    theme_dir.mkdir(parents=True)

    (theme_dir / "16x16/apps").mkdir(parents=True)
    (theme_dir / "32x32/apps").mkdir(parents=True)
    (theme_dir / "scalable/actions").mkdir(parents=True)
    (theme_dir / "16x16/categories").mkdir(parents=True)  # contexto no soportado

    Image.new("RGBA", (16, 16), (0, 0, 0, 255)).save(theme_dir / "16x16/apps/folder.png")
    Image.new("RGBA", (32, 32), (0, 0, 0, 255)).save(theme_dir / "32x32/apps/folder.png")
    (theme_dir / "scalable/actions/edit.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg"/>', encoding="utf-8"
    )
    (theme_dir / "16x16/categories/apps.png").write_bytes(b"fake")

    directories = "16x16/apps,32x32/apps,scalable/actions,16x16/categories"
    hidden_line = "Hidden=true\n" if hidden else ""
    (theme_dir / "index.theme").write_text(
        f"[Icon Theme]\nName={name}\n{hidden_line}Directories={directories}\n",
        encoding="utf-8",
    )
    return theme_dir


def test_default_icon_search_dirs_includes_system_paths(monkeypatch, tmp_path):
    """Breeze/Oxygen/Adwaita se instalan a nivel de sistema, nunca en
    ~/.local/share/icons: si no escaneamos XDG_DATA_DIRS, el buscador de
    temas no encuentra nada en una instalación KDE real."""
    fake_home = tmp_path / "home"
    monkeypatch.setattr(
        "src.core.theme_catalog.Path.home", staticmethod(lambda: fake_home)
    )
    monkeypatch.delenv("XDG_DATA_HOME", raising=False)
    monkeypatch.setenv("XDG_DATA_DIRS", "/usr/local/share:/usr/share")

    dirs = default_icon_search_dirs()

    assert fake_home / ".local/share/icons" in dirs
    assert fake_home / ".icons" in dirs
    assert Path("/usr/share/icons") in dirs
    assert Path("/usr/local/share/icons") in dirs


def test_default_icon_search_dirs_respects_xdg_data_home(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "custom-data"))
    monkeypatch.setenv("XDG_DATA_DIRS", "/usr/share")

    dirs = default_icon_search_dirs()

    assert tmp_path / "custom-data/icons" in dirs


def test_discover_installed_themes_finds_system_theme(tmp_path):
    """Un tema en una ruta 'de sistema' (fuera de HOME) también debe
    encontrarse cuando se pasa explícitamente como search_dir."""
    system_dir = tmp_path / "usr-share-icons"
    system_dir.mkdir()
    _make_fake_theme(system_dir, "breeze", "Breeze")

    themes = discover_installed_themes(search_dirs=[system_dir])

    assert [t.name for t in themes] == ["Breeze"]


def test_discover_installed_themes(tmp_path):
    base = tmp_path / "icons"
    base.mkdir()
    _make_fake_theme(base, "my-theme", "Mi Tema")

    themes = discover_installed_themes(search_dirs=[base])

    assert len(themes) == 1
    assert themes[0].id == "my-theme"
    assert themes[0].name == "Mi Tema"


def test_discover_installed_themes_skips_hidden(tmp_path):
    base = tmp_path / "icons"
    base.mkdir()
    _make_fake_theme(base, "hidden-theme", "Oculto", hidden=True)

    themes = discover_installed_themes(search_dirs=[base])

    assert themes == []


def test_discover_installed_themes_skips_dirs_without_index_theme(tmp_path):
    base = tmp_path / "icons"
    base.mkdir()
    (base / "not-a-theme").mkdir()

    themes = discover_installed_themes(search_dirs=[base])

    assert themes == []


def test_discover_installed_themes_missing_dir_is_ignored(tmp_path):
    themes = discover_installed_themes(search_dirs=[tmp_path / "no-existe"])
    assert themes == []


def test_build_catalog_groups_by_name_and_context(tmp_path):
    theme_dir = _make_fake_theme(tmp_path, "my-theme", "Mi Tema")

    catalog = build_catalog(theme_dir)
    names = {(c.context, c.name) for c in catalog}

    assert ("apps", "folder") in names
    assert ("actions", "edit") in names
    # El contexto "categories" no está soportado por la app: se ignora.
    assert not any(c.context == "categories" for c in catalog)


def test_build_catalog_folder_has_both_sizes(tmp_path):
    theme_dir = _make_fake_theme(tmp_path, "my-theme", "Mi Tema")
    catalog = build_catalog(theme_dir)

    folder = next(c for c in catalog if c.name == "folder")
    assert folder.sizes == {16, 32}
    assert not folder.scalable
    assert folder.svg_source is None


def test_build_catalog_svg_marks_scalable(tmp_path):
    theme_dir = _make_fake_theme(tmp_path, "my-theme", "Mi Tema")
    catalog = build_catalog(theme_dir)

    edit = next(c for c in catalog if c.name == "edit")
    assert edit.scalable
    assert edit.svg_source is not None
    assert edit.sizes == set()


def test_search_catalog_by_query_and_context(tmp_path):
    theme_dir = _make_fake_theme(tmp_path, "my-theme", "Mi Tema")
    catalog = build_catalog(theme_dir)

    assert [c.name for c in search_catalog(catalog, query="fold")] == ["folder"]
    assert [c.name for c in search_catalog(catalog, context="actions")] == ["edit"]
    assert search_catalog(catalog, query="nope") == []


def test_import_catalog_icon_png_only(tmp_path):
    theme_dir = _make_fake_theme(tmp_path, "my-theme", "Mi Tema")
    catalog = build_catalog(theme_dir)
    folder = next(c for c in catalog if c.name == "folder")

    manager = IconManager()
    item = import_catalog_icon(manager, folder)

    assert item.name == "folder"
    assert item.context == "apps"
    assert item.sizes == {16, 32}
    assert item.scalable is False
    assert item.source_path == theme_dir / "32x32/apps/folder.png"  # el de mayor tamaño


def test_import_catalog_icon_svg(tmp_path):
    theme_dir = _make_fake_theme(tmp_path, "my-theme", "Mi Tema")
    catalog = build_catalog(theme_dir)
    edit = next(c for c in catalog if c.name == "edit")

    manager = IconManager()
    item = import_catalog_icon(manager, edit)

    assert item.is_svg
    assert item.scalable is True
    assert item.source_path == theme_dir / "scalable/actions/edit.svg"


def test_import_catalog_icon_then_editable_independently(tmp_path):
    """Importar un icono del catálogo no debe impedir luego modificarlo
    (renombrar, cambiar tamaños) como a cualquier otro icono añadido."""
    theme_dir = _make_fake_theme(tmp_path, "my-theme", "Mi Tema")
    catalog = build_catalog(theme_dir)
    folder = next(c for c in catalog if c.name == "folder")

    manager = IconManager()
    import_catalog_icon(manager, folder)
    manager.set_sizes_for_icon("folder", {64})

    assert manager.find_by_name("folder").sizes == {64}
