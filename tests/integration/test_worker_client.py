"""Step 6: real worker lifecycle and the Java client (architecture §§2, 6, 12)."""
import http.client
import http.server
import json
import os
import subprocess
import threading
import urllib.parse
import pytest
from tests.harness.api import check_history, functional, manifest, request, task, uid, wait_for
from tests.harness.runtime import ROOT

native_only = pytest.mark.skipif(os.environ.get("MS2_BACKEND", "native") != "native",
                                 reason="needs in-process control of the scheduler address")


def client(system, *args):
    env = {**os.environ, "SCHEDULER_URL": system.scheduler, "ARTIFACT_BASE_URL": system.artifacts}
    result = subprocess.run([os.environ.get("JAVA", "java"), "-jar", str(ROOT / "client/target/client-0.2.0.jar"), *args],
                            env=env, capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


def test_java_client_upload_submit_status_fetch(system, tmp_path):
    worker = system.start_worker()
    srt = ROOT / "workloads/video/fixture.srt"
    descriptor = json.loads(client(system, "upload", str(srt)))
    assert descriptor["key"].startswith("inputs/") and descriptor["key"].endswith("/fixture.srt")
    assert descriptor["media_type"] == "application/x-subrip"
    assert system.api.get(descriptor) == srt.read_bytes()

    m = functional(50)
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(m))
    accepted = json.loads(client(system, "submit", str(path)))
    assert accepted["job_id"] == m["job_id"] and accepted["state"] == "ACCEPTED"
    system.api.job_ids.append(m["job_id"])
    assert json.loads(client(system, "submit", str(path)))["job_id"] == m["job_id"]    # idempotent replay
    snapshot = system.api.complete(m["job_id"])
    assert json.loads(client(system, "status", m["job_id"]))["state"] == "SUCCEEDED"
    out = tmp_path / "result.txt"
    client(system, "fetch", snapshot["outputs"]["result"]["key"], str(out))
    assert out.read_bytes() == b"result=22\n"
    check_history(m, snapshot, system.api.events(), system.worker_events(worker))


def test_worker_has_one_slot_and_starts_only_after_ack(system):
    workers = [system.start_worker() for _ in range(2)]
    jobs = [functional(150) for _ in range(3)]
    for m in jobs:
        system.api.submit(m)
    snapshots = {m["job_id"]: system.api.complete(m["job_id"]) for m in jobs}
    events = system.api.events()                     # after the snapshots, so the history covers them
    worker_events = [e for w in workers for e in system.worker_events(w)]
    for m in jobs:
        check_history(m, snapshots[m["job_id"]], events, worker_events)
    # Per session: after a task_assigned, the next claim comes only after that attempt is reported.
    active = {}
    for e in events:
        session = e.get("worker_session_id")
        if e["event_type"] == "task_assigned":
            assert session not in active, "session assigned a second task while one is active"
            active[session] = (e["job_id"], e["task_id"], e["attempt_no"])
        elif e["event_type"] in ("task_succeeded", "task_failed"):
            assert active.pop(session) == (e["job_id"], e["task_id"], e["attempt_no"])
        elif e["event_type"] == "work_claim":
            assert session not in active, "honest worker claimed while holding an attempt"
    started = [(e["job_id"], e["task_id"], e["attempt_no"]) for e in worker_events if e["event_type"] == "worker_operation_started"]
    assert len(started) == len(set(started)) == 3 * 5, "each logical task executed exactly once"


def test_hooks_are_disabled_by_default(system):
    system.start_worker({"TEST_FAIL_FIRST_TASK": "A", "TEST_GATE_TASK": "B"})       # no ENABLE_TEST_HOOKS
    m = functional(50)
    snapshot = system.api.complete(system.api.submit(m))
    assert all(len(t["attempts"]) == 1 for t in snapshot["tasks"].values())


def test_local_operation_timeout_is_an_explicit_bounded_failure(system):
    worker = system.start_worker({"OPERATION_TIMEOUT_MS": "300"})
    m = manifest([task("slow", delay_ms=5000)])
    job = system.api.submit(m)
    snapshot = wait_for(lambda: s if len((s := system.api.status(job))["tasks"]["slow"]["attempts"]) >= 3 else None,
                        timeout=30, description="three timed-out attempts")
    failed = [a for a in snapshot["tasks"]["slow"]["attempts"] if a["state"] == "FAILED"]
    assert len(failed) >= 2
    assert all(a["report_receipt"]["error"]["code"] == "OPERATION_TIMEOUT" for a in failed)
    assert [a["identity"]["attempt_no"] for a in snapshot["tasks"]["slow"]["attempts"]] == list(range(1, len(snapshot["tasks"]["slow"]["attempts"]) + 1))
    assert snapshot["state"] == "RUNNING"                     # no retry cap, no terminal FAILED job
    assert system.worker_running(worker)


