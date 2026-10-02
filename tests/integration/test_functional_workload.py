"""Step 7: the committed functional workload produces every expected intermediate value."""
import json
from tests.harness.api import check_history, uid
from tests.harness.runtime import ROOT

WORKLOAD = ROOT / "workloads/functional"


def test_committed_functional_workload(system):
    workers = [system.start_worker() for _ in range(3)]
    expected = json.loads((WORKLOAD / "expected.json").read_text())
    jobs = []
    for _ in range(3):
        m = json.loads((WORKLOAD / "functional.json").read_text())
        m["job_id"] = uid()
        jobs.append(m)
        system.api.submit(m)
    events = None
    for m in jobs:
        snapshot = system.api.complete(m["job_id"])
        for task_id, outputs in expected["outputs"].items():
            accepted = snapshot["tasks"][task_id]["outputs"]
            assert set(accepted) == set(outputs)
            for name, content in outputs.items():
                assert system.api.get(accepted[name]).decode() == content, (task_id, name)
                assert f"/tasks/{task_id}/attempts/1/{name}" in accepted[name]["key"]
        assert system.api.get(snapshot["outputs"]["result"]).decode() == expected["final_outputs"]["result"]
        events = system.api.events()
        check_history(m, snapshot, events, [e for w in workers for e in system.worker_events(w)])
    # Every edge released exactly once per job: A->B, A->C, B->D, C->D, D->E.
    for m in jobs:
        edges = [(e["parent_id"], e["task_id"]) for e in events if e["event_type"] == "dependency_satisfied" and e["job_id"] == m["job_id"]]
        assert sorted(edges) == sorted([("A", "B"), ("A", "C"), ("B", "D"), ("C", "D"), ("D", "E")])
