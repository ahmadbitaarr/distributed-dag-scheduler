# Distributed DAG Task Scheduler (CS4094, MS3)

We built this scheduler to run DAGs of video-processing tasks. One scheduler tracks dependencies and assigns ready work to workers that poll it. Workers exchange inputs and outputs through an immutable artifact store. MS3 adds leases: if a worker crashes or stops renewing, its unfinished task returns to the queue and another worker can take it. The scheduler rejects the expired attempt's later messages.

| Read this | For |
|---|---|
| [docs/specification.md](docs/specification.md) | What the system guarantees (safety, liveness, fault model, performance) and how to falsify each claim |
| [docs/test-matrix.md](docs/test-matrix.md) | Which test validates which property, and how to add tests |
| [docs/ms3-progress-report.md](docs/ms3-progress-report.md) | Changes since MS2, design choices, test and benchmark results, known limitations |
| [docs/api.md](docs/api.md), [docs/evidence.md](docs/evidence.md) | Wire contract; event schema and the history checker |
| [results/ms3-logs/](results/ms3-logs/) | Run logs and evidence for every test in the submitted run |

## Quick start: run the whole test suite with one command

You need Docker with the Compose plugin, `make` and a POSIX shell. The pinned Linux harness container supplies the language tools, so you do not need Java or Python installed on the host for `make test`.

```bash
git clone https://github.com/ahmadbitaarr/distributed-dag-scheduler.git
cd distributed-dag-scheduler
make test
```

Start with `make test`. It builds the harness, compiles the modules, runs 77 JUnit tests, then runs the pytest unit, integration and fault suites. Service-backed tests use real scheduler, artifact-store and worker processes. The submitted run finished with `102 passed`. Allow about 10–15 minutes after image setup; timing depends on the host. The suite permits no expected failures (`MS2_REQUIRE_XFAIL=0`) and writes per-test evidence to `results/latest-tests/<run>/<test>/`.

On Windows, use Git Bash (`sh deploy/harness/run.sh` is the same as `make test`), and set `git config --global core.longpaths true` before cloning, because some committed evidence paths are long.

## Commands

