# CS4094 MS2: Sequential Team Workflow and Implementation Roadmap

Planning deliverable • Continued from the existing workspace • 2 October 2026

**Use one shared repository and one active implementation step at a time.** A teammate completes the current step, verifies it, commits and pushes the accepted result, and hands the exact repository state to the next teammate. The next teammate pulls that state, reproduces its verification, and continues. Everyone works from the same architecture and accumulated implementation; there are no isolated “scheduler person,” “worker person,” or parallel component tracks.

This roadmap preserves the canonical `CS4094_MS2_Architecture.md`. It sequences its implementation and verification; it does not replace its technical decisions. The current request is planning-only. Existing partial code is preserved as an **unreviewed checkpoint**, not certified as the completed MS2 artifact.

## 1. Authority and frozen decisions

Resolve requirements in this order:

1. **[A] Course project guidelines:** `cs4094_f26_project_guidelines_v20260824.pdf`, especially MS2 on p. 2 and the software artifact requirement on p. 7.
2. **[P] Approved MS1 specification:** `CS4069 (1).pdf`, p. 1.
3. **[R] Canonical architecture:** `CS4094_MS2_Architecture.md`, all 19 sections and `IMPLEMENTATION CONTRACT`.
4. Supporting MS1 slides.
5. Lecture materials and primary technical documentation.

The supplied attachment named `CS4094_MS2_Architecture(2).md` is the architecture copy used for this roadmap. Its SHA-256 is `7d2f931bfcf308ccc2b32a899e8976e75656dab81f51b940df1aa136b37a8ef1`. Keep that content unchanged when establishing the canonical repository copy. If a future file differs, review the difference explicitly; do not silently adopt whichever filename looks newer.

The guidelines require happy-path functionality, an automated correctness violation, initial performance characterization, a revised specification, a progress report, and reproducible software. The approved worker-reassignment liveness claim remains an intended semester claim. MS2 deliberately demonstrates its current failure; it does not remove that claim from the project. [A, P, R §§1, 9–10]

| Boundary | Decision to preserve |
|---|---|
| Stack | Java 21; Maven modules `protocol`, `scheduler`, `worker`, `artifact-store`, `client`; JDK HTTP server/client; Jackson; JUnit; Python 3.12 and pytest. |
| Coordination | Scheduler owns all job, task, attempt, readiness, and completion decisions. One global scheduler mutex; network/file I/O outside it. |
| Workers | Polling, one execution slot per process, fresh session UUID on restart, start acknowledgment before execution, bounded allowlisted operations. |
| Scheduler state | In-memory implementation behind the state-store command boundary. A restart begins a new empty scheduler run. |
| Task states | `BLOCKED → READY → ASSIGNED → RUNNING → SUCCEEDED`; accepted explicit failure from ASSIGNED or RUNNING returns the logical task to READY. |
| Attempt states | `ASSIGNED → RUNNING → SUCCEEDED` or `FAILED`; explicit failure is also permitted from ASSIGNED. Attempt numbers increase on reassignment. |
| Job states | `ACCEPTED → RUNNING → SUCCEEDED`; retries/stalls do not introduce a terminal FAILED state. Every task must succeed. |
| Safety | Valid success report required; dependencies must complete before execution; at most one accepted logical success per task. |
| Intentional defect | No reassignment solely because an owning worker becomes silent or crashes. No leases, heartbeat expiry, recovery scanner, or administrative auto-requeue. |
| Artifacts | Separate HTTP service; completed immutable objects; attempt-specific output namespaces; accepted completion selects downstream inputs. |
| Evidence | Atomic decision events, scheduler sequence numbers, causal acknowledgments, local monotonic elapsed times. No cross-machine wall-clock subtraction. |
| Limits/resources | 128 tasks/job, 512 edges/job, 1 MiB manifest, 32 MiB artifact; 16 handler threads/server; 128 MiB JVM heap; benchmark service caps of 1 CPU and 512 MiB. |
| Deferred | Scheduler/storage failover, durable scheduler recovery, consensus, full worker-crash recovery, exactly-once external effects, paid APIs, UI, authentication, cancellation, and terminal retry exhaustion. |

**Conflict rule:** if [R] contradicts [A] or [P], stop the affected work and describe the conflicting passages. For consequential ambiguity, consult the complete contract and approved sources before proposing a resolution. Ordinary naming, formatting, and serialization details may be documented without redesigning the distributed system. [R, IMPLEMENTATION CONTRACT]

## 2. Existing checkpoint: what can actually be claimed

The interrupted workspace contains partial implementation work. Preserve it and inspect it at the appropriate roadmap steps rather than starting again.

