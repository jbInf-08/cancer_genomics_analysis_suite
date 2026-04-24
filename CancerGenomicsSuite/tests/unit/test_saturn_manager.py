"""Unit tests for SATurn CLI orchestration (subprocess mocked)."""

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from CancerGenomicsSuite.modules.pipeline_orchestration.saturn_manager import SATurnManager


def test_execute_job_completed(tmp_path):
    fake = MagicMock()
    fake.communicate.return_value = ("done", "")
    fake.returncode = 0
    mgr = SATurnManager(work_dir=str(tmp_path / "saturn_root"))
    with patch("subprocess.Popen", return_value=fake) as popen:
        info = mgr.execute_job("workflow.yaml", saturn_args=["--threads", "2"], job_name="job_a")
    assert info["status"] == "completed"
    assert info["return_code"] == 0
    cmd = popen.call_args[0][0]
    assert cmd[:3] == ["saturn", "run", "workflow.yaml"]
    assert "--threads" in cmd and "2" in cmd


def test_get_job_status_from_history(tmp_path):
    fake = MagicMock()
    fake.communicate.return_value = ("", "err")
    fake.returncode = 1
    mgr = SATurnManager(work_dir=str(tmp_path / "saturn_root"))
    with patch("subprocess.Popen", return_value=fake):
        info = mgr.execute_job("wf.json", job_name="job_b")
    assert info["status"] == "failed"
    loaded = mgr.get_job_status("job_b")
    assert loaded is not None
    assert loaded["name"] == "job_b"


def test_stop_job_unknown_returns_false(tmp_path):
    mgr = SATurnManager(work_dir=str(tmp_path / "saturn_root"))
    assert mgr.stop_job("nonexistent") is False


def test_stop_job_terminates_when_running(tmp_path):
    mgr = SATurnManager(work_dir=str(tmp_path / "saturn_root"))
    proc = MagicMock()
    proc.poll.return_value = None
    mgr.active_jobs["run1"] = {
        "name": "run1",
        "process": proc,
        "start_time": datetime.now(),
    }
    assert mgr.stop_job("run1") is True
    proc.terminate.assert_called_once()


def test_stop_job_returns_false_when_process_already_done(tmp_path):
    mgr = SATurnManager(work_dir=str(tmp_path / "saturn_root"))
    proc = MagicMock()
    proc.poll.return_value = 0
    mgr.active_jobs["run2"] = {
        "name": "run2",
        "process": proc,
        "start_time": datetime.now(),
    }
    assert mgr.stop_job("run2") is False


def test_get_outputs_empty_for_unknown_job(tmp_path):
    mgr = SATurnManager(work_dir=str(tmp_path / "saturn_root"))
    assert mgr.get_outputs("missing") == {}


def test_get_outputs_lists_files_after_completed_job(tmp_path):
    mgr = SATurnManager(work_dir=str(tmp_path / "saturn_root"))
    fake = MagicMock()
    fake.communicate.return_value = ("ok", "")
    fake.returncode = 0
    with patch("subprocess.Popen", return_value=fake):
        info = mgr.execute_job("wf.yaml", job_name="job_files")
    exec_dir = Path(info["exec_dir"])
    (exec_dir / "result.txt").write_text("hello", encoding="utf-8")
    out = mgr.get_outputs("job_files")
    assert out.get("execution_directory") == str(exec_dir)
    assert any(f["path"] == "result.txt" for f in out.get("files", []))


def test_execute_job_raises_on_popen_error(tmp_path):
    mgr = SATurnManager(work_dir=str(tmp_path / "saturn_root"))
    with patch("subprocess.Popen", side_effect=OSError("cannot start")):
        with pytest.raises(OSError):
            mgr.execute_job("wf.yaml", job_name="boom")
