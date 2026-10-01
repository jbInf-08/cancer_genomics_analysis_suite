"""Every plugin_registry entry must name a real Dash plugin.

get_registered_plugins() imports each DASH_MODULES entry and keeps it only if
the import succeeds and the module exposes `layout`. Anything else is dropped
with a warning, and the dashboard silently disappears from the app. Of the 35
entries, 19 were dropped that way:

- five named modules that do not exist. Each package's dashboard lives under
  another name (genome_browser/browser_dash.py, not genome_dash.py);
- five were not dashboards (data-fetch functions, a notification service, a
  framework class), and one was an empty file;
- the rest were missing dependencies, or the class-based dashboards below.

PENDING_ADAPTERS lists the class-based dashboards. Each builds its own Dash app
and has no module-level layout yet. The last test is strict both ways: the list
must shrink as they are adapted, and nothing else may start failing.
"""

from __future__ import annotations

import json
import subprocess
import sys
import textwrap
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
SUITE = REPO / "CancerGenomicsSuite"

PENDING_ADAPTERS = {
    "modules.mutation_effect_predictor.mutation_dash",
    "modules.microarray_analyzer.microarray_dash",
    "modules.ml_outcome_predictor.ml_dash",
    "modules.protein_structure_visualizer.structure_dash",
    "modules.genome_browser.browser_dash",
    "modules.batch_processing.batch_dash",
    "modules.reporting.report_dash",
}


def _registry():
    from CancerGenomicsSuite import plugin_registry

    return plugin_registry


def test_every_entry_names_an_existing_module_file():
    missing = [
        m
        for m in _registry().DASH_MODULES
        if not (SUITE / (m.replace(".", "/") + ".py")).is_file()
    ]
    assert not missing, f"registry entries with no module file: {missing}"


def test_entries_and_metadata_agree():
    reg = _registry()
    entries, metadata = set(reg.DASH_MODULES), set(reg.MODULE_METADATA)
    assert entries - metadata == set(), "entries without metadata"
    assert metadata - entries == set(), "metadata for modules that are not listed"
    assert len(reg.DASH_MODULES) == len(entries), "an entry is listed twice"


def test_display_names_are_unique():
    """Plugins are keyed by display name, so a duplicate silently replaces one."""
    reg = _registry()
    names = [reg.MODULE_METADATA[m]["name"] for m in reg.DASH_MODULES]
    assert len(names) == len(set(names)), sorted(
        {n for n in names if names.count(n) > 1}
    )


def test_registry_loads_every_entry_except_the_pending_adapters(tmp_path):
    """Runs get_registered_plugins() as main_dashboard does, in a subprocess.

    The suite directory goes on sys.path, entries are imported as
    `modules.<package>.<module>`, and every dashboard's import-time side effects
    stay out of this session.
    """
    body = f"""
        import io, json, contextlib, logging, sys, warnings
        warnings.filterwarnings("ignore")
        logging.disable(logging.CRITICAL)
        sys.path.insert(0, {str(SUITE)!r})
        with contextlib.redirect_stdout(io.StringIO()):
            import plugin_registry
            plugins = plugin_registry.get_registered_plugins()
        print(json.dumps(sorted(p["module_path"] for p in plugins.values())))
    """
    proc = subprocess.run(
        [sys.executable, "-c", textwrap.dedent(body)],
        capture_output=True,
        text=True,
        timeout=900,
        cwd=tmp_path,
    )
    assert proc.returncode == 0, proc.stderr[-3000:]
    loaded = set(json.loads(proc.stdout.strip().splitlines()[-1]))
    expected = set(_registry().DASH_MODULES) - PENDING_ADAPTERS

    not_loading = sorted(expected - loaded)
    assert not not_loading, f"registered dashboards that failed to load: {not_loading}"
    now_loading = sorted(loaded & PENDING_ADAPTERS)
    assert not now_loading, f"now load; remove from PENDING_ADAPTERS: {now_loading}"


# Component ids already shared between loaded plugins before any adapter work.
# They are not duplicate outputs (registration would fail), but each is still a
# shared name in one app; to be removed, not added to.
KNOWN_SHARED_IDS = {
    "analysis-options",
    "analysis-tabs",
    "clear-data-btn",
    "run-workflow",
    "upload-data",
}


def test_no_component_id_is_shared_between_plugins(tmp_path):
    """All plugins' callbacks are registered on one app, as main_dashboard does.

    An id used by two plugins (or by a plugin and the main app's own layout)
    either collides at registration or lets one plugin's input fire another's
    callback. The first adapted dashboards brought fourteen such ids -- four
    of them each had their own `main-tabs` and `load-mock-data` -- now
    prefixed.
    """
    body = f"""
        import ast, contextlib, io, json, logging, pathlib, sys, warnings
        from collections import defaultdict
        warnings.filterwarnings("ignore")
        logging.disable(logging.CRITICAL)
        sys.path.insert(0, {str(SUITE)!r})
        import dash
        with contextlib.redirect_stdout(io.StringIO()):
            import plugin_registry
            plugins = plugin_registry.get_registered_plugins()

        def layout_ids(c, out):
            if isinstance(c, (list, tuple)):
                for x in c:
                    layout_ids(x, out)
            elif hasattr(c, "to_plotly_json"):
                if isinstance(getattr(c, "id", None), str):
                    out.add(c.id)
                layout_ids(getattr(c, "children", None), out)

        def output_ids(spec):
            for part in spec.strip(".").split("..."):
                if not part.startswith("{{"):
                    yield part.rsplit(".", 1)[0]

        app = dash.Dash(__name__, suppress_callback_exceptions=True)
        uses = defaultdict(set)
        for name, p in plugins.items():
            ids = set()
            layout_ids(p["layout"], ids)
            seen = len(app._callback_list)
            if p.get("register_callbacks"):
                with contextlib.redirect_stdout(io.StringIO()):
                    p["register_callbacks"](app)
            for cb in app._callback_list[seen:]:
                ids.update(output_ids(cb["output"]))
                for dep in cb.get("inputs", []) + cb.get("state", []):
                    if isinstance(dep.get("id"), str):
                        ids.add(dep["id"])
            for i in ids:
                uses[i].add(name)
        src = pathlib.Path({str(SUITE / "main_dashboard.py")!r}).read_text("utf-8")
        for n in ast.walk(ast.parse(src)):
            if (isinstance(n, ast.keyword) and n.arg == "id"
                    and isinstance(n.value, ast.Constant)
                    and isinstance(n.value.value, str)):
                uses[n.value.value].add("(main app)")
        shared = {{i: sorted(p) for i, p in uses.items() if len(p) > 1}}
        print(json.dumps(shared))
    """
    proc = subprocess.run(
        [sys.executable, "-c", textwrap.dedent(body)],
        capture_output=True,
        text=True,
        timeout=900,
        cwd=tmp_path,
    )
    assert proc.returncode == 0, proc.stderr[-3000:]
    shared = json.loads(proc.stdout.strip().splitlines()[-1])

    new = {i: p for i, p in shared.items() if i not in KNOWN_SHARED_IDS}
    assert not new, f"component ids shared between plugins: {new}"
    resolved = sorted(KNOWN_SHARED_IDS - set(shared))
    assert not resolved, f"no longer shared; remove from KNOWN_SHARED_IDS: {resolved}"
