# Step 10 retained checkpoint evidence

Status: BLOCKED, not an accepted Step 10 gate. See `docs/handoffs/step-10.md`.

- `checks/`: nine recorded command executions; exact argv/environment, output,
  result, timing and per-run source manifest.
- `native-strict/test_worker_crash_reassignment/`: real native fault execution,
  one strict typed XFAIL, successful cleanup, raw events and both job histories.
- `worker-regressions/`: two real worker tests (hooks off; explicit local timeout).
- `compose-strict/`: setup-failure metadata only; no successful Compose experiment.
- `verification-blockers.json`: unexecuted retry and pending gate distinctions.
- `COMMANDS.md`: exact measured commands and separately labeled continuation.
- `source-SHA256SUMS.txt`: final tested implementation identity.
- `package-checks.json`: baseline preservation and clean-package validation.
- `checkpoint-SHA256SUMS.txt`: full packaged file hashes, excluding itself.

Copied run files are byte-identical to their original latest-tests files except
that temporary runtime directories were omitted. Original command paths remain
in metadata for provenance. The ZIP excludes latest-tests copies, build products,
cache directories, toolchains, proxy settings and artifact runtime state.
No Compose success, make-test success or real-failure demo is implied.
