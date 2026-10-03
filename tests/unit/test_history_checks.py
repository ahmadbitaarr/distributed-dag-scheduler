"""Step 8: the history checker falsifies each safety invariant on a real saved history.

The sample in results/handoffs/step-08/sample-history was exported by the harness from a
real three-job run of the committed functional workload. Each test injects one violation.
"""
import copy
import json
import shutil
import pytest
from tests.harness.api import HistoryViolation, check_history
from tests.harness.check_evidence import check_directory, load_worker_events, main
from tests.harness.runtime import ROOT

SAMPLE = ROOT / "results/handoffs/step-08/sample-history"


@pytest.fixture
def history():
    events = [json.loads(line) for line in (SAMPLE / "events.jsonl").read_text().splitlines()]
    manifests = json.loads((SAMPLE / "manifests.json").read_text())
    snapshots = json.loads((SAMPLE / "snapshots.json").read_text())
    job = next(iter(manifests))
    return {"events": events, "manifest": manifests[job], "snapshot": snapshots[job], "job": job,
            "workers": load_worker_events(SAMPLE)}


def check(h):
    check_history(h["manifest"], h["snapshot"], h["events"], h["workers"])


def resequence(events):
    for i, e in enumerate(events, 1):
        e["scheduler_event_seq"] = i
    return events


def find(h, kind, task):
    return next(i for i, e in enumerate(h["events"]) if e["event_type"] == kind and e.get("job_id") == h["job"] and e.get("task_id") == task)


def violated(h, fragment):
    with pytest.raises(HistoryViolation, match=fragment):
        check(h)


def test_sample_history_is_valid(history):
    check(history)
    assert len(check_directory(SAMPLE)) == 3


def test_missing_start_event_is_detected(history):
    # Drop task_started for D; also drop the worker event joined to it so only the scheduler gap remains.
    i = find(history, "task_started", "D")
    del history["events"][i]
    resequence(history["events"])
    history["workers"] = [w for w in history["workers"] if not (w.get("job_id") == history["job"] and w.get("task_id") == "D")]
    violated(history, "succeeded without an accepted start")


def test_sequence_gap_is_detected(history):
    del history["events"][5]
    violated(history, "gap")


def test_duplicate_logical_completion_is_detected(history):
    i = find(history, "task_succeeded", "B")
    history["events"].insert(i + 1, copy.deepcopy(history["events"][i]))   # a second accepted success for B
    resequence(history["events"])
    violated(history, "duplicate logical completion of B")


def test_child_assigned_before_parent_success_is_detected(history):
    child = history["events"].pop(find(history, "task_assigned", "D"))
    history["events"].insert(find(history, "task_succeeded", "C"), child)
    resequence(history["events"])
    violated(history, "D assigned before parents")


def test_success_from_non_owner_is_detected(history):
    i = find(history, "task_succeeded", "A")
    history["events"][i]["worker_session_id"] = "00000000-0000-4000-8000-00000000dead"
    violated(history, "success from a non-owner")


def test_success_without_success_report_is_detected(history):
    i = find(history, "task_succeeded", "E")
    history["events"][i]["report"] = {**history["events"][i]["report"], "outcome": "FAILURE"}
    violated(history, "without a matching SUCCESS report")


def test_early_job_completion_is_detected(history):
    done = history["events"].pop(next(i for i, e in enumerate(history["events"]) if e["event_type"] == "job_completed" and e["job_id"] == history["job"]))
    history["events"].insert(find(history, "task_succeeded", "E"), done)
    resequence(history["events"])
    violated(history, "job completed before")


def test_two_active_owners_are_detected(history):
    i = find(history, "task_assigned", "C")
    twin = copy.deepcopy(history["events"][i])
    twin["worker_session_id"] = "00000000-0000-4000-8000-00000000beef"
    history["events"].insert(i + 1, twin)
    resequence(history["events"])
    violated(history, "two active owners")


def test_worker_operation_without_matching_ack_is_detected(history):
    op = next(w for w in history["workers"] if w["event_type"] == "worker_operation_started" and w["job_id"] == history["job"] and w["task_id"] == "B")
    op["ack_scheduler_event_seq"] = history["events"][find(history, "task_started", "C")]["scheduler_event_seq"]
    violated(history, "joined to the wrong scheduler start")


def test_snapshot_disagreeing_with_history_is_detected(history):
    history["snapshot"] = {**history["snapshot"], "state": "RUNNING"}
    violated(history, "snapshot job state disagrees")


def test_offline_checker_detects_truncated_export(tmp_path):
    target = tmp_path / "evidence"
    shutil.copytree(SAMPLE, target)
    lines = (target / "events.jsonl").read_text().splitlines()
    (target / "events.jsonl").write_text("\n".join(lines[:-3]) + "\n")
    assert main([str(SAMPLE)]) == 0
    assert main([str(target)]) == 1


def older_snapshot(history, before_task):
    """The job's snapshot as it was just before `before_task` succeeded (a still-running job)."""
    cut = history["events"][find(history, "task_succeeded", before_task)]["scheduler_event_seq"] - 1
    later = {e["task_id"] for e in history["events"] if e.get("job_id") == history["job"]
             and e["event_type"] == "task_succeeded" and e["scheduler_event_seq"] > cut}
    snapshot = copy.deepcopy(history["snapshot"])
    snapshot.update({"state": "RUNNING", "snapshot_event_seq": cut})
    for name in later:
        snapshot["tasks"][name]["state"] = "RUNNING"
    return snapshot


def test_snapshot_older_than_history_is_consistent(history):
    # Step 12 regression: a censored benchmark run snapshotted a running job, then read history that
    # already contained a later success. That is consistent and must not be reported as a violation.
    history["snapshot"] = older_snapshot(history, "E")
    check(history)


def test_older_snapshot_still_detects_a_missing_covered_success(history):
    snapshot = older_snapshot(history, "E")
    snapshot["tasks"]["D"]["state"] = "RUNNING"          # D's success is inside the covered prefix
    history["snapshot"] = snapshot
    violated(history, "snapshot successes disagree")
