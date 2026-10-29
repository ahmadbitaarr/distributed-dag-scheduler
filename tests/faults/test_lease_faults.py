"""MS3 process faults: crashes at every attempt stage, restarts, pauses, and slow-but-alive workers.

Each test checks the same three things: the job finishes (liveness), the recorded history passes
every safety invariant (check_history), and only one attempt of each task is ever accepted.
Timing assertions use the scheduler's monotonic clock only.
"""
import time
import pytest
from tests.harness.api import binding, check_history, manifest, request, task, wait_for

SLACK_NS = 2_000_000_000          # expiry scan + idle poll + scheduling jitter on a shared host


def chain():
    """X writes 3; Y adds 4 to X's accepted output. Y's input proves which X attempt was accepted."""
    return manifest([task("X"), task("Y", "fixture_add", ["X"], {"value": binding("X")}, amount=4)])


def prefix(identity):
    return (f"runs/{identity['scheduler_run_id']}/jobs/{identity['job_id']}/tasks/{identity['task_id']}"
            f"/attempts/{identity['attempt_no']}/")


def one(events, kind, job, name, attempt=None):
    found = [e for e in events if e["event_type"] == kind and e.get("job_id") == job and e.get("task_id") == name
             and (attempt is None or e.get("attempt_no") == attempt)]
    assert len(found) == 1, (kind, name, attempt, len(found))
    return found[0]


def lease_ns(system):
    status, metrics = request(system.scheduler, "/v1/metrics")
    assert status == 200
    return metrics["lease_ns"]


def gate_event(system, worker, job, stage):
    return wait_for(lambda: next((e for e in system.worker_events(worker) if e["event_type"] == "worker_test_gate_entered"
                                  and e.get("job_id") == job and e.get("stage") == stage), None),
                    timeout=30, description=f"gate {stage}")


def assert_recovered(system, m, done, events, workers, old, new_session):
    """X attempt 1 expired, attempt 2 by `new_session` was the single accepted success; Y used it."""
    job = m["job_id"]
    x = done["tasks"]["X"]
    assert done["state"] == "SUCCEEDED"
    assert [a["state"] for a in x["attempts"]] == ["EXPIRED", "SUCCEEDED"]
    assert x["attempts"][1]["identity"]["worker_session_id"] == new_session
    assert x["outputs"]["value"]["key"].startswith(prefix(x["attempts"][1]["identity"]))
    assert system.api.get(done["outputs"]["result"]) == b"7"
    assert sum(e["event_type"] == "task_succeeded" and e.get("job_id") == job and e["task_id"] == "X" for e in events) == 1
    expired = one(events, "lease_expired", job, "X", 1)
    assert expired["worker_session_id"] == old["worker_session_id"]
    reassigned = one(events, "task_assigned", job, "X", 2)
    lease = lease_ns(system)
    assert expired["elapsed_ns"] - expired["last_alive_elapsed_ns"] >= lease, "expired before its deadline"
    assert reassigned["assigned_elapsed_ns"] - expired["last_alive_elapsed_ns"] <= lease + SLACK_NS
    check_history(m, done, events, [e for w in workers for e in system.worker_events(w)])
    return expired


@pytest.mark.faults
@pytest.mark.parametrize("stage", ["before_start", "operation", "before_report"])
def test_crash_at_each_attempt_stage_is_recovered(system, stage):
    """Kill the owner after claim, during the operation, and after upload but before its report."""
    a = system.start_worker({"ENABLE_TEST_HOOKS": "true", "TEST_GATE_TASK": "X", "TEST_GATE_STAGE": stage,
                             "OPERATION_TIMEOUT_MS": "120000"})
    m = chain()
    job = system.api.submit(m)
    gate_event(system, a, job, stage)
    before = system.api.status(job)
    old = before["tasks"]["X"]["attempts"][0]["identity"]
    output = "/v1/objects/" + prefix(old) + "value"
    assert before["tasks"]["X"]["state"] == ("ASSIGNED" if stage == "before_start" else "RUNNING")
    assert request(system.artifacts, output, method="HEAD")[0] == (200 if stage == "before_report" else 404)
    b = system.start_worker()                       # healthy capacity is waiting when the fault happens
    system.kill_worker(a)
    done = system.api.complete(job, timeout=30)
    events = system.api.events()
    expired = assert_recovered(system, m, done, events, [a, b], old, system.worker_session(b))
    assert expired["old_state"] == ("ASSIGNED" if stage == "before_start" else "RUNNING")
    if stage == "before_report":
        # The dead attempt's upload is an orphan: it still exists, but it was never accepted or used.
        assert request(system.artifacts, output, method="HEAD")[0] == 200
        assert not any(e["event_type"] in ("task_succeeded", "report_rejected") and e.get("attempt_no") == 1
                       and e.get("task_id") == "X" for e in events)


