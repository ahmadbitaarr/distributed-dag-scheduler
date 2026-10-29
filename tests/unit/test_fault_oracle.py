"""Step 10 safeguards, kept for MS3: malformed evidence must not pass as (or hide) a recovery verdict.

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


# Polling evidence (MS3): B's empty-claim counter read at window start, at the late boundary and at
# the end. Counters are per session, so another worker's or an old run's polls cannot be counted for B.

def test_polling_requires_a_new_late_claim():
    assert require_window_polling(0, 5, 7) == {"empty_claims_at_start": 0, "at_late_boundary": 5, "at_end": 7}
    with pytest.raises(AssertionError, match="fresh B claim"):
        require_window_polling(0, 5, 5)                    # B stopped polling before the late boundary


@pytest.mark.parametrize("counts", [(3, 3, 3), (3, 4, 4), (0, 1, 1)])
def test_early_or_absent_polling_cannot_hide_an_unhealthy_b(counts):
    with pytest.raises(AssertionError) as error:
        require_window_polling(*counts)
    assert not isinstance(error.value, RecoveryNotObserved)


def test_missing_late_boundary_is_not_an_expected_recovery_failure():
    with pytest.raises(AssertionError, match="late polling boundary") as error:
        require_window_polling(0, None, 5)
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
