"""Liveness L2: a killed worker's unfinished task is reassigned to a healthy worker.

MS2 shipped this oracle as the one intentional expected failure. MS3 leases make it pass, with
the same experiment unchanged; it now also checks how recovery happened and how long it took on
the scheduler's own clock. RecoveryNotObserved is still the only way the oracle reports no recovery.
"""
import json
import time
import traceback
from datetime import datetime, timezone
import pytest
from tests.harness.api import check_history, manifest, request, task, wait_for
from tests.harness.check_evidence import check_directory


WINDOW_NS = 10_000_000_000
LATE_POLL_NS = 8_000_000_000
GATE_TIMEOUT_MS = 120000
# Detection is bounded by the lease; reassignment adds the expiry scan, an idle worker's poll and
# scheduling jitter on a shared test host. The bound is on the scheduler clock, never across processes.
RECOVERY_SLACK_NS = 2_000_000_000


class RecoveryNotObserved(AssertionError):
    """Only the final reassignment oracle may raise this expected-failure type."""


def original_attempt_running(snapshot, identity):
    """Ordinary assertions: a timeout/retry or false success invalidates this experiment."""
    assert snapshot["scheduler_run_id"] == identity["scheduler_run_id"]
    assert snapshot["job_id"] == identity["job_id"]
    x = snapshot["tasks"][identity["task_id"]]
    assert snapshot["state"] == "RUNNING" and x["state"] == "RUNNING"
    assert x["owner"] == identity["worker_session_id"] and x["outputs"] is None
    assert len(x["attempts"]) == 1, "The fault must interrupt the original attempt, before any retry"
    assert x["attempt_no"] == identity["attempt_no"]
    attempt = x["attempts"][0]
    assert attempt["identity"] == identity and attempt["state"] == "RUNNING"
    assert attempt["start_receipt"] is not None
    assert attempt["report_receipt"] is None and attempt["report_ack"] is None
    assert attempt["finished_elapsed_ns"] is None
    assert snapshot["tasks"]["Y"]["state"] == "BLOCKED"
    assert snapshot["tasks"]["Y"]["attempts"] == []


def lease_recovery(events, job, identity):
    """Scheduler-clock decomposition of one recovery: last sign of life -> expiry -> new owner."""
    expired = next(e for e in events if e["event_type"] == "lease_expired" and e.get("job_id") == job
                   and e["task_id"] == identity["task_id"] and e["attempt_no"] == identity["attempt_no"])
    assigned = next(e for e in events if e["event_type"] == "task_assigned" and e.get("job_id") == job
                    and e["task_id"] == identity["task_id"] and e["attempt_no"] == identity["attempt_no"] + 1)
    alive = expired["last_alive_elapsed_ns"]
    return {"clock": "scheduler monotonic elapsed_ns", "last_alive_elapsed_ns": alive,
            "lease_expired_elapsed_ns": expired["elapsed_ns"], "reassigned_elapsed_ns": assigned["assigned_elapsed_ns"],
            "detection_ns": expired["elapsed_ns"] - alive, "requeue_to_assign_ns": assigned["assigned_elapsed_ns"] - expired["elapsed_ns"],
            "recovery_ns": assigned["assigned_elapsed_ns"] - alive, "new_owner": assigned["worker_session_id"],
            "expired_from_state": expired["old_state"]}


def polling_evidence(events, session, run_id, after_seq):
    """Pair scheduler claim/empty receipts by request ID, not cross-process clocks."""
    claims = {e["request_id"]: e for e in events if e["event_type"] == "work_claim"
              and e.get("worker_session_id") == session and e["scheduler_run_id"] == run_id
              and e["scheduler_event_seq"] > after_seq}
    pairs = []
    for e in events:
        if (e["event_type"] == "work_empty" and e.get("worker_session_id") == session
                and e["scheduler_run_id"] == run_id and e["request_id"] in claims):
            claim = claims[e["request_id"]]
            assert claim["scheduler_event_seq"] < e["scheduler_event_seq"]
            pairs.append({"claim": claim, "empty": e})
    return pairs


def require_window_polling(events, session, run_id, start_seq, late_seq):
    assert late_seq is not None, "Observation never reached the late polling boundary"
    pairs = polling_evidence(events, session, run_id, start_seq)
    assert len(pairs) >= 2, "Missing healthy-worker polling during observation"
    assert any(p["claim"]["scheduler_event_seq"] > late_seq for p in pairs), "No fresh B claim after the late boundary"
    return pairs


