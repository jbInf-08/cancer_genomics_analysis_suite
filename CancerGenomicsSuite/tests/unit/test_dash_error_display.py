"""Smoke tests for Dash error rendering (no full Dash app)."""

from CancerGenomicsSuite.modules.gene_annotation.dash_error_display import (
    structured_error_to_dash,
)


def test_structured_error_to_dash_builds():
    d = structured_error_to_dash(
        {
            "user_message": "Rate limited",
            "error_kind": "http_error",
            "http_status": 429,
            "retry_after_seconds": 30,
            "url": "https://rest.ensembl.org/x",
        }
    )
    assert d is not None
    # Dash html.Div has children
    assert d.children
