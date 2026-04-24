"""Unit tests for reporting_engine.html_reporter."""

from pathlib import Path
from unittest.mock import patch

import pandas as pd
import plotly.graph_objects as go
import pytest

from CancerGenomicsSuite.reporting_engine.html_reporter import HTMLReporter


@pytest.fixture
def reporter_empty_templates(tmp_path):
    """Empty template dir forces Jinja fallback to bundled default template."""
    d = tmp_path / "tpl"
    d.mkdir()
    return HTMLReporter(template_dir=str(d))


def test_set_metadata_and_text_section(reporter_empty_templates):
    r = reporter_empty_templates
    r.set_metadata("T1", author="A", description="D", keywords=["k"])
    assert r.metadata["title"] == "T1"
    r.add_text_section("Intro", "Hello")
    assert len(r.sections) == 1
    assert r.sections[0]["type"] == "text"


def test_add_table_section_interactive(reporter_empty_templates):
    r = reporter_empty_templates
    df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
    r.add_table_section("T", df, interactive=True)
    assert r.sections[0]["type"] == "table"
    assert "table" in r.sections[0]["content"].lower()


def test_add_table_section_non_interactive(reporter_empty_templates):
    r = reporter_empty_templates
    df = pd.DataFrame({"x": [1]})
    r.add_table_section("T", df, interactive=False)
    assert "table-bordered" in r.sections[0]["content"]


def test_create_bar_line_scatter_heatmap(reporter_empty_templates):
    r = reporter_empty_templates
    bar = r.create_bar_chart({"categories": ["a"], "values": [1]}, "B")
    assert isinstance(bar, go.Figure)
    line = r.create_line_chart(
        {"series": {"s": {"x": [0, 1], "y": [2, 3]}}}, "L"
    )
    assert isinstance(line, go.Figure)
    sc = r.create_scatter_plot({"x": [1], "y": [2]}, "S")
    assert isinstance(sc, go.Figure)
    hm = r.create_heatmap(pd.DataFrame([[1, 2], [3, 4]]), "H")
    assert isinstance(hm, go.Figure)


def test_add_chart_section_plotly(reporter_empty_templates):
    r = reporter_empty_templates
    fig = go.Figure(data=go.Bar(x=["a"], y=[1]))
    r.add_chart_section("C", fig, chart_type="plotly")
    assert r.sections[0]["type"] == "chart"
    assert "Plotly.newPlot" in r.sections[0]["content"]


def test_add_chart_section_static_image(reporter_empty_templates):
    r = reporter_empty_templates
    fig = go.Figure(data=go.Bar(x=["a"], y=[1]))
    png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 8
    with patch.object(go.Figure, "to_image", return_value=png):
        r.add_chart_section("Static", fig, chart_type="static")
    assert r.sections[0]["type"] == "chart"
    assert "data:image/png;base64" in r.sections[0]["content"]


def test_generate_html_uses_default_template(reporter_empty_templates):
    r = reporter_empty_templates
    r.set_metadata("Rep")
    r.add_text_section("S", "body")
    html = r.generate_html("nonexistent_template.html")
    assert "<!DOCTYPE html>" in html
    assert "Rep" in html
    assert "body" in html


def test_save_report(tmp_path, reporter_empty_templates):
    r = reporter_empty_templates
    r.set_metadata("SaveTest")
    out = tmp_path / "out.html"
    path = r.save_report(str(out))
    assert path == str(out)
    assert "<!DOCTYPE html>" in out.read_text(encoding="utf-8")


def test_create_analysis_report_end_to_end(tmp_path, reporter_empty_templates):
    r = reporter_empty_templates
    df = pd.DataFrame({"g": ["TP53"], "v": [1.0]})
    path = tmp_path / "analysis.html"
    out = r.create_analysis_report(
        {
            "title": "Full",
            "description": "Desc",
            "summary": "Sum",
            "tables": [{"title": "T1", "data": df}],
            "charts": [
                {"type": "bar", "title": "B", "data": {"categories": ["x"], "values": [1]}},
                {"type": "line", "title": "L", "data": {"series": {"m": {"x": [0], "y": [1]}}}},
                {"type": "scatter", "title": "S", "data": {"x": [0], "y": [1]}},
                {"type": "heatmap", "title": "H", "data": df},
                {"type": "unknown", "title": "X", "data": {}},
            ],
            "conclusions": ["c1", "c2"],
        },
        str(path),
    )
    assert Path(out).exists()
    text = Path(out).read_text(encoding="utf-8")
    assert "Full" in text and "c1" in text
