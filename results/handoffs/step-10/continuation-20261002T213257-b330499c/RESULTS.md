# Step 10 continuation results — 2026-10-02

**Status: BLOCKED. Implementation source unchanged.**
The attached blocked checkpoint was revalidated before edits or new verification.
Only coordination documentation and additional evidence changed. No Git action
or Step 11 work occurred.

Accepted baseline: `main @ 9bfd6d339d754475bcf218179f1cffdd4c07eeb3` (user supplied).
Authoritative continuation input ZIP SHA-256:
`89238dfdbe287cc2624c5606aeaf708dc53ffbeb6bb0a4e7c20703c1cee7290c`.
All 255 packaged input files matched the working tree at the start. The two
separately attached Markdown documents also matched their copies inside the ZIP.

Source identifier for both new native runs:
`9bfd6d339d754475bcf218179f1cffdd4c07eeb3+local-step10:sha256:83c1d8789c58643c2ea74015008c38e4a058957e6b0a477f0bfe9b881e7c62ae`.
All 63 files in the preserved implementation manifest verified. No implementation
manifest was regenerated because no implementation file changed.

## Actual commands and results

All commands below ran from the project root. `checks/<label>/command.json`
contains exact argv, cwd, environment overrides and exit status;
`command.log` contains full raw output. For native commands PATH selects the
outside-project temporary Python environment and JDK 21.0.8; MS2_BACKEND=native.
MS2_REQUIRE_XFAIL=1 was set only for the full native acceptance command. Each
native run has a unique label and the source ID above.

| Command / check | Actual result | Exit |
|---|---|---:|
| `python3 -m tests.harness.check_evidence results/handoffs/step-10/native-strict/test_worker_crash_reassignment` | Preserved two job histories passed | 0 |
| `sha256sum -c results/handoffs/step-10/source-SHA256SUMS.txt` | All 63 files OK | 0 |
| `docker compose version` | docker executable absent | 127 |
| `docker info` | docker executable absent | 127 |
| `python3 -m pytest --version` (initial default interpreter) | No module named pytest | 1 |
| `python3 -m pytest --version` (restored temporary environment) | pytest 8.3.4 | 0 |
| `make test` | Runner stopped at docker build: docker not found, recipe Error 127; no tests reached | 2 |
| `make fault-demo` | Same Docker prerequisite failure; did not reach the oracle | 2 |
| `MS2_REQUIRE_XFAIL=1 python3 -m pytest` (native) | **62 passed, 1 xfailed**, 240.98 s; zero XPASS/errors/unexpected failures | 0 |
| `python3 -m pytest -q --runxfail tests/faults/test_worker_crash.py` (native) | **1 failed**, 18.59 s; sole failure is final RecoveryNotObserved | 1 |
| `python3 -m tests.harness.check_evidence <all 38 retained native-acceptance directories>` | 38 directories accepted, 29 exported job histories checked | 0 |
| `python3 -m tests.harness.check_evidence <retained native-runxfail fault directory>` | 2 exported job histories checked | 0 |

The last two expanded argument lists are preserved in their command JSON files.
They target retained milestone copies, not temporary runtime state. Some API or
external-client test directories export zero tracked histories; the 29 count
refers to histories actually present and checked, not every job created by the
suite. All 38 runtime test metadata files record successful cleanup. The 25 unit
tests do not start services and therefore have no system-fixture directory.

The measured **61 JUnit passes** belong to the checkpoint's prior
`checks/java-acceptance/` run. Java verification was not unnecessarily repeated.
The new native suite uses its unchanged local packaged JARs; their SHA-256 values
are retained in `reused-build-SHA256SUMS.txt`. Those JARs are excluded from the ZIP.
These native results do not claim that the Docker-backed `make test` passed.

The temporary environment was restored outside the project using the existing
pinned `requirements.txt`. Setup commands and exact package versions are in
`environment.json`. Current approval review allowed this dependency setup and
local socket/process tests. The earlier usage-limit approval failure is historical,
not the active blocker. Docker CLI, daemon executable, Podman and Docker socket
remain absent. No Compose crash run was attempted again after that capability
check, and no Docker result was fabricated.

