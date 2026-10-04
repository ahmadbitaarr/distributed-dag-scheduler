# Distributed DAG Task Scheduler — CS4094 MS2

A distributed DAG task scheduler for a video-processing workload: one scheduler, polling workers, and an immutable HTTP artifact store. The intended semester goal is fault tolerance; MS2 preserves the intentional worker-crash liveness gap described below.

The design is fixed by [docs/CS4094_MS2_Architecture.md](docs/CS4094_MS2_Architecture.md). Work proceeds one step at a time per [docs/implementation-roadmap.md](docs/implementation-roadmap.md). For current status, see [docs/PROGRESS.md](docs/PROGRESS.md), [docs/HANDOFF.md](docs/HANDOFF.md) and [docs/OPEN_ISSUES.md](docs/OPEN_ISSUES.md).

> **MS2 status:** Steps 0–14 are accepted at `f4c5dceef533a98b195d7dfa2e54ec8cac788825`. Step 15 is **PASS — runtime/content audit complete**, using the supported-host results accepted by Planning; the initial Work-environment failures remain historical evidence; see [Step 15 verification](results/handoffs/step-15/VERIFICATION.md). Worker-crash task reassignment remains intentionally absent. Course service execution remains **NOT VERIFIED** after the earlier external Hokea runner mismatch.

Final reports: [MS2 progress report](docs/ms2-progress-report.md), [revised specification](docs/specification.md), [claim-to-test matrix](docs/ms2-claim-evidence.md), and [PDF exports](docs/pdf/README.md). Independent results: [Step 13 verification](results/handoffs/step-13/VERIFICATION.md).

## Required toolchain

| Tool | Version | Notes |
|---|---|---|
| Java | 21 **JDK** | You need the full JDK (e.g. `openjdk-21-jdk`), not only a JRE. With only a JRE, Maven fails with a misleading `release version 21 not supported`. |
| Maven | 3.9.x | Verified with 3.9.9. |
| Python | 3.12 | Provided by the harness container. Host Python is needed for demo, benchmark and offline evidence checks (standard library), and host-driven Compose/Hokea tests (pytest from `requirements.txt`; Hokea additionally needs its pinned package/dependencies). |
| pytest | pinned in `requirements.txt` | The only third-party Python dependency. |
| FFmpeg / ffprobe | any recent | Only workers need these, for video operations. The worker image installs them. |
| Docker + Docker Compose plugin | Engine 27.1.1 / Compose 2.29.1 in Step 12; Engine 29.7.2 / Compose v5.5.1 in Step 13 | Use `docker compose`, not the legacy standalone command. |
| POSIX shell and Make | recipes in `Makefile` | Used by the evaluator targets; see the direct shell alternative below. |

The native test harness (`tests/harness/runtime.py`, `NativeHarness`) uses POSIX process groups (`os.killpg`). Run it on Linux, macOS, or WSL. The Compose backend also needs Docker.

**Windows users: enable long paths before cloning or pulling.** Some committed evidence paths under `results/handoffs/step-10/` exceed Windows' 260-character limit. Without long paths, `git clone`, `git pull` and `git switch` fail partway with `Filename too long` and leave a half-updated working tree.

```bash
git config --global core.longpaths true
```

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
| `make test` | In the Linux harness container: `mvn -B verify`, then the full pytest suite. Requires **exactly one** XFAIL, the intentional worker-crash oracle. Evidence goes to `results/latest-tests/<unique-run>/<test>/`. |
| `make fault-demo` | Build and run the same crash oracle with `--runxfail`. MS2 must return nonzero specifically from `RecoveryNotObserved`; evidence is retained. |
| `make bench` | Build Compose images and run the full concurrent-jobs × workers × five-repetitions matrix. Raw and summary data go to `results/benchmark/<UTC timestamp>/`. |
| `make down` | Stop the deployment. Artifact files and `results/` are kept. |

On Windows without `make`, run the recipe lines from `Makefile` directly, for example `sh deploy/harness/run.sh` from Git Bash. A Linux/WSL-native checkout avoids the earlier OneDrive bind-mount issue.

A complete local flow from the repository root is:

