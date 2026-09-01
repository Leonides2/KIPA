from __future__ import annotations

import json
import stat
import tarfile

import pytest

from src.core.icon_manager import IconManager
from src.core.packager import Packager, PackagerError
from src.core.theme_builder import ThemeBuilder
from src.models.theme_metadata import ThemeMetadata


def _build_theme(tmp_path, sample_png, sample_svg):
    manager = IconManager()
    manager.add_icon(sample_png, name="folder", context="places", sizes={16, 32})
    manager.add_icon(sample_svg, name="edit", context="actions")
    metadata = ThemeMetadata(name="Mi Tema", author="Jorge")
    builder = ThemeBuilder(metadata, manager.icons)
    theme_root = builder.build(dest_dir=tmp_path / "build")
    return theme_root, metadata


def test_export_mode_a_creates_tar_with_expected_layout(tmp_path, sample_png, sample_svg):
    theme_root, metadata = _build_theme(tmp_path, sample_png, sample_svg)
    packager = Packager(theme_root, metadata)

    output = packager.export_mode_a(tmp_path / "out" / "mi-tema.tar.gz")

    assert output.is_file()
    with tarfile.open(output, "r:gz") as tar:
        names = tar.getnames()
        assert "mi-tema/index.theme" in names
        assert "mi-tema/install.sh" in names
        assert "mi-tema/16x16/places/folder.png" in names
        assert "mi-tema/scalable/actions/edit.svg" in names


def test_export_mode_a_install_sh_is_executable(tmp_path, sample_png, sample_svg):
    theme_root, metadata = _build_theme(tmp_path, sample_png, sample_svg)
    packager = Packager(theme_root, metadata)
    output = packager.export_mode_a(tmp_path / "out" / "mi-tema.tar.gz")

    with tarfile.open(output, "r:gz") as tar:
        member = tar.getmember("mi-tema/install.sh")
        assert member.mode & stat.S_IXUSR


def test_export_mode_a_install_sh_content(tmp_path, sample_png, sample_svg):
    theme_root, metadata = _build_theme(tmp_path, sample_png, sample_svg)
    packager = Packager(theme_root, metadata)
    output = packager.export_mode_a(tmp_path / "out" / "mi-tema.tar.gz")

    with tarfile.open(output, "r:gz") as tar:
        content = tar.extractfile("mi-tema/install.sh").read().decode()
        assert "$HOME/.local/share/icons/mi-tema" in content
        assert "kbuildsycoca6" in content


def test_export_mode_b_creates_tar_with_metadata_json(tmp_path, sample_png, sample_svg):
    theme_root, metadata = _build_theme(tmp_path, sample_png, sample_svg)
    packager = Packager(theme_root, metadata)

    output = packager.export_mode_b(tmp_path / "out" / "mi-tema-kpkg.tar.gz")

    assert output.is_file()
    with tarfile.open(output, "r:gz") as tar:
        names = tar.getnames()
        assert "metadata.json" in names
        assert "index.theme" in names
        assert "16x16/places/folder.png" in names

        metadata_content = json.loads(tar.extractfile("metadata.json").read())
        assert metadata_content["KPackageStructure"] == "Icons"
        assert metadata_content["KPlugin"]["Id"] == "mi-tema"
        assert metadata_content["KPlugin"]["Name"] == "Mi Tema"


def test_export_without_built_theme_raises(tmp_path):
    metadata = ThemeMetadata(name="Fantasma")
    packager = Packager(tmp_path / "no-existe", metadata)
    with pytest.raises(PackagerError):
        packager.export_mode_a(tmp_path / "out.tar.gz")


def test_export_theme_dir_without_index_theme_raises(tmp_path):
    empty_theme = tmp_path / "sin-index"
    empty_theme.mkdir()
    metadata = ThemeMetadata(name="Sin Index")
    packager = Packager(empty_theme, metadata)
    with pytest.raises(PackagerError):
        packager.export_mode_b(tmp_path / "out.tar.gz")