## New fault evidence

| Fact | Native acceptance strict XFAIL | Native real failure (--runxfail) |
|---|---|---|
| Scheduler run | `1c5b4cc2-3d61-4bbd-9d01-308d1f390513` | `2c5cd58a-9ff5-4455-a0cb-2ff958c1cfac` |
| X job | `3a6b5463-9d76-466e-b326-46b1d6594bec` | `4eb75563-a409-4c4e-a6bf-95e5bf8e608a` |
| A session | `5a1db8b4-8784-4acd-8378-b8524205507f` | `16232782-253f-4eba-ad79-b7528a381b43` |
| B session | `d48e2e4b-9a95-4a35-9747-e3f672e0de34` | `7356c34b-affd-4d28-8d1f-9ff12ea6227f` |
| A PID / SIGKILL exit | 4934 / -9 | 5117 / -9 |
| Original X attempt | 1 | 1 |
| Observation duration | 10.000123923 s | 10.000126193 s |
| Samples / B claim-empty pairs | 39 / 92 | 39 / 92 |
| Fresh late claim pairs | 18 | 17 |
| Cleanup | true | true |

Both experiments reached the acknowledged-start, operation-start, pre-publication
gate; hard-killed original A; confirmed original RUNNING ownership without a
report/retry; started distinct-session B; completed its independent probe; checked
both histories; verified health and late polling; and raised the final recovery
oracle. X remained RUNNING under dead A, Y BLOCKED, job RUNNING. `safety-checks.json`,
`fault.json`, `gate.json`, before/after snapshots, worker/scheduler events,
`observation-window.json`, polling pairs and the exact traceback are preserved.
The observations use harness monotonic timing and causal scheduler sequence
boundaries. Ten seconds is a controlled observation budget, not a recovery bound.

The real-failure run has metadata outcome=failed, xfail=false, cleanup_succeeded=true.
Its only test failure is `test_worker_crash.RecoveryNotObserved`; setup, probe,
safety, export and cleanup did not fail. This verifies the underlying native
oracle; the actual Make target still needs a successful Docker execution path.

## Remaining external environment gate

Only Docker-capable verification remains: Compose strict XFAIL, actual `make test`,
actual `make fault-demo`, and offline checks of their retained outputs. Follow the
single sequence in [EXTERNAL-VERIFICATION.md](EXTERNAL-VERIFICATION.md). It records
actual statuses, verifies why the demo failed, uses fresh labels, and retains raw
evidence without runtime objects. Do not mark Step 10 complete until these gates
produce the required observed results and the user accepts the Git handoff.

S10-03 remains a documented limitation: deliberately reusing a container run label
can overwrite host results. This continuation used fresh unique labels throughout.
No universal overwrite prevention is claimed, and no implementation change was
made merely to perfect that behavior.

## Evidence and preservation

- `native-acceptance/`: 38 retained runtime test evidence directories.
- `native-runxfail/`: separately retained real-failure experiment.
- `checks/`: exact commands, output and statuses, including Make prerequisite failures.
- `RESULTS.json`: measured summary derived from actual command logs and runtime JSON.
- `environment.json`, `context.json`, source and reused-JAR manifests: attribution.
- `input-coordination/`: exact prior coordination documents before this update.
- `package-checks.json` and `checkpoint-SHA256SUMS.txt`: this continuation package's integrity record.

Original `results/handoffs/step-10/COMMANDS.md`, blocker records and packaging
manifests describe the earlier checkpoint and remain unchanged. Their statements
that some commands had not run are historical; this report supplies the current
results. Historical Step 0–9 files and all prior raw Step 10 evidence are unchanged.

Architecture deviations: none. No production, test, build, Make or deployment
implementation changed. No leases, heartbeats/expiry, ownership expiration,
scanner, silent-worker/admin requeue, automatic A restart, scheduler replication,
failover or durable recovery was introduced. No Step 11 handoff is issued while
Step 10 remains blocked; Step 11 has not started.
