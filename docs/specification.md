# Distributed DAG Task Scheduler — Revised Specification (MS2)

> **Status: DRAFT for Step 14.**
>
> - Sections marked *[PENDING Step 10/11/13]* depend on gates other teammates are completing.
> - Benchmark numbers come from the Step 12 run in `results/handoffs/step-12/`.
> - Every "Current MS2 status" entry links to the test or evidence that supports it.

This document revises the approved MS1 specification (CS4069 MS1 Specification, p. 1). The approved **intended semester claims are kept unchanged**. Each claim gains an explicit *current MS2 status*, so readers can distinguish what the prototype guarantees today from what later milestones will add. Design detail lives in [CS4094_MS2_Architecture.md](CS4094_MS2_Architecture.md). The wire contract is in [api.md](api.md), and the evidence format in [evidence.md](evidence.md).

## 1. Overview (unchanged from MS1)

We are building a fault-tolerant distributed task scheduler for a video-processing platform. Each uploaded video creates a directed acyclic graph (DAG) of tasks such as transcoding, thumbnail generation, subtitle generation, and publishing. Some tasks can run in parallel; others must wait for their dependencies.

The system has one scheduler and multiple worker nodes. The scheduler tracks dependencies and assigns ready tasks to available workers. Workers execute tasks and report completion. If a worker fails before finishing, the unfinished task can be reassigned.

We are not building a full video-sharing platform, authentication, billing, or production-quality video-processing algorithms.

**MS2 realization.** The MS2 prototype has these parts:

- One Java 21 **scheduler** that owns every job, task, attempt and completion decision under a single mutex.
- An immutable **HTTP artifact store** through which workers exchange files.
- One-slot **polling workers** that run a fixed allowlist of operations, including FFmpeg transcodes and thumbnails.
- A Java **client**.

A concrete video DAG runs end to end on a committed synthetic clip: inspect → {720p, 360p, thumbnail, fixture subtitles} → publish. "Publishing" means producing an artifact manifest. Subtitles come from a labeled fixture file; no transcription service is used.

## 2. System model

These terms follow the course's network/node/timing taxonomy (L2).

| Dimension | MS2 assumption |
|---|---|
| Network | **Fair-loss point-to-point links.** Requests and responses may be lost, delayed, duplicated or reordered. Endpoints are honest, and there is no forgery. Every mutating request carries a stable identity (job ID, claim ID, attempt identity) and is idempotent on replay. |
| Worker nodes | **Crash-recovery.** A worker may stop at any time. If it restarts, it does so as a new session with no memory of its old attempt. A permanent crash is also allowed. |
| Scheduler | A single correct process for the lifetime of a run. A scheduler restart begins a **new, empty run** with a new `scheduler_run_id`, and messages from older runs are rejected. No scheduler crash tolerance is claimed. |
| Artifact store | Correct and available during a run. Completed objects are immutable. Store crash, disk loss and corruption are outside the claims. |
| Timing | **Partially synchronous** environment. Safety never depends on timing or synchronized clocks. Progress assumes eventual delivery, fair scheduling and operations that finish within their bounds. Durations are measured only on one process's monotonic clock; cross-node ordering uses IDs and scheduler acknowledgments. |

## 3. Safety

**Intended claim (unchanged from MS1).** A task will not be marked complete unless successful completion is reported, and a task will not run before its required dependencies finish. Retried tasks will not be recorded as multiple successful completions. These claims are violated if an unfinished task is marked complete, a task runs before its dependencies, or one logical task is recorded as completed multiple times.

