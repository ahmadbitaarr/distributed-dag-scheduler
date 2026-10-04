# Evidence, event schema, and history checks

This file describes how MS2 records what happened and how anyone can falsify the safety claims from saved files, without reading console output. It implements architecture §14.

## What service-backed tests export

The pytest `system` fixture runs one isolated deployment per service-backed test; pure unit tests do not start services or create these exports. Before teardown, even when the test fails, it writes the following to `results/latest-tests/<unique-run>/<test-name>/`:

| File | Contents |
|---|---|
| `events.jsonl` | The complete scheduler decision history for the run, in `scheduler_event_seq` order. The harness asserts it is gap-free while exporting. |
| `snapshots.json` | An atomic `GET /v1/jobs/{id}` snapshot of every job the test submitted. |
| `manifests.json` | The exact manifest submitted for each job. |
| `metrics.json` | Counters, state gauges, and timing summaries from `GET /v1/metrics`. |
| `evidence-boundary.json` | `scheduler_run_id` and `last_exported_event_seq`, which let a checker detect truncation. |
| `worker-N.jsonl`, `scheduler.jsonl`, `artifact-store.jsonl` | Raw process stdout and stderr: JSON events plus any diagnostics. |
| `metadata.json` | Test node ID, outcome (passed/failed/skipped), xfail flag, backend, scheduler run ID, source revision (`MS2_SOURCE_REV`, set by `deploy/harness/run.sh`, with `+uncommitted` for a dirty tree), UTC start and finish, Python/Java/platform versions, the run label, and whether export/cleanup returned successfully. |
| `compose.log` | Compose backend only: `docker compose logs` before `down`. |
| Test-specific files | For example `fault.json`, `gate.json` and `oracle-traceback.txt` for the crash test. |

Selected evidence is copied into `results/handoffs/step-XX/` and committed. `results/latest-tests/` is gitignored.

## Event schema (version 1)

Every event, from any producer, carries these base fields:

| Field | Meaning |
|---|---|
| `schema_version` | `1` |
| `scheduler_run_id` | The scheduler run the event belongs to. |
| `event_type` | One of the types below. |
| `producer` | `scheduler`, `worker`, or `harness`. |
| `producer_seq` | Strictly increasing per producer process. |
| `utc_timestamp` | Wall clock, for humans only. Never subtracted across processes. |
| `elapsed_ns` | The producer's local monotonic clock (`System.nanoTime`). It is comparable only within one process. |
| `request_id`, `job_id`, `task_id`, `attempt_no`, `worker_session_id` | Whichever apply; otherwise null. |

Scheduler decision events also carry:

- `scheduler_event_seq`: strictly increasing, gap-free, and appended in the same mutex-protected command as the state change it records;
- `old_state`/`new_state` where applicable;
- causal references.

| Event | Producer | Meaning and extra fields |
|---|---|---|
| `job_submitted` | scheduler | Acceptance committed. `state`. |
| `task_ready` | scheduler | The task entered the FIFO. `ready_seq`, `satisfied_parents`. |
| `task_assigned` | scheduler | Ownership and the attempt record installed. `ready_seq`, `ready_elapsed_ns`, `assigned_elapsed_ns`. |
| `task_retried` | scheduler | An attempt numbered above 1 was assigned. `previous_attempt_no`. |
| `task_started` | scheduler | Matching start accepted. Its sequence number is the acknowledgment the worker must receive before executing. |
| `task_failed` | scheduler | Explicit failure accepted. `error`, `report`. |
| `task_succeeded` | scheduler | The single logical success. `outputs`, `report`. |
| `dependency_satisfied` | scheduler | One parent-to-child edge satisfied. `parent_id`, `parent_success_event_seq`. |
| `job_completed` | scheduler | All tasks succeeded. `accepted_elapsed_ns`, `completed_elapsed_ns`. |
| `completion_duplicate` | scheduler | An exact replay of a finished attempt's report. `receipt_event_seq`. |
| `report_rejected` | scheduler | A start or report was rejected. `error_code`. No state change. |
| `work_claim` / `work_empty` | scheduler | Claim diagnostics that show a worker is available and polling. |
| `worker_session_started` | worker | A new session joined the scheduler run. |
| `worker_operation_started` | worker | Execution began. `ack_scheduler_event_seq` is the `task_started` sequence the worker received. |
| `worker_report_sent` | worker | The success report, with output descriptors. |
| `worker_operation_failed` | worker | A local failure or timeout. `error`. |
| `attempt_rejected` / `request_rejected` | worker | The scheduler rejected the worker's request. `status`, `code`. |
| `scheduler_run_changed` | worker | The scheduler run changed; the worker discards its assignment and starts a new session. |
| `worker_test_gate_entered` | worker | Test-only barrier inside an operation (hooks enabled only). |
| `fault_injected` | harness | Record of a deliberate kill. |