| Item | Observed state | What it does not establish |
|---|---|---|
| Five Java modules | Source and Maven build files exist. An earlier revision completed `mvn package` across all five modules. | The latest source has not completed the full acceptance suite. |
| Scheduler/domain code | Draft mutex/state-store core, identities, DAG validation, claims, transitions, receipts, snapshots, events, and metrics exist. | Full contract compliance or correctness under all required tests. |
| Artifact service, worker, client | Draft implementations exist. | Validated container deployment, all timeout/replay edge cases, or final API completeness. |
| Selected native integration checks | **6 passed, 15 deselected, in 28.52 s** in the recorded selected run. They covered functional multi-job execution, simultaneous claims, submission/claim receipts, duplicate/conflicting/stale reports, required output publication, and partial-upload visibility/conflicts. | Passing unit tests, the whole integration suite, video verification, the crash oracle, or clean-clone reproduction. |
| Later unit-test build | Attempted after additional tests/edits; stopped while resolving Maven's JUnit test provider because the execution environment's proxy connection failed. | Neither a JUnit pass nor a demonstrated product test failure. It must be rerun in a working build environment. |
| Workloads | Synthetic MP4 and fixture SRT exist. | Completed provenance/checksum documentation or a verified video DAG run. |
| Crash test and benchmark | Draft Python files exist. | They have **not** been executed as milestone evidence. There are **no measured benchmark results**. |
| Compose/Hokea/final documentation | Not completed. Hokea source was inspected at commit `427b94634b1736ba8e59d4977836162aa58bd2cb`. | Docker or course-cluster validation. |

The selected test run used Java processes on one host, not Docker. Native service launch code uses a bounded JVM heap and CPU affinity; it does not establish the required 512 MiB container memory cap. Do not label these results the final architecture-prescribed deployment experiment.

There is no established shared GitHub handoff commit in this checkpoint. **The immediate next action is Step 0: preserve/import the checkpoint and record the shared baseline.** Steps already represented by code become review-and-finish work; they are not automatically checked off.

The continuation package includes the partial source, selected test evidence, build logs, and an explicit checkpoint status file. Generated JARs, compiler outputs, downloaded toolchains, proxy settings, and temporary object-store files are excluded. No implementation change is required just to preserve this checkpoint.

## 3. The sequential team workflow

### One active step, one shared understanding

At any moment the team has one current roadmap step, one current writer, and a named next teammate. Choose the writer by availability; rotate across the entire system rather than assigning permanent component ownership. The next teammate's first job is to understand and verify the preceding handoff.

Use this cycle for every step:

1. **Pull and read.** Check the accepted commit, canonical architecture, current roadmap entry, latest handoff, and open issues. Reproduce the preceding step's gate.
2. **Implement only the current step.** Reuse existing code after inspection. Do not advance dependent work while its prerequisites are unverified.
3. **Verify.** Run the step's tests plus relevant existing regressions. Diagnose failures. Keep the intentional liveness failure separate from accidental failures.
4. **Record.** Save commands, exit codes, test counts, compact evidence, changed paths, and remaining limitations. Update the handoff and progress tracker.
5. **Commit and push.** Promote the verified step to the accepted branch. Communicate the exact resulting commit SHA and evidence path.
6. **Receive.** The next teammate pulls that SHA, reruns the gate, and explains the current behavior. If reproduction fails, resolve the same step before proceeding.

This is a development and learning workflow, not a division into independent mini-projects. A step may legitimately touch protocol, scheduler, worker, and tests together when an end-to-end behavior requires it.

### Source of truth

GitHub holds the accepted code, canonical design copy, tests, scripts, documentation, selected evidence, and handoff history. Chats explain or propose changes; they do not override the repository or supply missing implementations by implication.

Maintain these small coordination files:

| Path | Contents |
|---|---|
| `docs/CS4094_MS2_Architecture.md` | Unchanged canonical architecture copy. Reconcile the checkpoint's `docs/approved-architecture.md` to one canonical path during Step 0. |
| `docs/implementation-roadmap.md` | This roadmap, with stable step numbers. |
| `docs/PROGRESS.md` | Current step, status, current writer, next teammate, last accepted commit, blockers, and next gate. |
| `docs/HANDOFF.md` | The latest operational handoff. |
| `docs/handoffs/step-XX.md` | Historical step records. |
| `docs/OPEN_ISSUES.md` | Concrete defects, blocked checks, environment requirements, and unresolved consequential ambiguities. |
| `results/handoffs/step-XX/` | Compact verification evidence associated with that step. |

Use `NOT_STARTED`, `IN_PROGRESS`, `BLOCKED`, or `DONE`. “Source written” and “compiled once” are useful notes, not substitutes for a passed step gate.

### Git handoff procedure

Use one short branch for the active step. `main` contains accepted steps; unfinished work remains on the step branch. These are workflow commands to use in the shared repository, not commands already executed here.

```bash
git switch main
git pull --ff-only origin main
git status --short
git rev-parse HEAD
git switch -c ms2/step-XX-short-title
```

After the step's checks pass, stage its reviewed paths, commit its code/tests/documentation/evidence, and push the step branch. Then integrate it through the team's existing repository process. If there is no required PR process and `main` has not advanced, the current writer can fast-forward it:

```bash
git switch main
git pull --ff-only origin main
git merge --ff-only ms2/step-XX-short-title
git push origin main
git rev-parse HEAD
```

The next teammate verifies that this SHA is the one received after pulling. If `main` advanced unexpectedly, reconcile and rerun the affected checks; do not force-push over another teammate's work.

Keep the final accepted SHA in the handoff message and in the next step's base-commit record. A commit cannot contain its own hash in a file without changing that hash. Associate saved test evidence with the tested source through a source checksum manifest or the implementation commit it actually tested.

If work is interrupted, push a clearly labeled WIP checkpoint to the current step branch, document exactly what is unverified, and keep the step IN_PROGRESS or BLOCKED. The next writer can take over that same step. No one needs to recreate successful earlier work from a chat transcript.

