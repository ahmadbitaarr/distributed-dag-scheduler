# Step 10 — local checkpoint and exact remaining work

Status: **BLOCKED — implementation prepared; required verification incomplete.**
Writer: Codex, local files only. Checkpoint date: 2026-10-02 UTC.
Accepted branch: `main` (user supplied; this source ZIP has no Git metadata).
Accepted pre-Step-10 SHA: `9bfd6d339d754475bcf218179f1cffdd4c07eeb3`.
Steps 0–9 are accepted. No new commit or remote action was performed.

The user explicitly prioritized a complete checkpoint ZIP when Work budget/time
could prevent completion. This is that checkpoint. It does not claim Step 10 DONE.
Continue from these files, preserving existing work and historical evidence.

## Authority and exact source attribution

- Canonical architecture: `docs/CS4094_MS2_Architecture.md`, SHA-256
  `7d2f931bfcf308ccc2b32a899e8976e75656dab81f51b940df1aa136b37a8ef1`.
- Approved roadmap: `docs/implementation-roadmap.md`, SHA-256
  `2ac8ef1944d425a7416eb8bff8ee143d856030b59832a7f08cbd450459c5b921`.
- Authoritative input ZIP SHA-256:
  `10703f7828ba85a228ef69b4a4c637f68d99134b934540e3e97298907ec809b8`.
- Tested implementation manifest: `results/handoffs/step-10/source-SHA256SUMS.txt`.
  Its SHA-256 is `83c1d8789c58643c2ea74015008c38e4a058957e6b0a477f0bfe9b881e7c62ae`.
- Final-code runs use the source identifier
  `9bfd6d339d754475bcf218179f1cffdd4c07eeb3+local-step10:sha256:83c1d8789c58643c2ea74015008c38e4a058957e6b0a477f0bfe9b881e7c62ae`.
  This labels a local source snapshot, not a newly created Git commit.
- The manifest includes source, tests, deployment/build configuration and workloads;
  it excludes `docs/`, `results/`, README files, build outputs and caches. Final
  documentation/evidence consolidation did not change the tested implementation.
- Early `focused-unit` and `focused-java` runs used manifest
  `51841e9f88177994d0fb0029d6c23db8be65eec507f2c775f751205812e25b46`;
  their own manifests are retained. Do not relabel those runs as later executions.
- All production Java, Java tests, POMs, Compose configuration, approved documents
  and historical Step 0–9 handoff/evidence bytes are preserved from the input.

## Reused unchanged

`WorkerMain` still claims, acknowledges start, executes, uploads, reports and
polls. Its existing opt-in gate runs after acknowledged start and operation-start,
before output publication. The production operation timeout remains 30000 ms.
Fresh workers have fresh session IDs. `MemoryStateStore` retains one active owner
per attempt; explicit failure can retry, but worker disappearance has no reclaim
transition. Scheduler state remains in memory.

`NativeHarness` and `ComposeHarness` in `tests/harness/runtime.py` retain launch,
readiness, worker kill, log export and teardown behavior. The native kill is
SIGKILL with exit -9; the existing Compose adapter requires exit 137. `Api.export`,
`check_history`, `check_directory`, event schemas and `pytest.ini` are unchanged.
The existing fault test and `RecoveryNotObserved` were extended, not replaced.

## Files changed and reasons

| File | Change / reason |
|---|---|
| `tests/faults/test_worker_crash.py` | A-only 120000 ms timeout; full gate/snapshot identity; immediate post-kill original-attempt checks; probe history checks; distinct B session; monotonic observation samples and late claim/empty pairs; healthy service checks; both exported histories validated before the final typed oracle. |
| `tests/unit/test_fault_oracle.py` (new) | 13 focused tests cover invalid original-attempt evidence, late polling/session/run discrimination, reused per-test directory rejection and unsafe run labels. Synthetic helper fixtures are unit input, not runtime evidence. |
| `tests/conftest.py` | Unique invocation label, per-test directory collision refusal before service startup, metadata with label and successful-cleanup flag. Existing XFAIL count hook retained. |
| `Makefile` | Adds `fault-demo`, packages Java artifacts first, then runs the same test with `--runxfail`; preserves nonzero status. |
| `deploy/harness/run.sh` | Forwards unique run label, preserves explicitly supplied source identifier, corrects package-first example. |
| `deploy/harness/in-container.sh` | Copies evidence back with checked copy status; copy failure remains an ordinary error, otherwise returns actual command status. |
| `README.md` | Documents fault-demo, test semantics, host Compose path, unique labels and current blocked status. |
| `docs/evidence.md` | Documents new evidence files, monotonic/sequence correlation, cleanup metadata and explicit-label copy-back caveat. |
| `docs/PROGRESS.md` | Records accepted Steps 0–9, actual baseline and blocked Step 10 with measured local results. |
| `docs/OPEN_ISSUES.md` | Resolves old integration state; records Docker, approval-review and explicit-label retention limitations. |
| `docs/HANDOFF.md` | Replaces stale current Step 9 handoff with this interrupted Step 10 continuation. Historical Step 9 handoff remains unchanged. |
| `docs/handoffs/step-10.md` (new) | This complete checkpoint and precise remaining work. |
| `results/handoffs/step-10/` (new) | Raw measured evidence, command logs/results, source manifests, blocker record, continuation commands and package inventory. |

