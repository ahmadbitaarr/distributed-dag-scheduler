import concurrent.futures
import copy
import hashlib
import http.client
import json
import subprocess
import urllib.error
import urllib.parse
from pathlib import Path
import pytest
from tests.harness.api import binding, check_history, functional, manifest, request, task, uid, video_manifest, wait_for
from tests.harness.runtime import ROOT


def accept_success(api, assignment, value="3"):
    assert api.start(assignment)[0] == 200
    output = api.put(value, assignment["output_prefix"] + "value")
    assert api.report(assignment, outputs={"value": output})[0] == 200
    return output


def test_functional_multiple_jobs_workers(system):
    workers = [system.start_worker() for _ in range(3)]
    manifests = [functional() for _ in range(4)]
    for m in manifests:
        system.api.submit(m)
    for m in manifests:
        snapshot = system.api.complete(m["job_id"])
        assert system.api.get(snapshot["outputs"]["result"]) == b"result=22\n"
        check_history(m, snapshot, system.api.events(), [e for w in workers for e in system.worker_events(w)])


def test_join_and_independent_branch_concurrency(system):
    workers = [system.start_worker() for _ in range(2)]
    m = functional(600)
    job = system.api.submit(m)
    simultaneous = wait_for(lambda: s if all((s := system.api.status(job))["tasks"][n]["state"] == "RUNNING" for n in ["B", "C"]) else None,
                            description="both branches RUNNING")
    assert simultaneous["tasks"]["B"]["owner"] != simultaneous["tasks"]["C"]["owner"]
    assert simultaneous["tasks"]["D"]["state"] == "BLOCKED"
    wait_for(lambda: {e.get("task_id") for w in workers for e in system.worker_events(w) if e["event_type"] == "worker_operation_started"} >= {"B", "C"})
    snapshot = system.api.complete(job)
    events = system.api.events()
    order = {(e["event_type"], e.get("task_id")): e["scheduler_event_seq"] for e in events}
    assert order["task_started", "B"] < order["task_succeeded", "C"]
    assert order["task_started", "C"] < order["task_succeeded", "B"]
    check_history(m, snapshot, events, [e for w in workers for e in system.worker_events(w)])


def test_multiple_roots_sinks_and_all_tasks_required(system):
    m = manifest([task("A"), task("B")], final_task="A")
    job = system.api.submit(m)
    _, a = system.api.claim()
    accept_success(system.api, a)
    assert system.api.status(job)["state"] == "RUNNING"
    _, b = system.api.claim()
    assert b["identity"]["task_id"] == "B"
    accept_success(system.api, b)
    check_history(m, system.api.complete(job), system.api.events())


def test_simultaneous_claims_and_session_single_slot(system):
    system.api.submit(manifest([task("A")]))
    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
        results = list(pool.map(lambda _: system.api.claim(), range(12)))
    assignments = [a for code, a in results if code == 200]
    assert len(assignments) == 1 and sum(code == 204 for code, _ in results) == 11
    a = assignments[0]
    code, same = system.api.claim(a["identity"]["worker_session_id"])
    assert code == 200 and same["identity"] == a["identity"]


def test_submission_and_claim_receipts(system):
    m = functional()
    job = system.api.submit(m)
    equivalent = copy.deepcopy(m)
    equivalent["tasks"].reverse()
    next(t for t in equivalent["tasks"] if t["task_id"] == "D")["parents"].reverse()
    code, _ = request(system.scheduler, "/v1/jobs", {"scheduler_run_id": system.api.run_id, "manifest": equivalent})
    assert code == 200
    different = copy.deepcopy(m)
    different["tasks"][0]["parameters"]["value"] = 99
    assert request(system.scheduler, "/v1/jobs", {"scheduler_run_id": system.api.run_id, "manifest": different})[0] == 409
    session, claim_id = uid(), uid()
    _, a = system.api.claim(session, claim_id)
    assert system.api.claim(session, claim_id)[1] == a
    accept_success(system.api, a)
    terminal = system.api.claim(session, claim_id)[1]
    assert terminal["disposition"] == "TERMINAL_SUCCEEDED"
    assert system.api.status(job)["tasks"]["A"]["attempt_no"] == 1
    assert system.api.claim(uid(), claim_id)[0] == 409


def test_cached_empty_claim_stays_empty(system):
    session, claim_id = uid(), uid()
    assert system.api.claim(session, claim_id)[0] == 204
    system.api.submit(manifest([task("A")]))
    assert system.api.claim(session, claim_id)[0] == 204
    assert system.api.claim(session)[0] == 200


