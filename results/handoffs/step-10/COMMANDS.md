# Step 10 command record and continuation

Status: BLOCKED checkpoint. Commands below distinguish completed executions from
future instructions. The complete logs and source manifest for each executed
command are in `checks/<label>/`; `command.json` preserves exact argv, cwd,
environment overrides, start time, duration and exit code.

## Executed commands

All commands ran from the project root using the local pinned toolchain described
in `docs/handoffs/step-10.md`. `MS2_RUN_LABEL` equals the row label;
`MS2_BACKEND=compose` for compose rows, otherwise `native`.
`MS2_REQUIRE_XFAIL=1` was set for `native-strict` and `compose-strict` only.
Source IDs and complete manifests are recorded per row; early focused runs have
a different source manifest and must not be relabeled.

| Label | Exact test/build command | Exit | Duration (s) |
|---|---|---:|---:|
| `focused-unit` | `python -m pytest -q tests/unit/test_fault_oracle.py tests/unit/test_history_checks.py` | 0 | 0.213 |
| `focused-java` | `mvn -B verify -pl protocol,scheduler` | 0 | 19.149 |
| `focused-unit-final` | `python -m pytest -q tests/unit/test_fault_oracle.py tests/unit/test_history_checks.py` | 0 | 0.194 |
| `java-acceptance` | `mvn -B verify` | 0 | 7.530 |
| `worker-regressions` | `python -m pytest -q tests/integration/test_worker_client.py -k 'hooks_are_disabled or local_operation_timeout'` | 0 | 12.380 |
| `native-strict` | `python -m pytest -q tests/faults/test_worker_crash.py` | 0 | 16.695 |
| `compose-build` | `docker compose -f deploy/compose/compose.yaml build` | 127 | 0.001 |
| `compose-strict` | `python -m pytest -q tests/faults/test_worker_crash.py` | 1 | 0.200 |
| `native-offline` | `python -m tests.harness.check_evidence results/latest-tests/native-strict/test_worker_crash_reassignment` | 0 | 0.043 |

Results: focused-unit 23 passed; focused-java 53 JUnit passed; focused-unit-final
25 passed; java-acceptance 61 JUnit passed (33/20/8); worker-regressions 2 passed,
5 deselected; native-strict 1 XFAIL and zero errors/failures; native-offline 2
histories passed. These counts are from separate executions and are not added
together into a full-suite claim. Native setup and cleanup succeeded.

Compose build was not launched because `docker` was absent (recorder exit 127).
Compose pytest exited 1 with one setup error and zero XFAIL: sandbox socket
creation was denied before reaching Docker. The escalated retry was not executed
because Work usage prevented automatic approval review. It has no exit status.
See `verification-blockers.json`.

Additional already completed static checks: `sh -n deploy/harness/run.sh`,
`sh -n deploy/harness/in-container.sh`, and `make -n test fault-demo` each exited 0.
They were syntax/dry-run checks, not executions of either Make target. Their
terminal outputs were not retained as standalone logs. Package-integrity checks
are recorded separately in `package-checks.json`.

**Not executed:** `make test`; full native pytest acceptance; `make fault-demo`;
native `--runxfail`; escalated Compose retry. No successful Compose fault run,
full acceptance count or intended real-failure exit code exists in this checkpoint.

## Remaining commands — not execution evidence

Run from the repository root on a Docker-capable host. Host Python needs
`requirements.txt`; the harness image supplies Java/Maven/FFmpeg for `make test`.
Do not install tools into the project or add credentials/proxy files to it.
Only the user performs Git operations. Do not begin Step 11.

First, recheck the preserved native history and exact implementation files:

```bash
python3 -m tests.harness.check_evidence results/handoffs/step-10/native-strict/test_worker_crash_reassignment
sha256sum -c results/handoffs/step-10/source-SHA256SUMS.txt
```

Use this source identifier only while those implementation bytes remain unchanged:

```bash
export MS2_SOURCE_REV='9bfd6d339d754475bcf218179f1cffdd4c07eeb3+local-step10:sha256:83c1d8789c58643c2ea74015008c38e4a058957e6b0a477f0bfe9b881e7c62ae'
```

If editing the collision guard or any implementation file, regenerate a source
manifest/identifier before testing; retain this checkpoint's original attribution.
A future accepted Git SHA may be used only after the user actually creates it.

Check host capabilities; stop if unavailable:

```bash
docker compose version
docker info
python3 -m pytest --version
```

