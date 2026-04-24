"""Molecular dynamics workflow wiring."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from CancerGenomicsSuite.modules.pipeline_orchestration.md_workflow import (
    MolecularDynamicsWorkflow,
)
from CancerGenomicsSuite.modules.pipeline_orchestration.workflow_executor import (
    WorkflowExecutor,
)


def test_md_workflow_requires_input():
    md = MolecularDynamicsWorkflow()
    r = md.run({})
    assert r["success"] is False
    assert "Provide one of" in (r.get("error") or "")


@patch(
    "CancerGenomicsSuite.modules.pipeline_orchestration.md_workflow.GROMACSClient"
)
def test_md_workflow_respects_gromacs_unavailable(mock_client_cls, tmp_path):
    client = MagicMock()
    client.is_available.return_value = False
    client.get_version.return_value = "Not available"
    mock_client_cls.return_value = client

    md = MolecularDynamicsWorkflow(work_root=str(tmp_path))
    pdb = tmp_path / "x.pdb"
    pdb.write_text("HEADER    TEST\n", encoding="utf-8")
    r = md.run({"pdb_path": str(pdb)})
    assert r["success"] is False
    assert "PATH" in r.get("error", "") or "not found" in r.get("error", "").lower()


def test_workflow_executor_md_history(tmp_path):
    hist = tmp_path / "hist.jsonl"
    ex = WorkflowExecutor(
        work_dir=str(tmp_path / "wf"),
        history_persist_path=str(hist),
    )
    with patch.object(MolecularDynamicsWorkflow, "run", return_value={"success": True}):
        r = ex.run_molecular_dynamics_workflow({"pdb_id": "1CRN"}, workflow_name="md_unit")
    assert r["success"] is True
    assert any(w.get("name") == "md_unit" for w in ex.workflow_history)
    assert hist.is_file()
    assert "md_unit" in hist.read_text()

    ex2 = WorkflowExecutor(
        work_dir=str(tmp_path / "wf2"),
        history_persist_path=str(hist),
    )
    assert any(w.get("name") == "md_unit" for w in ex2.workflow_history)
