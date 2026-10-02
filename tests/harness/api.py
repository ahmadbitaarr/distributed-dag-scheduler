"""Standard-library client: assertions remain outside deployment adapters."""
import hashlib
import json
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path


def uid():
    return str(uuid.uuid4())


def request(base, path, body=None, method=None, headers=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(base + path, data=data, method=method or ("POST" if body is not None else "GET"),
                                 headers={"Content-Type": "application/json", **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=6) as response:
            raw = response.read()
            return response.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as error:
        raw = error.read()
        return error.code, json.loads(raw) if raw else None


def wait_for(predicate, timeout=20, description="condition"):
    deadline = time.monotonic() + timeout
    while True:
        result = predicate()
        if result:
            return result
        if time.monotonic() >= deadline:
            raise AssertionError(f"Timed out waiting for {description}")
        time.sleep(0.025)


def task(name, operation="fixture_write", parents=(), inputs=None, **parameters):
    outputs = {"fixture_format": "text", "video_inspect": "metadata", "video_transcode": "video",
               "video_thumbnail": "image", "fixture_subtitles": "subtitles", "video_publish": "manifest"}
    if operation == "fixture_write" and "value" not in parameters:
        parameters["value"] = 3
    return {"task_id": name, "operation": operation, "parameters": parameters,
            "parents": list(parents), "inputs": inputs or {}, "outputs": [outputs.get(operation, "value")]}


def binding(parent, output="value"):
    return {"task_id": parent, "output_name": output}


def manifest(tasks, final_task=None, output="value"):
    return {"schema_version": 1, "job_id": uid(), "tasks": tasks,
            "final_outputs": {"result": binding(final_task or tasks[-1]["task_id"], output)}}


def functional(delay=100):
    return manifest([
        task("A", value=3, delay_ms=delay),
        task("B", "fixture_add", ["A"], {"value": binding("A")}, amount=4, delay_ms=delay),
        task("C", "fixture_multiply", ["A"], {"value": binding("A")}, amount=5, delay_ms=delay),
        task("D", "fixture_sum", ["B", "C"], {"left": binding("B"), "right": binding("C")}, delay_ms=delay),
        task("E", "fixture_format", ["D"], {"value": binding("D")}, delay_ms=delay),
    ], output="text")


def benchmark_manifest():
    ts = [task("A", value=1, delay_ms=100)]
    for name, amount in zip("BCD", [1, 2, 3]):
        ts.append(task(name, "fixture_add", ["A"], {"value": binding("A")}, amount=amount, delay_ms=100))
    ts += [task("E", "fixture_sum", list("BCD"), {n: binding(n) for n in "BCD"}, delay_ms=100),
           task("F", "fixture_format", ["E"], {"value": binding("E")}, delay_ms=100)]
    return manifest(ts, output="text")


def video_manifest(video, subtitles):
    source = {"video": {"source": video}}
    return manifest([
        task("inspect", "video_inspect", inputs=source),
        task("transcode720", "video_transcode", ["inspect"], source, height=720),
        task("transcode360", "video_transcode", ["inspect"], source, height=360),
        task("thumbnail", "video_thumbnail", ["inspect"], source),
        task("subtitles", "fixture_subtitles", ["inspect"], {"srt": {"source": subtitles}}),
        task("publish", "video_publish", ["transcode720", "transcode360", "thumbnail", "subtitles"], {
            "video720": binding("transcode720", "video"), "video360": binding("transcode360", "video"),
            "image": binding("thumbnail", "image"), "subtitles": binding("subtitles", "subtitles")}),
    ], output="manifest")


class Api:
    def __init__(self, scheduler, artifacts):
        self.scheduler, self.artifacts = scheduler, artifacts
        status, data = request(scheduler, "/v1/health")
        assert status == 200, data
        self.run_id = data["scheduler_run_id"]
        self.job_ids = []

    def submit(self, value):
        status, data = request(self.scheduler, "/v1/jobs", {"scheduler_run_id": self.run_id, "manifest": value})
        assert status in (200, 201), (status, data)
        if value["job_id"] not in self.job_ids:
            self.job_ids.append(value["job_id"])
        return value["job_id"]

    def status(self, job):
        status, data = request(self.scheduler, f"/v1/jobs/{job}")
        assert status == 200, data
        assert data["scheduler_run_id"] == self.run_id
        return data

    def complete(self, job, timeout=30):
        return wait_for(lambda: (s if (s := self.status(job))["state"] == "SUCCEEDED" else None), timeout, f"job {job} success")

    def events(self):
        events, cursor = [], 0
        while True:
            status, page = request(self.scheduler, f"/v1/events?after={cursor}&limit=1000")
            assert status == 200 and page["scheduler_run_id"] == self.run_id
            events.extend(page["events"])
            cursor = page["next_after"]
            if not page["has_more"]:
                break
        assert [e["scheduler_event_seq"] for e in events] == list(range(1, cursor + 1)), "Event loss"
        return events

    def claim(self, session=None, claim_id=None):
        body = {"scheduler_run_id": self.run_id, "worker_session_id": session or uid(), "claim_id": claim_id or uid()}
        return request(self.scheduler, "/v1/work/claim", body)

    def start(self, assignment):
        return request(self.scheduler, "/v1/attempts/start", assignment["identity"])

    def put(self, content, key=None, media="application/json"):
        content = content.encode() if isinstance(content, str) else content
        key = key or f"inputs/{uid()}/input"
        descriptor = {"key": key, "length": len(content), "sha256": hashlib.sha256(content).hexdigest(), "media_type": media}
        req = urllib.request.Request(self.artifacts + "/v1/objects/" + key, content, method="PUT",
                                     headers={"X-Content-SHA256": descriptor["sha256"], "Content-Type": media})
        with urllib.request.urlopen(req, timeout=6) as response:
            assert response.status in (200, 201)
            return json.load(response)

    def get(self, descriptor):
        with urllib.request.urlopen(self.artifacts + "/v1/objects/" + descriptor["key"], timeout=6) as response:
            content = response.read()
        assert len(content) == descriptor["length"]
        assert hashlib.sha256(content).hexdigest() == descriptor["sha256"]
        return content

    def report(self, assignment, outcome="SUCCESS", outputs=None):
        body = {"identity": assignment["identity"], "outcome": outcome,
                "outputs": outputs or {}, "error": {"code": "TEST_FAILURE", "message": "Controlled failure"} if outcome == "FAILURE" else None}
        return request(self.scheduler, "/v1/attempts/report", body)

    def export(self, directory):
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        snapshots = {job: self.status(job) for job in self.job_ids}
        events = self.events()
        assert all(s["snapshot_event_seq"] <= len(events) for s in snapshots.values())
        (directory / "snapshots.json").write_text(json.dumps(snapshots, indent=2))
        (directory / "events.jsonl").write_text("".join(json.dumps(e) + "\n" for e in events))
        status, metrics = request(self.scheduler, "/v1/metrics")
        assert status == 200
        (directory / "metrics.json").write_text(json.dumps(metrics, indent=2))
        (directory / "evidence-boundary.json").write_text(json.dumps({"scheduler_run_id": self.run_id, "last_exported_event_seq": len(events)}))
        return snapshots, events


def check_history(manifest_value, snapshot, events, worker_events=()):
    """Check decision order and worker start acknowledgments, never cross-node clocks."""
    events = [e for e in events if e.get("job_id") == manifest_value["job_id"]]
    successes = {}
    started = {}
    assigned = {}
    definitions = {t["task_id"]: t for t in manifest_value["tasks"]}
    owners = {}
    for e in events:
        name, kind = e.get("task_id"), e["event_type"]
        if kind == "task_assigned":
            assert name not in owners, "Two active owners"
            assert all(p in successes for p in definitions[name]["parents"]), "Dependency assigned too early"
            owners[name] = (e["attempt_no"], e["worker_session_id"])
            assigned[(name, e["attempt_no"])] = e["scheduler_event_seq"]
        if kind == "task_started":
            assert owners[name] == (e["attempt_no"], e["worker_session_id"])
            assert (name, e["attempt_no"]) in assigned
            started[e["scheduler_event_seq"]] = (name, e["attempt_no"], e["worker_session_id"])
        if kind == "task_failed":
            assert owners.pop(name) == (e["attempt_no"], e["worker_session_id"])
        if kind == "task_succeeded":
            assert name not in successes, "Duplicate logical completion"
            assert owners.pop(name) == (e["attempt_no"], e["worker_session_id"])
            report = e["report"]
            assert report["outcome"] == "SUCCESS" and report["identity"]["attempt_no"] == e["attempt_no"]
            assert (name, e["attempt_no"], e["worker_session_id"]) in started.values()
            successes[name] = e["scheduler_event_seq"]
        if kind == "job_completed":
            assert set(successes) == set(definitions)
    for e in worker_events:
        if e.get("job_id") == manifest_value["job_id"] and e["event_type"] == "worker_operation_started":
            assert started[e["ack_scheduler_event_seq"]] == (e["task_id"], e["attempt_no"], e["worker_session_id"])
    assert sum(t["state"] == "SUCCEEDED" for t in snapshot["tasks"].values()) == len(successes)
