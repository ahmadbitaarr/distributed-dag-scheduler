"""MS3 communication faults on one worker's link to the scheduler: loss, delay, duplication, partition.

Faults are injected by tests/harness/netfault.FaultProxy and logged to proxy-<worker>.jsonl next to
the scheduler and worker histories. Native backend only (the proxy runs inside the test process).
"""
import os
import random
import time
import pytest
from tests.harness.api import binding, check_history, functional, manifest, request, task, wait_for

native_only = pytest.mark.skipif(os.environ.get("MS2_BACKEND", "native") != "native",
                                 reason="per-link network faults need the in-process proxy (native backend)")
pytestmark = [pytest.mark.faults, native_only]


def successes(events, job, name):
    return [e for e in events if e["event_type"] == "task_succeeded" and e.get("job_id") == job and e["task_id"] == name]


def running_on(system, job, name):
    return wait_for(lambda: s if (s := system.api.status(job))["tasks"][name]["state"] == "RUNNING" else None,
                    timeout=30, description=f"{name} running")["tasks"][name]["attempts"][-1]["identity"]


def all_worker_events(system):
    return [e for w in system.workers for e in system.worker_events(w)]


def test_lost_heartbeats_expire_the_lease_and_the_late_success_is_rejected(system):
    """A live worker whose renewals are all lost looks dead. Its later SUCCESS must not count."""
    a = system.start_worker(proxy=True)
    system.proxy(a).add("drop_request", path="/v1/attempts/heartbeat")
    m = manifest([task("X", delay_ms=7000)])
    job = system.api.submit(m)
    old = running_on(system, job, "X")
    b = system.start_worker()
    done = system.api.complete(job, timeout=45)
    late = wait_for(lambda: next((e for e in system.worker_events(a) if e["event_type"] == "attempt_rejected"
                                  and e.get("task_id") == "X" and e["attempt_no"] == 1), None),
                    timeout=20, description="A's late report rejected")
    assert late["status"] == 409 and "LEASE_EXPIRED" in late["message"]
    sent = [e for e in system.worker_events(a) if e["event_type"] == "worker_report_sent" and e["attempt_no"] == 1]
    assert sent and sent[0]["report"]["outcome"] == "SUCCESS", "A really finished and really reported"
    events = system.api.events()
    rejected = [e for e in events if e["event_type"] == "report_rejected" and e.get("attempt_no") == 1]
    assert rejected and rejected[0]["error_code"] == "LEASE_EXPIRED"
    x = done["tasks"]["X"]
    assert [att["state"] for att in x["attempts"]] == ["EXPIRED", "SUCCEEDED"]
    assert x["attempts"][1]["identity"]["worker_session_id"] == system.worker_session(b)
    assert len(successes(events, job, "X")) == 1 and successes(events, job, "X")[0]["attempt_no"] == 2
    assert old["attempt_no"] == 1
    check_history(m, done, events, all_worker_events(system))


def test_partition_longer_than_the_lease_moves_the_task(system):
    a = system.start_worker(proxy=True)
    m = manifest([task("X", delay_ms=4000), task("Y", "fixture_add", ["X"], {"value": binding("X")}, amount=4)])
    job = system.api.submit(m)
    running_on(system, job, "X")
    system.proxy(a).partition()
    b = system.start_worker()
    done = system.api.complete(job, timeout=45)
    system.proxy(a).heal()
    stood_down = wait_for(lambda: next((e for e in system.worker_events(a) if e.get("task_id") == "X" and e.get("attempt_no") == 1
                                        and e["event_type"] in ("worker_lease_lost", "attempt_rejected")), None),
                          timeout=20, description="A standing down after the partition heals")
    assert stood_down["status"] == 409
    events = system.api.events()
    assert [att["state"] for att in done["tasks"]["X"]["attempts"]] == ["EXPIRED", "SUCCEEDED"]
    assert system.api.get(done["outputs"]["result"]) == b"7"
    assert len(successes(events, job, "X")) == 1
    assert system.proxy(a).applied("drop_request"), "the partition really dropped A's traffic"
    # After healing, A serves new work again.
    system.kill_worker(b)
    probe = manifest([task("probe")])
    result = system.api.complete(system.api.submit(probe), timeout=30)
    assert result["tasks"]["probe"]["attempts"][0]["identity"]["worker_session_id"] == system.worker_session(a)
    check_history(m, done, events, all_worker_events(system))


