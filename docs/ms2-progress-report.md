# CS4094 MS2 Progress Report — Distributed DAG Task Scheduler

> **Status: DRAFT (Step 14), not final.**
>
> - Steps 10, 11 and 12 results are filled in.
> - The only remaining marker is *[PENDING Step 13]*, the independent clean-checkout verification.
> - Do not submit until it is resolved.
> - Every number in this report comes from committed evidence under `results/handoffs/`.

Revised specification: [specification.md](specification.md). Architecture: [CS4094_MS2_Architecture.md](CS4094_MS2_Architecture.md). Roadmap and step records: [implementation-roadmap.md](implementation-roadmap.md), `docs/handoffs/`.

## A. Implemented capabilities

All planned MS2 functionality works on the happy path.

| Capability | Where |
|---|---|
| Versioned JSON/HTTP API (§6) with strict typed parsing, structured errors and limits | `protocol/`, `scheduler/`, [api.md](api.md) |
| DAG validation: cycles, unknown or self/duplicate parents, bindings, operation allowlist; 128 tasks / 512 edges / 1 MiB / 32 MiB | `ManifestValidator` |
| Atomic scheduler state machine under one mutex: ready FIFO, ownership, attempts, receipts, joins, all-tasks job completion | `SchedulerCore`, `MemoryStateStore` |
| Explicit-failure retry with increasing attempt numbers; idempotent replay of submissions, claims, starts and reports; stale/conflicting rejection | same |
| Immutable HTTP artifact store: staged, length- and hash-verified, never partially visible, conflict on different bytes | `artifact-store/` |
| One-slot polling worker: start acknowledged before execution, bounded allowlisted operations (fixtures, ffprobe, FFmpeg 720p/360p, thumbnail), timeouts, survives rejections, follows scheduler-run changes | `worker/` |
| Java client: upload, submit, status, fetch | `client/` |
| Functional workload (A=3 → 7 / 15 → 22 → `result=22`) and the concrete video pipeline on a byte-reproducible synthetic clip | `workloads/` |
| Event histories, metrics, atomic snapshots, per-test metadata, offline safety-invariant checker | `tests/harness/`, [evidence.md](evidence.md) |
| Docker images, Compose deployment (1 CPU / 512 MiB caps, `restart: no`), Linux harness container, `make build / up / demo / test / fault-demo / bench / down` | `deploy/`, `Makefile` |

## B. Repository structure

| Path | Contents |
|---|---|
| `protocol/`, `scheduler/`, `artifact-store/`, `worker/`, `client/` | Java 21 Maven modules; each service produces `<module>/target/<module>-0.2.0.jar` |
| `tests/unit`, `tests/integration`, `tests/faults`, `tests/harness` | pytest suites, the harness adapters (native, Compose), the history checker and the demo driver |
| `benchmarks/run.py` | The approved C × W × 5 benchmark driver |
| `deploy/compose`, `deploy/harness`, `*/Dockerfile` | Deployment and the test container |
| `workloads/functional`, `workloads/video` | Committed workloads with expected outputs, checksums and provenance |
| `docs/` | Architecture, roadmap, specification, API, evidence schema, this report, progress, handoffs, open issues |
| `results/handoffs/step-XX/` | Committed verification evidence for each roadmap step |

## C. Tests and results

| Suite | Count | Latest result | Evidence |
|---|---|---|---|
| JUnit: wire contract, state machine, artifact store over real HTTP | 61 | 61 passed (`mvn -B verify`, exit 0) | `results/handoffs/step-09/make-test-gate.txt` |
| pytest unit: history checker falsification | 12 | passed | same |
| pytest integration: API, worker/client, functional, replay/retry, video | 37 at Step 9 | passed | same |
| Fault oracle: worker-crash reassignment | 1 | **xfailed**, as required (strict, limited to `RecoveryNotObserved`) | same |
| Whole suite with `MS2_REQUIRE_XFAIL=1` | — | 49 passed + 1 xfailed (Step 9). `make test`: 62 passed + 1 xfailed (Step 10, Docker host). 84 passed + 1 xfailed (Step 11). **86 passed + 1 xfailed** (Step 12, after the checker fix). All exit 0. | step-09, step-10, step-11, step-12 |
| Offline invariant re-check of all exported histories | 38 test directories | all OK | `results/handoffs/step-08/` |

Defects found and fixed during verification. A mutation check confirmed each new test fails on the old code.

1. An incomplete manifest binding caused a `NullPointerException`, returned as **503** instead of 400.
2. Artifact keys accepted non-canonical UUIDs.
3. An artifact replay with a different media type was silently accepted.
4. **A worker process exited** whenever any request was rejected, for example a stale report.
5. *(Step 12)* The history checker reported a **false violation** when it compared a still-running job's snapshot with a later, longer event history. It now compares a snapshot only with the history prefix it covers (`snapshot_event_seq`). Regression tests were added.
6. *(Step 12)* A Hokea unit test wrote its fixture with text-mode line endings and failed on Windows only. It now writes bytes.

Docker-host gates (Step 10, external evidence `results/handoffs/step-10/external-9064f75356bf492aa6dd3189c72dc88c/checks/`):

