# Distributed DAG Task Scheduler — CS4094 MS2

A fault-tolerant distributed DAG task scheduler for a video-processing workload: one scheduler, polling workers, and an immutable HTTP artifact store.

The design is fixed by [docs/CS4094_MS2_Architecture.md](docs/CS4094_MS2_Architecture.md). Work proceeds one step at a time per [docs/implementation-roadmap.md](docs/implementation-roadmap.md). For current status, see [docs/PROGRESS.md](docs/PROGRESS.md), [docs/HANDOFF.md](docs/HANDOFF.md) and [docs/OPEN_ISSUES.md](docs/OPEN_ISSUES.md).

> **MS2 status:** this is an in-progress milestone. Worker-crash task reassignment is **intentionally not implemented** in MS2. It is the milestone's demonstrated liveness failure.

## Required toolchain

| Tool | Version | Notes |
|---|---|---|
| Java | 21 **JDK** | You need the full JDK (e.g. `openjdk-21-jdk`), not only a JRE. With only a JRE, Maven fails with a misleading `release version 21 not supported`. |
| Maven | 3.9.x | Verified with 3.9.9. |
| Python | 3.12 | Used for pytest orchestration, the harness and benchmarks. Provided by the harness container. A host Python is needed only for `make demo` and the Compose backend (standard library plus pytest). |
| pytest | pinned in `requirements.txt` | The only third-party Python dependency. |
| FFmpeg / ffprobe | any recent | Only workers need these, for video operations. The worker image installs them. |
| Docker + Docker Compose v2 | Engine 27.x, Compose 2.29 verified | Used for the containerized deployment. |

The native test harness (`tests/harness/runtime.py`, `NativeHarness`) uses POSIX process groups (`os.killpg`). Run it on Linux, macOS, or WSL. The Compose backend also needs Docker.

## Build

```bash
mvn -B verify
```

This compiles all five modules (`protocol`, `scheduler`, `artifact-store`, `worker`, `client`) and runs the module JUnit tests. Each service module produces a runnable shaded JAR at `<module>/target/<module>-0.2.0.jar` (no `-shaded` suffix).

## Run natively

```bash
# artifact store (PORT default 8081, DATA_DIR default .runtime/objects)
PORT=8081 DATA_DIR=.runtime/objects java -Xmx128m -jar artifact-store/target/artifact-store-0.2.0.jar
# scheduler (PORT default 8080)
PORT=8080 ARTIFACT_BASE_URL=http://localhost:8081 java -Xmx128m -jar scheduler/target/scheduler-0.2.0.jar
# one worker per process (one execution slot each)
SCHEDULER_URL=http://localhost:8080 ARTIFACT_BASE_URL=http://localhost:8081 java -Xmx128m -jar worker/target/worker-0.2.0.jar
```

Optional worker settings: `POLL_INTERVAL_MS` (default 100) and `OPERATION_TIMEOUT_MS` (default 30000). `HOKEA_HEALTH_PORT` enables a worker health endpoint for the course cluster. Test hooks (`ENABLE_TEST_HOOKS`) are off by default.

The client CLI uses `SCHEDULER_URL` and `ARTIFACT_BASE_URL` with the same defaults: `java -jar client/target/client-0.2.0.jar <upload|submit|status|fetch> ...`.

Health: `curl http://localhost:8080/v1/health` and `curl http://localhost:8081/v1/health`.

## Run with Docker Compose

Each service has a multi-stage Dockerfile (`scheduler/`, `artifact-store/`, `worker/`) whose build context is the repository root. Every container is capped at 1 CPU and 512 MiB, with a 128 MiB JVM heap and `restart: "no"`.

```bash
docker compose -f deploy/compose/compose.yaml build
docker compose -f deploy/compose/compose.yaml up -d --wait scheduler artifact-store
docker compose -f deploy/compose/compose.yaml run -d --no-deps worker   # add a worker
docker compose -f deploy/compose/compose.yaml down                      # artifact files are kept
```

