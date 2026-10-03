"""Real service connectivity check, also runnable with the existing native/Compose backends."""
import json

from tests.harness.api import check_history, manifest, request, task


def test_service_exchange(system):
    health = {}
    for name, url in [("scheduler", system.scheduler), ("artifact-store", system.artifacts)]:
        status, health[name] = request(url, "/v1/health")
        assert status == 200 and health[name]["ready"] is True
    source = system.api.put(b"7", media="text/plain")
    assert request(system.artifacts, "/v1/objects/" + source["key"], method="HEAD")[0] == 200
    assert system.api.get(source) == b"7"
    worker = system.start_worker()
    session = next(e["worker_session_id"] for e in system.worker_events(worker)
                   if e["event_type"] == "worker_session_started")
    m = manifest([task("http-probe", "fixture_add", inputs={"value": {"source": source}}, amount=4)])
    result = system.api.complete(system.api.submit(m))
    assert system.api.get(result["outputs"]["result"]) == b"11"
    assert result["tasks"]["http-probe"]["attempts"][0]["identity"]["worker_session_id"] == session
    assert system.worker_running(worker)
    check_history(m, result, system.api.events(), system.worker_events(worker))
    (system.evidence / "service-exchange.json").write_text(json.dumps({
        "health": health, "input": source, "worker_session_id": session,
        "job_id": m["job_id"], "output": result["outputs"]["result"],
        "input_bytes": "7", "output_bytes": "11", "history_check": "PASS"}, indent=2))
