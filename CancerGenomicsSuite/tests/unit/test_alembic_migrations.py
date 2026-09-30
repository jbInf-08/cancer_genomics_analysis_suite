"""`alembic upgrade head` must actually run, and must record the revision.

INTEGRATION_UPDATES.md documents `alembic upgrade head` as the migration step.
Until this was fixed it could not have worked, for four independent reasons:

* there was no alembic.ini, so Alembic stopped before loading anything;
* env.py imported DATABASE_URL from config.settings, which never defined it;
* env.py used a relative import, which cannot work in a file Alembic executes
  as a script rather than as part of a package;
* it imported a declarative `Base`, but the models are Flask-SQLAlchemy models
  and there is no Base.

Past those, V1 added its CHECK constraints with op.create_check_constraint,
which SQLite cannot do. SQLite is the application's default database, so the
migration created all 26 tables and then failed before writing the revision --
leaving a database that looks migrated and is not. These tests check the stamp
and the constraints, not just that tables exist, for that reason.

Everything runs against a throwaway SQLite file.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

alembic_config = pytest.importorskip("alembic.config")
alembic_command = pytest.importorskip("alembic.command")

SUITE = Path(__file__).resolve().parents[2]
INI = SUITE / "alembic.ini"

CHECK_CONSTRAINTS = [
    "check_positive_expression",
    "check_allele_frequency",
    "check_positive_read_depth",
    "check_progress_range",
    "check_priority_range",
    "check_positive_file_size",
    "check_quality_score_range",
    "check_ngs_priority_range",
    "check_queue_priority_range",
    "check_positive_metric_value",
    "check_positive_response_time",
]


@pytest.fixture
def migrated(tmp_path, monkeypatch):
    """Run upgrade head against a fresh SQLite database and hand back its path."""
    db = tmp_path / "migrations.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db.as_posix()}")
    cfg = alembic_config.Config(str(INI))
    alembic_command.upgrade(cfg, "head")
    return db, cfg


def _schema(db: Path):
    con = sqlite3.connect(db)
    try:

        def names(kind):
            return {
                r[0]
                for r in con.execute(
                    "select name from sqlite_master where type=? "
                    "and name not like 'sqlite_%'",
                    (kind,),
                )
            }

        tables = names("table")
        stamp = (
            [r[0] for r in con.execute("select version_num from alembic_version")]
            if "alembic_version" in tables
            else None
        )
        ddl = " ".join(
            r[0] or ""
            for r in con.execute("select sql from sqlite_master where type='table'")
        )
        return tables - {"alembic_version"}, names("index"), stamp, ddl
    finally:
        con.close()


def test_alembic_ini_exists_where_the_docs_say_to_run_from():
    assert INI.is_file(), "alembic.ini missing -- `alembic upgrade head` cannot start"


def test_upgrade_head_records_the_revision(migrated):
    """The stamp is the proof of completion; tables alone were not."""
    db, _ = migrated
    _, _, stamp, _ = _schema(db)
    assert stamp == ["V1_initial_schema"]


def test_upgrade_head_creates_the_full_schema(migrated):
    db, _ = migrated
    tables, indexes, _, _ = _schema(db)
    assert len(tables) == 26
    # batch mode rebuilds tables on SQLite; the indexes must survive that
    assert len(indexes) == 115


def test_every_check_constraint_is_present(migrated):
    db, _ = migrated
    *_, ddl = _schema(db)
    missing = [c for c in CHECK_CONSTRAINTS if c not in ddl]
    assert not missing, f"CHECK constraints not created: {missing}"


def test_a_check_constraint_is_enforced(migrated):
    """Present in the DDL is not the same as enforced; exercise one."""
    db, _ = migrated
    con = sqlite3.connect(db)
    try:
        info = list(con.execute("pragma table_info(gene_expression)"))
        required = {row[1] for row in info if row[3] and row[1] != "id"}
        values = {col: "x" for col in required}
        values["expression_value"] = -1
        with pytest.raises(sqlite3.IntegrityError, match="check_positive_expression"):
            con.execute(
                f"insert into gene_expression ({','.join(values)}) "
                f"values ({','.join('?' * len(values))})",
                list(values.values()),
            )
    finally:
        con.close()


def test_downgrade_base_removes_everything(migrated):
    db, cfg = migrated
    alembic_command.downgrade(cfg, "base")
    tables, indexes, stamp, _ = _schema(db)
    assert tables == set()
    assert indexes == set()
    assert stamp == []


def test_running_migrations_leaves_application_loggers_enabled(tmp_path, monkeypatch):
    """env.py must not silence the application's loggers.

    logging.config.fileConfig disables every existing logger not named in the
    ini unless told otherwise, and env.py imports the application first -- so
    with the default, running a migration switched off the app's logging for
    the rest of the process. That surfaced as unrelated test failures: tests
    that assert on a logged error ran after this module and saw nothing.
    """
    import logging

    from CancerGenomicsSuite.modules.pipeline_orchestration import workflow_executor

    app_logger = logging.getLogger(workflow_executor.__name__)
    assert not app_logger.disabled

    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{(tmp_path / 'l.db').as_posix()}")
    alembic_command.upgrade(alembic_config.Config(str(INI)), "head")

    assert not app_logger.disabled, "running migrations disabled an app logger"


def test_round_trip_reproduces_the_schema(migrated):
    db, cfg = migrated
    first = _schema(db)
    alembic_command.downgrade(cfg, "base")
    alembic_command.upgrade(cfg, "head")
    second = _schema(db)
    assert first[:3] == second[:3]