def test_real_worker_failure_attempt_two(system):
    worker = system.start_worker({"ENABLE_TEST_HOOKS": "true", "TEST_FAIL_FIRST_TASK": "A"})
    m = functional()
    job = system.api.submit(m)
    snapshot = system.api.complete(job)
    a = snapshot["tasks"]["A"]
    assert [x["state"] for x in a["attempts"]] == ["FAILED", "SUCCEEDED"]
    assert system.api.get(snapshot["outputs"]["result"]) == b"result=22\n"
    check_history(m, snapshot, system.api.events(), system.worker_events(worker))
    assert sum(e["event_type"] == "task_succeeded" and e.get("task_id") == "A" for e in system.api.events()) == 1


def test_duplicate_conflicting_stale_reports_and_retry(system):
    m = manifest([task("A"), task("B", parents=["A"])])
    job = system.api.submit(m)
    _, a = system.api.claim()
    assert system.api.report(a)[0] == 409  # Cannot succeed before a start.
    assert system.api.report(a, "FAILURE")[0] == 200  # Explicit failure from ASSIGNED.
    assert system.api.report(a, "FAILURE")[0] == 200
    _, a2 = system.api.claim()
    assert a2["identity"]["attempt_no"] == 2
    assert system.api.report(a, "FAILURE")[0] == 200  # Replay old receipt remains harmless.
    assert system.api.report(a)[0] == 409
    output = accept_success(system.api, a2)
    assert system.api.report(a2, outputs={"value": output})[0] == 200
    assert system.api.start(a2)[0] == 200
    assert system.api.report(a2, "FAILURE")[0] == 409
    wrong = copy.deepcopy(a2)
    wrong["identity"]["worker_session_id"] = uid()
    assert system.api.report(wrong, outputs={"value": output})[0] == 409
    wrong["identity"]["scheduler_run_id"] = uid()
    assert system.api.start(wrong)[0] == 409
    snapshot = system.api.status(job)
    assert snapshot["tasks"]["B"]["satisfied_parents"] == ["A"]
    assert snapshot["tasks"]["A"]["state"] == "SUCCEEDED"
    events = system.api.events()
    assert sum(e["event_type"] == "dependency_satisfied" for e in events) == 1
    check_history(m, snapshot, events)


def test_success_requires_published_correct_outputs(system):
    job = system.api.submit(manifest([task("A")]))
    _, a = system.api.claim()
    assert system.api.start(a)[0] == 200
    descriptor = {"key": a["output_prefix"] + "value", "length": 1, "sha256": hashlib.sha256(b"3").hexdigest(), "media_type": "application/json"}
    assert system.api.report(a, outputs={"value": descriptor})[0] == 400
    published = system.api.put("3", descriptor["key"])
    assert system.api.status(job)["tasks"]["A"]["state"] == "RUNNING"
    wrong = {**published, "length": 2}
    assert system.api.report(a, outputs={"value": wrong})[0] == 400
    assert system.api.report(a, outputs={"value": published})[0] == 200
    assert system.api.complete(job)["state"] == "SUCCEEDED"


def test_artifact_staging_atomic_publication_and_conflicts(system):
    key = f"inputs/{uid()}/partial"
    url = urllib.parse.urlparse(system.artifacts)
    conn = http.client.HTTPConnection(url.hostname, url.port, timeout=5)
    conn.putrequest("PUT", "/v1/objects/" + key)
    conn.putheader("Content-Length", "4")
    conn.putheader("X-Content-SHA256", hashlib.sha256(b"1234").hexdigest())
    conn.putheader("Content-Type", "application/json")
    conn.endheaders()
    conn.send(b"12")
    assert request(system.artifacts, "/v1/objects/" + key, method="HEAD")[0] == 404
    conn.send(b"34")
    response = conn.getresponse()
    assert response.status == 201
    descriptor = json.loads(response.read())
    conn.close()
    assert system.api.get(descriptor) == b"1234"
    assert system.api.put("1234", key) == descriptor
    with pytest.raises(urllib.error.HTTPError) as exc:
        system.api.put("5678", key)
    assert exc.value.code == 409


@pytest.mark.parametrize("change", ["cycle", "duplicate", "unknown_parent", "self", "duplicate_parent", "bad_binding", "operation", "empty", "too_many"])
def test_invalid_dags_never_accepted(system, change):
    m = functional()
    if change == "cycle":
        m["tasks"][0]["parents"] = ["E"]
    elif change == "duplicate":
        m["tasks"].append(copy.deepcopy(m["tasks"][0]))
    elif change == "unknown_parent":
        m["tasks"][1]["parents"] = ["unknown"]
    elif change == "self":
        m["tasks"][0]["parents"] = ["A"]
    elif change == "duplicate_parent":
        m["tasks"][1]["parents"] = ["A", "A"]
    elif change == "bad_binding":
        m["tasks"][1]["inputs"]["value"]["output_name"] = "wrong"
    elif change == "operation":
        m["tasks"][0]["operation"] = "shell"
    elif change == "empty":
        m["tasks"] = []
    elif change == "too_many":
        m = manifest([task(f"T{i}") for i in range(129)])
    code, _ = request(system.scheduler, "/v1/jobs", {"scheduler_run_id": system.api.run_id, "manifest": m})
    assert code == (413 if change == "too_many" else 400)
    assert request(system.scheduler, "/v1/jobs/" + m["job_id"])[0] == 404