## 4. Ordered MS2 roadmap

Each step below is one team handoff unit. Existing checkpoint code should be assessed within that step. The step ends only when its exit gate has evidence.

The outer sequence remains: approved architecture → sequential implementation → independent verification → completed milestone writing → final audit. Documentation and tests are maintained throughout; the final writing step consolidates verified facts.

| Step | Deliverable | Exit gate |
|---|---|---|
| 0 | Shared baseline and checkpoint inventory | Canonical sources and unverified work are traceable to a shared commit. |
| 1 | Build, repository, and deployment foundation | Clean build and documented toolchain; deployment structure established. |
| 2 | Protocol, identities, manifests, and DAG validation | Typed contracts and graph/binding/limit tests pass. |
| 3 | Scheduler domain core and memory state store | Transition, FIFO, ownership, retry, and atomicity tests pass. |
| 4 | Immutable HTTP artifact service | No partial publication; descriptor and immutability tests pass. |
| 5 | Scheduler HTTP API, snapshots, events, and metrics | API behavior matches the core and contract. |
| 6 | Worker, Java client, and first complete execution | A real worker produces and reports a real artifact through HTTP. |
| 7 | Functional DAG and full happy-path semantics | Multi-job/multi-worker, dependency, concurrency, and replay tests pass. |
| 8 | Evidence collection and history checks | Complete, causally interpretable histories are exported automatically. |
| 9 | Concrete video demonstration | Programmatic checks verify the approved video pipeline outputs. |
| 10 | Intentional worker-crash liveness failure | Exactly one narrowly typed strict XFAIL; visible failing demonstration saved. |
| 11 | Hokea adapter and cluster handoff | Version-grounded adapter; cluster run recorded if access is available. |
| 12 | Exact initial performance experiment | All 45 measured runs attempted; raw samples, summaries, and limitations saved. |
| 13 | Independent clean-environment verification | Another teammate reproduces the full artifact and reports concrete findings. |
| 14 | Revised specification and progress report | Claims match evidence; all required reporting sections are complete. |
| 15 | Final audit and submission package | A clean checkout can reproduce the documented workflow; one ZIP/tar.gz is prepared. |

### Step 0 — Establish the shared baseline without restarting

**Prerequisite:** supplied course sources, canonical architecture, and preserved checkpoint.

**Work and outputs:** identify or establish the team's repository, import the checkpoint on a review branch, record the architecture checksum, and create the coordination files above. Keep partial implementation marked unreviewed. Inventory every existing path against the contract; record missing files and unexecuted checks. Do not adopt incidental draft-code choices as new architecture decisions.

**Verification:** compare the canonical copy byte-for-byte with the supplied architecture; verify that the archive opens and its checksums match; confirm no generated builds, secrets, temporary runtime state, or machine-specific configuration is being committed. Record which code revision the existing build/test evidence actually covers.

**Evidence/commit:** baseline inventory, source authority map, checkpoint status, source checksums, and accepted baseline SHA. Suggested commit: `docs(ms2): establish canonical baseline and sequential roadmap`.

**Handoff:** explain what is present, what is unverified, and why Step 1 is the current gate. Do not report later steps as complete just because their source files exist.

### Step 1 — Make the repository buildable and set up reproducible execution

**Prerequisite:** Step 0 accepted.

**Work and outputs:** complete the approved Maven module layout, pin dependency/runtime/container versions, establish JUnit and pytest configuration, and document Java 21/Python 3.12/FFmpeg/Docker prerequisites. Provide Docker build and Compose structure as services become runnable. Establish launch/stop/collect harness interfaces so later fault tests do not depend on one machine's process IDs or paths. Keep test hooks off by default.

**Verification:** build from the shared checkout with `mvn -B verify`; resolve the checkpoint's dependency-download blocker through the evaluator's normal build environment. Check that pinned images/dependencies can actually be obtained. Record Docker/Compose versions. Confirm that compile success is not presented as service readiness.

**Evidence/commit:** toolchain versions, clean build log, module list, and documented resource settings. Suggested commit: `build(ms2): establish reproducible modules and runtime foundation`.

**Handoff:** the next teammate can build without private paths or caches. Identify which service-level deployment checks will become available at Steps 4–6. [R §§2, 7, 15–16]

### Step 2 — Freeze the wire contracts and validate DAGs

**Prerequisite:** Step 1 build works.

**Work and outputs:** inspect/finish `protocol/`; document versioned request/response schemas for every approved endpoint. Implement immutable typed manifests and the job/task/attempt/session/run identities. Validate operations, parameters, parents, named inputs/outputs, final bindings, graph topology, and specified limits. Preserve semantic submission equality for task maps and dependency sets while preserving meaningful numeric/string distinctions and operation-array order.

**Verification:** test valid chains, joins, multiple roots/sinks and disconnected subgraphs; reject empty DAGs, duplicate IDs/dependencies, cycles, self-edges, unknown parents, invalid bindings, unsupported operations, and over-limit requests. Test manifest replay equivalence/conflict, namespace validation, malformed input, and required identity fields. Source-object existence is verified at acceptance once the artifact service is available.