def test_stale_report_rejection_does_not_kill_the_worker(system):
    worker = system.start_worker()
    m = manifest([task("A", delay_ms=1500)])
    job = system.api.submit(m)
    running = wait_for(lambda: s if (s := system.api.status(job))["tasks"]["A"]["state"] == "RUNNING" else None,
                       description="A running on the worker")
    identity = running["tasks"]["A"]["attempts"][0]["identity"]
    # The scheduler accepts a failure for attempt 1 while the worker is still executing it.
    body = {"identity": identity, "outcome": "FAILURE", "outputs": {}, "error": {"code": "INJECTED", "message": "test"}}
    assert request(system.scheduler, "/v1/attempts/report", body)[0] == 200
    snapshot = system.api.complete(job, 30)                     # the same worker later runs attempt 2
    attempts = snapshot["tasks"]["A"]["attempts"]
    assert [a["state"] for a in attempts] == ["FAILED", "SUCCEEDED"]
    assert attempts[0]["identity"]["worker_session_id"] == attempts[1]["identity"]["worker_session_id"]
    rejected = [e for e in system.worker_events(worker) if e["event_type"] == "attempt_rejected"]
    assert rejected and rejected[0]["attempt_no"] == 1 and rejected[0]["status"] == 409
    assert system.worker_running(worker)


class DropFirstReportReply(http.server.BaseHTTPRequestHandler):
    """Forwards to the scheduler. The first SUCCESS report is delivered, but its reply is dropped."""
    target = None
    dropped = []
    lock = threading.Lock()

    def log_message(self, *args):
        pass

    def forward(self):
        body = self.rfile.read(int(self.headers.get("Content-Length") or 0))
        url = urllib.parse.urlparse(self.target)
        conn = http.client.HTTPConnection(url.hostname, url.port, timeout=10)
        conn.request(self.command, self.path, body or None, {"Content-Type": "application/json"} if body else {})
        response = conn.getresponse()
        payload = response.read()
        with self.lock:
            drop = self.path == "/v1/attempts/report" and b'"SUCCESS"' in body and not self.dropped
            if drop:
                self.dropped.append(json.loads(payload))
        if drop:
            self.close_connection = True                       # accepted by the scheduler, reply lost
            return
        self.send_response(response.status)
        for key, value in response.getheaders():
            if key.lower() not in ("transfer-encoding", "connection", "content-length", "date", "server"):
                self.send_header(key, value)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    do_GET = do_POST = forward


@native_only
def test_lost_report_ack_is_replayed_not_reexecuted(system):
    DropFirstReportReply.target, DropFirstReportReply.dropped = system.scheduler, []
    proxy = http.server.ThreadingHTTPServer(("127.0.0.1", 0), DropFirstReportReply)
    threading.Thread(target=proxy.serve_forever, daemon=True).start()
    try:
        worker = system.start_worker({"SCHEDULER_URL": f"http://127.0.0.1:{proxy.server_address[1]}"})
        m = manifest([task("A", delay_ms=50), task("B", parents=["A"], delay_ms=50)])
        snapshot = system.api.complete(system.api.submit(m))
    finally:
        proxy.shutdown()
    assert DropFirstReportReply.dropped, "the proxy dropped one accepted report reply"
    events = system.api.events()
    worker_events = system.worker_events(worker)
    first = DropFirstReportReply.dropped[0]
    lost_task = next(e["task_id"] for e in events if e["scheduler_event_seq"] == first["scheduler_event_seq"])
    executions = [e for e in worker_events if e["event_type"] == "worker_operation_started" and e["task_id"] == lost_task]
    assert len(executions) == 1, "a lost acknowledgment must not re-run the operation"
    reports = [e for e in worker_events if e["event_type"] == "worker_report_sent" and e["task_id"] == lost_task]
    assert len(reports) == 1
    duplicates = [e for e in events if e["event_type"] == "completion_duplicate" and e["task_id"] == lost_task]
    assert len(duplicates) == 1 and duplicates[0]["receipt_event_seq"] == first["scheduler_event_seq"]
    assert sum(e["event_type"] == "task_succeeded" and e["task_id"] == lost_task for e in events) == 1
    check_history(m, snapshot, events, worker_events)


@native_only
def test_worker_abandons_old_run_and_joins_the_new_one(system):
    worker = system.start_worker()
    old_run = system.api.run_id
    m = manifest([task("A", delay_ms=2000)])
    job = system.api.submit(m)
    wait_for(lambda: system.api.status(job)["tasks"]["A"]["state"] == "RUNNING", description="A running in the old run")
    old_session = next(e["worker_session_id"] for e in system.worker_events(worker) if e["event_type"] == "worker_session_started")
    new_run = system.restart_scheduler()
    assert new_run != old_run
    assert request(system.scheduler, "/v1/jobs/" + job)[0] == 404            # the new run starts empty
    wait_for(lambda: any(e["event_type"] == "worker_session_started" and e["scheduler_run_id"] == new_run
                         for e in system.worker_events(worker)), timeout=30, description="worker joined new run")
    worker_events = system.worker_events(worker)
    assert any(e["event_type"] == "scheduler_run_changed" for e in worker_events)
    new_session = next(e["worker_session_id"] for e in worker_events if e["event_type"] == "worker_session_started" and e["scheduler_run_id"] == new_run)
    assert new_session != old_session
    code, body = request(system.scheduler, "/v1/work/claim", {"scheduler_run_id": old_run, "worker_session_id": old_session, "claim_id": uid()})
    assert code == 409 and body["error"]["code"] == "STALE_RUN"
    fresh = manifest([task("B", delay_ms=50)])
    snapshot = system.api.complete(system.api.submit(fresh))
    assert snapshot["tasks"]["B"]["attempts"][0]["identity"]["worker_session_id"] == new_session
    # The old run's late report is only a rejection diagnostic in the new run; it changes no state.
    assert {e["event_type"] for e in system.api.events() if e.get("job_id") == job} <= {"report_rejected"}
    assert system.worker_running(worker)
