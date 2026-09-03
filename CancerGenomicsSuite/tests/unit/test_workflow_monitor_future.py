"""A monitoring thread that dies must say so.

``_start_workflow`` submits ``_monitor_workflow`` to a ThreadPoolExecutor and
used to drop the returned future. An executor stores an escaped exception *on
the future* rather than raising it, so with no reference kept, nothing ever
observed it: the thread died silently and the workflow sat in
``active_workflows`` looking like it was still running.

``_report_monitor_exit`` is the done-callback that now reads the future. These
tests exercise it directly against real futures -- no workflow managers, no
orchestration systems, no threads left running.
"""

from __future__ import annotations

import concurrent.futures
import logging

from CancerGenomicsSuite.modules.pipeline_orchestration.workflow_executor import (
    WorkflowExecutor,
)

report = WorkflowExecutor._report_monitor_exit


def completed_future(fn):
    """Run fn in a real executor and hand back the settled future."""
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(fn)
        concurrent.futures.wait([future])
    return future


def test_escaped_exception_is_logged_with_the_workflow_name(caplog):
    def boom():
        # The shape that actually escapes _monitor_workflow: a dict lookup
        # made before its try block.
        raise KeyError("variant_calling")

    future = completed_future(boom)

    with caplog.at_level(logging.ERROR):
        report("variant_calling", future)

    assert len(caplog.records) == 1
    record = caplog.records[0]
    assert "variant_calling" in record.getMessage()
    assert record.levelno == logging.ERROR
    # The traceback has to survive, or the log says a thread died without
    # saying where.
    assert record.exc_info is not None
    assert isinstance(record.exc_info[1], KeyError)


def test_normal_completion_logs_nothing(caplog):
    future = completed_future(lambda: "finished")

    with caplog.at_level(logging.ERROR):
        report("expression_analysis", future)

    assert caplog.records == []


def test_returning_none_is_not_treated_as_failure(caplog):
    """_monitor_workflow returns None on its ordinary paths."""
    future = completed_future(lambda: None)

    with caplog.at_level(logging.ERROR):
        report("multi_omics", future)

    assert caplog.records == []


def test_cancelled_future_logs_nothing(caplog):
    """A cancelled monitor is a shutdown, not a crash.

    future.exception() raises CancelledError on a cancelled future, so the
    callback has to check before asking -- otherwise the callback itself blows
    up during executor shutdown.
    """
    pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    blocker = pool.submit(lambda: __import__("time").sleep(0.3))
    victim = pool.submit(lambda: "never runs")
    cancelled = victim.cancel()

    with caplog.at_level(logging.ERROR):
        report("cancelled_workflow", victim)

    concurrent.futures.wait([blocker])
    pool.shutdown(wait=True)

    assert cancelled, "victim should have been cancellable while pool was busy"
    assert caplog.records == []


def test_callback_attaches_to_a_real_future_and_fires(caplog):
    """End to end: add_done_callback, as _start_workflow wires it up."""
    import functools

    with caplog.at_level(logging.ERROR):
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(lambda: 1 / 0)
            future.add_done_callback(functools.partial(report, "divide_by_zero"))
            concurrent.futures.wait([future])

    assert len(caplog.records) == 1
    assert "divide_by_zero" in caplog.records[0].getMessage()
    assert isinstance(caplog.records[0].exc_info[1], ZeroDivisionError)