| Claim | Current MS2 status | Mechanism | Evidence |
|---|---|---|---|
| S1. No completion without a reported success | **Satisfied in MS2 scope** | Only a matching SUCCESS report from the current owner of a RUNNING attempt can set SUCCEEDED. All of its outputs must already be published with matching descriptors. An assignment, a start, a failure, silence, an uploaded file or a timeout cannot set it. | `SchedulerStateMachineTest`, `test_success_requires_published_correct_outputs`, `test_duplicate_conflicting_stale_reports_and_retry`; history invariant "success needs a SUCCESS report from the owner after an accepted start" |
| S2. No task runs before its dependencies finish | **Satisfied in MS2 scope** | Only READY tasks are assigned. Readiness requires every parent's accepted success. A worker executes only after the scheduler acknowledges its start. Inputs bind to accepted parent outputs. | `test_join_and_independent_branch_concurrency`, `test_worker_has_one_slot_and_starts_only_after_ack`, concurrency stress test; history invariant joining each `worker_operation_started` to its acknowledged `task_started` |
| S3. No duplicate logical completion | **Satisfied in MS2 scope** within one scheduler run | Logical identity `(job_id, task_id)` survives retries. SUCCEEDED is terminal. An exact report replay returns the stored receipt. A late success from an older or failed attempt is rejected. | `test_lost_report_ack_is_replayed_not_reexecuted`, `test_real_worker_failure_attempt_two`, `oldDuplicateFailureDoesNotDisturbNewerAttempt`, 20-job concurrency stress test |

The safety invariants are checked mechanically on every test's exported history. `python -m tests.harness.check_evidence <dir>` re-checks them offline. `tests/unit/test_history_checks.py` shows that the checker detects each violation.

Assumption: workers are honest. The scheduler checks identity, state, attempt and output integrity; it does not recompute results.

## 4. Liveness

**Intended claim (unchanged from MS1).** If workers remain available, every ready task will eventually be assigned and either complete or be retried after failure. If a worker fails while executing a task, that unfinished task will eventually become available for reassignment. This claim is violated if an unfinished task remains permanently stuck.

| Claim | Current MS2 status | Explanation | Evidence |
|---|---|---|---|
| L1. Ready tasks are eventually assigned, and complete or are retried after failure | **Partially satisfied** | The ready FIFO is fair: requeued tasks go to the tail. An explicit failure from ASSIGNED or RUNNING returns the task to READY, and it is reassigned with a higher attempt number. There is no retry cap and no terminal FAILED job. This holds while workers stay available and do not crash while holding a task; a crash after assignment can block completion (see L2). | `test_real_worker_failure_attempt_two`, `test_local_operation_timeout_is_an_explicit_bounded_failure`, `repeatedFailuresKeepIncreasingAttemptNumbersWithoutRetryCap` |
| L2. A failed worker's unfinished task eventually becomes available for reassignment | **Intentionally not satisfied in MS2** | MS2 has no lease, heartbeat, expiry scan or silent-owner release. An attempt owned by a crashed worker can leave RUNNING only through a report from that worker, which will never come. This is MS2's **single demonstrated correctness violation**. | `tests/faults/test_worker_crash.py::test_worker_crash_reassignment`: strict XFAIL limited to `RecoveryNotObserved`; `make fault-demo` shows the real failure *[PENDING Step 10 Docker gates]*. Unit-level pin: `silentOwnerKeepsTaskForeverEvenAsTimePasses`. |

L1 and L2 are overlapping consequences of the same missing mechanism. Progress is not promised during a permanent partition, while all workers are unavailable, or under unbounded overload.

## 5. Fault model

**Intended (unchanged from MS1).** The system will handle worker crashes, worker restarts, temporary worker unavailability, and delayed or lost communication. Byzantine or malicious worker behavior is outside the scope of the project. These failures will be tested by stopping workers and introducing communication problems during active jobs.