**Evidence/commit:** protocol tests, schema examples, error/status-code table, and validation cases. Suggested commit: `feat(protocol): define MS2 identities and validated DAG contracts`.

**Handoff:** demonstrate one valid manifest and one rejected manifest, and identify the exact ownership tuple used in reports. Any consequential schema ambiguity remains an explicit blocker rather than an undocumented design change. [R §§3, 6]

### Step 3 — Finish the scheduler domain state machine

**Prerequisite:** Step 2 contracts are stable.

**Work and outputs:** complete transport-independent core commands, the state-store interface, and its memory backend. Under one mutex, maintain jobs/tasks/attempts, parent/child adjacency, satisfied-parent sets, FIFO readiness, session ownership, request receipts, accepted completions, counters, and decision events. Inject a monotonic clock. Keep all I/O outside commands.

**Verification:** test every legal transition and representative illegal transitions; deterministic ready ordering; simultaneous claims; one active attempt per session; explicit failure from ASSIGNED and RUNNING; tail requeue with a larger attempt number; duplicate failure/success receipts; stale/conflicting reports; one satisfied-edge update; joins; and all-tasks-success job completion. Test a success precheck invalidated by a concurrent failure before commit. A duplicate old failure receipt must not disturb a newer attempt.

**Evidence/commit:** JUnit output plus compact state/event traces. Suggested commit: `feat(scheduler): implement atomic MS2 scheduling state machine`.

**Handoff:** walk through an explicit failure/retry and a duplicate success. Identify the intentionally absent silent-worker transition. Do not add EXPIRED, leases, recovery scans, retry exhaustion, or a terminal FAILED job. [R §§4–5, 7, 11]

### Step 4 — Complete immutable artifact storage

**Prerequisite:** Step 2 artifact descriptors/namespaces; Step 3 accepted in the sequential workflow.

**Work and outputs:** finish PUT/HEAD/GET, staging, length/hash verification, per-key publication serialization, and the completed-object index. Use HTTP between services, not shared worker disks. Provide service health, its Docker image, and a storage-directory mount that survives worker termination. Explain the service-lifetime persistence boundary.

**Verification:** HEAD/GET must not reveal partial uploads; invalid length/hash and oversize objects must not publish. Identical PUT replay succeeds; conflicting bytes under one key fail. Concurrent publication is immutable. Completed files remain available after a worker process dies. Old staging files are not treated as published objects.

**Evidence/commit:** publication/race/integrity tests, descriptor examples, and service smoke output. Suggested commit: `feat(artifacts): publish verified immutable HTTP objects`.

**Handoff:** show a successful upload and an incomplete upload that remains invisible. Do not claim store restart reconstruction, replication, or power-loss durability. [R §§3, 6, 11]

### Step 5 — Expose the scheduler API and observation endpoints

**Prerequisite:** scheduler core and artifact service verified.

**Work and outputs:** connect HTTP handlers to core commands; complete health, submission/status, claim, start/report, events, and metrics endpoints. Validate source artifacts before accepting a job. Validate success outputs outside the mutex, then recheck state/owner/attempt during commit. Implement immutable atomic snapshots and ordered pagination. Drain decision events outside the mutex.

**Verification:** check all endpoint success/error statuses; same-job replay/conflict; cached empty/assigned/terminal claim results; active-session claims; source/output descriptor rejection; storage unavailability producing transient errors without accepting a new job; and rejected commands preserving scheduling state. Verify events/counters/gauges and snapshot/event-sequence consistency. Do not acknowledge success before all descriptor checks and atomic state changes finish.

**Evidence/commit:** API tests, example exchanges, ordered event pages, and metrics snapshots. Suggested commit: `feat(api): expose validated scheduler commands and evidence`.

**Handoff:** show one atomic job snapshot, one paginated event history, and how the scheduler rejects an old run. [R §§6–7, 14]

### Step 6 — Complete one worker, the Java client, and real end-to-end execution

**Prerequisite:** Steps 4–5 services available through HTTP.

**Work and outputs:** implement the one-slot worker cycle: claim → acknowledged start → bounded allowlisted operation → upload → acknowledged immutable report → next claim. Complete Java upload/submit/status/fetch commands. Use fixed claim IDs across transport retries, exact report replay, defined polling/backoff/timeouts, fresh worker sessions, and new-run handling. Finish Compose health checks and isolated harness deployment for the real services.

**Verification:** submit a one-task job via the Java client; fetch its actual output. Verify worker operation-start follows the scheduler acknowledgment; the worker does not claim a second task while its first is active. Verify bounded local operation failure, transport retry without duplicate execution after a lost report acknowledgment, and new scheduler-run handling. Confirm test hooks are disabled in normal deployment.

**Evidence/commit:** client transcript, worker/scheduler correlated events, output checksum, and lifecycle tests. Suggested commit: `feat(worker): execute and report bounded HTTP DAG attempts`.

**Handoff:** the next teammate can launch scheduler/store/workers, execute a real task, and stop them with evidence preserved. Workers have no production coordination API or dependency state. [R §§2, 6, 12, 15]

### Step 7 — Verify the complete functional happy path

**Prerequisite:** real end-to-end path and deployable services.

