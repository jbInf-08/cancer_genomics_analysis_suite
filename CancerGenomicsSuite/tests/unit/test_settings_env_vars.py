"""Settings are read from the environment variables they declare.

config/settings.py declares each variable pydantic-v1 style, Field(env="..."),
and the project requires pydantic 2, which has no `env` argument. Pydantic kept
it as schema metadata and warned, and pydantic-settings read the variable named
after the field instead. So none of the declared variables worked. Setting
DATABASE_URL left database.url at its default while an unrelated URL variable
replaced it, and the generic PORT and USERNAME variables became the email
server's port and login.
"""

from __future__ import annotations

import inspect
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]

settings_module = pytest.importorskip("CancerGenomicsSuite.config.settings")

pytestmark = pytest.mark.skipif(
    settings_module.PYDANTIC_VERSION != 2, reason="pydantic 2 behaviour"
)


def _settings_classes():
    base = settings_module.BaseSettings
    return [
        obj
        for _, obj in inspect.getmembers(settings_module, inspect.isclass)
        if issubclass(obj, base) and obj is not base
    ]


def test_documented_variables_are_read(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://db.example/genomics")
    monkeypatch.setenv("MAIL_PORT", "2525")
    monkeypatch.setenv("PORT", "9999")
    assert settings_module.DatabaseSettings().url == "postgresql://db.example/genomics"
    assert settings_module.EmailSettings().port == 2525
    main = settings_module.Settings()
    assert main.port == 9999
    assert main.database.url == "postgresql://db.example/genomics"


@pytest.mark.parametrize("variable", ["URL", "PORT", "USERNAME", "PASSWORD"])
def test_variables_named_after_a_field_do_not_leak_in(monkeypatch, variable):
    for name in ("DATABASE_URL", "MAIL_PORT", "MAIL_USERNAME", "MAIL_PASSWORD"):
        monkeypatch.delenv(name, raising=False)
    defaults = (settings_module.DatabaseSettings(), settings_module.EmailSettings())
    monkeypatch.setenv(variable, "4242")
    after = (settings_module.DatabaseSettings(), settings_module.EmailSettings())
    assert [m.model_dump() for m in after] == [m.model_dump() for m in defaults]


def test_every_declared_variable_is_the_lookup_name():
    """No field may keep `env` as inert metadata; each is its validation alias."""
    leftovers, checked = [], 0
    for cls in _settings_classes():
        for name, field in cls.model_fields.items():
            extra = field.json_schema_extra
            if isinstance(extra, dict) and "env" in extra:
                leftovers.append(f"{cls.__name__}.{name}")
            if field.validation_alias is not None:
                checked += 1
    assert not leftovers, leftovers
    assert checked > 150, f"only {checked} fields have an environment variable"


def test_declarations_raise_no_pydantic_deprecation_warnings():
    """Imported fresh in a subprocess; reloading here would swap the classes
    other tests hold."""
    code = (
        "import warnings, logging\n"
        "logging.disable(logging.CRITICAL)\n"
        "warnings.simplefilter('always')\n"
        "with warnings.catch_warnings(record=True) as caught:\n"
        "    warnings.simplefilter('always')\n"
        "    import CancerGenomicsSuite.config.settings\n"
        "print(sum('extra keyword' in str(w.message) for w in caught))\n"
    )
    proc = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        timeout=300,
        cwd=REPO,
    )
    assert proc.returncode == 0, proc.stderr[-2000:]
    assert proc.stdout.strip().splitlines()[-1] == "0"
