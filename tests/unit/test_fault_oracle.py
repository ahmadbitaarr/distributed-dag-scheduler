"""Step 10 safeguards: malformed evidence must not become the liveness XFAIL.

These small synthetic inputs are unit fixtures, not runtime milestone evidence.
"""
import copy
from types import SimpleNamespace
import pytest
from tests import conftest as fixture_module
from tests.faults.test_worker_crash import (
    RecoveryNotObserved, original_attempt_running, require_window_polling,
)


IDENTITY = {"scheduler_run_id": "run", "job_id": "job", "task_id": "X",
            "attempt_no": 1, "worker_session_id": "A"}


def snapshot():
    return {"scheduler_run_id": "run", "job_id": "job", "state": "RUNNING", "tasks": {
        "X": {"state": "RUNNING", "owner": "A", "outputs": None, "attempt_no": 1,
              "attempts": [{"identity": copy.deepcopy(IDENTITY), "state": "RUNNING",
                            "start_receipt": {"scheduler_event_seq": 3}, "report_receipt": None,
                            "report_ack": None, "finished_elapsed_ns": None}]},
        "Y": {"state": "BLOCKED", "attempts": []}}}


def test_original_attempt_validation_is_an_experiment_precondition():
    original_attempt_running(snapshot(), IDENTITY)


@pytest.mark.parametrize("damage", ["failure", "success", "retry", "owner", "child"])
def test_invalid_kill_precondition_is_an_ordinary_failure(damage):
    value = snapshot()
    x = value["tasks"]["X"]
    if damage == "failure":
        x["attempts"][0]["report_receipt"] = {"outcome": "FAILURE"}
    elif damage == "success":
        x["outputs"] = {"value": {"key": "published"}}
    elif damage == "retry":
        x["attempts"].append(copy.deepcopy(x["attempts"][0]))
    elif damage == "owner":
        x["owner"] = "B"
    else:
        value["tasks"]["Y"]["state"] = "RUNNING"
    with pytest.raises(AssertionError) as error:
        original_attempt_running(value, IDENTITY)
    assert not isinstance(error.value, RecoveryNotObserved)


def pair(sequence, request_id, session="B", run="run"):
    return [{"event_type": kind, "request_id": request_id, "worker_session_id": session,
             "scheduler_run_id": run, "scheduler_event_seq": sequence + i}
            for i, kind in enumerate(["work_claim", "work_empty"])]


def test_polling_requires_a_new_late_claim_not_a_late_replayed_receipt():
    events = pair(11, "early") + pair(21, "late")
    assert len(require_window_polling(events, "B", "run", 10, 20)) == 2
    events[-2]["scheduler_event_seq"] = 19  # empty arrived late; claim predates boundary
    with pytest.raises(AssertionError, match="fresh B claim"):
        require_window_polling(events, "B", "run", 10, 20)


@pytest.mark.parametrize("late", [[], pair(21, "wrong-worker", "A"), pair(21, "wrong-run", run="old")])
def test_early_or_unrelated_polling_cannot_hide_an_unhealthy_b(late):
    with pytest.raises(AssertionError) as error:
        require_window_polling(pair(11, "one") + pair(13, "two") + late, "B", "run", 10, 20)
    assert not isinstance(error.value, RecoveryNotObserved)


def test_missing_late_boundary_is_not_an_expected_recovery_failure():
    with pytest.raises(AssertionError, match="late polling boundary") as error:
        require_window_polling(pair(11, "one"), "B", "run", 10, None)
    assert not isinstance(error.value, RecoveryNotObserved)


def test_reused_run_directory_refuses_to_overwrite_evidence(tmp_path, monkeypatch):
    monkeypatch.setenv("MS2_EVIDENCE_DIR", str(tmp_path))
    directory = tmp_path / "old-run" / "crash"
    directory.mkdir(parents=True)
    marker = directory / "kept.txt"
    marker.write_text("previous evidence")
    request_value = SimpleNamespace(config=SimpleNamespace(_ms2_run_label="old-run"),
                                    node=SimpleNamespace(name="crash"))
    with pytest.raises(FileExistsError):
        next(fixture_module.system.__wrapped__(request_value))
    assert marker.read_text() == "previous evidence"


def test_run_label_cannot_escape_evidence_root(monkeypatch):
    monkeypatch.setenv("MS2_RUN_LABEL", "../other-run")
    with pytest.raises(pytest.UsageError):
        fixture_module.pytest_configure(SimpleNamespace(option=SimpleNamespace(runxfail=False)))
