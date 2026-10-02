"""Class-based dashboards expose the plugin interface plugin_registry reads.

The clinical data, article scraper, article manager, metabolic pathway and
multi-omics dashboards are classes that took a Dash app, created their services
and registered callbacks in __init__. With no module-level `layout`, the
registry skipped all five. The app is now optional: without one, an instance
only builds the layout, creating no services and registering no callbacks
(the article manager would otherwise create its SQLite file at import). Each
module exposes that layout and register_callbacks(app).

The genome browser, mutation effect, microarray, protein structure and ML
outcome dashboards went further: each created its own Dash app and assigned
that app's layout. Their layout now comes from a static build_layout(), and
given an app they register their callbacks on it without touching its layout or
title. That app is the main dashboard's, and setting its layout would replace
the whole page.
"""

from __future__ import annotations

import importlib
from pathlib import Path

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


SELF_CONTAINED = [
    ("genome_browser.browser_dash", "GenomeBrowserDashboard"),
    ("mutation_effect_predictor.mutation_dash", "MutationEffectDashboard"),
    ("microarray_analyzer.microarray_dash", "MicroarrayDashboard"),
    ("protein_structure_visualizer.structure_dash", "ProteinStructureDashboard"),
    ("ml_outcome_predictor.ml_dash", "MLOutcomeDashboard"),
]


@pytest.mark.parametrize(("module", "cls"), SELF_CONTAINED)
def test_self_contained_dashboard_leaves_a_given_app_alone(
    module, cls, tmp_path, monkeypatch
):
    # Their services create working directories (e.g. workflow_work/).
    monkeypatch.chdir(tmp_path)
    mod = importlib.import_module(f"{PKG}.{module}")
    dashboard_class = getattr(mod, cls)
    expected = _ids(dashboard_class.build_layout())
    assert expected and _ids(mod.layout) == expected

    app = dash.Dash(__name__, suppress_callback_exceptions=True, title="Main")
    main_layout = dash.html.Div(id="main-app-layout")
    app.layout = main_layout
    dashboard = mod.register_callbacks(app)
    assert isinstance(dashboard, dashboard_class)
    assert dashboard.app is app
    assert app.callback_map, "register_callbacks registered no callbacks"
    assert app.layout is main_layout, "the main app's layout was replaced"
    assert app.title == "Main"

    # Standalone use is unchanged: its own app, with the dashboard's layout.
    standalone = dashboard_class()
    assert standalone.app is not app
    assert _ids(standalone.app.layout) == expected


def test_batch_dashboard_registers_on_a_given_app(tmp_path, monkeypatch):
    """Same contract; and its job database goes to the working directory.

    BatchQueue defaults to a file in the package directory, which an installed
    package may not be able to write; registering would then fail.
    """
    monkeypatch.chdir(tmp_path)
    mod = importlib.import_module(f"{PKG}.batch_processing.batch_dash")
    expected = _ids(mod.BatchDashboard.build_layout())
    assert expected and _ids(mod.layout) == expected

    app = dash.Dash(__name__, suppress_callback_exceptions=True)
    main_layout = dash.html.Div(id="main-app-layout")
    app.layout = main_layout
    dashboard = mod.register_callbacks(app)
    assert dashboard.app is app
    assert app.layout is main_layout
    assert app.callback_map
    db = Path(dashboard.batch_queue.db_path).resolve()
    assert db.parent == tmp_path.resolve()
