"""get_queue_lengths must count the backlog, not just what is already running.

The function asked workers for active, scheduled and reserved tasks, then
counted only the active ones -- the other two were fetched and dropped. Active
means "executing right now", so a queue with a thousand tasks waiting and one
running reported 1. The backlog is exactly the part that is not yet running.

There is a second trap in counting the other two. ``active()`` and
``reserved()`` return the task dict itself, but ``scheduled()`` wraps it as
``{"eta": ..., "request": {...}}``. Reading ``delivery_info`` at the top level
of a scheduled entry finds nothing, so every scheduled task lands under
"default" -- the metric looks fixed while quietly misattributing the counts.

These use canned inspect payloads, so no broker and no workers are involved.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from CancerGenomicsSuite.app.celery_config import get_queue_lengths

EMPTY = {"active": 0, "reserved": 0, "scheduled": 0, "total": 0}


def running(queue):
    """An active/reserved entry, as a worker reports it."""
    return {"id": "t1", "name": "task", "delivery_info": {"routing_key": queue}}


def waiting(queue):
    """A scheduled entry -- note the task is nested under "request"."""
    return {
        "eta": "2026-01-01T00:00:00+00:00",
        "priority": 6,
        "request": {
            "id": "t2",
            "name": "task",
            "delivery_info": {"routing_key": queue},
        },
    }


def inspecting(active=None, reserved=None, scheduled=None):
    """Patch celery_app.control.inspect() to return canned payloads."""
    probe = MagicMock()
    probe.active.return_value = active
    probe.reserved.return_value = reserved
    probe.scheduled.return_value = scheduled
    app = MagicMock()
    app.control.inspect.return_value = probe
    return patch("CancerGenomicsSuite.app.celery_config.celery_app", app)


def test_all_three_states_are_counted():
    with inspecting(
        active={"w1": [running("ml")]},
        reserved={"w1": [running("ml"), running("ml")]},
        scheduled={"w1": [waiting("ml")]},
    ):
        assert get_queue_lengths() == {
            "ml": {"active": 1, "reserved": 2, "scheduled": 1, "total": 4}
        }


def test_reserved_backlog_is_visible():
    """The case the old behaviour got worst: one running, many queued."""
    with inspecting(
        active={"w1": [running("high_priority")]},
        reserved={"w1": [running("high_priority") for _ in range(50)]},
    ):
        counts = get_queue_lengths()["high_priority"]

    assert counts["active"] == 1
    assert counts["reserved"] == 50
    assert counts["total"] == 51, "counting active only would report 1"


def test_scheduled_tasks_are_attributed_to_their_own_queue():
    """Guards the nested-"request" trap: this must not land under "default"."""
    with inspecting(scheduled={"w1": [waiting("reporting")]}):
        result = get_queue_lengths()

    assert "default" not in result
    assert result == {"reporting": {**EMPTY, "scheduled": 1, "total": 1}}


def test_counts_are_split_across_queues_and_workers():
    with inspecting(
        active={"w1": [running("ml")], "w2": [running("reporting")]},
        reserved={"w2": [running("ml")]},
    ):
        assert get_queue_lengths() == {
            "ml": {**EMPTY, "active": 1, "reserved": 1, "total": 2},
            "reporting": {**EMPTY, "active": 1, "total": 1},
        }


def test_no_workers_responding_is_empty_not_an_error():
    """Celery returns None, not {}, when no worker answers the broadcast.

    The old code called .items() on that and raised, so a cluster with zero
    workers reported a broker error instead of an empty queue set.
    """
    with inspecting(active=None, reserved=None, scheduled=None):
        assert get_queue_lengths() == {}


def test_worker_reporting_no_tasks_is_handled():
    with inspecting(active={"w1": []}, reserved={"w1": None}):
        assert get_queue_lengths() == {}


def test_task_without_delivery_info_falls_back_to_default():
    with inspecting(active={"w1": [{"id": "t", "name": "task"}]}):
        assert get_queue_lengths() == {"default": {**EMPTY, "active": 1, "total": 1}}


def test_empty_delivery_info_falls_back_to_default():
    with inspecting(active={"w1": [{"delivery_info": {}}]}):
        assert get_queue_lengths() == {"default": {**EMPTY, "active": 1, "total": 1}}


def test_total_always_equals_the_sum_of_the_states():
    with inspecting(
        active={"w1": [running("a"), running("b")]},
        reserved={"w1": [running("a")]},
        scheduled={"w1": [waiting("b"), waiting("b")]},
    ):
        for counts in get_queue_lengths().values():
            assert counts["total"] == (
                counts["active"] + counts["reserved"] + counts["scheduled"]
            )


def test_broker_failure_still_returns_the_error_shape():
    """Callers branch on the "error" key, and the text must stay generic --
    this value is served by an unauthenticated status route."""
    app = MagicMock()
    app.control.inspect.side_effect = OSError("redis://:hunter2@broker refused")

    with patch("CancerGenomicsSuite.app.celery_config.celery_app", app):
        result = get_queue_lengths()

    assert result == {"error": "queue lengths unavailable"}
    assert "hunter2" not in str(result)
