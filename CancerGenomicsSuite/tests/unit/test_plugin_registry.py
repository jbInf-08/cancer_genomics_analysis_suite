"""Unit tests for dashboard plugin registry helpers."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from CancerGenomicsSuite import plugin_registry


def test_get_plugin_info_not_found():
    with patch.object(plugin_registry, "get_registered_plugins", return_value={}):
        assert plugin_registry.get_plugin_info("No Such Plugin") is None


def test_get_plugins_by_category_empty():
    with patch.object(plugin_registry, "get_registered_plugins", return_value={}):
        assert plugin_registry.get_plugins_by_category() == {}


def test_get_plugins_by_category_groups():
    plugins = {
        "Alpha": {
            "metadata": {
                "name": "Alpha",
                "category": "Core",
                "description": "d",
                "icon": "a",
            },
            "module_path": "mod.a",
        },
        "Beta": {
            "metadata": {
                "name": "Beta",
                "category": "Core",
                "description": "d",
                "icon": "b",
            },
            "module_path": "mod.b",
        },
    }
    with patch.object(plugin_registry, "get_registered_plugins", return_value=plugins):
        cats = plugin_registry.get_plugins_by_category()
    assert "Core" in cats
    assert len(cats["Core"]) == 2


def test_reload_plugin_missing_from_sys_modules():
    assert plugin_registry.reload_plugin("definitely.not.a.loaded.module") is False


def test_reload_plugin_success():
    with patch("importlib.reload", return_value=None) as mock_reload:
        assert plugin_registry.reload_plugin("CancerGenomicsSuite.plugin_registry") is True
        mock_reload.assert_called_once()


def test_reload_plugin_reload_error():
    with patch("importlib.reload", side_effect=RuntimeError("reload failed")):
        assert plugin_registry.reload_plugin("CancerGenomicsSuite.plugin_registry") is False


def test_get_registered_plugins_import_error():
    with patch("importlib.import_module", side_effect=ImportError("no module")):
        with patch.object(plugin_registry, "DASH_MODULES", ["bad.module"]):
            out = plugin_registry.get_registered_plugins()
    assert out == {}


def test_get_registered_plugins_generic_exception():
    with patch("importlib.import_module", side_effect=RuntimeError("boom")):
        with patch.object(plugin_registry, "DASH_MODULES", ["bad.module"]):
            out = plugin_registry.get_registered_plugins()
    assert out == {}


def test_get_registered_plugins_accepts_module_with_layout():
    fake_layout = MagicMock(name="layout")
    fake_mod = MagicMock()
    fake_mod.layout = fake_layout
    fake_mod.__name__ = "pkg.sub.fake_dash"

    with patch("importlib.import_module", return_value=fake_mod):
        with patch.object(plugin_registry, "DASH_MODULES", ["pkg.sub.fake_dash"]):
            with patch.object(
                plugin_registry,
                "MODULE_METADATA",
                {
                    "pkg.sub.fake_dash": {
                        "name": "FakeDash",
                        "category": "Test",
                        "description": "x",
                        "icon": "y",
                    }
                },
            ):
                out = plugin_registry.get_registered_plugins()
    assert "FakeDash" in out
    assert out["FakeDash"]["layout"] is fake_layout


def test_get_registered_plugins_skips_when_no_layout():
    fake_mod = SimpleNamespace(__name__="pkg.sub.nolayout")

    with patch("importlib.import_module", return_value=fake_mod):
        with patch.object(plugin_registry, "DASH_MODULES", ["pkg.sub.nolayout"]):
            out = plugin_registry.get_registered_plugins()
    assert out == {}