## Measured verification

Full command arguments, environment overrides, start times, durations and source
manifests are under `results/handoffs/step-10/checks/<label>/`. All test commands
ran from the project root. See `COMMANDS.md` there for the complete table.

| Label | Result | Exit |
|---|---|---:|
| `focused-unit` | 23 passed on earlier manifest | 0 |
| `focused-java` | 53 JUnit tests passed on earlier manifest | 0 |
| `focused-unit-final` | 25 passed, including all 13 new unit checks | 0 |
| `java-acceptance` | `mvn -B verify`: 61 JUnit tests passed (33 protocol + 20 scheduler + 8 artifact-store); all modules packaged | 0 |
| `worker-regressions` | 2 passed, 5 deselected: hooks disabled by default; local timeout is explicit bounded failure | 0 |
| `native-strict` | Exactly 1 typed XFAIL in 16.55 s; no unexpected failures/errors; cleanup metadata true | 0 |
| `native-offline` | Both job histories satisfy safety invariants | 0 |
| `compose-build` | Docker executable absent; command could not start | 127 |
| `compose-strict` | 1 setup error, 0 XFAIL: sandbox denied socket creation in `free_port()` before Docker access | 1 |

The Compose setup error is an ordinary failure, not the intended demonstration.
The escalated retry was **not executed**: automatic approval review could not
complete because the Work usage limit was reached. No process exit code exists
for that rejected launch. `verification-blockers.json` records this distinction.

`make test`, full native pytest acceptance, `make fault-demo`, and a native
`--runxfail` run were **not executed**. There is no new full-suite pass count or
real-demo exit code to report. Historical Step 9 counts remain historical only.

Toolchain used for measured local runs: Linux x86-64, Java 21.0.8, Maven 3.9.9,
Python 3.12.14, pytest 8.3.4. Maven used a temporary dependency cache and the host
CA truststore after the downloaded JDK truststore initially rejected the proxy
certificate. TLS verification was not disabled. Toolchains, caches and proxy
settings are excluded from the ZIP. Exact local paths remain in command records
as provenance, not reusable configuration.

## Native experiment facts

Retained directory:
`results/handoffs/step-10/native-strict/test_worker_crash_reassignment/`.
Files were copied byte-for-byte from the original `results/latest-tests/native-strict/`
run, excluding `runtime/`. Metadata and commands retain the original paths.

- Scheduler run: `f45db35f-6a4b-4139-b38c-d2a1dc34de9c`.
- Faulted job: `7ec1a544-d717-4849-b504-5ce8d15431c7`; task X; original attempt 1.
- A session: `43062efc-b268-47ff-964e-0bcd7bc9b37e`.
- A's gate has worker producer sequence 4 and acknowledges scheduler event 7
  (`task_started`); the operation-start precedes the gate.
- A PID 1956 was hard-killed with SIGKILL, exit -9. `fault.json` records the full
  run/job/task/attempt/session tuple and kill start/confirmation monotonic times.
- Before kill, immediately after kill and after observation, X remains RUNNING
  under A, exactly one attempt, null output and report receipt; Y remains BLOCKED
  with no attempt. No accepted success/failure or retry occurred for X.
- B session: `40aa2014-bf95-46d1-ad9d-b8a0fee4b6cc`, distinct from A.
- Probe job: `1fc49152-7af7-4b60-8b69-31b22daaa0b8`; B completed it and returned
  bytes `3`. Both histories passed live and exported history checks.
