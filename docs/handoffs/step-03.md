# Step 03 — Scheduler domain state machine

Status: DONE on branch ms2/step-03-scheduler-core (gate passed; not yet on main — push blocked, see OPEN_ISSUES S1-04).
Base commit: f30fe57 (Step 2). Writer: Hasanlm23123.

## Review result

`SchedulerCore`, `SchedulerState`, `MemoryStateStore` and `StateStore` were reviewed against architecture §§4, 5, 7 and 11. **No code change was needed.**

- Every command validates fully before it mutates, inside one `synchronized` store monitor.
- Success uses a two-phase pattern: `prepareReport`, then an artifact HEAD request outside the lock, then `report` re-validates. A failure accepted in between turns the success into a 409.
- Children are released, and roots enqueued, in task-ID order (TreeMap); the ready FIFO carries a monotonically increasing `ready_seq`.
- The clock is injected through `SchedulerCore(StateStore, LongSupplier)`.
- No timer, lease, expiry or silent-owner transition exists.

## Tests added: `SchedulerStateMachineTest` (12)

- **Silent owner:** the task stays RUNNING under its owner after 24 h of injected clock and 50 foreign claims. The child stays BLOCKED and the job stays RUNNING. This is the intentional MS2 defect, pinned at the unit level.
- **Rejected commands:** none of them change the snapshot, the event count, counters or gauges. Covered: success before RUNNING, wrong owner, unknown attempt, blocked task, stale run claim/submission.
- **Retries:**
  - A start after an explicit failure is stale.
  - Replaying the attempt-1 failure leaves attempt 2 running and owned, with no second requeue. A late success from attempt 1 is rejected.
  - Five alternating ASSIGNED/RUNNING failures give attempts 1–5; there is no retry cap and no terminal FAILED job.
- **Duplicates:** a duplicate success, repeated through both `prepareReport` and `report`, satisfies each edge exactly once and enqueues each child once.
- **Ordering:** roots across jobs follow FIFO with children in task-ID order, and `ready_seq` is gap-free.
- **Job completion:** a job does not succeed while a disconnected task is unfinished, and it emits exactly one `job_completed`.
- **Sessions:** a session gets its active attempt back on new claims; other sessions get other tasks.
- **Submissions:** replay returns 201, then 200, with no new events. A different manifest under the same ID gets 409.
- **Report shape:** wrong output names or extra outputs, outputs in another attempt's namespace, an error on success, outputs on failure, a missing or invalid error, an over-long message, and a bad outcome are all 400.
- **Concurrency stress:** 8 threads run 20 six-task DAGs, with a controlled first-attempt failure on C. Result: 120 successes, each `(job, task)` succeeding once, 20 `task_retried`, and every assignment after all of its parents' successes. Nothing is left active or queued.

The 8 existing `SchedulerCoreTest` tests are unchanged.

## Verification

`mvn -B verify -pl protocol,scheduler` exited 0: protocol 33 tests, scheduler 20 (8 + 12), 0 failures. See results/handoffs/step-03/mvn-verify.summary.txt.

Architecture deviations: none.

## Next

Step 4 — immutable artifact storage.
