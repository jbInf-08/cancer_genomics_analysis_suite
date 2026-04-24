"""Tests for optional Celery MD result polling."""

from unittest.mock import MagicMock, patch

import time

from CancerGenomicsSuite.modules.pipeline_orchestration.celery_md_poll import (
    poll_md_async_result,
)


def _err_dash(d):
    return str(d)


def test_poll_md_async_result_no_app():
    with patch(
        "CancerGenomicsSuite.modules.pipeline_orchestration.celery_md_poll.get_celery_app",
        return_value=None,
    ):
        div, stop = poll_md_async_result(
            "task-1",
            "wf",
            structured_error_to_dash=_err_dash,
        )
    assert stop is True
    assert "Cannot import Celery app" in str(div)


def test_poll_md_async_result_time_limit():
    app = MagicMock()
    with patch(
        "CancerGenomicsSuite.modules.pipeline_orchestration.celery_md_poll.get_celery_app",
        return_value=app,
    ):
        div, stop = poll_md_async_result(
            "task-1",
            "wf",
            structured_error_to_dash=_err_dash,
            started_monotonic=time.monotonic() - 99999,
            max_poll_seconds=60,
        )
    assert stop is True
    assert "Stopped polling" in str(div)


def test_poll_md_async_result_success():
    app = MagicMock()
    with patch(
        "CancerGenomicsSuite.modules.pipeline_orchestration.celery_md_poll.get_celery_app",
        return_value=app,
    ):
        with patch("celery.result.AsyncResult") as AR:
            ar_inst = MagicMock()
            ar_inst.state = "SUCCESS"
            ar_inst.successful.return_value = True
            ar_inst.result = {
                "success": True,
                "work_dir": "/tmp/md",
                "force_field": "amber99sb-ildn",
            }
            AR.return_value = ar_inst
            div, stop = poll_md_async_result(
                "task-1",
                "wf_x",
                structured_error_to_dash=_err_dash,
                started_monotonic=time.monotonic(),
            )
    assert stop is True
    assert "completed" in str(div)
    assert "wf_x" in str(div)
