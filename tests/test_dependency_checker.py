from __future__ import annotations

from src.core import dependency_checker as dc


def test_check_dependencies_in_dev_env_has_no_missing_required():
    # El entorno de desarrollo/test tiene PySide6 y Pillow instalados.
    report = dc.check_dependencies()
    assert report.is_ok
    assert report.missing_required == []


def test_check_dependencies_python_version_check(monkeypatch):
    monkeypatch.setattr(dc.sys, "version_info", (3, 9, 0))
    report = dc.check_dependencies()
    python_check = next(c for c in report.checks if c.name.startswith("Python"))
    assert python_check.ok is False
    assert not report.is_ok


def test_check_dependencies_missing_required_package(monkeypatch):
    original_find_spec = dc.importlib.util.find_spec

    def fake_find_spec(name):
        if name == "PySide6":
            return None
        return original_find_spec(name)

    monkeypatch.setattr(dc.importlib.util, "find_spec", fake_find_spec)
    report = dc.check_dependencies()

    pyside_check = next(c for c in report.checks if c.name == "PySide6")
    assert pyside_check.ok is False
    assert pyside_check in report.missing_required
    assert not report.is_ok


def test_format_report_includes_install_hint_for_missing_required(monkeypatch):
    original_find_spec = dc.importlib.util.find_spec

    def fake_find_spec(name):
        if name == "PIL":
            return None
        return original_find_spec(name)

    monkeypatch.setattr(dc.importlib.util, "find_spec", fake_find_spec)
    report = dc.check_dependencies()

    text = dc.format_report(report)
    assert "Pillow" in text
    assert "pip install Pillow" in text


def test_install_hint_falls_back_to_pip_on_unknown_distro(monkeypatch):
    monkeypatch.setattr(dc, "_distro_id", lambda: "some-unknown-distro")
    hint = dc._install_hint("pillow")
    assert hint == "pip install Pillow"


def test_install_hint_prefers_system_package_on_known_distro(monkeypatch):
    monkeypatch.setattr(dc, "_distro_id", lambda: "ubuntu")
    hint = dc._install_hint("pyside6")
    assert "apt install" in hint
    assert "pip install PySide6" in hint


def test_dependency_report_missing_optional():
    report = dc.DependencyReport(
        checks=[
            dc.DependencyCheck(name="req", required=True, ok=True),
            dc.DependencyCheck(name="opt", required=False, ok=False),
        ]
    )
    assert report.is_ok
    assert [c.name for c in report.missing_optional] == ["opt"]
    assert report.missing_required == []
