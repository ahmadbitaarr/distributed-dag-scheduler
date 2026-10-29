# CS4094 MS3 Progress Report: Distributed DAG Task Scheduler

Specification: [specification.md](specification.md). Test-to-property table: [test-matrix.md](test-matrix.md). Run logs: [results/ms3-logs/](../results/ms3-logs/). The MS2 report is kept unchanged as [ms2-progress-report.md](ms2-progress-report.md).

## A. Status of every claim

| Claim (spec §) | MS2 | MS3 | Evidence |
|---|---|---|---|
| S1 No completion without a reported success (§3) | Held | **Holds**, now including late successes from expired attempts | `LeaseTest`, lost-heartbeat, pause, partition, restart tests; `check_history` on every test |
| S2 No task before its dependencies (§3) | Held | **Holds** | ordering tests; `check_history` joins every worker start to its acknowledgment |
| S3 No duplicate completion (§3) | Held | **Holds** under crash, pause, loss, duplication and partition | duplicate/lost-reply tests, chaos run, 8-thread JUnit races |
| L1 Ready tasks make progress (§4) | Partial | **Holds**, including slow tasks longer than the lease | slow-task and short-partition tests, all workload tests |
| L2 A failed worker's task is reassigned (§4) | **Intentionally broken** | **Holds** | MS2's crash oracle now passes; crash at three attempt stages, restart, pause, partition, lost heartbeats |
| Fault model (§5) | Crash only, safe but stuck | Crash, restart, pause, message loss/delay/duplication, partitions all tested | 14 fault tests |
| Performance (§6) | 3 of 4 metrics | **All 4**, including recovery time, with and without failures | `make bench-recovery` (§E) |

The submitted run is `results/ms3-logs/make-test-2.log` (source `fdf5d02`): `mvn -B verify` passed all 76 JUnit tests, then pytest reported **102 passed, 0 failed, 0 expected failures** (exit 0). Its JUnit XML is `results/ms3-logs/junit-make-test-2.xml`, and the per-test evidence (52 directories) is in `results/ms3-logs/evidence-make-test-2/`. Re-checking every one of its 52 job histories offline found no violations. An earlier full run (`make-test-1.log`) failed one test, which still expected MS2's exact metrics counter list; the test was updated for the two new lease counters, and nothing else changed.

## B. What changed since MS2

**Leases (scheduler).** Every attempt is now owned through a lease on the scheduler's monotonic clock (`LEASE_TIMEOUT_MS`, default 5 s). Assignment grants it; the start acknowledgment and a new endpoint, `POST /v1/attempts/heartbeat`, renew it. When the deadline passes, the attempt becomes `EXPIRED`, its owner is released, a `lease_expired` event is recorded, and the task rejoins the end of the ready queue. Expiry is applied at the start of every claim, start, heartbeat and report, and by a background scan every 100 ms. Every later message from an expired attempt, including a replayed start, gets `409 LEASE_EXPIRED` and changes nothing. Under 100 lines changed in `SchedulerCore`; the happy path is unchanged.

**Heartbeats (worker).** While a worker holds an attempt, a background thread renews the lease every `lease/5` (read from `/v1/health`). A `409` on renewal cancels the running operation, and the worker drops the attempt without uploading or reporting. Workers also gained test-only stall points before start, during the operation and before the report.

**Test harness.** A per-worker fault proxy (`tests/harness/netfault.py`) can drop requests or replies, delay, duplicate, or partition one worker's link and logs every action; the harness can pause and resume workers (SIGSTOP/SIGCONT, `docker pause` on Compose). The history checker now also rejects expiry of a non-owner and any success from an expired attempt.

**Tests.** 16 deterministic lease tests in JUnit (an injected clock, no sleeps), 13 new fault-injection tests, and 2 new checker-falsification tests. MS2's intentional failing oracle, `test_worker_crash_reassignment`, now passes and additionally checks the recovery path and its time bound. `make test` now requires zero expected failures.

**Benchmark.** `benchmarks/recovery.py` (`make bench-recovery`) measures recovery time by killing busy workers mid-run, against a fault-free baseline of the same code.

**Docs.** The specification's claims are sharpened (§9 of the spec), the API and evidence docs cover leases, and the test-to-property matrix is new.

**Defect found and fixed during MS3.** A *replayed* start for an attempt that had already expired returned its cached acknowledgment. That was safe, since the worker's heartbeat and report would then be rejected, but it broke the rule that every message from an expired attempt is refused. The restart test caught it, and a JUnit assertion now covers it.

## C. Design choices and trade-offs