def test_strict_json_types_and_unknown_fields(system):
    for bad in ["3", 3.5]:
        m = manifest([task("A", value=bad)])
        assert request(system.scheduler, "/v1/jobs", {"scheduler_run_id": system.api.run_id, "manifest": m})[0] == 400
    m = functional()
    m["shell"] = "echo"
    assert request(system.scheduler, "/v1/jobs", {"scheduler_run_id": system.api.run_id, "manifest": m})[0] == 400


def ffprobe(path):
    return json.loads(subprocess.check_output(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)]))


def test_video_pipeline(system):
    workers = [system.start_worker() for _ in range(3)]
    directory = ROOT / "workloads/video"
    expected_sums = dict(reversed(line.split()) for line in (directory / "SHA256SUMS").read_text().splitlines())
    for name, digest in expected_sums.items():
        assert hashlib.sha256((directory / name).read_bytes()).hexdigest() == digest, f"{name} differs from SHA256SUMS"
    video = system.api.put((directory / "sample.mp4").read_bytes(), f"inputs/{uid()}/sample.mp4", "video/mp4")
    subtitles = system.api.put((directory / "fixture.srt").read_bytes(), f"inputs/{uid()}/fixture.srt", "application/x-subrip")
    m = video_manifest(video, subtitles)
    snapshot = system.api.complete(system.api.submit(m), 90)
    tasks = snapshot["tasks"]
    evidence = {"inputs": {"video": video, "subtitles": subtitles}, "outputs": {}}

    metadata = json.loads(system.api.get(tasks["inspect"]["outputs"]["metadata"]))
    source = next(s for s in metadata["streams"] if s["codec_type"] == "video")
    assert (source["width"], source["height"]) == (1280, 720)
    assert abs(float(metadata["format"]["duration"]) - 10.0) < 0.1

    publication = json.loads(system.api.get(snapshot["outputs"]["result"]))
    assert publication["schema_version"] == 1 and publication["fixture_subtitles"] is True
    accepted = {"video720": tasks["transcode720"]["outputs"]["video"], "video360": tasks["transcode360"]["outputs"]["video"],
                "image": tasks["thumbnail"]["outputs"]["image"], "subtitles": tasks["subtitles"]["outputs"]["subtitles"]}
    assert publication["artifacts"] == accepted, "publish must reference exactly the accepted branch outputs"

    for name, height in [("video720", 720), ("video360", 360)]:
        file = system.evidence / (name + ".mp4")
        file.write_bytes(system.api.get(accepted[name]))
        info = ffprobe(file)
        stream = next(s for s in info["streams"] if s["codec_type"] == "video")
        assert stream["codec_name"] == "h264"
        assert (stream["width"], stream["height"]) == ((1280, 720) if height == 720 else (640, 360))
        assert abs(float(info["format"]["duration"]) - 10.0) < 0.2
        assert publication["metadata"][name]["streams"][0]["height"] == height
        evidence["outputs"][name] = {"descriptor": accepted[name], "codec": stream["codec_name"], "width": stream["width"],
                                     "height": stream["height"], "duration": info["format"]["duration"]}

    png = system.api.get(accepted["image"])
    assert png.startswith(bytes([0x89]) + b"PNG" + bytes([13, 10, 26, 10])) and png[12:16] == b"IHDR"
    width, height = int.from_bytes(png[16:20], "big"), int.from_bytes(png[20:24], "big")
    assert (width, height) == (1280, 720)
    (system.evidence / "thumbnail.png").write_bytes(png)
    evidence["outputs"]["image"] = {"descriptor": accepted["image"], "width": width, "height": height}

    assert system.api.get(accepted["subtitles"]) == (directory / "fixture.srt").read_bytes()
    evidence["outputs"]["subtitles"] = {"descriptor": accepted["subtitles"], "byte_identical_to_fixture": True}

    events = system.api.events()
    check_history(m, snapshot, events, [e for w in workers for e in system.worker_events(w)])
    branches = ["transcode720", "transcode360", "thumbnail", "subtitles"]
    sessions = {tasks[b]["attempts"][-1]["identity"]["worker_session_id"] for b in branches}
    assert len(sessions) >= 2, "independent branches should spread across workers"
    seq = {(e["event_type"], e.get("task_id")): e["scheduler_event_seq"] for e in events if e.get("job_id") == m["job_id"]}
    assert all(seq["task_succeeded", b] < seq["task_assigned", "publish"] for b in branches)
    assert all(seq["task_succeeded", "inspect"] < seq["task_assigned", b] for b in branches)
    evidence.update({"publication": publication, "branch_sessions": sorted(sessions), "job_duration_ns": snapshot["duration_ns"]})
    (system.evidence / "video-demo.json").write_text(json.dumps(evidence, indent=2))
