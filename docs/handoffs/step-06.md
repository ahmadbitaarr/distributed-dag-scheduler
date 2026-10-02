# Step 06 — Worker, Java client, and real end-to-end execution

Status: DONE on branch ms2/step-06-worker (gate passed; not yet on main — push blocked, see S1-04).
Base commit: d72b887 (Step 5). Writer: Hasanlm23123.

## Fix

`WorkerMain` used to rethrow every `ApiException` (any 4xx) out of its main loop, so the worker **process exited**. A stale or conflicting report rejection, which architecture §6 says should only end that attempt, therefore killed the worker.

The worker now handles rejections as follows:

- During an attempt, it records `attempt_rejected` (identity, status, code), keeps its slot, and claims again.
- Outside an attempt, it records `request_rejected` and backs off by the poll interval.

A mutation check confirmed the new test fails on the old code.

## Harness

- `restart_scheduler()` (native backend) starts a new scheduler run at the same address.
- `deploy/harness/in-container.sh` runs the suite on a container-local copy and copies evidence back. The `run.sh` default is now package plus the full suite with `MS2_REQUIRE_XFAIL=1`.

## Tests added: `tests/integration/test_worker_client.py` (7)

- **Java client:** `upload` (descriptor, media type, bytes), `submit` (201, then an idempotent replay), `status`, and `fetch` of the real output `result=22\n`. Includes the history check.
- **One slot, start after ack:** across 2 workers and 3 functional jobs, the per-session event order shows no second assignment and no claim while an attempt is active. There are exactly 15 operation starts for 15 logical tasks, each joined to its scheduler start acknowledgment.
- **Hooks off by default:** `TEST_FAIL_FIRST_TASK` and `TEST_GATE_TASK` without `ENABLE_TEST_HOOKS` have no effect.
- **Operation timeout:** a local timeout produces a bounded, explicit failure (`OPERATION_TIMEOUT`, `OPERATION_TIMEOUT_MS=300`). Attempt numbers increase, the job stays RUNNING (no retry cap), and the worker stays alive.
- **Stale rejection:** an injected failure is accepted while the worker is still executing. The worker's late success gets 409, the worker survives, and it runs attempt 2 to success.
- **Lost acknowledgment** (native only): a fault-injecting proxy delivers the first success report but drops its reply. The worker replays the identical report and gets the cached ack (`completion_duplicate` refers to the original receipt). The operation runs exactly once, and there is one logical success.
- **New run** (native only): the scheduler restarts mid-attempt. The worker records `scheduler_run_changed`, starts a new session in the new run, and executes new work. The old run's claim gets `STALE_RUN`. Its late report appears only as a `report_rejected` diagnostic.

## Verification

- Native (harness container): 7/7 passed.
- Compose (real images and containers): 7 passed and 2 skipped (native-only) across `test_system` and `test_worker_client` subsets.

See `results/handoffs/step-06/pytest.summary.txt`.

Architecture deviations: none. Workers still hold no dependency state, have no production coordination API, and do not recover tasks.