```bash
java -version
mvn -version
python3 --version
docker compose version
docker info
make build
make up
make demo
make down
make test
# Run separately: this must be nonzero solely from RecoveryNotObserved.
make fault-demo
fault_status=$?
printf "fault-demo shell exit: %s\n" "$fault_status"
# The intended fault failure does not skip these later commands.
make bench
make down
```

Use a shell without `set -e` for this walkthrough, or run fault-demo separately. Inspect the traceback and cleanup evidence as well as the actual exit: build/setup/probe/safety/export/cleanup failures are not the intended demonstration. Step 13 recorded the intentional nonzero result but did not preserve its shell `$?`; no historical code is inferred. `make test` independently deploys native services inside the harness container; `make demo` uses the live Compose deployment. The first `make down` releases the demo services before testing/benchmarking. Stop any native processes launched manually as well.

### Client upload, submit, status and fetch

After building the JARs and starting a deployment, the existing CLI can be used directly:

```bash
# Prints an immutable source descriptor; this fixture upload is separate from the arithmetic DAG.
java -jar client/target/client-0.2.0.jar upload workloads/video/fixture.srt
java -jar client/target/client-0.2.0.jar submit workloads/functional/functional.json
java -jar client/target/client-0.2.0.jar status 00000000-0000-4000-8000-000000000001
# Repeat status until SUCCEEDED, then substitute outputs.result.key from its JSON:
java -jar client/target/client-0.2.0.jar fetch '<outputs.result.key>' results/client-result.txt
```

The committed functional manifest has that stable job ID; submitting identical content with the same ID replays the original job. Use a new UUID in a copy of the manifest for a new job. For a video submission, upload its source objects and place the returned descriptors in the source bindings described in [docs/api.md](docs/api.md); `make demo` does this automatically. A successful arithmetic fetch contains `result=22`. The CLI honors `SCHEDULER_URL` and `ARTIFACT_BASE_URL` for nondefault addresses. These four operations are covered by `test_java_client_upload_submit_status_fetch`.

### Benchmark and saved evidence

`make bench` runs the Step 12 matrix: C=1/4/16, W=1/2/4, five fresh deployments per configuration, four excluded warmup jobs and 24 measured six-task jobs per run. No faults are injected. For a small reproduction, use a fresh output directory:

```bash
docker compose -f deploy/compose/compose.yaml build
python3 -m benchmarks.run --backend compose --out results/benchmark/verify-$(date -u +%Y%m%dT%H%M%SZ) --configs c1-w1 --repetitions 1
python3 -m benchmarks.report '<completed-benchmark-directory>'
```

The driver writes `environment.json`, `runs.csv`, `jobs.csv`, `tasks.csv`, `summary.csv` and `summary.json`; per-run harness evidence is retained below its output root. It exports and tears down each fresh deployment. Use the report generator on a completed directory; do not overwrite the accepted results under `results/handoffs/step-12/`. Those 45 measured runs and the independent Step 13 one-repetition result are different experiments. See [docs/handoffs/step-12.md](docs/handoffs/step-12.md) for aggregation, aborted runs and shared-host limitations; there is no recovery-time measurement.

Test exports live in `results/latest-tests/<fresh-run>/<test>/`, demo outputs in `results/demo/<timestamp>/`, and benchmark output in the directory printed by the driver. Only selected committed evidence is under `results/handoffs/`. With host Python, recheck every exported test/benchmark history as follows:

```bash
python3 - '<export-root>' <<'PY'
from pathlib import Path
import sys
from tests.harness.check_evidence import check_directory
paths = sorted(Path(sys.argv[1]).rglob('manifests.json'))
if not paths:
    raise SystemExit('No exported histories found')
for manifest in paths:
    print(manifest.parent, check_directory(manifest.parent))
PY
```

Any exception is a real validation failure. The demo uses its own manifest/summary layout and checks histories live; it is not a `check_evidence` directory. Inspect `metadata.json` for actual source attribution, outcome, export and cleanup success, plus fault/probe/safety files for the crash oracle. The 40/40 Step 13 count comes from its committed verification record; generated directories in the original checkout are not reproduced by that summary alone.