**Work and outputs:** finish the five-task functional workload: A writes 3; B adds 4 → 7; C multiplies by 5 → 15; D joins and sums → 22; E writes exactly `result=22\n`. Complete integration cases for multiple jobs/workers, branch execution, multiple roots/sinks, replay, ownership, and explicit retry.

**Verification:** B and C execute concurrently on distinct sessions; D cannot start until both succeed; the job cannot succeed while an unrelated task remains unfinished. A controlled attempt-1 failure must be followed by a successful attempt 2 with one logical success. Verify real artifacts, duplicate/conflicting/stale reports, submission/claim replay, and exactly one dependency release. Exercise simultaneous worker claims programmatically.

**Evidence/commit:** full functional integration output, manifests, accepted outputs, snapshots, and histories. Suggested commit: `test(ms2): verify multi-worker DAG execution and replay safety`.

**Handoff:** demonstrate a join, an explicit retry, and a rejected stale result. Reuse the checkpoint's six selected passing checks, but run all required cases on the current source and deployment. [R §§3, 7, 9, 12]

### Step 8 — Make evidence complete and machine-checkable

**Prerequisite:** successful functional workload and lifecycle events.

**Work and outputs:** complete automatic export of scheduler JSONL, worker events, atomic snapshots, counters/gauges, and test metadata before teardown. Implement history assertions and a launch/stop/collect adapter boundary reusable by Compose and Hokea. Preserve raw failed-test diagnostics as well as successful evidence.

**Verification:** sequence pagination is gap-free through the recorded export boundary; a missing event needed by an invariant causes a harness failure. Every accepted success has a valid report and preceding start; dependencies succeed before child assignment/start; no task has two active owners or two accepted successes; job completion follows all tasks. Join worker operation events to scheduler acknowledgments using IDs/sequences, not timestamps from different processes.

**Evidence/commit:** event schema, one reconstructable history, automated history-check results, and teardown evidence. Suggested commit: `test(evidence): export and verify causal scheduler histories`.

**Handoff:** explain how another teammate can falsify each safety claim from the saved evidence without manually interpreting console output. [R §§8–10, 14]

### Step 9 — Finish the concrete video-file demonstration

**Prerequisite:** functional scheduling and evidence collection pass.

**Work and outputs:** commit a small project-owned/redistributable MP4 or clearly labeled generated FFmpeg sample, matching fixture SRT, checksums, provenance, and manifest. Implement the approved graph: inspect → four branches (720p, 360p, thumbnail, fixture subtitles) → publish accepted artifact references and metadata. Use fixed codec/preset, one FFmpeg thread, bounded operations, and checked process exits. Do not add paid transcription or a platform UI.

**Verification:** run the video DAG with multiple workers; inspect readable output media, expected dimensions, PNG output, exact fixture subtitle contents, and publish references matching accepted branch outputs. Check join ordering and job completion programmatically. Verify that no runtime media download is required.

**Evidence/commit:** sample manifest, checksum/provenance file, ffprobe validation, output references, and test history. Suggested commit: `feat(workloads): add verified MS2 video-file demonstration`.

**Handoff:** show how to reproduce the demo and why the subtitles are a labeled fixture. The video is workload data; the scheduler remains the project. [R §12]

### Step 10 — Demonstrate the single intentional crash-recovery failure

**Prerequisite:** functional safety, worker test gate, fault-capable deployment adapter, and complete evidence.

**Work and outputs:** complete the exact `worker_crash_reassignment` experiment from [R §10]:

1. Fresh scheduler/store; start only A; submit X → Y.
2. Wait for A's structured gate inside X, after acknowledged start/operation-start and before output publication.
3. Confirm X RUNNING under A, no accepted output/success; hard-kill A and confirm exit.
4. Start healthy B; require an independent probe job to succeed; record B's continued no-work polling.
5. Observe up to **10 seconds** for X to be assigned to B with a greater attempt number. If recovered, allow the original job to finish.
6. Require recovery in the final correctness oracle. MS2 should violate that oracle while preserving safety: X RUNNING under dead A, Y BLOCKED, job RUNNING.

**Verification:** use one strict pytest XFAIL limited to the dedicated `RecoveryNotObserved` exception from that final oracle. Setup, process control, probe, missing-evidence, and safety failures remain ordinary failures. Normal acceptance requires exactly one XFAIL and zero unexpected failures; XPASS is a failure until milestone scope changes deliberately. Run `make fault-demo` with `--runxfail` and preserve its expected nonzero failure. A blanket XFAIL or a test that asserts “stuck is correct” does not satisfy this step. [T3]

**Evidence/commit:** gate/start correlation; pre/post status; kill/session/attempt record; B claim evidence; successful probe; scheduler events; real assertion traceback; command and exit status. Suggested commit: `test(faults): demonstrate intentional MS2 crash-reassignment violation`.

**Handoff:** explain the structural missing transition. The 10-second window is a controlled test budget, not a universal liveness/recovery-time bound. Do not fix this defect in MS2. [P, R §§9–10]

### Step 11 — Integrate with the actual Hokea version

**Prerequisite:** the same service boundaries and crash oracle work through the local adapter.