| Gate | Result |
|---|---|
| `make test` | 62 passed + 1 xfailed, exit 0 |
| Compose backend, strict oracle | 1 xfailed, exit 0 |
| `make fault-demo` | 1 failed with `RecoveryNotObserved`, exit 2: the intended nonzero result |

## D. Intentional correctness violation

**Property:** an unfinished task owned by a failed worker eventually becomes available for reassignment (MS1 liveness, claim L2).

**Why this one:** it postpones the substantial MS3 problem of telling silence apart from failure and expiring ownership safely, while leaving all three safety claims intact.

**Test:** `tests/faults/test_worker_crash.py::test_worker_crash_reassignment`.

1. Start the scheduler, the store and worker A, then submit job X → Y.
2. Wait for A's structured test gate inside X. This happens after the scheduler-acknowledged start and before any output exists.
3. Hard-kill A (SIGKILL) and confirm it exited.
4. Start healthy worker B. It completes an independent probe job and keeps polling, which shows workers are available and the system is live.
5. Observe for 10 s.
6. The oracle requires X to be reassigned to B with a higher attempt number. In MS2, X stays RUNNING under dead A, Y stays BLOCKED, and the job stays RUNNING.

Safety is asserted alongside: no false success, Y never starts early, and X has at most one success.

**Structural cause:** the only transitions out of an owned ASSIGNED or RUNNING attempt need a report from its owner. MS2 has no lease, expiry or silent-owner release, so B's claims cannot free A's task.

**How it is reported:**

- `make test` runs the oracle as one strict XFAIL that accepts only `RecoveryNotObserved`. Setup, process-control, probe or safety failures fail normally, and an XPASS fails the run.
- `make fault-demo` runs it with `--runxfail` and exits nonzero with the real assertion traceback.

The 10 s window is a controlled test budget, not a liveness bound or a recovery-time measurement.

**Results (Step 10, Docker host):**

- `make test`: 62 passed + 1 xfailed, exit 0.
- Compose backend: the strict oracle xfailed, exit 0.
- `make fault-demo`: exit 2, with exactly one failure: `RecoveryNotObserved: Expected X to be reassigned to healthy worker B with attempt_no > 1 within the controlled 10 s window; X remains RUNNING under killed worker A, Y BLOCKED…`.

In every crash run, the history checks pass (no false success, no early start, at most one success). Evidence: `results/handoffs/step-10/`.

## E. Performance characterization (Step 12)

All **45/45 runs completed**: C ∈ {1, 4, 16} in-flight jobs × W ∈ {1, 2, 4} one-slot workers × 5 fresh repetitions. There were no censored or error runs.

That covers 1,080 measured jobs and 6,480 measured logical tasks. Every run produced 24/24 correct outputs, and its peak in-flight count equalled C.

Each repetition used a fresh Compose deployment with every service capped at 1 CPU / 512 MiB and a 128 MiB heap. It ran 4 excluded warmup jobs, then 24 measured six-task jobs (100 ms fixture operations), with a 120 s measured-phase timeout.

All metrics use the scheduler's monotonic clock:

- **Job time:** acceptance → `job_completed`.
- **Scheduling latency:** READY → ASSIGNED.
- **Throughput:** logical successes ÷ the measured batch interval.

Percentiles are nearest-rank, pooled over complete runs. Throughput is reported as the mean (sample sd) of the 5 run-level values. Full method, environment and raw data: [handoffs/step-12.md](handoffs/step-12.md) and `results/handoffs/step-12/full-20261003c/` (`RESULTS.md` is regenerated from the raw CSVs).

| C | W | job p50 / p95 ms | scheduling p50 / p95 ms | throughput tasks/s, mean (sd) |
|---|---|---|---|---|
| 1 | 1 | 1,398 / 1,454 | 5.7 / 450 | 4.20 (0.02) |
| 1 | 2 | 1,149 / 1,202 | 4.4 / 228 | 5.09 (0.06) |
| 1 | 4 | 961 / 1,027 | 4.9 / 80 | 6.04 (0.10) |
| 4 | 1 | 5,435 / 5,543 | 1,107 / 2,251 | 4.34 (0.01) |
| 4 | 2 | 2,800 / 2,921 | 459 / 1,133 | 8.31 (0.04) |
| 4 | 4 | 1,488 / 1,570 | 82 / 469 | 15.36 (0.04) |
| 16 | 1 | 19,561 / 21,889 | 3,934 / 9,731 | 4.35 (0.06) |
| 16 | 2 | 9,951 / 11,122 | 1,881 / 4,785 | 8.56 (0.03) |
| 16 | 4 | 5,151 / 5,718 | 834 / 2,329 | 16.69 (0.28) |

**Observed bottlenecks.**

