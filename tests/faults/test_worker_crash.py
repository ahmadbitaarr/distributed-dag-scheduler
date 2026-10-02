"""The oracle asks for recovery. It never asserts that remaining stuck is correct."""
import json
import time
import traceback
from datetime import datetime, timezone
import pytest
from tests.harness.api import check_history, manifest, task, wait_for


class RecoveryNotObserved(AssertionError):
    """Only the final reassignment oracle may raise this expected-failure type."""


@pytest.mark.intentional_ms2
@pytest.mark.xfail(strict=True, raises=RecoveryNotObserved, reason="MS2 deliberately omits silent-worker ownership reclamation")
def test_worker_crash_reassignment(system):
    a = system.start_worker({"ENABLE_TEST_HOOKS": "true", "TEST_GATE_TASK": "X"})
    m = manifest([task("X"), task("Y", parents=["X"])])
    job = system.api.submit(m)
    gate = wait_for(lambda: next((e for e in system.worker_events(a) if e["event_type"] == "worker_test_gate_entered" and e.get("job_id") == job), None),
                    description="A's in-operation gate")
    before = system.api.status(job)
    x = before["tasks"]["X"]
    assert x["state"] == "RUNNING" and x["owner"] == gate["worker_session_id"]
    assert x["outputs"] is None
    check_history(m, before, system.api.events(), system.worker_events(a))
    correlated = next(e for e in system.api.events() if e["scheduler_event_seq"] == gate["ack_scheduler_event_seq"])
    assert correlated["event_type"] == "task_started" and correlated["task_id"] == "X"
    operation = next(e for e in system.worker_events(a) if e["event_type"] == "worker_operation_started" and e.get("task_id") == "X")
    assert operation["ack_scheduler_event_seq"] == gate["ack_scheduler_event_seq"]
    assert operation["producer_seq"] < gate["producer_seq"]
    fault_time = datetime.now(timezone.utc).isoformat()
    fault = system.kill_worker(a)
    assert not system.worker_running(a)
    fault.update({"schema_version": 1, "event_type": "fault_injected", "producer": "harness", "producer_seq": 1,
                  "utc_timestamp": fault_time, "elapsed_ns": time.monotonic_ns(), "request_id": "kill-worker-A",
                  "scheduler_run_id": system.api.run_id, "job_id": job, "task_id": "X", "attempt_no": 1,
                  "worker_session_id": gate["worker_session_id"]})
    (system.evidence / "fault.json").write_text(json.dumps(fault, indent=2))
    (system.evidence / "gate.json").write_text(json.dumps(gate, indent=2))
    (system.evidence / "before-kill.json").write_text(json.dumps(before, indent=2))

    b = system.start_worker()
    b_session = next(e["worker_session_id"] for e in system.worker_events(b) if e["event_type"] == "worker_session_started")
    probe = manifest([task("probe")])
    probe_result = system.api.complete(system.api.submit(probe))
    assert probe_result["tasks"]["probe"]["attempts"][0]["identity"]["worker_session_id"] == b_session
    assert system.api.get(probe_result["outputs"]["result"]) == b"3"
    probe_done = max(e["scheduler_event_seq"] for e in system.api.events() if e["event_type"] == "job_completed" and e.get("job_id") == probe["job_id"])
    wait_for(lambda: any(e["event_type"] == "work_empty" and e.get("worker_session_id") == b_session and e["scheduler_event_seq"] > probe_done for e in system.api.events()),
             description="B polling after successful probe")
    deadline = time.monotonic() + 10.0
    recovered = False
    while time.monotonic() < deadline:
        after = system.api.status(job)
        recovered = any(attempt["identity"]["worker_session_id"] == b_session and attempt["identity"]["attempt_no"] > 1 for attempt in after["tasks"]["X"]["attempts"])
        if recovered:
            break
        time.sleep(0.05)
    assert system.worker_running(b), "Surviving worker died"
    if recovered:
        after = system.api.complete(job)
    after = system.api.status(job)
    events = system.api.events()
    check_history(m, after, events, system.worker_events(a) + system.worker_events(b))
    assert sum(e["event_type"] == "task_succeeded" and e.get("job_id") == job and e.get("task_id") == "X" for e in events) <= 1
    if not recovered:
        assert after["state"] == "RUNNING" and after["tasks"]["X"]["state"] == "RUNNING"
        assert after["tasks"]["X"]["owner"] == gate["worker_session_id"]
        assert after["tasks"]["X"]["outputs"] is None and after["tasks"]["Y"]["state"] == "BLOCKED"
    polls = [e for e in events if e["event_type"] == "work_empty" and e.get("worker_session_id") == b_session and e["scheduler_event_seq"] > probe_done]
    assert len(polls) >= 2, "Missing sustained healthy-worker evidence"
    (system.evidence / "surviving-worker-claims.json").write_text(json.dumps(polls, indent=2))
    (system.evidence / "probe.json").write_text(json.dumps(probe_result, indent=2))
    (system.evidence / "after-window.json").write_text(json.dumps(after, indent=2))
    system.api.export(system.evidence)
    try:
        if not recovered:
            raise RecoveryNotObserved("Expected X to be reassigned to healthy worker B with attempt_no > 1 within the controlled 10 s window; X remains RUNNING under killed worker A, Y BLOCKED, job RUNNING.")
    except RecoveryNotObserved:
        (system.evidence / "oracle-traceback.txt").write_text(traceback.format_exc())
        raise