**Work and outputs:** pin the course-provided Hokea revision and implement an adapter for launch/stop/kill/log collection. The repository inspected during continuation was commit `427b94634b1736ba8e59d4977836162aa58bd2cb`; verify that this is the course version being used rather than silently upgrading. Reuse the existing service logic, images/environment contracts, artifact HTTP access, and stdout events. The current Hokea docs describe node IDs/roles, `/health`, Docker and Kubernetes backends, and private per-node scratch storage. Implement only the needed deployment wrapper; do not move scheduling into it. [H1–H3]

**Verification:** first verify image startup, service addressing, health, and artifact reachability. Then run the functional workload and the **same** crash oracle on the cluster if credentials/access are available. Confirm that killing a worker does not restart it automatically or kill the artifact store. Do not assume shared worker mounts or a persistent-volume class. Record the exact Hokea/image revision and namespace/configuration actually used.

**Evidence/commit:** adapter/configuration, version reference, launch/cleanup instructions, deployment logs, and fault-test evidence. Suggested commit: `deploy(hokea): adapt MS2 services and fault harness to course runtime`.

**Handoff:** if cluster access is unavailable, mark cluster execution NOT VERIFIED and name the exact remaining command, access prerequisite, and responsible teammate. Do not fabricate an observed cluster result. Adapter implementation can be handed off; the environment validation remains an explicit open gate. [R §15; lecture L3; L5 pp. 2–3]

### Step 12 — Run the exact benchmark and keep the raw measurements

**Prerequisite:** the complete happy path is stable, observability is verified, and resource settings/deployment are reproducible. The intentional crash test is separate; inject no faults in these runs.

| Parameter | Required value |
|---|---|
| In-flight job concurrency C | 1, 4, 16 |
| Worker count W | 1, 2, 4; one slot per worker |
| Configurations | All 9 C/W combinations |
| Repetitions | 5 independent fresh scheduler/worker runs per configuration: **45 measured runs** |
| Warmup | 4 jobs before each measurement; excluded; keep the same JVMs running between warmup and measurement |
| Measured load | 24 jobs/run, 6 tasks/job, 100 ms fixture operations; closed-loop replacement up to C |
| Totals for complete matrix | 180 warmup jobs, 1,080 measured jobs, 6,480 measured logical tasks |
| DAG | A=1; B/C/D add 1/2/3; E sums to 9; F formats the result |
| Measured-phase timeout | 120 seconds; record censored/incomplete/error runs explicitly |
| Per-service resources | 1 CPU, 512 MiB memory, 128 MiB JVM heap, defined handler count |

**Work and outputs:** complete the driver, raw per-job/per-task CSV, per-run throughput and metadata, summary script, and `make bench`. Validate the driver's counts and C bound before committing to the full run. Preserve all completed results if execution is interrupted; do not invent replacement samples.

**Verification/metrics:** job time = scheduler acceptance → all-task success; scheduling latency = READY → ASSIGNED; throughput = measured accepted logical successes / scheduler interval from first measured acceptance to last measured completion. All use the scheduler's local monotonic clock. Exclude warmup and duplicate messages. Retain run-level repetitions; summarize p50/p95 and throughput mean/spread, plus incomplete/error counts. State the percentile calculation and aggregation method. Verify expected results and event counts, not just timings.

**Evidence/commit:** exact command; date; host/tool/image/resource metadata; raw job/task/run files; summaries; error/censoring records; supporting histories. Suggested commit: `perf(ms2): record the approved initial benchmark matrix`.

**Handoff:** explain the measurements and shared-host/synthetic-wait limitations. A native run without enforced container caps must be labeled as such and cannot silently stand in for the exact capped deployment. Do not report the fault-test observation window as measured recovery time. [P, R §§8, 13–14; T2]

### Step 13 — Have the next teammate independently reproduce and challenge the artifact

**Prerequisite:** implementation, local deployment, crash evidence, and benchmark outputs are available.

**Work and outputs:** use a fresh checkout/environment, without the prior writer's caches, generated outputs, or chat-only instructions. Follow the README and top-level commands. Review the required safety, state, retry, publication, and fault assertions against the source. Add or repair meaningful checks only where a concrete gap remains; do not weaken tests to accept accidental failures.

**Verification:** reproduce the complete normal suite with exactly one permitted XFAIL, the visible failing demo, the functional/video outputs, and the benchmark procedure. Check that every required command cleans up and preserves its exit status/evidence. If defects are found, return them to the affected step, fix sequentially, rerun affected gates, and update the accepted commit before writing final claims.

**Evidence/commit:** independent verification report with checkout SHA, environment, commands, outcomes, and unresolved issues. Suggested commit: `test(ms2): record independent clean-checkout verification`.

**Handoff:** the next teammate receives reproducible facts, not an implementation author's assurance. Hokea or container checks that could not run remain explicitly unverified. [A p. 7; R, stop condition]

### Step 14 — Finish the revised specification and progress report

**Prerequisite:** independent verification results and actual benchmark evidence.

**Work and outputs:** finish `README.md`, `docs/specification.md`, API/deployment/test/benchmark instructions, limitations, and the MS2 progress report. Preserve the approved intended semester claims while separately stating current MS2 support and the one missing worker-recovery mechanism. Use the course's network/node/timing vocabulary. Include the actual environment, results, and deviations.

**Verification:** reconcile every supported claim with a test/evidence path; reconcile every reported number with raw measurements. Check that the complete evaluator flow includes setup, build, launch, submit, status/fetch, normal tests, intentional failure, benchmark, evidence locations, and cleanup. A stalled job must never be described as failed or completed. Do not imply that scheduler restart recovery or exactly-once external effects exist.