| Command | What it does |
|---|---|
| `make test` | Everything: JUnit plus all pytest suites, in the Linux harness container. |
| `make faults` | Only the fault-injection tests (crash, restart, pause, message loss/delay/duplication, partition, chaos). |
| `make fault-demo` | Only the original worker-crash reassignment oracle (MS2's intentional failure, passing since MS3). |
| `make build` | `mvn -B verify` on the host (needs JDK 21 and Maven 3.9). |
| `make up` / `make demo` / `make down` | Start scheduler, artifact store and `WORKERS` (default 3) workers with Docker Compose; run the functional and video demos against them (outputs in `results/demo/`); stop. |
| `make bench` | Fault-free benchmark matrix: C ∈ {1,4,16} concurrent jobs × W ∈ {1,2,4} workers × 5 runs. |
| `make bench-recovery` | Recovery experiment: W = 4, C ∈ {1,4,16}, baseline vs. two worker kills per run, 3 runs each. |

For a smaller check, run a subset inside the same harness container:

```bash
sh deploy/harness/run.sh sh -c 'mvn -B -q package -DskipTests && pytest -q tests/faults/test_network_faults.py'
```

You can also check saved evidence without starting services. This needs only standard-library Python:

```bash
python3 -m tests.harness.check_evidence results/latest-tests/<run>/*/
```

## How the components work together

```
 client ──submit/status──▶  SCHEDULER (one process, one mutex, in-memory state, leases)
   │                          ▲   claim / start / heartbeat / report (workers pull; scheduler never calls out)
   │ upload/fetch             │
   ▼                        WORKERS (one task each; heartbeat every lease/5)
 ARTIFACT STORE ◀──get inputs / put outputs (immutable, SHA-256 verified, per-attempt keys)
```

- **Task states:** BLOCKED → READY → ASSIGNED → RUNNING → SUCCEEDED. An explicit failure or an **expired lease** sends the task back to READY (end of the FIFO queue), and its next attempt gets `attempt_no + 1`.
- **Attempt states:** ASSIGNED, RUNNING, SUCCEEDED, FAILED, EXPIRED. Any message from an EXPIRED attempt gets `409 LEASE_EXPIRED`.
- **Ownership** is the tuple `(scheduler_run_id, job_id, task_id, attempt_no, worker_session_id)`. The attempt number is the fencing token, and outputs live under `runs/<run>/jobs/<job>/tasks/<task>/attempts/<n>/`.

## Running the services yourself

```bash
mvn -B verify                                   # JDK 21 + Maven 3.9; produces <module>/target/<module>-0.2.0.jar
PORT=8081 DATA_DIR=.runtime/objects java -jar artifact-store/target/artifact-store-0.2.0.jar
PORT=8080 ARTIFACT_BASE_URL=http://localhost:8081 java -jar scheduler/target/scheduler-0.2.0.jar
SCHEDULER_URL=http://localhost:8080 ARTIFACT_BASE_URL=http://localhost:8081 java -jar worker/target/worker-0.2.0.jar   # one per worker
java -jar client/target/client-0.2.0.jar <upload|submit|status|fetch> ...
```

Or with Docker Compose (each service capped at 1 CPU / 512 MiB, `restart: "no"`):

```bash
docker compose -f deploy/compose/compose.yaml up -d --build --wait scheduler artifact-store
docker compose -f deploy/compose/compose.yaml run -d --no-deps worker    # add a worker
docker compose -f deploy/compose/compose.yaml down
```

| Setting | Service | Default | Meaning |
|---|---|---|---|
| `LEASE_TIMEOUT_MS` | scheduler | 5000 | Lease length; recovery time is about this long |
| `LEASE_SCAN_MS` | scheduler | 100 | Background expiry scan period |
| `HEARTBEAT_INTERVAL_MS` | worker | lease / 5 | Renewal period (read from `/v1/health` unless set) |
| `POLL_INTERVAL_MS` | worker | 100 | Idle claim interval |
| `OPERATION_TIMEOUT_MS` | worker | 30000 | Longer operations fail explicitly and are retried |
| `ENABLE_TEST_HOOKS` | worker | false | Test-only stall points; never enable in a deployment |

Example job: `java -jar client/target/client-0.2.0.jar submit workloads/functional/functional.json`, then `status 00000000-0000-4000-8000-000000000001` until `SUCCEEDED`, then `fetch '<outputs.result.key>' out.txt` gives `result=22`. The manifest format and operation allowlist are in [docs/api.md](docs/api.md).

## Tests

| Suite | Location | Contents |
|---|---|---|
| JUnit | `*/src/test/java` | Wire contract and DAG validation; scheduler state machine; **leases on an injected clock** (`LeaseTest`); artifact store over HTTP. |
| Unit | `tests/unit/` | History-checker falsification, crash-oracle safeguards, Hokea adapter/packaging. |
| Integration | `tests/integration/` | API, worker lifecycle, Java client, retries, replays, the functional and video workloads. |
| Faults | `tests/faults/` | Crashes at every attempt stage, restart, pause, slow tasks, lost/delayed/duplicated messages, partitions, a seeded chaos run, and the crash-reassignment oracle. |

We save the scheduler history, worker logs, snapshots and metrics for each service-backed test. Network tests also save the proxy's fault log. The checker looks for safety violations in those records. The native harness needs POSIX process control, so use Linux/macOS/WSL for direct pytest runs or use `make test`. For tests without the in-process fault proxy, `MS2_BACKEND=compose` runs real containers from host Python.

## Workloads

- `workloads/functional/`: five-task DAG A=3 → B=7, C=15 → D=22 → `result=22`.
- `workloads/video/`: a byte-reproducible 10 s 1280×720 synthetic clip and fixture subtitles; DAG inspect → 720p / 360p / thumbnail / subtitles → publish.

## Repository layout

| Path | Contents |
|---|---|
| `protocol/`, `scheduler/`, `artifact-store/`, `worker/`, `client/` | Java 21 Maven modules |
| `tests/harness/` | Deployment adapters (native, Compose, Hokea), fault proxy, history checker, demo driver |
| `tests/unit`, `tests/integration`, `tests/faults` | pytest suites |
| `benchmarks/` | `run.py` (fault-free matrix), `recovery.py` (crash experiment), `report.py` |
| `deploy/` | Compose file, harness container, Hokea adapter |
| `docs/` | Specification, progress reports, API, evidence schema, test matrix, MS2 architecture and roadmap, step handoffs |
| `results/` | Committed run logs and evidence (`ms3-logs/`, `handoffs/step-XX/`) |

We kept the MS2 architecture, roadmap, handoffs and report unchanged under `docs/` so reviewers can see how the project developed. The current test results and benchmark limitations are in the MS3 report; course-cluster execution remains unverified.