Use a new tag for this continuation and a separate command-log directory. The
following shell recipe records exact command, source ID, selected environment,
combined output and real exit status. Run each `record_step10` invocation
separately; inspect its log/status before proceeding. It returns the original
status, including the intentional demo failure; it does not convert errors into
success. No command here has been run as part of checkpoint packaging.

```bash
cs4094_run_tag=$(python3 -c 'import uuid; print(uuid.uuid4().hex[:12])')
cs4094_check_dir="results/handoffs/step-10/checks/resume-$cs4094_run_tag"
mkdir -p "$cs4094_check_dir"
record_step10() {
  cs4094_label=$1
  shift
  python3 -c 'import os, shlex, sys; print(shlex.join(sys.argv[1:])); print("source_revision=" + os.environ.get("MS2_SOURCE_REV", "UNSET")); print("run_label=" + os.environ.get("MS2_RUN_LABEL", "generated")); print("backend=" + os.environ.get("MS2_BACKEND", "native")); print("require_xfail=" + os.environ.get("MS2_REQUIRE_XFAIL", "unset"))' "$@" > "$cs4094_check_dir/$cs4094_label.command.txt"
  if "$@" > "$cs4094_check_dir/$cs4094_label.log" 2>&1; then
    cs4094_status=0
  else
    cs4094_status=$?
  fi
  printf '%s\n' "$cs4094_status" > "$cs4094_check_dir/$cs4094_label.exit.txt"
  return "$cs4094_status"
}
```

Build images, then run the same oracle through **host** Compose, with a fresh label:

```bash
record_step10 compose-build docker compose -f deploy/compose/compose.yaml build
MS2_BACKEND=compose MS2_REQUIRE_XFAIL=1 MS2_RUN_LABEL="step10-compose-$cs4094_run_tag" record_step10 compose-strict python3 -m pytest -q tests/faults/test_worker_crash.py
python3 -m tests.harness.check_evidence "results/latest-tests/step10-compose-$cs4094_run_tag/test_worker_crash_reassignment"
```

Require one typed XFAIL, exit 0, no failures/errors, cleanup true, SIGKILL exit 137,
distinct sessions, original-attempt snapshots, successful B probe, late polling
and both histories valid. Do not accept build/startup failures as the oracle.

Next, normal acceptance:

```bash
MS2_RUN_LABEL="step10-acceptance-$cs4094_run_tag" record_step10 acceptance make test
python3 -m tests.harness.check_evidence results/latest-tests/step10-acceptance-"$cs4094_run_tag"/*/
```

Require exit 0, all ordinary tests passing, exactly one XFAIL, no XPASS/errors.
Record the actual new JUnit/pytest counts. This covers the existing explicit-failure
retry, duplicate/conflicting/stale report, dependency, publication, slot, hooks-off
and history-check regressions. Run a targeted regression separately only if the
full gate exposes a concrete problem or excludes relevant coverage.

Finally, visible real failure:

```bash
MS2_RUN_LABEL="step10-fault-demo-$cs4094_run_tag" record_step10 fault-demo make fault-demo
python3 -m tests.harness.check_evidence "results/latest-tests/step10-fault-demo-$cs4094_run_tag/test_worker_crash_reassignment"
```

The first command must return nonzero. Inspect both the actual Make exit code and
pytest traceback: the only test failure must be the final `RecoveryNotObserved`,
with zero setup/teardown errors and complete safety/probe/export/cleanup evidence.
A failed copy or cleanup does not qualify. Do not hardcode an expected Make exit
value into evidence; record what the command returned.

The existing native targeted run already satisfies the native strict-XFAIL gate.
If a source change or host difference requires repeating it, use another fresh
label and package Java before native execution:

```bash
MS2_RUN_LABEL="step10-native-$cs4094_run_tag" record_step10 native-strict sh deploy/harness/run.sh sh -c 'mvn -B -q package -DskipTests && MS2_REQUIRE_XFAIL=1 pytest -q tests/faults/test_worker_crash.py'
```

After each successful/completed run, copy that uniquely named run directory to
`results/handoffs/step-10/`, excluding `runtime/`, caches and build outputs.
Preserve original metadata and raw events, including the demo traceback; do not
edit them to change source revision or outcome. Refuse an existing destination.
Retain command files alongside runs. Default generated labels avoid collisions;
explicit labels must never be reused while S10-03 is unresolved.

Update PROGRESS/HANDOFF/OPEN_ISSUES with observed results only. Step 10 remains
BLOCKED until all required gates pass and the user accepts it. No Step 11 work or
Git operation is authorized for this implementation agent.
