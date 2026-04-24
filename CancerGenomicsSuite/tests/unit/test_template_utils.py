"""Unit tests for reporting_engine.template_utils."""

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from CancerGenomicsSuite.reporting_engine.template_utils import TemplateUtils


def test_template_utils_loads_html_from_directory(tmp_path):
    d = tmp_path / "tpl"
    d.mkdir()
    (d / "report.html").write_text("<p>{{ name }}</p>", encoding="utf-8")
    tu = TemplateUtils(template_dir=str(d))
    assert tu.get_template("report") == "<p>{{ name }}</p>"


def test_substitute_variables_simple():
    tu = TemplateUtils(template_dir=str(Path(__file__).parent))  # may be empty of html
    out = tu.substitute_variables("Hello {{ x }}", {"x": "world"})
    assert out == "Hello world"


def test_substitute_variables_unknown_placeholder_preserved():
    tu = TemplateUtils(template_dir=str(Path(__file__).parent))
    out = tu.substitute_variables("Hi {{ missing }}", {})
    assert "{{ missing }}" in out


def test_substitute_variables_if_block():
    tu = TemplateUtils(template_dir=str(Path(__file__).parent))
    tpl = "{% if show %}YES{% endif %}"
    assert tu.substitute_variables(tpl, {"show": True}) == "YES"
    assert tu.substitute_variables(tpl, {"show": False}) == ""


def test_substitute_variables_for_loop():
    tu = TemplateUtils(template_dir=str(Path(__file__).parent))
    tpl = "{% for n in nums %}{{ n }};{% endfor %}"
    out = tu.substitute_variables(tpl, {"nums": [1, 2, 3]})
    assert "1;" in out and "2;" in out and "3;" in out


def test_substitute_variables_if_equals():
    tu = TemplateUtils(template_dir=str(Path(__file__).parent))
    tpl = "{% if role == 'admin' %}OK{% endif %}"
    assert tu.substitute_variables(tpl, {"role": "admin"}) == "OK"
    assert tu.substitute_variables(tpl, {"role": "user"}) == ""


def test_substitute_variables_json_list():
    tu = TemplateUtils(template_dir=str(Path(__file__).parent))
    out = tu.substitute_variables("Data: {{ items }}", {"items": [1, 2]})
    assert "[1, 2]" in out


def test_set_and_get_template():
    tu = TemplateUtils(template_dir=str(Path(__file__).parent))
    tu.set_template("custom", "<html></html>")
    assert tu.get_template("custom") == "<html></html>"


def test_format_number():
    tu = TemplateUtils(template_dir=str(Path(__file__).parent))
    s = tu.format_number(1234.567, precision=2, use_thousands_separator=True)
    assert "234" in s
    s2 = tu.format_number(3.1, precision=1, use_thousands_separator=False)
    assert s2.startswith("3.")


def test_format_number_non_numeric_passthrough():
    tu = TemplateUtils(template_dir=str(Path(__file__).parent))
    assert tu.format_number("n/a") == "n/a"


def test_format_percentage_and_currency():
    tu = TemplateUtils(template_dir=str(Path(__file__).parent))
    assert "%" in tu.format_percentage(0.42, precision=1)
    assert tu.format_percentage(50, precision=0).startswith("50")
    cur = tu.format_currency(1999.5, currency="$")
    assert cur.startswith("$")


def test_format_date_iso_and_datetime():
    tu = TemplateUtils(template_dir=str(Path(__file__).parent))
    dt = datetime(2024, 6, 1, 12, 0, tzinfo=timezone.utc)
    assert tu.format_date(dt) == "2024-06-01"
    assert "2024" in tu.format_date("2024-06-01T00:00:00")


def test_format_dataframe_truncates():
    tu = TemplateUtils(template_dir=str(Path(__file__).parent))
    df = pd.DataFrame({"a": range(5), "b": range(5, 10)})
    out = tu.format_dataframe(df, max_rows=3, max_cols=10)
    assert len(out) <= 3


def test_save_template_writes_file(tmp_path):
    d = tmp_path / "tpl2"
    d.mkdir()
    tu = TemplateUtils(template_dir=str(d))
    tu.save_template("saved", "<html>ok</html>")
    assert (d / "saved.html").read_text(encoding="utf-8") == "<html>ok</html>"
    assert tu.get_template("saved") == "<html>ok</html>"


def test_create_table_html_smoke():
    tu = TemplateUtils(template_dir=str(Path(__file__).parent))
    df = pd.DataFrame({"x": [1]})
    html = tu.create_table_html(df, table_id="t1")
    assert "t1" in html and "x" in html
