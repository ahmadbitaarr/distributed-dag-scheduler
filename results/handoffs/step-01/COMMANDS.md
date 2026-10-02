# Step 1 verification record

Date: 2026-10-02. Host: Windows 11 (10.0.26200), Docker Desktop with a Linux engine.
Base commit: 51a979ae42acfbec4ce22e6eeb9093a716963e3d. Step 1 changed no Java source or POM.

## Tested source identity

The build ran on the base commit's Java/POM trees plus the uncommitted Step 1 files. Those files went into the Step 1 commit unchanged. Git object IDs of the module trees as built:

| Path | Git object at 51a979a |
|---|---|
| pom.xml | 863292c8f3741aabdabde5f1263a0102cffcfd37 |
| protocol | 7a26b20d2aec3b3971332f87b11c60e9c5e3916b |
| scheduler | 56b3f9c550b100a17891ebba9068479c3e6efb29 (the Step 1 commit adds only scheduler/Dockerfile) |
| artifact-store | 4b96bf135777a7003e69704152fa17d43f57501b (the Step 1 commit adds only artifact-store/Dockerfile) |
| worker | 7d168b2905618c2ccb61b9129bed2d085d59c8fd (the Step 1 commit adds only worker/Dockerfile) |
| client | 9c7f69e4aba983e2795b5d8df933ff35cd8e300a |

## Toolchain observed

- Java: OpenJDK 21.0.2 (full JDK, `javac 21.0.2`)
- Maven: Apache Maven 3.9.9. It was not installed on the host, so the official binary archive was unpacked into a temporary directory outside the repo.
- Python: 3.13.1. **Python 3.12 is not installed on this host**, so 3.12 is not yet verified.
- pytest: 8.3.4, from `pip install -r requirements.txt` in a fresh venv
- Docker: client/server 27.1.1; Compose v2.29.1-desktop.1
- Images: maven:3.9.9-eclipse-temurin-21 (sha256:3a4ab3276a087bf276f79cae96b1af04f53731bec53fb2e651aca79e4b10211e), eclipse-temurin:21.0.5_11-jre-jammy (sha256:ebeb51a2a147be42b7d42342fecbeb2d9cb764f7742054024ac9a17bc1c8a21b; runtime Java 21.0.5, Ubuntu 22.04.5)
- Worker image ffmpeg/ffprobe: 4.4.2-0ubuntu0.22.04.1
- Host ffmpeg: not installed. Native video operations were not exercised.

## Commands and results

| # | Command | Exit | Result |
|---|---|---|---|
| 1 | `mvn -B verify` (before any Step 1 change) | 0 | BUILD SUCCESS. protocol: 6 tests, 0 failures. scheduler: 8 tests, 0 failures. artifact-store/worker/client: no tests. See `mvn-verify-before-changes.summary.txt`. |
| 2 | `docker compose -f deploy/compose/compose.yaml build` | 0 | Built dag-ms2/scheduler:0.2.0, dag-ms2/artifact-store:0.2.0, dag-ms2/worker:0.2.0 |
| 3 | `docker compose -f deploy/compose/compose.yaml up -d --wait scheduler artifact-store` | 0 | Both containers reported `(healthy)`. Ports: 127.0.0.1:8080 and 127.0.0.1:8081 |
| 4 | `curl http://127.0.0.1:8080/v1/health` / `:8081/v1/health` | 0 | `{"scheduler_run_id":"886f5890-…","ready":true}` / `{"ready":true}` |
| 5 | `docker compose … run -d --no-deps worker`, then `docker logs` | 0 | Worker emitted `worker_session_started` with the same scheduler_run_id, then `work_empty` polls |
| 6 | `docker exec <worker> ffmpeg -version; ffprobe -version; id -un` | 0 | 4.4.2; user `dag` (non-root) |
| 7 | `docker inspect` restart/NanoCpus/Memory, all 3 containers | 0 | `restart=no nanocpus=1000000000 mem=536870912` for each |
| 8 | `docker compose … down` | 0 | Containers and network removed. The `.runtime/objects` host dir is kept (gitignored) |
| 9 | `pip install -r requirements.txt` (fresh venv, Python 3.13.1) | 0 | pytest 8.3.4 installed |
| 10 | `python -m pytest --collect-only -q` | 0 | 22 tests collected (21 integration + 1 fault). **Not executed.** |
| 11 | `mvn -B verify` (after Step 1 changes) | 0 | BUILD SUCCESS, 14 tests, 0 failures/errors/skips. Full log: `mvn-verify.log` |

## What this does not establish

- No pytest integration or fault test ran, and no job was submitted to any deployment. Service readiness here means only that the health endpoints answered and a worker polled.
- `ComposeHarness` itself was not run end to end. Its compose invocation shape (`up -d --wait scheduler artifact-store`, `run -d --no-deps worker`) was exercised manually.
- The 14 JUnit tests pass but have not been reviewed against the contract. That happens at Steps 2–3.
