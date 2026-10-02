# Step 08 — Evidence collection and history checks

Status: DONE on branch ms2/step-08-evidence (gate passed; not yet on main — push blocked, see S1-04).
Base commit: d40f701 (Step 7). Writer: Hasanlm23123.

## Added and changed

- **Exports** (`Api.export`, before teardown, for passing and failing tests): `manifests.json` is now exported alongside events, snapshots, metrics, the evidence boundary and raw process logs.
- **`metadata.json`** for every test (conftest): node ID, outcome, xfail flag, backend, run ID, source revision with a `+uncommitted` marker, UTC start and finish, and Python/Java/platform. `deploy/harness/run.sh` passes `MS2_SOURCE_REV`.
- **`check_history` hardened:**
  - Every violation raises `HistoryViolation` with a named reason. Previously, a missing event surfaced as a `KeyError` crash.
  - New invariants: a gap-free, ordered sequence; no assignment after a logical success; no task events after `job_completed`; `job_completed` exactly once; snapshot job state agrees with history; the snapshot is not newer than the exported history.
  - Worker operations must join to an existing acknowledged start.
- **`tests/harness/check_evidence.py`** re-checks saved directories offline. It also detects truncation against `evidence-boundary.json` and events from mixed runs.
- **`tests/unit/test_history_checks.py`** (12 tests) runs against the real committed sample history `results/handoffs/step-08/sample-history/` (3 functional jobs, 3 workers). It first shows the sample is valid, then injects one violation each:
  - a dropped `task_started`;
  - a sequence gap;
  - a duplicate logical completion;
  - a child assigned before its parent's success;
  - a success from a non-owner;
  - a success without a SUCCESS report;
  - early `job_completed`;
  - two active owners;
  - a worker operation joined to the wrong start;
  - snapshot/history disagreement;
  - a truncated export, caught by the offline checker.

  The checker names each one.
- **`docs/evidence.md`**: the exported files, the event schema (base fields, every event type, causal joins), the invariant-to-safety-claim map, offline re-check commands, and the harness adapter interface.
- `pytest.ini` now includes `tests/unit` in `testpaths`.
- Test fix: the Step 6 one-slot test now takes snapshots before reading events (idle workers keep adding poll events).

## Verification

Harness container, native backend:

`MS2_REQUIRE_XFAIL=1 pytest` gave **49 passed, 1 xfailed** (exit 0). The single XFAIL is `test_worker_crash_reassignment`.

`python -m tests.harness.check_evidence` over all 38 exported test directories reported every one OK (exit 0). That includes the crash test's stuck job plus probe: the safety invariants hold during the intentional liveness failure.

Full output: `results/handoffs/step-08/full-suite-and-offline-check.txt`.

## How a teammate falsifies the safety claims

Run `python -m tests.harness.check_evidence <evidence-dir>`. Only the standard library is needed; no running system, console reading or wall-clock comparison is involved.

Architecture deviations: none.