@pytest.mark.faults
def test_restarted_worker_is_a_new_session_and_the_old_identity_stays_dead(system):
    a = system.start_worker({"ENABLE_TEST_HOOKS": "true", "TEST_GATE_TASK": "X", "OPERATION_TIMEOUT_MS": "120000"})
    m = chain()
    job = system.api.submit(m)
    gate_event(system, a, job, "operation")
    old = system.api.status(job)["tasks"]["X"]["attempts"][0]["identity"]
    system.kill_worker(a)
    restarted = system.start_worker()               # the same machine coming back: a fresh process and session
    session = system.worker_session(restarted)
    assert session != old["worker_session_id"]
    done = system.api.complete(job, timeout=30)
    events = system.api.events()
    assert_recovered(system, m, done, events, [a, restarted], old, session)
    # Nothing can act for the dead attempt any more, whoever sends it.
    tasks_before = system.api.status(job)["tasks"]
    for path, body in [("/v1/attempts/heartbeat", old), ("/v1/attempts/start", old),
                       ("/v1/attempts/report", {"identity": old, "outcome": "FAILURE", "outputs": {},
                                                "error": {"code": "LATE", "message": "late"}})]:
        status, reply = request(system.scheduler, path, body)
        assert status == 409, (path, status, reply)
    after = system.api.status(job)
    assert after["state"] == "SUCCEEDED" and after["tasks"] == tasks_before     # rejections change no task state


@pytest.mark.faults
def test_paused_worker_loses_its_lease_and_its_late_work_is_rejected(system):
    """A frozen worker is indistinguishable from a dead one until it wakes up; then it must stand down."""
    a = system.start_worker()
    m = manifest([task("X", delay_ms=3000), task("Y", "fixture_add", ["X"], {"value": binding("X")}, amount=4)])
    job = system.api.submit(m)
    wait_for(lambda: system.api.status(job)["tasks"]["X"]["state"] == "RUNNING", description="X running on A")
    old = system.api.status(job)["tasks"]["X"]["attempts"][0]["identity"]
    system.pause_worker(a)
    b = system.start_worker()
    done = system.api.complete(job, timeout=40)
    system.resume_worker(a)
    stood_down = wait_for(lambda: next((e for e in system.worker_events(a) if e.get("attempt_no") == 1 and e.get("task_id") == "X"
                                        and e["event_type"] in ("worker_lease_lost", "attempt_rejected")), None),
                          timeout=20, description="A standing down from its expired attempt")
    assert stood_down["status"] == 409
    events = system.api.events()
    assert_recovered(system, m, done, events, [a, b], old, system.worker_session(b))
    # A is healthy again and keeps serving: stop B and give A new work.
    system.kill_worker(b)
    probe = manifest([task("probe")])
    result = system.api.complete(system.api.submit(probe), timeout=30)
    assert result["tasks"]["probe"]["attempts"][0]["identity"]["worker_session_id"] == old["worker_session_id"]
    check_history(probe, result, system.api.events(), system.worker_events(a))


@pytest.mark.faults
def test_slow_worker_with_heartbeats_keeps_its_task(system):
    """Slow is not dead: a task running for more than two lease periods is never taken away."""
    a = system.start_worker()
    lease = lease_ns(system)
    delay_ms = int(2.4 * lease / 1_000_000)
    m = manifest([task("X", delay_ms=delay_ms)])
    started = time.monotonic()
    done = system.api.complete(system.api.submit(m), timeout=delay_ms / 1000 + 30)
    assert time.monotonic() - started >= delay_ms / 1000
    attempt, = done["tasks"]["X"]["attempts"]
    assert attempt["state"] == "SUCCEEDED" and attempt["identity"]["attempt_no"] == 1
    assert attempt["lease_renewals"] >= 8          # heartbeats every lease/5 for 2.4 leases: about 11
    events = system.api.events()
    assert not any(e["event_type"] == "lease_expired" for e in events)
    check_history(m, done, events, system.worker_events(a))
