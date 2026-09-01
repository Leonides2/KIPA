from __future__ import annotations

import configparser

import pytest

from src.core.icon_manager import IconManager
from src.core.theme_builder import ThemeBuildError, ThemeBuilder
from src.models.theme_metadata import ThemeMetadata


def test_build_creates_expected_structure(tmp_path, sample_png, sample_svg):
    manager = IconManager()
    manager.add_icon(sample_png, name="folder", context="places", sizes={16, 32})
    manager.add_icon(sample_svg, name="edit", context="actions")  # scalable

    metadata = ThemeMetadata(name="Mi Tema", author="Jorge")
    builder = ThemeBuilder(metadata, manager.icons)

    theme_root = builder.build(dest_dir=tmp_path)

    assert theme_root == tmp_path / "mi-tema"
    assert (theme_root / "index.theme").is_file()
    assert (theme_root / "16x16/places/folder.png").is_file()
    assert (theme_root / "32x32/places/folder.png").is_file()
    assert (theme_root / "scalable/actions/edit.svg").is_file()


def test_generated_png_has_requested_size(tmp_path, sample_png):
    from PIL import Image

    manager = IconManager()
    manager.add_icon(sample_png, name="folder", sizes={16, 48})
    metadata = ThemeMetadata(name="Sized Theme")
    builder = ThemeBuilder(metadata, manager.icons)

    theme_root = builder.build(dest_dir=tmp_path)

    with Image.open(theme_root / "16x16/apps/folder.png") as img:
        assert img.size == (16, 16)
    with Image.open(theme_root / "48x48/apps/folder.png") as img:
        assert img.size == (48, 48)


def test_index_theme_content(tmp_path, sample_png):
    manager = IconManager()
    manager.add_icon(sample_png, name="folder", sizes={16, 32})
    metadata = ThemeMetadata(
        name="Mi Tema", comment="Un tema de prueba", inherits="breeze", version="2.0"
    )
    builder = ThemeBuilder(metadata, manager.icons)
    theme_root = builder.build(dest_dir=tmp_path)

    config = configparser.ConfigParser()
    config.optionxform = str
    config.read(theme_root / "index.theme")

    assert config["Icon Theme"]["Name"] == "Mi Tema"
    assert config["Icon Theme"]["Comment"] == "Un tema de prueba"
    assert config["Icon Theme"]["Inherits"] == "breeze"
    assert config["Icon Theme"]["Version"] == "2.0"
    directories = config["Icon Theme"]["Directories"].split(",")
    assert "16x16/apps" in directories
    assert "32x32/apps" in directories

    assert config["16x16/apps"]["Size"] == "16"
    assert config["16x16/apps"]["Type"] == "Fixed"
    assert config["16x16/apps"]["Context"] == "Applications"


def test_index_theme_scalable_section(tmp_path, sample_svg):
    manager = IconManager()
    manager.add_icon(sample_svg, name="edit", context="actions")
    metadata = ThemeMetadata(name="Scalable Theme")
    builder = ThemeBuilder(metadata, manager.icons)
    theme_root = builder.build(dest_dir=tmp_path)

    config = configparser.ConfigParser()
    config.optionxform = str
    config.read(theme_root / "index.theme")

    section = config["scalable/actions"]
    assert section["Type"] == "Scalable"
    assert section["MinSize"] == "16"
    assert section["MaxSize"] == "512"
    assert section["Context"] == "Actions"


def test_build_without_icons_raises():
    metadata = ThemeMetadata(name="Vacío")
    builder = ThemeBuilder(metadata, [])
    with pytest.raises(ThemeBuildError):
        builder.build()


def test_build_without_theme_name_raises(sample_png):
    manager = IconManager()
    manager.add_icon(sample_png, sizes={16})
    metadata = ThemeMetadata(name="")
    builder = ThemeBuilder(metadata, manager.icons)
    with pytest.raises(ValueError):
        builder.build()


def test_build_uses_tempdir_when_no_dest_given(sample_png):
    manager = IconManager()
    manager.add_icon(sample_png, name="folder", sizes={16})
    metadata = ThemeMetadata(name="Temp Theme")
    builder = ThemeBuilder(metadata, manager.icons)

    theme_root = builder.build()

    assert theme_root.is_dir()
    assert (theme_root / "index.theme").is_file()