1. **Throughput is bounded by worker capacity**, about 4.2 tasks/s per one-slot worker. With C ≥ 4 it scales near-linearly in W: 4.3 → 8.3–8.6 → 15.4–16.7.
2. **At C=1, the DAG's width (3 parallel branches) limits parallelism**, so W=2 and W=4 give only 5.1 and 6.0 tasks/s.
3. **The scheduler is not the bottleneck at this scale.**
   - With an idle worker, median READY→ASSIGNED is 4–6 ms.
   - Larger scheduling latencies are queueing for busy workers, growing with C/W.
   - Median execution time (RUNNING→SUCCEEDED) stays at 172–188 ms from C=1 to C=16.
4. **Per task, a worker spends** about 100 ms on the operation, 75–90 ms on HTTP artifact transfer and verification, and about 45 ms on the start-acknowledgment round trip.

No performance target was promised, and none is claimed.

**Environment and validity.**

- One Windows 11 host (12 CPUs, 16 GB), running Docker Desktop 27.1.1 with its WSL2 VM capped at 3 GB.
- Host free memory stayed at 1.9 GB or more throughout.
- Two earlier full attempts on this host *without* the VM cap ran with 0.4–1 GB free and suffered system-wide stalls. One run was censored, and the Docker engine crashed. Both attempts are kept unmodified as aborted records under `results/handoffs/step-12/aborted-*` and are not used.

**Recovery time is not measured in MS2**, because crashed-worker recovery does not exist yet.

## F. Deployment

- **Local deployment:** `make up` runs Compose with one scheduler (port 8080), one artifact store (port 8081) and `WORKERS` one-slot workers. Each service is capped at 1 CPU / 512 MiB with a 128 MiB heap and `restart: "no"`. `make demo` and `make down` were verified at Step 9, with a live demo on 3 worker containers.
- **Tests:** they run in a pinned Linux harness container, so the host needs only Docker.
- **Course cluster (Hokea), Step 11:**
  - **The adapter** is version-grounded at pinned Hokea revision `427b94634b1736ba8e59d4977836162aa58bd2cb`, with the package-source hashes verified.
  - **Local verification passed:** Hokea/Compose/Make, with `make test` at 84 passed + 1 xfailed and `make fault-demo` failing only with `RecoveryNotObserved`.
  - **The course-cluster run was attempted and externally blocked.** It ran in namespace `team-06` with public immutable GHCR images. Hokea accepted the request, created the runner Job and pod, started pytest, and copied evidence back. All three tests then stopped during fixture setup, **before any project service ran**, because the Hokea package installed in the course runner does not match the pinned revision (`Hokea source mismatch at check.py`).
  - **This is an external course-runner environment issue, not a project defect and not the intentional failure.** The pin was deliberately not relaxed.
  - Evidence: `results/handoffs/step-11/acceptance-hokea-20261003T200759-f99f027a/`.
  - It can be retried unchanged if course staff provide a correctly pinned runner.

## G. Limitations

- The worker-crash recovery gap (D) is intentional for MS2.
- Scheduler state is in memory. A scheduler restart starts a new empty run; no scheduler crash tolerance is claimed.
- The artifact store's index lives only as long as its process. Files remain on disk, but the store does not rebuild its index after a restart.
- Workers are assumed honest; results are not recomputed.
- Benchmarks ran on one shared Windows host (Docker WSL2 VM capped at 3 GB) with a synthetic waiting workload, and polling latency is included. Absolute numbers are host-specific, and results are sensitive to host memory pressure (see E). Recovery time is unmeasured.
- The course-cluster execution is externally blocked (F). Cluster behavior is unverified until a correctly pinned course runner is available.
- Explicit failures retry forever (no retry cap, no terminal FAILED job), so an operation that always fails keeps its job RUNNING.
- *[PENDING Step 13: any findings from independent verification.]*

## H. Deviations from the architecture and the plan

- **Architecture deviations: none.** Every behavior change was a bug fix that brought the code into line with the contract: the four defects in C, plus missing `scheduler_run_id` now returning 400 instead of 409.
- **Additions not named in the architecture**, all within its §15 harness-container role:
  - the harness container runs the suite on a container-local copy, because a Windows bind mount made the JVM too slow (environment, not product);
  - the synthetic video sample was regenerated by a byte-reproducible committed script, so its provenance is exact;
  - `.gitattributes` keeps checksummed and byte-compared files LF.
- **Process:** Step 12 began on its own branch while Step 11 was being finished, by agreement, and merged accepted `main` (`bf4f784`) before measuring. The measured service code is byte-identical to the Step 9 gate.
- **Benchmark environment:** the Docker WSL2 VM was capped at 3 GB through the user's `.wslconfig` to keep the host stable. This is recorded in the Step 12 evidence; it is not a product change.

## I. MS3 handoff (extension points only; nothing implemented)

- **Scheduler leases:** add lease deadlines on the injected monotonic clock (`SchedulerCore(StateStore, LongSupplier)`) and an atomic expiry command: attempt → EXPIRED, task → READY at the FIFO tail.
- **What already exists:** owner and attempt checks reject late results, attempt-numbered output namespaces prevent overwrites, and the event schema and history checker carry over.
- **Then:** remove the XFAIL marker so the same oracle becomes a passing regression. Add tests for pause, restart and report loss at every attempt boundary, plus communication-fault campaigns.
- **Separate scope decisions:** scheduler durability or replication, and exactly-once external effects.
