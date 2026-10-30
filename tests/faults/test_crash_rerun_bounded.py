"""A task whose worker dies mid-execution is re-run on a live worker within a stated bound.

The instructor's draft from the MS2 feedback ("one test you should implement and pass"), kept as written
except for one MS3 adaptation: idle polls are no longer scheduler events (they grew memory without bound),
so "the survivor was told there is no work after X was assigned" is read from the scheduler's per-session
polling metric, whose last_empty_claim_elapsed_ns is on the same scheduler clock as X's assignment.

This is the bounded, stronger form of the liveness claim in docs/specification.md section 4:

    "If a worker fails while executing a task, that unfinished task will eventually become
    available for reassignment."

and of tests/faults/test_worker_crash.py::test_worker_crash_reassignment, which was MS2's strict XFAIL
(10 s observation budget, worker hung by a test hook with its timeout raised to 120 s) and passes since MS3.

Proposed guarantee (falsifiable):

    If a worker dies while executing task X and at least one other worker is alive and
    polling, the scheduler assigns a new attempt of X to a live worker within
    RERUN_BUDGET_S of the death, and X succeeds exactly once; the dead attempt's outputs
    are never accepted.

Differences from the XFAIL oracle, each of which makes the test harder to pass by accident:
  * no test hooks: X is an ordinary fixture task that happens to take 20 s under the
    normal 30 s OPERATION_TIMEOUT_MS, so the worker is genuinely mid-operation;
  * the surviving worker is already up and polling before the kill, so "no worker was
    available" cannot explain a stuck task;
  * the budget is a number the spec could commit to (60 s = 2x the operation timeout),
    not a 10 s observation window labelled as not-a-bound;
  * the job must then finish, and the end-to-end delay the death added is reported.

What is NOT checked here (needs a paused worker, not a dead one): that an expired-but-alive
worker does not complete a paid external call a second time. External side effects are out of
scope (spec section 1); the pause, partition and lost-heartbeat tests check that such a worker's
late result is never accepted.
"""
import json
import time

import pytest

from tests.harness.api import binding, check_history, manifest, request, task, wait_for

RERUN_BUDGET_S = 60          # proposed bound: 2 x OPERATION_TIMEOUT_MS (30 s) after the worker's death
TASK_RUNTIME_MS = 20_000     # X sleeps this long, so the kill lands inside the operation
SAMPLE_S = 0.5


def session_of(system, worker):
    return next(e["worker_session_id"] for e in system.worker_events(worker) if e["event_type"] == "worker_session_started")


def output_key(identity, name="value"):
    return (f"runs/{identity['scheduler_run_id']}/jobs/{identity['job_id']}/tasks/{identity['task_id']}/"
            f"attempts/{identity['attempt_no']}/{name}")


def last_empty_claim_ns(system, session):
    """Scheduler-clock time of the session's latest "no work" answer (MS3 polling metric), or -1."""
    status, metrics = request(system.scheduler, "/v1/metrics")
    assert status == 200
    return metrics["polling"].get(session, {}).get("last_empty_claim_elapsed_ns", -1)


