# Distributed DAG Task Scheduler — CS4094 MS2

A fault-tolerant distributed DAG task scheduler for a video-processing workload: one scheduler, polling workers, and an immutable HTTP artifact store.

The design is fixed by [docs/CS4094_MS2_Architecture.md](docs/CS4094_MS2_Architecture.md). Work proceeds one step at a time per [docs/implementation-roadmap.md](docs/implementation-roadmap.md). For current status, see [docs/PROGRESS.md](docs/PROGRESS.md), [docs/HANDOFF.md](docs/HANDOFF.md) and [docs/OPEN_ISSUES.md](docs/OPEN_ISSUES.md).

> **MS2 status:** this is an in-progress milestone. Worker-crash task reassignment is **intentionally not implemented** in MS2. It is the milestone's demonstrated liveness failure.

## Required toolchain

| Tool | Version | Notes |
|---|---|---|
| Java | 21 **JDK** | You need the full JDK (e.g. `openjdk-21-jdk`), not only a JRE. With only a JRE, Maven fails with a misleading `release version 21 not supported`. |
| Maven | 3.9.x | Verified with 3.9.9. |
| Python | 3.12 | Used for pytest orchestration, the harness and benchmarks. |
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

## Tests

```bash
python3.12 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
mvn -B verify                         # JUnit
pytest                                # integration + fault tests (native backend by default)
MS2_BACKEND=compose pytest            # same tests against the Compose deployment
```

`pytest.ini` enables `xfail_strict`. The MS2 suite is expected to have exactly one strict, narrowly typed XFAIL: the worker-crash reassignment oracle in `tests/faults/`. Integration and fault tests are verified at later roadmap steps. See [docs/PROGRESS.md](docs/PROGRESS.md) for which ones currently have evidence.

The top-level `make up | demo | test | fault-demo | bench | down` targets required by the architecture (§15) do not exist yet. They are added at later roadmap steps.

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
| `workloads/` | Video sample and fixture subtitles |
| `deploy/compose/` | Local Docker Compose deployment |
| `docs/` | Architecture, roadmap, progress, handoffs, open issues |
| `results/handoffs/` | Per-step verification evidence |
