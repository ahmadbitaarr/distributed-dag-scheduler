# Preserved implementation inventory

All 37 preserved paths were byte-compared with the continuation ZIP before Step 0 changes. Production code, tests, POMs and fixtures remain unchanged. Only the canonical architecture filename was reconciled. Existence is not contract acceptance. No later step is DONE.

| Existing checkpoint path | Roadmap review step | Architecture/contract | Exists; verification boundary |
|---|---|---|---|
| `artifact-store/pom.xml` | 1 | §§2,16 | Existing Maven module/dependency configuration |
| `artifact-store/src/main/java/edu/vt/dag/ArtifactMain.java` | 4 | §§6,11 | Staged immutable publication, process-local completed index, GET/HEAD |
| `benchmarks/__init__.py` | 1,7,12 | §16 | Python package marker |
| `benchmarks/run.py` | 12 | §13 / Required benchmark | Draft 45-run benchmark matrix; never executed; native memory cap inadequate |
| `client/pom.xml` | 1 | §§2,16 | Existing Maven module/dependency configuration |
| `client/src/main/java/edu/vt/dag/ClientMain.java` | 6 | §6 | Submit/status CLI |
| `docs/approved-architecture.md` | 0 | All sections / IMPLEMENTATION CONTRACT | Approved architecture renamed byte-for-byte to docs/CS4094_MS2_Architecture.md |
| `pom.xml` | 1 | §§2,16 | Existing Maven module/dependency configuration |
| `protocol/pom.xml` | 1 | §§2,16 | Existing Maven module/dependency configuration |
| `protocol/src/main/java/edu/vt/dag/ApiException.java` | 2,5 | §6 | HTTP/domain error carrier |
| `protocol/src/main/java/edu/vt/dag/ArtifactClient.java` | 4,6 | §§6,11 | HEAD verification, integrity-checked GET, immutable PUT client |
| `protocol/src/main/java/edu/vt/dag/HttpSupport.java` | 1,5 | §§6–7 | Bounded HTTP body/thread helpers; HEAD response handling |
| `protocol/src/main/java/edu/vt/dag/Json.java` | 2 | §6 | Strict JSON serialization/parsing |
| `protocol/src/main/java/edu/vt/dag/ManifestValidator.java` | 2 | §3 / Protocol and structures | DAG, operation, binding, namespace and size checks |
| `protocol/src/main/java/edu/vt/dag/Model.java` | 2 | §§3–6 / Protocol and structures | Typed immutable records, identities, states, namespace |
| `protocol/src/main/java/edu/vt/dag/Transport.java` | 6 | §6 / Happy path and retry behavior | HTTP timeouts and bounded backoff |
| `protocol/src/test/java/edu/vt/dag/ManifestValidatorTest.java` | 2 | Required tests | 6 written JUnit tests; no executed passing JUnit evidence |
| `pytest.ini` | 1,10 | Required tests | Strict pytest markers/XFAIL configuration |
| `scheduler/pom.xml` | 1 | §§2,16 | Existing Maven module/dependency configuration |
| `scheduler/src/main/java/edu/vt/dag/MemoryStateStore.java` | 3 | §§7,11 | Single synchronized memory backend |
| `scheduler/src/main/java/edu/vt/dag/SchedulerCore.java` | 3,5 | §§3–7,14 | Transitions, claims, receipts, detached snapshots, events/metrics |
| `scheduler/src/main/java/edu/vt/dag/SchedulerMain.java` | 5 | §§6–7 | HTTP endpoints; artifact checks outside core command then revalidation |
| `scheduler/src/main/java/edu/vt/dag/SchedulerState.java` | 3 | §§3–5,11 | Memory jobs/tasks/attempts, FIFO, ownership, receipts/events |
| `scheduler/src/main/java/edu/vt/dag/StateStore.java` | 3 | §§7,11 | Command boundary interface |
| `scheduler/src/test/java/edu/vt/dag/SchedulerCoreTest.java` | 3 | Required tests | 8 written JUnit tests; no executed passing JUnit evidence |
| `tests/__init__.py` | 1,7,12 | §16 | Python package marker |
| `tests/conftest.py` | 1,8,10 | Required tests / §14 | Harness selection, evidence fixture, optional XFAIL count enforcement |
| `tests/faults/test_worker_crash.py` | 10 | §10 / Deliberate defect | Typed strict RecoveryNotObserved XFAIL draft; never executed as evidence |
| `tests/harness/__init__.py` | 1,7,12 | §16 | Python package marker |
| `tests/harness/api.py` | 7,8,9 | §§12,14 / Required tests | Manifest factories, HTTP access, export/history checks |
| `tests/harness/runtime.py` | 1,8,11 | §15 | Native launch/kill/collect; draft Compose harness; missing Hokea adapter import |
| `tests/integration/test_system.py` | 7,9 | Required tests / §12 | 21 integration items in historical collection, including video and 9 invalid-DAG variants |
| `worker/pom.xml` | 1 | §§2,16 | Existing Maven module/dependency configuration |
| `worker/src/main/java/edu/vt/dag/Operations.java` | 6,9 | §12 | Allowlisted arithmetic and FFmpeg/video/fixture operations |
| `worker/src/main/java/edu/vt/dag/WorkerMain.java` | 6,10 | §§6–7,10 | Single slot/session, poll/start/execute/upload/report retry and off-by-default gate |
| `workloads/video/fixture.srt` | 9 | §12 | Existing subtitle fixture; provenance documentation pending |
| `workloads/video/sample.mp4` | 9 | §12 | Existing synthetic video fixture; video pipeline verification pending |

## Evidence classification

- **Exists:** five Java modules; 16 Java production files; two JUnit files containing 14 tests; Python harness, integration/fault tests and benchmark draft; video fixtures.
- **Previously tested:** six selected native integration checks against an earlier packaged build. One earlier five-module package succeeded with no JUnit tests to run. See HISTORICAL_EVIDENCE.md for the provenance limit.
- **Not yet verified:** present source as a whole, JUnit tests, remaining integration cases, video outputs, hard-kill recovery oracle, strict XFAIL count, benchmark execution, clean evaluator build, resource caps, Compose and Hokea.
- **Missing:** Makefile; Dockerfiles and Compose service configuration; Hokea adapter; complete README/toolchain instructions, API schemas, workload provenance/functional manifest, revised specification, progress report, independent reproduction and submission artifact. The empty deploy/compose, deploy/hokea, scripts, tests/unit and workloads/functional directories do not implement these features.
- **Environment/build blockers:** GitHub repository access (Step 0); previous Maven JUnit-provider resolution failure; normal Java 21/Maven dependency access must be verified at Step 1; Docker/Compose/course-cluster availability is unverified, not demonstrated absent.

## Frozen failure boundary

The checkpoint core has a synchronized memory command boundary and no recovery timer. No lease, heartbeat expiry, silent-worker recovery, expiry scanning, administrative auto-requeue, scheduler replication/failover, or durable scheduler recovery was added. Explicit accepted failure can return a task to READY; silent worker death intentionally cannot. The worker-crash reassignment property remains broken until MS3. This inspection is not full contract certification.
