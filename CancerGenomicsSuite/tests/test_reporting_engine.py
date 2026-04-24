"""
Tests for reporting_engine (HTML / templates) aligned with current API.
"""

import sys
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from reporting_engine.html_reporter import HTMLReporter
from reporting_engine.pdf_builder import PDFBuilder
from reporting_engine.template_utils import TemplateUtils


class TestHTMLReporter:
    def test_init_default_template_dir(self):
        r = HTMLReporter()
        assert r.template_dir
        assert r.sections == []

    def test_set_metadata_and_section(self):
        r = HTMLReporter()
        r.set_metadata("T", author="A", description="D")
        r.add_text_section("Intro", "Hello")
        assert r.metadata["title"] == "T"
        assert len(r.sections) == 1

    @patch.object(HTMLReporter, "generate_html", return_value="<html></html>")
    def test_save_report(self, _gen, tmp_path):
        r = HTMLReporter()
        r.set_metadata("R")
        r.add_text_section("S", "c")
        out = tmp_path / "x.html"
        p = r.save_report(str(out))
        assert Path(p).exists()

    def test_add_table_section(self):
        r = HTMLReporter()
        df = pd.DataFrame({"a": [1, 2]})
        r.add_table_section("T", df, interactive=False)
        assert r.sections[-1]["type"] == "table"


class TestPDFBuilder:
    def test_init(self, tmp_path):
        p = str(tmp_path / "o.pdf")
        b = PDFBuilder(p)
        assert b.output_path == p


class TestTemplateUtils:
    def test_set_get_template(self, tmp_path):
        t = TemplateUtils(str(tmp_path))
        t.set_template("k", "<html></html>")
        assert t.get_template("k") == "<html></html>"
