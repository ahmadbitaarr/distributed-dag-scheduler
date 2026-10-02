"""Step 5: scheduler HTTP API behavior beyond the happy path (architecture §§6, 7, 14)."""
import hashlib
import json
import urllib.request
from tests.harness.api import functional, manifest, request, task, uid


def raw(base, path, method="GET", body=b""):
    req = urllib.request.Request(base + path, data=body or None, method=method, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            return response.status, response.headers, response.read()
    except urllib.error.HTTPError as error:
        return error.code, error.headers, error.read()


def submit(system, value):
    return request(system.scheduler, "/v1/jobs", {"scheduler_run_id": system.api.run_id, "manifest": value})


def source_manifest(descriptor):
    return manifest([task("inspect", "video_inspect", inputs={"video": {"source": descriptor}})], output="metadata")


def test_health_and_run_header(system):
    code, headers, body = raw(system.scheduler, "/v1/health")
    data = json.loads(body)
    assert code == 200 and data["ready"] is True
    assert headers["X-Scheduler-Run-Id"] == data["scheduler_run_id"] == system.api.run_id


def test_endpoint_errors_are_structured(system):
    cases = [
        ("/v1/jobs/" + uid(), "GET", b"", 404, "JOB_NOT_FOUND"),
        ("/v1/jobs/not-a-uuid", "GET", b"", 400, "INVALID_INPUT"),
        ("/v1/jobs", "GET", b"", 405, "METHOD_NOT_ALLOWED"),
        ("/v1/work/claim", "GET", b"", 405, "METHOD_NOT_ALLOWED"),
        ("/v1/nothing", "GET", b"", 404, "NOT_FOUND"),
        ("/v1/events?after=-1", "GET", b"", 400, "INVALID_INPUT"),
        ("/v1/events?limit=0", "GET", b"", 400, "INVALID_INPUT"),
        ("/v1/events?limit=1001", "GET", b"", 400, "INVALID_INPUT"),
        ("/v1/events?after=x", "GET", b"", 400, "INVALID_INPUT"),
        ("/v1/events?other=1", "GET", b"", 400, "INVALID_INPUT"),
        ("/v1/jobs", "POST", b"{not json", 400, "INVALID_INPUT"),
        ("/v1/work/claim", "POST", b"{}", 400, "INVALID_INPUT"),
        ("/v1/attempts/start", "POST", b"{}", 400, "INVALID_INPUT"),
        ("/v1/attempts/report", "POST", b"{}", 400, "INVALID_INPUT"),
    ]
    for path, method, body, status, code in cases:
        got, _, payload = raw(system.scheduler, path, method, body)
        assert got == status, (path, method, got, payload)
        assert json.loads(payload)["error"]["code"] == code, (path, payload)


def test_request_body_limit_is_413(system):
    padding = "x" * (1024 * 1024)
    code, _, payload = raw(system.scheduler, "/v1/jobs", "POST", json.dumps({"scheduler_run_id": system.api.run_id, "pad": padding}).encode())
    assert code == 413 and json.loads(payload)["error"]["code"] == "MANIFEST_TOO_LARGE"


def test_stale_run_is_rejected_everywhere(system):
    other = uid()
    m = manifest([task("A")])
    assert request(system.scheduler, "/v1/jobs", {"scheduler_run_id": other, "manifest": m})[0] == 409
    assert request(system.scheduler, "/v1/jobs/" + m["job_id"])[0] == 404
    code, body = request(system.scheduler, "/v1/work/claim", {"scheduler_run_id": other, "worker_session_id": uid(), "claim_id": uid()})
    assert code == 409 and body["error"]["code"] == "STALE_RUN"
    system.api.submit(m)
    _, a = system.api.claim()
    stale = {**a["identity"], "scheduler_run_id": other}
    assert request(system.scheduler, "/v1/attempts/start", stale)[1]["error"]["code"] == "STALE_RUN"
    assert system.api.status(m["job_id"])["tasks"]["A"]["state"] == "ASSIGNED"


def test_source_descriptors_are_verified_before_acceptance(system):
    content = b"not really a video"
    published = system.api.put(content, f"inputs/{uid()}/clip.mp4", "video/mp4")
    unpublished = {**published, "key": f"inputs/{uid()}/clip.mp4"}
    wrong_hash = {**published, "sha256": hashlib.sha256(b"other").hexdigest()}
    wrong_length = {**published, "length": published["length"] + 1}
    wrong_media = {**published, "media_type": "video/webm"}
    for bad in (unpublished, wrong_hash, wrong_length, wrong_media):
        m = source_manifest(bad)
        code, body = submit(system, m)
        assert code == 400, (bad, body)
        assert request(system.scheduler, "/v1/jobs/" + m["job_id"])[0] == 404
    good = source_manifest(published)
    assert submit(system, good)[0] == 201
    _, metrics = request(system.scheduler, "/v1/metrics")
    assert metrics["counters"]["accepted_jobs"] == 1


def test_storage_unavailable_is_transient_and_accepts_nothing(system):
    published = system.api.put(b"bytes", f"inputs/{uid()}/clip.mp4", "video/mp4")
    system.stop_artifacts()
    m = source_manifest(published)
    code, body = submit(system, m)
    assert code == 503 and body["error"]["code"] == "ARTIFACT_UNAVAILABLE"
    assert request(system.scheduler, "/v1/jobs/" + m["job_id"])[0] == 404
    _, metrics = request(system.scheduler, "/v1/metrics")
    assert metrics["counters"]["accepted_jobs"] == 0
    assert not [e for e in system.api.events() if e["event_type"] == "job_submitted"]
    # A job without source artifacts needs no storage check and is still accepted.
    assert submit(system, manifest([task("A")]))[0] == 201


def test_counters_gauges_and_snapshot_sequence_are_consistent(system):
    m = manifest([task("A"), task("B", parents=["A"])])
    job = system.api.submit(m)
    _, first = system.api.claim()
    assert system.api.report(first, "FAILURE")[0] == 200                    # explicit failure from ASSIGNED
    assert system.api.report(first, "FAILURE")[0] == 200                    # duplicate receipt
    _, second = system.api.claim()
    assert second["identity"]["attempt_no"] == 2                            # retry assigned
    assert system.api.report(second)[0] == 409                              # rejected: success before start
    assert system.api.start(second)[0] == 200
    out = system.api.put("3", second["output_prefix"] + "value")
    assert system.api.report(second, outputs={"value": out})[0] == 200
    snapshot = system.api.status(job)
    events = system.api.events()
    assert snapshot["snapshot_event_seq"] == len(events)                    # nothing else ran
    _, metrics = request(system.scheduler, "/v1/metrics")
    assert metrics["counters"] == {"accepted_jobs": 1, "accepted_logical_successes": 1, "explicit_failed_attempts": 1,
                                   "retries_assigned": 1, "duplicate_reports": 1, "rejected_reports": 1}
    assert metrics["tasks_by_state"] == {"BLOCKED": 0, "READY": 1, "ASSIGNED": 0, "RUNNING": 0, "SUCCEEDED": 1}
    assert metrics["ready_queue_length"] == 1 and metrics["active_attempts"] == 0
    assert metrics["scheduling_latency_ns"]["count"] == 2
    kinds = [e["event_type"] for e in events]
    for kind in ("job_submitted", "task_ready", "task_assigned", "task_failed", "task_retried", "completion_duplicate",
                 "report_rejected", "task_started", "task_succeeded", "dependency_satisfied", "work_claim"):
        assert kind in kinds, kind
    # Page size 1 walks the same gap-free history.
    walked, cursor = [], 0
    while True:
        _, page = request(system.scheduler, f"/v1/events?after={cursor}&limit=1")
        walked += page["events"]
        cursor = page["next_after"]
        if not page["has_more"]:
            break
    assert walked == events
    required = {"schema_version", "scheduler_run_id", "event_type", "producer", "producer_seq", "utc_timestamp",
                "elapsed_ns", "request_id", "job_id", "task_id", "attempt_no", "worker_session_id", "scheduler_event_seq"}
    assert all(required <= set(e) for e in events)


def test_rejected_commands_do_not_change_snapshots(system):
    m = manifest([task("A")])
    job = system.api.submit(m)
    _, a = system.api.claim()
    before = system.api.status(job)
    wrong_owner = {**a["identity"], "worker_session_id": uid()}
    assert request(system.scheduler, "/v1/attempts/start", wrong_owner)[0] == 409
    assert system.api.report(a)[0] == 409
    bad_outputs = {"value": {"key": f"inputs/{uid()}/x", "length": 1, "sha256": "0" * 64, "media_type": "application/json"}}
    assert request(system.scheduler, "/v1/attempts/report", {"identity": a["identity"], "outcome": "SUCCESS", "outputs": bad_outputs, "error": None})[0] == 409
    after = system.api.status(job)
    assert after["tasks"] == before["tasks"] and after["state"] == before["state"]