**Leases instead of a failure detector.** The scheduler cannot tell a slow worker from a dead one, so it does not try to. It only knows that it has not heard a renewal within the lease. Using leases means all timing lives on one clock (the scheduler's), so no clocks have to agree, and the existing pull model is kept: the scheduler still never contacts workers.

**Attempt numbers as fencing tokens.** A requeued task's next attempt has a higher attempt number. Every start, heartbeat and report names its attempt, and the scheduler accepts only the current, unexpired one. Outputs are written under an attempt-specific key, so a late worker cannot overwrite a newer attempt's files either. This fences everything the scheduler controls; it would not fence an external side effect such as a paid API call, which is out of scope.

**Lease length 5 s, renewal every 1 s.** Recovery time is roughly the lease, so a shorter lease recovers faster but expires live workers on slow links more often. With five renewals per lease, up to three consecutive heartbeats can always be lost without expiring a live worker; a fourth may cause expiry. A false expiry costs repeated work, never correctness, so we chose a lease that keeps false expiries rare on our hosts rather than the fastest recovery.

**Expiry before every decision, plus a scan.** If expiry happened only in a background scan, whether a late report is accepted would depend on scan timing. Checking deadlines at the start of every command makes the rule exact: after the deadline, the attempt is dead. The scan exists only so that an orphaned task is requeued even when no worker happens to claim.

**A late success is rejected even if nobody took the task.** A simpler alternative was to accept a success that arrives after the deadline when no other worker has claimed the task. We rejected it: one rule ("expired means dead") is easier to reason about and to test, and the cost is a re-run in a rare race.

**Workers do not fence themselves.** A worker that cannot reach the scheduler keeps working and lets the scheduler decide. Self-fencing would save some wasted work, but it would need the worker to estimate the scheduler's lease on its own clock, and safety does not need it.

**Still one in-memory scheduler.** Making the scheduler durable or replicated is a separate, large problem (a write-ahead log or consensus). The approved fault model is about workers, so we kept the scheduler out of scope and state plainly what a scheduler restart loses.

## D. Testing

`make test` runs the whole suite in a pinned Linux container: 76 JUnit tests, then the pytest suites against real scheduler, artifact-store and worker processes. Every service-backed test exports the scheduler's full event history, worker logs and snapshots and runs the safety checker on them, so S1–S3 are checked in every test, not only in the ones aimed at them. The test-to-property table is in [test-matrix.md](test-matrix.md).

Faults are injected with SIGKILL, SIGSTOP/SIGCONT, worker stall points, and a per-link proxy that logs every dropped, delayed or duplicated message (`proxy-worker-N.jsonl` in each test's evidence). Timing assertions use only the scheduler's clock, never differences between processes.

Key results from the submitted run (`make-test-2`):

- Leases expired 10 times across the fault tests, once for every injected crash, freeze, partition or heartbeat loss that outlasted the lease, and never in a fault-free test or in the slow-task and short-partition tests.
- Detection took 5.01–5.12 s from the last accepted renewal, never less than the 5 s lease.
- Recovery (last renewal → new owner) took 5.04–5.12 s when an idle worker was polling, and 6.04–6.06 s in the chaos run, where the recovered tasks waited behind queued work.
- In every one of those tests, the late worker's messages were rejected or abandoned, exactly one success per task was recorded, and the job finished with the correct output.

**Do the tests test anything?** For the lease logic we broke the code on purpose and checked that the tests failed. Stopping heartbeats from renewing the lease failed 2 lease tests. Skipping the expiry check before reports failed 2 others. The history checker's tests each inject one violation into a real saved history and require the checker to report it.

## E. Performance

PERF_PLACEHOLDER

## F. Deployment

`make up` starts the scheduler, the artifact store and three workers under Docker Compose (1 CPU and 512 MiB each, no automatic restarts), and `make demo` runs the functional and video workloads against them. The Hokea adapter for the course cluster from MS2 is unchanged except that it now packages the fault proxy and expects zero expected failures. As in MS2, the course runner's Hokea version did not match the pinned one, so a cluster run is still unverified.

## G. Limitations and known risks

- **The scheduler is a single point of failure.** Its state is in memory; a restart starts an empty run and in-flight jobs must be resubmitted.
- **A paused scheduler expires live leases.** If the scheduler process itself is frozen for longer than the lease, every lease looks overdue when it resumes, and live workers' attempts are expired and redone. Safety holds; work is repeated.
- **At-least-once execution.** A task can run more than once (after an expiry, or a lost reply that a crashed worker never retried); only one result is accepted. External side effects would need their own idempotency.
- **No retry limit.** An operation that always fails is retried forever and its job stays RUNNING.
- **Network faults are injected only on the worker↔scheduler link,** and only with the native backend. The artifact store is assumed available.
- **The artifact store's index is not rebuilt** after the store restarts, although its files stay on disk.
- **Workers are trusted;** results are not recomputed.
- **Performance numbers come from one shared Windows laptop** with a synthetic workload (§E).

## H. Next steps (MS4–MS5)

Respond to the red team's findings and the plot twist. Candidates we already know about: an optional retry limit with a terminal FAILED job state, scheduler durability through a write-ahead log, and running the fault suites on the Compose and Hokea backends.
