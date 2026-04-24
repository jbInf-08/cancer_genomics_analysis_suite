"""Unit tests for reporting_engine.pdf_builder."""

from pathlib import Path

import pandas as pd
import pytest

pytest.importorskip("reportlab")

from CancerGenomicsSuite.reporting_engine.pdf_builder import PDFBuilder


def test_pdf_builder_a4_and_letter(tmp_path):
    p_a4 = tmp_path / "a4.pdf"
    b1 = PDFBuilder(str(p_a4), page_size="A4")
    assert b1.output_path == str(p_a4)

    p_let = tmp_path / "letter.pdf"
    b2 = PDFBuilder(str(p_let), page_size="letter")
    b2.add_title("T", subtitle="S")
    b2.add_heading("H2", level=2)
    b2.add_heading("H1", level=1)
    b2.add_paragraph("P")
    b2.add_table([["1", "2"]], headers=["a", "b"], title="Tbl")
    b2.add_dataframe_table(pd.DataFrame({"x": [1]}), title="DF")
    b2.add_chart({"data": [[1, 2]], "categories": ["a", "b"]}, chart_type="bar", title="Ch")
    b2.add_chart({"data": [[1]], "categories": ["a"]}, chart_type="line", title="Ln")
    b2.add_metadata()
    out = b2.build()
    assert Path(out).exists()
    assert Path(out).stat().st_size > 0


def test_pdf_builder_add_heading_level3(tmp_path):
    p = tmp_path / "h3.pdf"
    b = PDFBuilder(str(p))
    b.add_heading("Three", level=3)
    b.build()
    assert p.exists()


def test_pdf_builder_add_image_skips_missing(tmp_path):
    p = tmp_path / "img.pdf"
    b = PDFBuilder(str(p))
    b.add_title("I")
    b.add_image("/nonexistent/path/xyz.png")
    b.build()
    assert p.exists()


def test_pdf_builder_add_page_break(tmp_path):
    p = tmp_path / "break.pdf"
    b = PDFBuilder(str(p))
    b.add_title("PB")
    b.add_page_break()
    b.add_paragraph("after")
    b.build()
    assert p.exists()


def test_pdf_builder_create_analysis_report(tmp_path):
    p = tmp_path / "full.pdf"
    b = PDFBuilder(str(p))
    df = pd.DataFrame({"c": [1, 2]})
    out = b.create_analysis_report(
        {
            "summary": "S",
            "tables": [{"title": "T", "data": df}],
            "charts": [{"type": "bar", "title": "C", "data": {"data": [[1]], "categories": ["x"]}}],
            "conclusions": ["done"],
        },
        output_path=str(p),
    )
    assert Path(out).exists()