**Evidence/commit:** revised specification, progress report, command walkthrough, claim-to-test matrix, and MS3 extension notes. Suggested commit: `docs(ms2): reconcile specification and progress report with evidence`.

**Handoff:** deliver reporting sections A–I: implemented capabilities; repository structure; exact tests/results; intentional failure; benchmark; deployment; limitations; every deviation; and MS3 handoff. The MS3 section identifies extension points only—it does not implement them. [A p. 2; P; R §§8–11, 17, 19]

### Step 15 — Audit and package the milestone

**Prerequisite:** all required local gates passed, documents reconciled, and any environment-only unverified gates explicitly recorded.

**Work and outputs:** inspect the accepted repository and submission contents from a clean checkout. Include source, tests, small sample media, build/deployment automation, revised specification, progress report, and selected raw/summary evidence. Record the submission commit SHA and checksums. Exclude caches, build outputs, temporary object directories, credentials, and unrelated large logs.

**Verification:** execute the documented command sequence on the packaged source, confirm all required files are present, verify archive extraction, and confirm the normal suite/fault-demo behavior remains distinct. Lecture 6 p. 2 explicitly says to submit everything as a single ZIP or tar.gz; check the current Canvas assignment for any additional required naming/location details. Do not infer a new deadline from inconsistent older weekday/date text. [L6 p. 2]

**Evidence/commit:** final audit record, packaging manifest/checksums, final repository SHA, and one submission archive. Suggested commit: `chore(ms2): finalize audited milestone artifact`.

**Handoff:** the whole team can explain the happy path, safety checks, intentional stuck-task failure, benchmark limitations, and remaining MS3 work. Archive preparation does not itself submit to Canvas or certify unrun cluster checks.

## 5. Top-level evaluator command contract

These are required commands for the **finished artifact**. The current partial checkpoint does not yet provide a completed Makefile/Compose workflow.

| Command | Required behavior |
|---|---|
| `make up` | Build/start one scheduler, one artifact service, configured worker count; wait for actual readiness. |
| `make demo` | Submit/run documented functional and video examples; produce discoverable outputs and status. |
| `make test` | Build, deploy isolated fixtures, run unit/integration/fault tests, enforce exactly one narrowly permitted XFAIL, export evidence, clean up, retain the correct exit status. |
| `make fault-demo` | Execute the primary fault test with pytest `--runxfail`; produce the expected nonzero failure and evidence. |
| `make bench` | Run the exact C/W/repetition/warmup/load matrix and export raw and summarized results. |
| `make down` | Gracefully stop the regular deployment without silently deleting outputs/evidence. |

Test deployments use `restart: no`; workers have no fixed container name or published production port. Expose scheduler 8080 and artifact service 8081 locally as specified. Container images, workload samples, API semantics, and resource settings must match the documentation. [R §15; T5]

## 6. Definition of done

### A step is done when

- Its required output exists in the shared repository and follows the canonical architecture.
- Its gate and relevant regressions pass on the current source; failures are investigated rather than hidden.
- Commands, outcomes, evidence, and open limitations are recorded.
- The handoff identifies the accepted commit and the next step.
- The next teammate can reproduce the gate and understands the state being handed over.

### MS2 is done when

- A clean checkout runs all required functionality on the happy path with real artifact exchange and the concrete video example.
- All three approved safety claims have automated checks, including after explicit retries and duplicated/stale reports.
- Exactly one primary worker-crash reassignment oracle is a strict, narrowly scoped XFAIL, and its visible failing run is preserved.
- The complete benchmark experiment has raw evidence, justified summaries, and honest environment/measurement limitations.
- Required local deployment and evaluator commands work and preserve evidence/exit status.
- The actual course Hokea adapter is provided; any required cluster verification has been performed when access is available, or is explicitly listed as outstanding.
- The revised specification, report, source, tests, data, and documentation agree.
- The final archive is tied to the accepted repository state, and no deferred MS3 mechanism has been implemented accidentally.

An unavailable environment check is not a pass. It must remain visible in the report and handoff, even when the rest of the deliverable is ready.

## 7. Reusable teammate handoff record

Copy this into `docs/HANDOFF.md` and archive it under the completed step number:

```text
Project: CS4094 distributed DAG task scheduler / MS2
Step number and title:
Status: IN_PROGRESS | BLOCKED | DONE
Current writer:
Next teammate:
Base commit:
Accepted commit: communicate final SHA after commit/push; do not self-reference it inside its own commit
Canonical architecture path and checksum:

Behavior completed:
Paths changed and why:
Existing work reused:
Commands run, exit codes, and test counts:
Evidence paths and tested source identifier/checksums:
Intentional XFAIL status (if Step 10 or later):
Known unverified behavior / environment blockers:
Architecture deviations: none, or exact details requiring review
Open issues:
Exact next step and first verification command:

Explain to the next teammate:
- Current job/task/attempt lifecycle
- Ownership and dependency rules relevant to this step
- What the code intentionally cannot do yet
```

For an interrupted step, add the last successful command, the first failing/incomplete command, any running process that must be checked, and the exact remaining work. Keep that step open; do not tell the next teammate to start its dependent step.