def test_partition_shorter_than_the_lease_keeps_the_attempt(system):
    """Temporary unavailability inside the lease budget costs nothing: no expiry, one attempt."""
    a = system.start_worker(proxy=True)
    m = manifest([task("X", delay_ms=4000)])
    job = system.api.submit(m)
    running_on(system, job, "X")
    system.proxy(a).partition()
    time.sleep(2.0)
    system.proxy(a).heal()
    done = system.api.complete(job, timeout=30)
    events = system.api.events()
    assert [att["state"] for att in done["tasks"]["X"]["attempts"]] == ["SUCCEEDED"]
    assert not any(e["event_type"] == "lease_expired" for e in events)
    assert any(r.get("path") == "/v1/attempts/heartbeat" for r in system.proxy(a).applied("drop_request"))
    check_history(m, done, events, system.worker_events(a))


def test_lost_claim_and_start_replies_are_replayed_from_receipts(system):
    """A worker that never hears its assignment or start ack retries; it gets the same answer, once."""
    a = system.start_worker(proxy=True)
    proxy = system.proxy(a)
    proxy.add("drop_response", path="/v1/work/claim", status=200, times=1)
    proxy.add("drop_response", path="/v1/attempts/start", times=1)
    m = manifest([task("X"), task("Y", "fixture_add", ["X"], {"value": binding("X")}, amount=4)])
    done = system.api.complete(system.api.submit(m), timeout=30)
    events = system.api.events()
    assert len(proxy.applied("drop_response", "/v1/work/claim")) == 1
    assert len(proxy.applied("drop_response", "/v1/attempts/start")) == 1
    for name in ("X", "Y"):
        assert len(done["tasks"][name]["attempts"]) == 1
        assert sum(e["event_type"] == "task_assigned" and e["task_id"] == name for e in events) == 1
        assert sum(e["event_type"] == "task_started" and e["task_id"] == name for e in events) == 1
    # The resent claim carried the same claim_id and was answered from the stored receipt.
    claims = [r for r in proxy.records() if r.get("path") == "/v1/work/claim"]
    dropped = next(r for r in claims if r["action"] == "drop_response")
    resent = [r for r in claims if r["request"]["claim_id"] == dropped["request"]["claim_id"]]
    assert len(resent) == 2 and resent[1]["status"] == 200 and resent[1]["response"] == dropped["response"]
    assert system.api.get(done["outputs"]["result"]) == b"7"
    check_history(m, done, events, system.worker_events(a))


def test_crash_after_success_is_accepted_but_its_reply_is_lost(system):
    """Report boundary: the scheduler committed X, the worker never learned it and died. X is done."""
    a = system.start_worker(proxy=True)
    system.proxy(a).add("drop_response", path="/v1/attempts/report", when=lambda body: body and body.get("outcome") == "SUCCESS")
    m = manifest([task("X"), task("Y", "fixture_add", ["X"], {"value": binding("X")}, amount=4)])
    job = system.api.submit(m)
    wait_for(lambda: system.proxy(a).applied("drop_response", "/v1/attempts/report"), timeout=30, description="first lost report reply")
    system.kill_worker(a)
    b = system.start_worker()
    done = system.api.complete(job, timeout=30)
    events = system.api.events()
    x = done["tasks"]["X"]
    assert [att["state"] for att in x["attempts"]] == ["SUCCEEDED"], "an accepted success is never expired or redone"
    assert done["tasks"]["Y"]["attempts"][0]["identity"]["worker_session_id"] == system.worker_session(b)
    assert not any(e["event_type"] == "lease_expired" for e in events)
    assert len(successes(events, job, "X")) == 1
    assert system.api.get(done["outputs"]["result"]) == b"7"
    check_history(m, done, events, all_worker_events(system))


