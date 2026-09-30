"""The orchestrator's Kafka notifications must import, serialize, and send.

unified_orchestrator imported StreamEvent and StreamEventType from
kafka_stream_processor and called KafkaStreamProcessor.produce_event -- none of
which had ever been defined. The import failed at module load, so the whole
unified pipeline orchestrator was unimportable.

No Kafka broker is involved: the producer is replaced with a stub that applies
the real producer's value_serializer (json.dumps), which is the step that
would reject a raw datetime or Enum.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime

import pytest

from CancerGenomicsSuite.modules.real_time_processing.kafka_stream_processor import (
    KafkaStreamProcessor,
    StreamEvent,
    StreamEventType,
)


class RecordingProducer:
    """Stands in for KafkaProducer, serializing exactly as it is configured to."""

    def __init__(self):
        self.sent = []

    def send(self, topic, value):
        self.sent.append((topic, json.dumps(value).encode("utf-8")))


def _processor(producer):
    proc = KafkaStreamProcessor.__new__(KafkaStreamProcessor)  # no broker needed
    proc.producer = producer
    return proc


def _event(**overrides):
    fields = dict(
        event_id="e-1",
        event_type=StreamEventType.WORKFLOW_EVENT,
        timestamp=datetime(2026, 9, 30, 12, 0, 0),
        source="test",
        data={"status": "started"},
    )
    fields.update(overrides)
    return StreamEvent(**fields)


def test_orchestrator_module_imports():
    import CancerGenomicsSuite.modules.pipeline_orchestration.unified_orchestrator  # noqa: F401


def test_to_dict_is_json_serializable():
    payload = _event().to_dict()
    decoded = json.loads(json.dumps(payload))
    assert decoded["event_type"] == "workflow_event"
    assert decoded["timestamp"] == "2026-09-30T12:00:00"
    assert decoded["data"] == {"status": "started"}


def test_raw_asdict_would_not_serialize():
    """Pin why to_dict converts: the producer's serializer rejects these types."""
    from dataclasses import asdict

    with pytest.raises(TypeError):
        json.dumps(asdict(_event()))


def test_data_defaults_are_not_shared_between_events():
    a = StreamEvent("a", StreamEventType.WORKFLOW_EVENT, datetime.now(), "s")
    b = StreamEvent("b", StreamEventType.WORKFLOW_EVENT, datetime.now(), "s")
    a.data["x"] = 1
    assert b.data == {}


def test_produce_event_sends_to_the_given_topic():
    producer = RecordingProducer()
    _processor(producer).produce_event("workflow-events", _event())
    assert len(producer.sent) == 1
    topic, raw = producer.sent[0]
    assert topic == "workflow-events"
    assert json.loads(raw)["event_id"] == "e-1"


def test_produce_event_before_initialize_raises():
    with pytest.raises(RuntimeError, match="initialize"):
        _processor(None).produce_event("workflow-events", _event())


def _orchestrator(kafka_processor):
    from CancerGenomicsSuite.modules.pipeline_orchestration import (
        unified_orchestrator as uo,
    )

    orch = uo.UnifiedPipelineOrchestrator.__new__(uo.UnifiedPipelineOrchestrator)
    orch.kafka_processor = kafka_processor
    return uo, orch


def _execution(uo):
    return uo.PipelineExecution(
        execution_id="ex-1",
        pipeline_id="p-1",
        status=next(iter(uo.PipelineStatus)),
        started_at=datetime(2026, 9, 30, 12, 0),
    )


def _workflow(uo):
    stamp = datetime(2026, 9, 30)
    return uo.WorkflowDefinition(
        workflow_id="wf-1",
        name="demo",
        description="",
        version="1",
        author="a",
        created_at=stamp,
        updated_at=stamp,
    )


def test_orchestrator_notifications_are_delivered(caplog):
    """End to end, through the orchestrator's own methods."""
    producer = RecordingProducer()
    uo, orch = _orchestrator(_processor(producer))

    with caplog.at_level(logging.ERROR, logger=uo.__name__):
        orch._send_execution_notification(_execution(uo), "started")
        orch._send_workflow_notification(_workflow(uo), "ex-1", "completed")

    assert [r.getMessage() for r in caplog.records] == []
    assert [t for t, _ in producer.sent] == ["workflow-events", "workflow-events"]
    statuses = [json.loads(raw)["data"]["status"] for _, raw in producer.sent]
    assert statuses == ["started", "completed"]


def test_uninitialized_processor_is_logged_not_raised(caplog):
    """The orchestrator's own try/except must still contain a send failure."""
    uo, orch = _orchestrator(_processor(None))

    with caplog.at_level(logging.ERROR, logger=uo.__name__):
        orch._send_execution_notification(_execution(uo), "started")

    assert any("initialize" in r.getMessage() for r in caplog.records)