| Fault | MS2 handling | Evidence |
|---|---|---|
| Lost, delayed or duplicated messages | **Handled for safety and progress.** Stable IDs plus cached receipts make retries idempotent. A lost report acknowledgment causes a replayed report, never a second execution. | `test_lost_report_ack_is_replayed_not_reexecuted` (a fault-injecting proxy drops an accepted reply), `test_submission_and_claim_receipts` |
| Worker restart | **Safe.** A restarted worker gets a new session and cannot report for its old attempt. Recovering the old attempt is **not** implemented (L2). | `sessionHoldsOneActiveAttemptAndGetsItBackOnNewClaims`, crash oracle |
| Worker crash while holding a task | **Safe but not live.** The task stays RUNNING under the dead owner and dependents stay BLOCKED. This is the intentional MS2 defect. | `test_worker_crash_reassignment` *[PENDING Step 10 Docker gates]* |
| Stale or conflicting reports | **Rejected without a state change.** The worker abandons that attempt and keeps working. | `test_stale_report_rejection_does_not_kill_the_worker`, `rejectedCommandsLeaveStateAndEventsUnchanged` |
| Scheduler restart | **New empty run.** Old-run messages get `409 STALE_RUN`. Workers detect the change and join the new run. | `test_worker_abandons_old_run_and_joins_the_new_one` |
| Artifact store unavailable | **Transient 503**: no job is accepted and no state changes. | `test_storage_unavailable_is_transient_and_accepts_nothing` |
| Byzantine workers | Out of scope (unchanged). | — |

Planned for later milestones (MS3): communication-fault campaigns, pause/restart at every attempt boundary, and lease-based recovery.

## 6. Performance

**Intended (unchanged from MS1).** We will measure job completion time, task throughput, scheduling latency, and recovery time after worker failures. Performance will be evaluated by submitting increasing numbers of concurrent DAG-based jobs under normal operation and while intentionally introducing worker failures.

**MS2 status.** Job completion time, task throughput and scheduling latency are **measured** under normal operation. Recovery time is **not measurable in MS2**, because crashed-worker recovery does not exist. The 10 s crash-test window is a test budget, not a recovery measurement.

| Item | MS2 design |
|---|---|
| Workload | Six-task DAG: A, three parallel branches, a join, then format. 100 ms fixture operations, tiny artifacts. |
| Variables | In-flight jobs C ∈ {1, 4, 16} × one-slot workers W ∈ {1, 2, 4}: 9 configurations × 5 fresh repetitions = 45 runs. |
| Per run | 4 warmup jobs (excluded), then 24 measured jobs in a closed loop. 120 s measured-phase timeout. |
| Resources | Each service capped at 1 CPU and 512 MiB (Docker), with a 128 MiB JVM heap and 16 handler threads. |
| Metrics | Job completion time = scheduler acceptance → `job_completed`. Scheduling latency = READY → ASSIGNED. Throughput = measured logical successes ÷ (last measured completion − first measured acceptance). All are measured on the scheduler's monotonic clock. |

Results and limitations are in the MS2 progress report, §E. No numeric performance target is claimed.

## 7. Scope

| MS2 implements | Deferred (later milestones or out of scope) |
|---|---|
| DAG submission, validation and limits (128 tasks, 512 edges, 1 MiB manifest, 32 MiB artifact) | Lease, heartbeat or expiry-based recovery of crashed workers' tasks (MS3) |
| Ready FIFO, branch parallelism, joins, all-tasks-success job completion | Durable scheduler restart recovery, replication, consensus, failover |
| Attempt identities, explicit-failure retry, duplicate/stale/conflict handling | Artifact-store crash recovery and replication |
| Immutable artifact store with attempt-isolated output namespaces | Exactly-once external effects, paid transcription APIs |
| Event histories, metrics, snapshots, offline invariant checker | Authentication, UI, cancellation, priorities, retry caps or terminal job failure |
| Functional and video workloads; Compose deployment; benchmark | Performance targets; finite recovery-time measurement |
| Hokea adapter *[PENDING Step 11]* | Cluster verification is recorded honestly if access is unavailable *[PENDING Step 11]* |

## 8. MS3 extension path (not implemented)

Add scheduler-side lease deadlines on the injected monotonic clock and an expiry transition, ASSIGNED/RUNNING → READY, that marks the attempt EXPIRED. Existing owner and attempt checks already reject late results from an expired attempt, and attempt-isolated output keys already prevent overwrites.

When that lands, the strict XFAIL marker on `test_worker_crash_reassignment` is removed and the same test becomes a passing regression.
