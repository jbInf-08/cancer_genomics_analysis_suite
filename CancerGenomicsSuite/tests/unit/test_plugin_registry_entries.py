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

PENDING_ADAPTERS listed the class-based dashboards while each still lacked a
module-level layout; all are adapted now, so it is empty and every entry must
load. The loading test stays strict both ways.
"""

from __future__ import annotations

import json
import subprocess
import sys
import textwrap
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
SUITE = REPO / "CancerGenomicsSuite"

PENDING_ADAPTERS: set = set()


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


# Callbacks whose outputs are rendered later by another callback (a sub-tab or
# a results area), in plugins not yet converted. Each such output is missing
# whenever its container is not showing, and Dash then drops the callback's
# whole update ("A nonexistent object was used in an Output"). To be removed,
# not added to.
KNOWN_OUTPUTS_OUTSIDE_LAYOUT = {
    "A Plasmid Editor (APE)": {
        "cloning-results",
        "create-plasmid-results",
        "load-plasmid-results",
        "primer-results",
        "restriction-results",
    },
    "DNA Sequence Analyzer": {
        "dna-analysis-results",
        "dna-sequence-input",
        "dna-visualizations",
        "sequence-name",
    },
    "Gene Expression Plotter": {
        "expression-analysis-results",
        "expression-data-preview",
        "expression-upload-status",
        "expression-visualizations",
        "upload-expression-data",
        "upload-metadata",
    },
    "IGV Integration": {"genome-results", "navigation-results", "track-results"},
    "MATLAB Integration": {"descriptive-results", "fft-results"},
    "Phylogenetic Tree Viewer": {
        "tree-alignment-preview",
        "tree-comparison-results",
        "tree-results",
        "tree-upload-status",
        "tree-visualization",
        "tree1-select",
        "tree2-select",
        "upload-alignment",
    },
    "Protein Sequence Viewer": {
        "protein-analysis-results",
        "protein-sequence-input",
        "protein-sequence-name",
        "protein-visualizations",
    },
    "PyMOL Integration": {
        "alignment-results",
        "file-load-results",
        "pdb-fetch-results",
    },
    "R Integration": {"deseq2-results", "go-results"},
    "Text Editors": {
        "create-file-results",
        "edit-file-results",
        "file-info-results",
        "open-file-results",
        "preview-results",
        "replace-results",
        "search-results",
    },
}


def test_every_callback_output_is_in_its_plugins_layout(tmp_path):
    """The clinical, multi-omics, pathway, article manager and scraper
    dashboards rendered each sub-tab from a callback. Seventeen of their
    callbacks wrote into sub-tabs, so they failed whenever another sub-tab was
    showing: at tab open, and when an action was taken from the wrong sub-tab.
    Their sub-tab content is now Tab children, always in the layout.
    """
    body = f"""
        import contextlib, io, json, logging, sys, warnings
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

        app = dash.Dash(__name__, suppress_callback_exceptions=True)
        outside = {{}}
        for name, p in plugins.items():
            static = set()
            layout_ids(p["layout"], static)
            seen = len(app._callback_list)
            if p.get("register_callbacks"):
                with contextlib.redirect_stdout(io.StringIO()):
                    p["register_callbacks"](app)
            for cb in app._callback_list[seen:]:
                for part in cb["output"].strip(".").split("..."):
                    if part.startswith("{{"):
                        continue
                    cid = part.rsplit(".", 1)[0]
                    if cid not in static:
                        outside.setdefault(name, []).append(cid)
        print(json.dumps({{k: sorted(set(v)) for k, v in outside.items()}}))
    """
    proc = subprocess.run(
        [sys.executable, "-c", textwrap.dedent(body)],
        capture_output=True,
        text=True,
        timeout=900,
        cwd=tmp_path,
    )
    assert proc.returncode == 0, proc.stderr[-3000:]
    outside = {
        k: set(v) for k, v in json.loads(proc.stdout.strip().splitlines()[-1]).items()
    }

    new = {
        name: sorted(ids - KNOWN_OUTPUTS_OUTSIDE_LAYOUT.get(name, set()))
        for name, ids in outside.items()
    }
    new = {k: v for k, v in new.items() if v}
    assert not new, f"callback outputs missing from the plugin's layout: {new}"
    fixed = {
        name: sorted(ids - outside.get(name, set()))
        for name, ids in KNOWN_OUTPUTS_OUTSIDE_LAYOUT.items()
    }
    fixed = {k: v for k, v in fixed.items() if v}
    assert (
        not fixed
    ), f"now in the layout; remove from KNOWN_OUTPUTS_OUTSIDE_LAYOUT: {fixed}"