Worker and scheduler events are joined through `ack_scheduler_event_seq`, never by comparing timestamps.

## History checks

`tests/harness/api.py: check_history(manifest, snapshot, events, worker_events)` raises `HistoryViolation` with a named reason when any of the following fails. It covers all three approved safety claims:

| Invariant | Safety claim |
|---|---|
| The event sequence is gap-free and ordered. | Prerequisite: otherwise an invariant could pass vacuously. |
| A task is assigned only after every parent's `task_succeeded`. | No task runs before its dependencies. |
| A start comes only from the current owner of an assigned attempt. Every `worker_operation_started` joins to that exact acknowledged start. | No task runs before its dependencies, measured at the worker. |
| A success needs a matching SUCCESS report, the current owner, and an accepted start. | No completion without a reported success. |
| A task has at most one active owner, and nothing is assigned after its success. | Ownership. |
| A task has at most one `task_succeeded`. | No duplicate logical completion. |
| `job_completed` comes once, only after every task succeeds, with no task events after it. | Job semantics. |
| Snapshot success counts and job state agree with the history; the snapshot is not newer than the export. | Snapshot/history consistency. |

A missing event needed by an invariant (for example, a dropped `task_started`) produces a violation, not a silent pass. `tests/unit/test_history_checks.py` demonstrates each violation by mutating a real saved history.

## Re-checking saved evidence offline

```bash
python -m tests.harness.check_evidence results/handoffs/step-08/sample-history
python -m tests.harness.check_evidence results/latest-tests/<unique-run>/*/      # every test from the last run
```

The command exits non-zero if any directory falsifies an invariant, is truncated relative to its boundary file, or mixes scheduler runs. Only the Python standard library is needed.

## Harness adapter boundary

Backends implement one interface in `tests/harness/runtime.py`:

| Method | Meaning |
|---|---|
| `__enter__` | Launch the scheduler and artifact store and wait for readiness. |
| `start_worker(env)` | Launch one worker and wait for `worker_session_started`. |
| `worker_events(name)` | Collect that worker's events. |
| `worker_running(name)` | Whether that worker is alive. |
| `kill_worker(name)` | Hard kill (SIGKILL), returning the exit record. |
| `stop_artifacts()` | Stop the artifact service. |
| `__exit__` | Export evidence, then tear down. |

`NativeHarness` (local processes) and `ComposeHarness` (containers) implement it. `restart_scheduler()` is native only. The Hokea adapter (Step 11) implements the same interface. Tests never use process IDs or paths directly.

## Step 10 evidence

A run label is generated once per pytest invocation (mode, backend, UTC label,
random suffix), or supplied by `MS2_RUN_LABEL`. It is a simple directory name.
The fixture refuses an existing per-test directory. Use a fresh label for every
container invocation: the runner excludes host results from its temporary source
copy, and copy-back does not yet reject an explicitly reused host label (S10-03).
`metadata.json` records `run_label` and
`cleanup_succeeded`; a failed teardown remains an ordinary pytest error.

The crash test saves `gate.json`, `before-kill.json`, `fault.json`,
`after-kill.json`, `probe.json`, `observation-window.json`,
`surviving-worker-claims.json`, `after-window.json`,
`services-after-window.json`, `safety-checks.json`, and `oracle-traceback.txt`,
as well as the normal exports and raw worker logs. Claim evidence contains
paired scheduler `work_claim`/`work_empty` records joined by request ID.

Observation times come from the harness's monotonic clock relative to one test
origin. After at least 8 seconds, the harness reads a scheduler-sequence
boundary; a later B claim must exceed it. Worker/scheduler elapsed clocks and
wall-clock timestamps are never subtracted across processes. The actual window
and request overrun are recorded. Recovery observations after the deadline do
not count as recovery within the budget.

Both job histories are checked live and from exported files before the typed
recovery failure. The normal stuck-state checks are experiment/safety
preconditions, not a passing assertion of the required recovery property.
Retain separate native-XFAIL, Compose-XFAIL, real-failure and acceptance run
directories under `results/handoffs/step-10/`. Keep runtime/ and build outputs out
of that retained evidence. Store full commands, exit codes and the tested source
manifest alongside each run. A nonzero build or Docker startup is not the
intentional demonstration.