@pytest.mark.faults
def test_dead_worker_task_rerun_within_budget(system):
    origin = time.monotonic_ns()

    def save(name, value):
        (system.evidence / name).write_text(json.dumps(value, indent=2))

    # Two ordinary workers, both polling, before any job exists.
    workers = [system.start_worker(), system.start_worker()]
    sessions = {w: session_of(system, w) for w in workers}
    assert len(set(sessions.values())) == 2

    m = manifest([task("X", value=7, delay_ms=TASK_RUNTIME_MS),
                  task("Y", "fixture_add", ["X"], {"value": binding("X")}, amount=1)])
    job = system.api.submit(m)
    running = wait_for(lambda: (s if (s := system.api.status(job))["tasks"]["X"]["state"] == "RUNNING" else None),
                       description="X acknowledged as RUNNING")
    identity = running["tasks"]["X"]["attempts"][0]["identity"]
    victim = next(w for w, s in sessions.items() if s == identity["worker_session_id"])
    survivor = next(w for w in workers if w != victim)
    wait_for(lambda: any(e["event_type"] == "worker_operation_started" and e.get("job_id") == job
                         for e in system.worker_events(victim)), description="victim's operation started")
    # Survivor is idle: the scheduler has answered one of its claims with "no work" after X was assigned.
    assigned_ns = next(e["assigned_elapsed_ns"] for e in system.api.events()
                       if e["event_type"] == "task_assigned" and e.get("job_id") == job and e.get("task_id") == "X")
    wait_for(lambda: last_empty_claim_ns(system, sessions[survivor]) > assigned_ns,
             description="survivor polling while X runs")

    fault = system.kill_worker(victim)
    killed_ns = time.monotonic_ns()
    fault.update({"victim": victim, "survivor": survivor, "x_identity": identity,
                  "kill_confirmed_elapsed_ns": killed_ns - origin})
    save("fault.json", fault)

    # Preconditions of the experiment (not the oracle): the kill landed inside attempt 1.
    after_kill = system.api.status(job)
    x = after_kill["tasks"]["X"]
    assert x["state"] == "RUNNING" and x["attempt_no"] == 1 and x["owner"] == identity["worker_session_id"], x
    assert after_kill["tasks"]["Y"]["state"] == "BLOCKED"
    assert request(system.artifacts, "/v1/objects/" + output_key(identity), method="HEAD")[0] == 404
    assert system.worker_running(survivor) and not system.worker_running(victim)

    # Observe until a new attempt of X exists on a live worker, or the budget is spent.
    deadline = killed_ns + RERUN_BUDGET_S * 1_000_000_000
    samples, rerun = [], None
    while True:
        snap = system.api.status(job)
        now = time.monotonic_ns()
        x = snap["tasks"]["X"]
        later = [a for a in x["attempts"] if a["identity"]["attempt_no"] > identity["attempt_no"]]
        samples.append({"since_kill_s": round((now - killed_ns) / 1e9, 2), "x_state": x["state"],
                        "x_attempt_no": x["attempt_no"], "x_owner": x["owner"], "y_state": snap["tasks"]["Y"]["state"],
                        "job_state": snap["state"], "survivor_alive": system.worker_running(survivor)})
        assert samples[-1]["survivor_alive"], "Surviving worker died during observation"
        if later:
            rerun = {"since_kill_s": samples[-1]["since_kill_s"], "attempt": later[0]["identity"]}
            assert later[0]["identity"]["worker_session_id"] != identity["worker_session_id"], "Re-run on the dead session"
            break
        if now >= deadline:
            break
        time.sleep(min(SAMPLE_S, max(0.0, (deadline - now) / 1e9)))

    completed = None
    if rerun is not None:
        completed = system.api.complete(job, timeout=TASK_RUNTIME_MS / 1000 + 30)
        assert system.api.get(completed["outputs"]["result"]) == b"8"
    final = system.api.status(job)
    events = system.api.events()
    worker_events = [e for w in workers for e in system.worker_events(w)]
    check_history(m, final, events, worker_events)
    successes = [e for e in events if e["event_type"] == "task_succeeded" and e.get("job_id") == job and e.get("task_id") == "X"]
    assert len(successes) <= 1, "X succeeded twice"
    assert all(e["worker_session_id"] != identity["worker_session_id"] for e in successes), "Success accepted from the dead session"
    assert request(system.artifacts, "/v1/objects/" + output_key(identity), method="HEAD")[0] == 404, "Dead attempt's output appeared"
    starts = [(e["worker_session_id"], e["attempt_no"]) for e in worker_events
              if e["event_type"] == "worker_operation_started" and e.get("job_id") == job and e.get("task_id") == "X"]
    summary = {"proposed_bound_s": RERUN_BUDGET_S, "task_runtime_ms": TASK_RUNTIME_MS,
               "operation_timeout_ms": 30000, "poll_interval_ms": 100,
               "victim_session": identity["worker_session_id"], "survivor_session": sessions[survivor],
               "rerun": rerun, "x_operation_starts": starts, "x_successes": len(successes),
               "job_completed_since_kill_s": None if completed is None else round((time.monotonic_ns() - killed_ns) / 1e9, 2),
               "final_x_state": final["tasks"]["X"]["state"], "final_x_attempt_no": final["tasks"]["X"]["attempt_no"],
               "final_y_state": final["tasks"]["Y"]["state"], "final_job_state": final["state"],
               "samples": samples}
    save("rerun-window.json", summary)
    assert rerun is not None, (f"X was not re-run within {RERUN_BUDGET_S} s of its worker's death "
                               f"(observed {samples[-1]['since_kill_s']} s): X {final['tasks']['X']['state']} attempt "
                               f"{final['tasks']['X']['attempt_no']} owner {final['tasks']['X']['owner']}, Y {final['tasks']['Y']['state']}, "
                               f"job {final['state']}; survivor {survivor} alive and polling throughout")
    assert final["state"] == "SUCCEEDED"