Ports bind to `127.0.0.1`: scheduler `${SCHEDULER_PORT:-8080}` and artifact store `${ARTIFACT_PORT:-8081}`. Artifact bytes go to the host directory `${ARTIFACT_DATA_DIR:-.runtime/objects}`. Workers have no published port and no fixed container name. The service names and these variables are the contract used by `ComposeHarness` in `tests/harness/runtime.py`.

Pinned images: `maven:3.9.9-eclipse-temurin-21` (build stage) and `eclipse-temurin:21.0.5_11-jre-jammy` (runtime). The worker runtime adds Ubuntu 22.04's `ffmpeg` package (4.4.2 when verified).

## Evaluator commands

| Command | What it does |
|---|---|
| `make build` | `mvn -B verify`: compile and run the JUnit tests. |
| `make up` | Build the images and start the scheduler, the artifact store and `WORKERS` (default 3) workers via Compose. Waits for readiness. |
| `make demo` | Against `make up`: upload the committed workloads and run the functional DAG and the video DAG. Checks the results and writes all outputs to `results/demo/<timestamp>/`. |
| `make test` | In the Linux harness container: `mvn -B verify`, then the full pytest suite. Requires **exactly one** XFAIL, the intentional worker-crash oracle. Evidence goes to `results/latest-tests/`. |
| `make down` | Stop the deployment. Artifact files and `results/` are kept. |

`make fault-demo` and `make bench` are added at roadmap Steps 10 and 12. On Windows without `make`, run the recipe lines from `Makefile` directly, for example `sh deploy/harness/run.sh` from Git Bash.

## Tests

The suite runs in a pinned Linux harness container, so the host needs only Docker:

```bash
sh deploy/harness/run.sh                              # = make test
sh deploy/harness/run.sh pytest -q tests/integration/test_api.py   # any command, run in the harness
MS2_BACKEND=compose pytest -q tests/integration/test_system.py     # host Python: drive real containers
```

The harness image is `deploy/harness/Dockerfile`: Ubuntu 24.04, JDK 21, Maven 3.9.9, Python 3.12, pytest from `requirements.txt`, and FFmpeg. It works on a container-local copy of the checkout and copies evidence back.

| Suite | Location | Contents |
|---|---|---|
| JUnit | `*/src/test/java` | Wire contract and DAG validation, the scheduler state machine (including concurrency and the silent-owner gap), and the artifact store over real HTTP. |
| Unit (pytest) | `tests/unit/` | The history checker falsifies each safety invariant on a real saved history. |
| Integration | `tests/integration/` | API, worker and client lifecycle, the functional workload, replay and retry safety, and the video pipeline. |
| Fault | `tests/faults/` | The worker-crash reassignment oracle: one strict XFAIL limited to `RecoveryNotObserved`. |

`pytest.ini` enables `xfail_strict`, and `MS2_REQUIRE_XFAIL=1` fails the run unless exactly one XFAIL occurs. Every test exports its evidence. `python -m tests.harness.check_evidence <dir>` re-checks the safety invariants offline. See [docs/evidence.md](docs/evidence.md).

## Workloads

- [workloads/functional/](workloads/functional/): the five-task DAG (A=3 → B=7, C=15 → D=22 → `result=22`) with expected outputs.
- [workloads/video/](workloads/video/): a synthetic, reproducible 10 s 1280×720 sample, fixture subtitles, checksums and provenance. The video DAG is inspect → 720p / 360p / thumbnail / subtitles → publish.

## Repository layout

| Path | Contents |
|---|---|
| `protocol/` | Typed manifests, identities, DAG validation, HTTP/JSON helpers |
| `scheduler/` | Scheduler core, in-memory state store, HTTP API |
| `artifact-store/` | Immutable object PUT/HEAD/GET service |
| `worker/` | Polling worker and allowlisted operations |
| `client/` | CLI for upload, submit, status and fetch |
| `tests/` | pytest harness, integration and fault tests |
| `benchmarks/` | Benchmark driver |
| `workloads/` | Functional and video workloads with provenance |
| `deploy/compose/` | Local Docker Compose deployment |
| `deploy/harness/` | Linux harness/client container for tests |
| `docs/` | Architecture, roadmap, API contract (`api.md`), evidence and event schema (`evidence.md`), progress, handoffs, open issues |
| `results/handoffs/` | Per-step verification evidence |
