"""Class-based dashboards expose the plugin interface plugin_registry reads.

The clinical data, article scraper, article manager, metabolic pathway and
multi-omics dashboards are classes that took a Dash app, created their services
and registered callbacks in __init__. With no module-level `layout`, the
registry skipped all five. The app is now optional: without one, an instance
only builds the layout, creating no services and registering no callbacks
(the article manager would otherwise create its SQLite file at import). Each
module exposes that layout and register_callbacks(app).
"""

from __future__ import annotations

import importlib

import dash
import pytest

PKG = "CancerGenomicsSuite.modules"

ADAPTED = [
    ("clinical_data_dashboard.clinical_dash", "ClinicalDashboard", ["analyzer"]),
    ("article_scraper.scraper_dash", "ScraperDashboard", ["scraper"]),
    ("article_manager.manager_dash", "ManagerDashboard", ["db_manager"]),
    (
        "metabolic_pathway_mapper.pathway_dash",
        "PathwayDashboard",
        ["mapper", "kegg_overlay"],
    ),
    ("multi_omics_integrator.multiomics_dash", "MultiOmicsDashboard", ["integrator"]),
]


def _ids(component, out=None):
    out = set() if out is None else out
    if isinstance(component, (list, tuple)):
        for c in component:
            _ids(c, out)
    elif hasattr(component, "to_plotly_json"):
        cid = getattr(component, "id", None)
        if isinstance(cid, str):
            out.add(cid)
        _ids(getattr(component, "children", None), out)
    return out


@pytest.mark.parametrize(("module", "cls", "services"), ADAPTED)
def test_layout_only_instance_starts_nothing(module, cls, services):
    mod = importlib.import_module(f"{PKG}.{module}")
    dashboard = getattr(mod, cls)()
    assert dashboard.app is None
    for name in services:
        assert not hasattr(dashboard, name), f"{cls}() created {name}"


@pytest.mark.parametrize(("module", "cls", "services"), ADAPTED)
def test_module_exposes_layout_and_register_callbacks(
    module, cls, services, tmp_path, monkeypatch
):
    # Full instances create their services, some of which open SQLite files
    # relative to the working directory.
    monkeypatch.chdir(tmp_path)
    mod = importlib.import_module(f"{PKG}.{module}")
    assert _ids(mod.layout), "layout has no component ids"

    app = dash.Dash(__name__, suppress_callback_exceptions=True)
    dashboard = mod.register_callbacks(app)
    assert isinstance(dashboard, getattr(mod, cls))
    assert dashboard.app is app
    assert app.callback_map, "register_callbacks registered no callbacks"
    for name in services:
        assert hasattr(dashboard, name)
    # The layout the registry serves is the one the callbacks were written for.
    assert _ids(dashboard.create_layout()) == _ids(mod.layout)