Normal test/benchmark cleanup is harness-owned, including after the intentional failure. `make down` keeps `.runtime/objects` and `results/` for inspection; scheduler state and the store index are not restored from those retained files. For interrupted Compose/Hokea runs, inspect their recorded run-owned resource names and follow [deploy/hokea/README.md](deploy/hokea/README.md) for Hokea cleanup. Remove only resources belonging to that run. Preserve evidence before discarding runtime object directories; do not use blanket Docker prune or namespace deletion.

## Tests

The suite runs in a pinned Linux harness container, so the host needs only Docker:

```bash
sh deploy/harness/run.sh                              # = make test
sh deploy/harness/run.sh sh -c 'mvn -B -q package -DskipTests && pytest -q tests/integration/test_api.py'
MS2_BACKEND=compose pytest -q tests/integration/test_system.py     # host Python: drive real containers
```

The harness image is `deploy/harness/Dockerfile`: Ubuntu 24.04, JDK 21, Maven 3.9.9, Python 3.12, pytest from `requirements.txt`, and FFmpeg. It works on a container-local copy of the checkout and copies evidence back.

| Suite | Location | Contents |
|---|---|---|
| JUnit | `*/src/test/java` | Wire contract and DAG validation, the scheduler state machine (including concurrency and the silent-owner gap), and the artifact store over real HTTP. |
| Unit (pytest) | `tests/unit/` | History-checker falsification, fault-oracle checks and Hokea adapter/packaging tests. |
| Integration | `tests/integration/` | API, worker and client lifecycle, the functional workload, replay and retry safety, and the video pipeline. |
| Fault | `tests/faults/` | The worker-crash reassignment oracle: one strict XFAIL limited to `RecoveryNotObserved`. |

`pytest.ini` enables `xfail_strict`, and `MS2_REQUIRE_XFAIL=1` fails the run unless exactly one XFAIL occurs. Service-backed tests using the system fixture export their evidence; pure unit tests do not launch a deployment. `python -m tests.harness.check_evidence <dir>` re-checks the safety invariants offline. See [docs/evidence.md](docs/evidence.md).

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

## Step 10 crash demonstration

The worker-crash oracle demands recovery. Only its final `RecoveryNotObserved`
is an expected strict XFAIL in normal acceptance. `make fault-demo` disables that
marker with `--runxfail` and must fail visibly for the same oracle; infrastructure,
probe, safety, export and cleanup errors are never expected failures.

Only gated A gets `OPERATION_TIMEOUT_MS=120000`; the normal 30000 ms default is
unchanged. The test proves the original attempt is still RUNNING immediately
after SIGKILL, verifies B's independent probe and both histories, records a
10-second harness-monotonic observation, and requires a new B claim after a
scheduler-sequence boundary captured at least 8 seconds into that interval.
The 10 seconds are an observation budget, not a universal recovery-time bound.
Request delays and actual elapsed time are recorded.

Each pytest invocation chooses a unique run directory. `MS2_RUN_LABEL` can set a
readable unique name; the fixture refuses a populated test directory before startup.
Always use a fresh label across container runs: their temporary source copies do
not include earlier host results, so copy-back does not yet reject a reused label.
`MS2_SOURCE_REV` can identify a source manifest when testing a ZIP without Git
metadata. The Docker runner otherwise records local HEAD and a dirty marker.
Native, Compose, acceptance and real-failure evidence must be retained separately.

The Linux harness runs native services inside one container. For Compose use
host Python (with requirements.txt installed), not Docker-in-Docker:

```bash
docker compose -f deploy/compose/compose.yaml build
unset MS2_RUN_LABEL  # let the fixture choose a fresh timestamp+UUID
MS2_BACKEND=compose MS2_REQUIRE_XFAIL=1 python3 -m pytest -q tests/faults/test_worker_crash.py
```

Set `MS2_SOURCE_REV` to the actual tested source before a host-Python run; a dirty implementation requires its own accurate identifier. Steps 10–13 are accepted. Historical Step 10 handoffs retain intermediate blocked states for provenance; current acceptance is documented by `results/handoffs/step-11/FINAL-RESULTS.md` and `results/handoffs/step-13/VERIFICATION.md`. Step 13 reported 86 passes, exactly one intentional XFAIL and no failures, and separately exposed the sole `RecoveryNotObserved` failure.