def test_delayed_and_duplicated_messages_change_nothing(system):
    workers = [system.start_worker(proxy=True, seed=n) for n in range(2)]
    for w in workers:
        proxy = system.proxy(w)
        proxy.add("delay", delay_ms=150, jitter=True)
        proxy.add("duplicate", path="/v1/attempts/start")
        proxy.add("duplicate", path="/v1/attempts/report")
    jobs = [functional(50) for _ in range(3)]
    for m in jobs:
        system.api.submit(m)
    done = {m["job_id"]: system.api.complete(m["job_id"], timeout=60) for m in jobs}
    events = system.api.events()
    for m in jobs:
        snapshot = done[m["job_id"]]
        assert system.api.get(snapshot["outputs"]["result"]) == b"result=22\n"
        assert all(len(t["attempts"]) == 1 for t in snapshot["tasks"].values())
        check_history(m, snapshot, events, all_worker_events(system))
    duplicates = [e for e in events if e["event_type"] == "completion_duplicate"]
    assert len(duplicates) == 15, "every duplicated report was answered from its receipt"
    assert sum(e["event_type"] == "task_succeeded" for e in events) == 15
    assert sum(len(system.proxy(w).applied("duplicate")) for w in workers) >= 30


def test_chaos_campaign_keeps_every_guarantee(system):
    """Seeded mix of loss, delay, a crash, a long pause and a replacement worker during live jobs."""
    rng = random.Random(4094)
    # Hold a known running attempt until its worker is killed. Fixed sleeps alone
    # can hit idle workers and exercise no lease recovery at all.
    crash_gate = {"ENABLE_TEST_HOOKS": "true", "TEST_GATE_TASK": "A",
                  "TEST_GATE_STAGE": "operation", "OPERATION_TIMEOUT_MS": "120000"}
    workers = [system.start_worker(env=crash_gate if n == 0 else None,
                                   proxy=True, seed=rng.randrange(1 << 30)) for n in range(3)]
    for w in workers:
        proxy = system.proxy(w)
        proxy.add("delay", delay_ms=100, jitter=True)
        proxy.add("drop_request", probability=0.05)
        proxy.add("drop_response", probability=0.05)
    jobs = [functional(400) for _ in range(6)]
    for m in jobs:
        system.api.submit(m)
    gate = wait_for(lambda: next((e for e in system.worker_events(workers[0])
                                  if e["event_type"] == "worker_test_gate_entered"
                                  and e.get("stage") == "operation"), None),
                    timeout=30, description="chaos crash victim holding a running attempt")
    held = system.api.status(gate["job_id"])["tasks"][gate["task_id"]]
    assert held["state"] == "RUNNING" and held["owner"] == gate["worker_session_id"]
    assert held["attempt_no"] == gate["attempt_no"]
    system.kill_worker(workers[0])
    time.sleep(1.0)
    system.pause_worker(workers[1])                    # long freeze: longer than the lease
    replacement = system.start_worker()
    time.sleep(7.0)
    system.resume_worker(workers[1])
    done = {m["job_id"]: system.api.complete(m["job_id"], timeout=120) for m in jobs}
    events = system.api.events()
    worker_events = all_worker_events(system)
    for m in jobs:
        snapshot = done[m["job_id"]]
        assert system.api.get(snapshot["outputs"]["result"]) == b"result=22\n"
        check_history(m, snapshot, events, worker_events)
    keys = [(e["job_id"], e["task_id"]) for e in events if e["event_type"] == "task_succeeded"]
    assert len(keys) == len(set(keys)) == 6 * 5
    assert any(e["event_type"] == "lease_expired"
               and all(e.get(k) == gate[k] for k in
                       ("job_id", "task_id", "attempt_no", "worker_session_id"))
               for e in events), "the gated crash victim's attempt must expire"
    injected = sum(len(system.proxy(w).applied("drop_request")) + len(system.proxy(w).applied("drop_response")) for w in workers)
    assert injected > 0
    assert system.worker_running(replacement) and system.worker_running(workers[1])