@pytest.mark.faults
def test_worker_crash_reassignment(system):
    origin = time.monotonic_ns()
    def save(name, value):
        (system.evidence / name).write_text(json.dumps(value, indent=2))

    a = system.start_worker({"ENABLE_TEST_HOOKS": "true", "TEST_GATE_TASK": "X",
                             "TEST_FAIL_FIRST_TASK": "", "OPERATION_TIMEOUT_MS": str(GATE_TIMEOUT_MS)})
    m = manifest([task("X"), task("Y", parents=["X"])])
    job = system.api.submit(m)
    gate = wait_for(lambda: next((e for e in system.worker_events(a) if e["event_type"] == "worker_test_gate_entered" and e.get("job_id") == job), None),
                    description="A's in-operation gate")
    before = system.api.status(job)
    x = before["tasks"]["X"]
    identity = x["attempts"][0]["identity"]
    assert all(gate[key] == value for key, value in identity.items())
    original_attempt_running(before, identity)
    check_history(m, before, system.api.events(), system.worker_events(a))
    correlated = next(e for e in system.api.events() if e["scheduler_event_seq"] == gate["ack_scheduler_event_seq"])
    assert correlated["event_type"] == "task_started" and correlated["task_id"] == "X"
    operation = next(e for e in system.worker_events(a) if e["event_type"] == "worker_operation_started" and e.get("task_id") == "X")
    assert operation["ack_scheduler_event_seq"] == gate["ack_scheduler_event_seq"]
    assert operation["producer_seq"] < gate["producer_seq"]
    output_key = (f"runs/{identity['scheduler_run_id']}/jobs/{job}/tasks/X/"
                  f"attempts/{identity['attempt_no']}/value")
    assert request(system.artifacts, "/v1/objects/" + output_key, method="HEAD")[0] == 404
    save("gate.json", gate)
    save("before-kill.json", before)
    fault_time = datetime.now(timezone.utc).isoformat()
    kill_started_ns = time.monotonic_ns() - origin
    fault = system.kill_worker(a)
    assert not system.worker_running(a)
    fault.update({"schema_version": 1, "event_type": "fault_injected", "producer": "harness", "producer_seq": 1,
                  "utc_timestamp": fault_time, "elapsed_ns": kill_started_ns, "request_id": "kill-worker-A",
                  **identity, "kill_confirmed_elapsed_ns": time.monotonic_ns() - origin,
                  "gate_operation_timeout_ms": GATE_TIMEOUT_MS})
    save("fault.json", fault)
    killed = system.api.status(job)
    save("after-kill.json", killed)
    original_attempt_running(killed, identity)
    assert request(system.artifacts, "/v1/objects/" + output_key, method="HEAD")[0] == 404
    check_history(m, killed, system.api.events(), system.worker_events(a))

    b = system.start_worker({"ENABLE_TEST_HOOKS": "false"})
    b_session = next(e["worker_session_id"] for e in system.worker_events(b) if e["event_type"] == "worker_session_started")
    assert b_session != identity["worker_session_id"], "B must have a fresh session"
    probe = manifest([task("probe")])
    probe_result = system.api.complete(system.api.submit(probe))
    assert probe_result["tasks"]["probe"]["attempts"][0]["identity"]["worker_session_id"] == b_session
    assert system.api.get(probe_result["outputs"]["result"]) == b"3"
    check_history(probe, probe_result, system.api.events(), system.worker_events(b))
    probe_done = max(e["scheduler_event_seq"] for e in system.api.events() if e["event_type"] == "job_completed" and e.get("job_id") == probe["job_id"])
    wait_for(lambda: any(e["event_type"] == "work_empty" and e.get("worker_session_id") == b_session and e["scheduler_event_seq"] > probe_done for e in system.api.events()),
             description="B polling after successful probe")
    start_seq = system.api.events()[-1]["scheduler_event_seq"]
    started_ns = time.monotonic_ns()
    deadline = started_ns + WINDOW_NS
    late_seq = None
    window = {"clock": "harness time.monotonic_ns relative to test origin; no cross-process subtraction",
              "budget_ns": WINDOW_NS, "start_elapsed_ns": started_ns - origin,
              "start_scheduler_event_seq": start_seq, "late_threshold_ns": LATE_POLL_NS,
              "worker_a_identity": identity, "worker_b_session_id": b_session, "samples": []}
    recovered = False
    while time.monotonic_ns() < deadline:
        sample_started = time.monotonic_ns()
        if late_seq is None and sample_started - started_ns >= LATE_POLL_NS:
            # Events already present here cannot count as late polling. A later claim must
            # have a greater scheduler sequence, observed causally after this harness boundary.
            late_seq = system.api.events()[-1]["scheduler_event_seq"]
            window.update({"late_scheduler_event_seq": late_seq,
                           "late_boundary_elapsed_ns": time.monotonic_ns() - origin})
        after = system.api.status(job)
        observed_ns = time.monotonic_ns()
        events = system.api.events()
        alive = system.worker_running(b)
        window["samples"].append({"started_elapsed_ns": sample_started - origin,
                                  "snapshot_observed_elapsed_ns": observed_ns - origin,
                                  "finished_elapsed_ns": time.monotonic_ns() - origin,
                                  "snapshot_event_seq": after["snapshot_event_seq"],
                                  "last_scheduler_event_seq": events[-1]["scheduler_event_seq"],
                                  "b_alive": alive, "x_state": after["tasks"]["X"]["state"],
                                  "x_attempt_no": after["tasks"]["X"]["attempt_no"]})
        assert alive, "Surviving worker died during observation"
        recovered = observed_ns <= deadline and any(
            attempt["identity"]["worker_session_id"] == b_session
            and attempt["identity"]["attempt_no"] > identity["attempt_no"]
            for attempt in after["tasks"]["X"]["attempts"])
        if recovered:
            break
        remaining = (deadline - time.monotonic_ns()) / 1e9
        if remaining > 0:
            time.sleep(min(0.25, remaining))
    ended_ns = time.monotonic_ns()
    window.update({"end_elapsed_ns": ended_ns - origin, "actual_duration_ns": ended_ns - started_ns,
                   "deadline_overrun_ns": max(0, ended_ns - deadline), "recovered_within_window": recovered})
    save("observation-window.json", window)
    assert system.worker_running(b), "Surviving worker died"
    if recovered:
        after = system.api.complete(job)
    after = system.api.status(job)
    events = system.api.events()
    workers = system.worker_events(a) + system.worker_events(b)
    check_history(m, after, events, workers)
    check_history(probe, system.api.status(probe["job_id"]), system.api.events(), workers)
    assert sum(e["event_type"] == "task_succeeded" and e.get("job_id") == job and e.get("task_id") == "X" for e in events) <= 1
    if recovered:
        status, metrics = request(system.scheduler, "/v1/metrics")
        assert status == 200
        recovery = {**lease_recovery(events, job, identity), "lease_ns": metrics["lease_ns"]}
        save("recovery.json", recovery)
        assert after["state"] == "SUCCEEDED" and after["tasks"]["Y"]["state"] == "SUCCEEDED"
        x = after["tasks"]["X"]
        assert [attempt["state"] for attempt in x["attempts"]] == ["EXPIRED", "SUCCEEDED"]
        assert x["attempts"][1]["identity"]["worker_session_id"] == b_session == recovery["new_owner"]
        assert x["outputs"]["value"]["key"].startswith(f"runs/{identity['scheduler_run_id']}/jobs/{job}/tasks/X/attempts/2/")
        assert recovery["expired_from_state"] == "RUNNING"
        assert recovery["detection_ns"] >= metrics["lease_ns"], "never expire a lease early"
        assert recovery["recovery_ns"] <= metrics["lease_ns"] + RECOVERY_SLACK_NS, recovery
        assert sum(e["event_type"] == "task_succeeded" and e.get("job_id") == job and e.get("task_id") == "X" for e in events) == 1
    if not recovered:
        original_attempt_running(after, identity)
        assert request(system.artifacts, "/v1/objects/" + output_key, method="HEAD")[0] == 404
        assert not any(e.get("job_id") == job and e.get("task_id") == "X"
                       and e["scheduler_event_seq"] > gate["ack_scheduler_event_seq"]
                       and e["event_type"] in {"task_failed", "task_ready", "task_retried", "task_assigned", "task_succeeded"}
                       for e in events), "X changed after the acknowledged original start"
        # Bound polling evidence to events observed in-window, not later teardown activity.
        end_seq = window["samples"][-1]["last_scheduler_event_seq"]
        polls = require_window_polling([e for e in events if e["scheduler_event_seq"] <= end_seq],
                                       b_session, system.api.run_id, start_seq, late_seq)
    else:
        polls = polling_evidence(events, b_session, system.api.run_id, start_seq)
    health = {}
    for name, base in [("scheduler", system.scheduler), ("artifact-store", system.artifacts)]:
        status, body = request(base, "/v1/health")
        assert status == 200 and body["ready"] is True, (name, status, body)
        health[name] = body
    assert health["scheduler"]["scheduler_run_id"] == identity["scheduler_run_id"]
    assert system.api.get(probe_result["outputs"]["result"]) == b"3"
    assert not system.worker_running(a) and system.worker_running(b)
    save("services-after-window.json", health)
    save("surviving-worker-claims.json", polls)
    save("probe.json", probe_result)
    save("after-window.json", after)
    system.api.export(system.evidence)
    checked = check_directory(system.evidence)
    assert set(checked) == {job, probe["job_id"]}, "Both exported histories must pass"
    save("safety-checks.json", {"checked_jobs": checked, "history_check": "PASS",
                               "probe_bytes": "3", "b_session_distinct": True,
                               "a_dead": True, "b_alive": True, "services_healthy": True,
                               "faulted_attempt_unchanged": not recovered, "recovered": recovered})
    try:
        if not recovered:
            raise RecoveryNotObserved("Expected X to be reassigned to healthy worker B with attempt_no > 1 within the controlled 10 s window; X remains RUNNING under killed worker A, Y BLOCKED, job RUNNING.")
    except RecoveryNotObserved:
        (system.evidence / "oracle-traceback.txt").write_text(traceback.format_exc())
        raise
