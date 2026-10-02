# Step 01 — Build, repository, and deployment foundation

```text
Project: CS4094 distributed DAG task scheduler / MS2
Step number and title: 1 — Build, repository, and deployment foundation
Status: DONE on branch ms2/step-01-build-foundation (gate passed). Awaiting integration into main.
Current writer: Hasanlm23123
Next teammate: not assigned
Base commit: 51a979a (82ca8bc + "docs(ms2): close out step 0 baseline acceptance")
Accepted commit: communicated in the handoff message after push (not self-referenced here)
Canonical architecture path and checksum: docs/CS4094_MS2_Architecture.md,
  SHA-256 7d2f931bfcf308ccc2b32a899e8976e75656dab81f51b940df1aa136b37a8ef1 (committed LF blob)
```

## Behavior completed

- `README.md`: toolchain (Java 21 **JDK**, Maven 3.9, Python 3.12, pytest, FFmpeg, Docker/Compose), build, native run, Compose run and test commands.
- `requirements.txt`: pins `pytest==8.3.4`. Grepping `tests/` and `benchmarks/` confirms pytest is the only non-stdlib import.
- Multi-stage Dockerfiles: `scheduler/Dockerfile`, `artifact-store/Dockerfile` and `worker/Dockerfile`. They build with `maven:3.9.9-eclipse-temurin-21` and run on `eclipse-temurin:21.0.5_11-jre-jammy`. The worker image adds apt `ffmpeg`. JVM flags: `-Xmx128m -XX:ActiveProcessorCount=1`. Scheduler and artifact store have curl health checks on `/v1/health`.
- `deploy/compose/compose.yaml`: services `scheduler`, `artifact-store` and `worker`, matching `tests/harness/runtime.py` (ComposeHarness). It honors `SCHEDULER_PORT`, `ARTIFACT_PORT` and `ARTIFACT_DATA_DIR`. Every service is capped at 1 CPU / 512 MiB with `restart: "no"`. Workers have no published port or fixed name.
- `.dockerignore` keeps the build context small.
- `.gitattributes` (`* text=auto eol=lf`) makes working copies LF on every OS. Without it, a Windows `core.autocrlf=true` checkout produces CRLF files whose SHA-256 differs from the recorded canonical checksums. It changes no committed blob.

No Java source, POM, test, or scheduling logic changed. No MS3 mechanism was added.

## Commands run

See `results/handoffs/step-01/COMMANDS.md`. Summary: `mvn -B verify` exited 0 before and after the changes, with 14 JUnit tests passing (6 protocol + 8 scheduler). `docker compose build` exited 0. `up -d --wait scheduler artifact-store` exited 0 with both containers healthy. A worker started via `compose run -d --no-deps worker` connected and polled. `down` exited 0. `pip install -r requirements.txt` and `pytest --collect-only` exited 0 with 22 tests collected.

## Known unverified behavior / environment notes

- Python 3.12 is not verified; only 3.13.1 was available on the verifying host.
- Maven is not vendored (no `mvnw`). Install Maven 3.9.x yourself.
- No pytest integration or fault test was executed, and no job ran through containers.
- The `Makefile` targets (§15) do not exist yet.
- `NativeHarness` uses `os.killpg`, so it needs Linux, macOS, or WSL.
- On an existing Windows clone, the working copy stays CRLF until files are re-checked out (for example, `git rm --cached -r . && git reset --hard` on a clean tree). Fresh clones are LF.

Architecture deviations: none. The artifact-store container runs as root so it can write a host bind mount regardless of host UID. Scheduler and worker run as the non-root user `dag`.

## Explain to the next teammate

- Lifecycle: tasks BLOCKED → READY → ASSIGNED → RUNNING → SUCCEEDED. An explicit failure from ASSIGNED or RUNNING requeues the task at the FIFO tail, and its next assignment gets a higher attempt number. Jobs go ACCEPTED → RUNNING → SUCCEEDED.
- The scheduler alone owns decisions under one mutex. Workers poll, need a start acknowledgment before executing, and publish outputs to the artifact store over HTTP.
- The code intentionally cannot reassign a task owned by a silent or crashed worker. A killed container stays dead (`restart: "no"`).

## Exact next step

Step 2 — Freeze the wire contracts and validate DAGs. First verification command: `mvn -B verify -pl protocol`. Then review `ManifestValidatorTest`'s 6 existing tests against architecture §§3 and 6 before extending them.