## 8. Reusable AI continuation prompt

Use this in the teammate's implementation chat after supplying repository access or a complete current source snapshot:

```text
You are helping our team with ONE sequential step of the Virginia Tech CS4094
distributed DAG task scheduler MS2 project.

Current step: [number and title]
Expected base commit: [SHA]
Current branch: [branch]
Handoff file: docs/HANDOFF.md
Roadmap: docs/implementation-roadmap.md
Canonical architecture: docs/CS4094_MS2_Architecture.md

First read the repository instructions, current handoff/progress/open-issue files,
canonical architecture, and the applicable course requirements. Confirm the actual
checkout matches the handoff and inspect existing work before editing.

Source priority: course guidelines > approved CS4069 MS1 specification > canonical
architecture/IMPLEMENTATION CONTRACT > supporting slides > lecture references.
If the contract conflicts with the two governing sources, stop and explain it.

Our team works sequentially with shared context. Do not divide the project into
parallel isolated components. Complete only this step and its required regression
checks. Reuse correct existing code. Do not restart, redesign, or silently alter
approved decisions. If this is an interrupted step, resume the remaining work.

Preserve Java 21 services, the Java client/shared protocol, the HTTP artifact store,
Python/pytest tooling, one scheduler mutex, memory-only scheduler state, exact
state machines, and logical-task/attempt/session/run identities.

MS2 must NOT recover ownership merely because a worker disappears. Do not add
leases, heartbeats, expiry scanning, automatic silent-worker requeue, scheduler
replication, durable restart recovery, or other deferred MS3 mechanisms. Preserve
the narrowly typed strict XFAIL for the final recovery oracle when that step exists.
Setup, safety, and unrelated failures must still fail normally.

Before changing files, summarize the existing state and this step's checklist.
Implement/review incrementally; compile and run meaningful tests. Diagnose failures
rather than weakening assertions. Record actual commands/results and evidence.
Never invent test, benchmark, Docker, Hokea, or cluster results.

Finish with:
1. Changes and why they satisfy this step.
2. Exact verification commands, exit codes, results, and evidence paths.
3. Remaining issues, unverified checks, and all architecture deviations.
4. Updated progress/handoff records and a suggested commit message.
5. The exact next-step handoff, without starting that next step.

Follow repository permissions for commit/push. Never force-push or claim a GitHub
handoff exists until it has actually been saved there. The repository and accepted
commit are the source of truth; a chat summary is not a substitute for source files.
```

## 9. MS3 handoff boundary

Preserve the logical-task/attempt distinction, increasing attempt numbers, session/run checks, atomic command boundary, injected scheduler clock, immutable report receipts, output namespaces, event schema, and fault-harness adapter.

Those are the extension points for later lease deadlines/renewal, expiry-driven state transitions, and rejection of late results. In MS3 the existing recovery oracle should become a passing regression when its expected-failure marker is consciously removed. Scheduler replication, durable scheduler restart, and exactly-once external effects remain separate scope decisions. **This roadmap stops at MS2.** [R §17]

## 10. Sources and supporting references

The continuation package includes the supplied primary sources under `sources/` for portable reference:

- **[A]** [Course project guidelines](sources/cs4094_f26_project_guidelines_v20260824.pdf), version 0.1, 24 August 2026, pp. 2 and 7.
- **[P]** [Approved MS1 specification](sources/CS4069_MS1_Specification.pdf), p. 1.
- **[R]** [Canonical MS2 architecture](sources/CS4094_MS2_Architecture.md), supplied unchanged, §§1–19 and IMPLEMENTATION CONTRACT.
- **[L6]** [Consensus lecture](sources/CS4094_F26_L6_Consensus.pdf), p. 2, ZIP/tar.gz instruction.
- **[H1]** [Hokea README at inspected commit](https://github.com/spin-vt/hokea/blob/427b94634b1736ba8e59d4977836162aa58bd2cb/README.md).
- **[H2]** [Hokea cluster API documentation](https://github.com/spin-vt/hokea/blob/427b94634b1736ba8e59d4977836162aa58bd2cb/docs/api/cluster.md).
- **[H3]** [Hokea storage and durability assumptions](https://github.com/spin-vt/hokea/blob/427b94634b1736ba8e59d4977836162aa58bd2cb/docs/data-and-durability.md).
- **[T1]** [Oracle Java 21 HttpServer](https://docs.oracle.com/en/java/javase/21/docs/api/jdk.httpserver/com/sun/net/httpserver/HttpServer.html), executor and handler behavior.
- **[T2]** [Oracle Java 21 System.nanoTime](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/System.html#nanoTime()), process-local elapsed-time measurement.
- **[T3]** [pytest expected failures](https://docs.pytest.org/en/stable/how-to/skipping.html), strict expected failures, permitted exception types, and `--runxfail`.
- **[T4]** [FFmpeg filters](https://ffmpeg.org/ffmpeg-filters.html), generated test sources and scaling.
- **[T5]** [Docker Compose up](https://docs.docker.com/reference/cli/docker/compose/up/), starting and scaling services.

Technical references support tool behavior. The source of the project's scope and guarantees remains [A], [P], and [R]. The sequential teammate workflow comes from the user's requested collaboration process.
