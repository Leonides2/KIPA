from __future__ import annotations

import pytest

from src.core.icon_manager import IconManager


def test_add_icon_from_png(sample_png):
    manager = IconManager()
    icon = manager.add_icon(sample_png, sizes={32, 48})

    assert len(manager) == 1
    assert icon.name == "sample-icon"
    assert icon.context == "apps"
    assert icon.sizes == {32, 48}
    assert not icon.scalable


def test_add_icon_from_svg_defaults_to_scalable(sample_svg):
    manager = IconManager()
    icon = manager.add_icon(sample_svg)

    assert icon.scalable is True
    assert icon.sizes == set()


def test_add_icons_batch(sample_png, sample_svg):
    manager = IconManager()
    added = manager.add_icons([sample_png, sample_svg], context="places")

    assert len(added) == 2
    assert all(icon.context == "places" for icon in added)


def test_add_icon_duplicate_name_gets_suffixed(sample_png):
    manager = IconManager()
    manager.add_icon(sample_png, name="folder")
    second = manager.add_icon(sample_png, name="folder")

    assert second.name == "folder-2"
    assert len(manager) == 2


def test_add_icon_missing_file_raises(tmp_path):
    manager = IconManager()
    with pytest.raises(FileNotFoundError):
        manager.add_icon(tmp_path / "no-existe.png")


def test_add_icon_unsupported_format_raises(tmp_path):
    bogus = tmp_path / "icon.bmp"
    bogus.write_bytes(b"not-a-real-bmp")
    manager = IconManager()
    with pytest.raises(ValueError):
        manager.add_icon(bogus)


def test_remove_icon(sample_png):
    manager = IconManager()
    manager.add_icon(sample_png, name="folder")

    assert manager.remove_icon("folder") is True
    assert manager.is_empty()
    assert manager.remove_icon("folder") is False


def test_replace_icon(sample_png, sample_svg):
    manager = IconManager()
    manager.add_icon(sample_png, name="folder", sizes={32})

    updated = manager.replace_icon("folder", sample_svg)

    assert updated.source_path == sample_svg
    assert updated.is_svg


def test_set_sizes_and_context_for_all(sample_png, sample_svg):
    manager = IconManager()
    manager.add_icon(sample_png, name="a")
    manager.add_icon(sample_svg, name="b")

    manager.set_sizes_for_all({16, 32})
    manager.set_context_for_all("status")

    assert all(icon.sizes == {16, 32} for icon in manager.icons)
    assert all(icon.context == "status" for icon in manager.icons)


def test_set_context_for_all_invalid_raises(sample_png):
    manager = IconManager()
    manager.add_icon(sample_png)
    with pytest.raises(ValueError):
        manager.set_context_for_all("bogus")


def test_set_sizes_for_icon(sample_png):
    manager = IconManager()
    manager.add_icon(sample_png, name="a")
    manager.set_sizes_for_icon("a", {64})
    assert manager.find_by_name("a").sizes == {64}


def test_set_sizes_for_unknown_icon_raises():
    manager = IconManager()
    with pytest.raises(KeyError):
        manager.set_sizes_for_icon("missing", {16})


def test_validate_all_empty_manager():
    manager = IconManager()
    errors = manager.validate_all()
    assert any("ningún icono" in e for e in errors)


def test_validate_all_icon_without_sizes_or_scalable(sample_png):
    manager = IconManager()
    manager.add_icon(sample_png, name="a")  # PNG sin tamaños ni scalable
    errors = manager.validate_all()
    assert any("no tiene tamaños" in e for e in errors)


def test_validate_all_ok(sample_png, sample_svg):
    manager = IconManager()
    manager.add_icon(sample_png, name="a", sizes={32})
    manager.add_icon(sample_svg, name="b")
    assert manager.validate_all() == []


def test_clear(sample_png):
    manager = IconManager()
    manager.add_icon(sample_png)
    manager.clear()
    assert manager.is_empty()
