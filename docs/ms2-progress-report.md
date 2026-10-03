# CS4094 MS2 Progress Report — Distributed DAG Task Scheduler

> **Status: DRAFT (Step 14), not final.**
>
> - Sections marked *[PENDING Step N]* need results that teammates are still producing: Step 10 Docker gates, Step 11 Hokea, Step 13 independent verification.
> - Do not submit until every PENDING marker is resolved, or deliberately reported as outstanding.
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
| Whole suite with `MS2_REQUIRE_XFAIL=1` | — | **49 passed, 1 xfailed**, exit 0 (Step 9); 62 passed, 1 xfailed on the native backend at Step 10 | step-09, step-10 |
| Offline invariant re-check of all exported histories | 38 test directories | all OK | `results/handoffs/step-08/` |

Defects found and fixed during verification. A mutation check confirmed each new test fails on the old code.

1. An incomplete manifest binding caused a `NullPointerException`, returned as **503** instead of 400.
2. Artifact keys accepted non-canonical UUIDs.
3. An artifact replay with a different media type was silently accepted.
4. **A worker process exited** whenever any request was rejected, for example a stale report.

*[PENDING Step 10]:* actual `make test` and Compose strict-XFAIL results on a Docker host.

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

**Results:** on the native backend (Step 10 continuation) the strict suite gave 62 passed + 1 xfailed, and `--runxfail` produced exactly 1 failure, `RecoveryNotObserved`, with cleanup succeeding. *[PENDING Step 10: actual `make fault-demo` and Compose results on a Docker host.]*

## E. Performance characterization (Step 12)

*[Filled from `results/handoffs/step-12/` once the 45-run matrix finishes. See that directory's README for the method and the raw files.]*

## F. Deployment

- **Local deployment:** `make up` runs Compose with one scheduler (port 8080), one artifact store (port 8081) and `WORKERS` one-slot workers. Each service is capped at 1 CPU / 512 MiB with a 128 MiB heap and `restart: "no"`. `make demo` and `make down` were verified at Step 9, with a live demo on 3 worker containers.
- **Tests:** they run in a pinned Linux harness container, so the host needs only Docker.
- **Course cluster (Hokea):** *[PENDING Step 11: adapter at the pinned course revision, and the cluster run or an explicit NOT VERIFIED.]*

## G. Limitations

- The worker-crash recovery gap (D) is intentional for MS2.
- Scheduler state is in memory. A scheduler restart starts a new empty run; no scheduler crash tolerance is claimed.
- The artifact store's index lives only as long as its process. Files remain on disk, but the store does not rebuild its index after a restart.
- Workers are assumed honest; results are not recomputed.
- Benchmarks ran on one shared host with a synthetic waiting workload, and polling latency is included. Recovery time is unmeasured.
- Explicit failures retry forever (no retry cap, no terminal FAILED job), so an operation that always fails keeps its job RUNNING.
- *[PENDING Step 13: any findings from independent verification.]*

## H. Deviations from the architecture and the plan

- **Architecture deviations: none.** Every behavior change was a bug fix that brought the code into line with the contract: the four defects in C, plus missing `scheduler_run_id` now returning 400 instead of 409.
- **Additions not named in the architecture**, all within its §15 harness-container role:
  - the harness container runs the suite on a container-local copy, because a Windows bind mount made the JVM too slow (environment, not product);
  - the synthetic video sample was regenerated by a byte-reproducible committed script, so its provenance is exact;
  - `.gitattributes` keeps checksummed and byte-compared files LF.
- **Process:** Steps 10–11 and Step 12 proceeded in parallel by agreement, on separate branches.

## I. MS3 handoff (extension points only; nothing implemented)

- **Scheduler leases:** add lease deadlines on the injected monotonic clock (`SchedulerCore(StateStore, LongSupplier)`) and an atomic expiry command: attempt → EXPIRED, task → READY at the FIFO tail.
- **What already exists:** owner and attempt checks reject late results, attempt-numbered output namespaces prevent overwrites, and the event schema and history checker carry over.
- **Then:** remove the XFAIL marker so the same oracle becomes a passing regression. Add tests for pause, restart and report loss at every attempt boundary, plus communication-fault campaigns.
- **Separate scope decisions:** scheduler durability or replication, and exactly-once external effects.