- Budget: 10000000000 ns. Actual window: 10009972320 ns (10.009972320 s);
  request overrun 9972320 ns. Forty samples show B alive and X at attempt 1.
- Polling evidence: 95 paired B `work_claim`/`work_empty` receipts, matched by
  request ID; 18 have a fresh claim after late scheduler sequence 170. The late
  boundary was captured 8.211439204 s after window start. Last pair sequences
  205/206. This uses harness monotonic timing and causal scheduler sequence order,
  not subtraction of clocks from different processes.
- Scheduler and artifact service health succeeded after the window; A remained
  dead; B remained alive; cleanup succeeded. The probe output was re-read.
- `oracle-traceback.txt` contains the final `RecoveryNotObserved`, requiring
  reassignment to B with a higher attempt. Stuck state is evidence of the intended
  liveness violation, not a passing correctness oracle.

The 10-second budget is not a universal recovery bound. A request in flight may
finish just after the deadline; elapsed duration and overrun are explicitly saved.
No artificial stale report was injected into this crash experiment. It proves
the original attempt stayed unchanged; dedicated existing replay/stale-report
regressions must also pass in the pending full suite.

## Exact unfinished work

1. On a Docker-capable host, verify this source manifest and recheck retained
   native history offline. Do not rebuild the implementation or discard evidence.
2. Address S10-03 before claiming universal no-overwrite behavior: the fixture
   rejects local collisions, but container copy-back can overwrite an explicitly
   reused host label. Add/verify a narrow host collision guard if that guarantee
   is required; retain fresh labels for every run regardless. Default randomized
   labels and all measured checkpoint labels are distinct. Any source edit needs
   a new source identifier and reruns of affected checks.
3. Build Compose images and run the exact existing crash oracle through host
   Python/Compose with `MS2_REQUIRE_XFAIL=1`. Require one `RecoveryNotObserved`
   XFAIL, zero errors/failures, successful cleanup and both histories checked.
4. Run full `make test`, preserving actual counts and command exit. It must pass
   with exactly one expected XFAIL and no XPASS/errors/unexpected failures.
5. Run real `make fault-demo` and preserve the actual nonzero Make status and
   pytest failure trace. Confirm failure comes only from `RecoveryNotObserved`;
   missing Docker, build/setup/probe/safety/export/cleanup errors do not qualify.
6. Recheck exported evidence for these new runs and retain each under a distinct
   Step 10 directory without runtime objects. Confirm full-suite coverage of
   explicit-failure retry, duplicate/conflicting/stale reports, dependency order,
   publication-before-success, worker slot, hooks-off defaults and history checks.
7. Update coordination state only from observed results. Keep Step 10 blocked if
   a required gate is still missing. The user inspects and performs all Git work.

Exact commands and log/exit capture instructions are in
`results/handoffs/step-10/COMMANDS.md`. The first verification command is:

```bash
python3 -m tests.harness.check_evidence results/handoffs/step-10/native-strict/test_worker_crash_reassignment
```

Last successful runtime/evidence verification: the recorded `native-offline`
command, exit 0. First incomplete retry: escalated Compose prerequisite/fault
check, not launched by approval review. No test is intentionally left running;
completed native runs record cleanup true. A separate process-list inspection
was unavailable (`ps` returned a platform library error), so no independent
global orphan-process audit is claimed.

## Architecture guardrails and next step

Architecture deviations: **none**. No production implementation was changed.
Do not add leases, heartbeat protocol/expiry, ownership expiration, expiry
scanning, silent-worker requeue, administrative automatic requeue, automatic
restart of A, scheduler replication/failover or durable scheduler recovery.
The absent RUNNING-owner reclamation transition is intentionally deferred to MS3.

Suggested commit after the user verifies and accepts Step 10:
`test(faults): demonstrate intentional MS2 crash-reassignment violation`.
Ask the user to return the full accepted SHA, branch, clean/dirty status,
push/acceptance status and final command/evidence results. No Step 10 SHA exists
from this agent's work.

Step 11 handoff only, after Step 10 acceptance: confirm the actual course Hokea
revision against roadmap reference `427b94634b1736ba8e59d4977836162aa58bd2cb`;
implement the adapter for launch/stop/kill/logs using current service boundaries;
verify addressing, health and artifact access before functional and identical
fault tests. Record cluster-access limitations. Step 11 has not started.
