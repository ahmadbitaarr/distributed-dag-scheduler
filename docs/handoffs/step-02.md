# Step 02 — Wire contracts and DAG validation

```text
Project: CS4094 distributed DAG task scheduler / MS2
Step number and title: 2 — Freeze the wire contracts and validate DAGs
Status: DONE on branch ms2/step-02-protocol (gate passed). Awaiting integration: Step 1 and Step 2 branches are not yet on main.
Current writer: Hasanlm23123
Next teammate: not assigned
Base commit: 7c74937 (Step 1, ms2/step-01-build-foundation)
Accepted commit: communicated in the handoff message after push (not self-referenced here)
Canonical architecture path and checksum: docs/CS4094_MS2_Architecture.md,
  SHA-256 7d2f931bfcf308ccc2b32a899e8976e75656dab81f51b940df1aa136b37a8ef1 (committed LF blob)
```

## Behavior completed

- **`docs/api.md`**: the version 1 wire contract. It covers:
  - identities and the ownership tuple,
  - artifact namespaces,
  - the manifest schema with a full example,
  - the operation allowlist,
  - validation rules and limits,
  - replay-equality rules,
  - every scheduler and artifact endpoint,
  - the error/status-code table,
  - an example rejection.
- **Fixed in `ManifestValidator`:**
  - An input binding or `final_outputs` binding that lacked `task_id` or `output_name` threw a `NullPointerException`. The HTTP layer reported that as `503 SERVICE_UNAVAILABLE`. It is now `400 INVALID_INPUT`.
  - Object keys accepted non-canonical UUIDs (`inputs/1-1-1-1-1/x`), because `UUID.fromString` is lenient. Keys now require the canonical lowercase form. I also removed a dead branch that only returned `false`.
- **New shared validators** `ManifestValidator.identity(Identity)` and `ManifestValidator.claim(Claim)` define the required ownership and claim fields in one place. `SchedulerCore` calls them instead of its duplicated inline checks, with the same rules.
- **`SchedulerCore.run()`** now rejects a missing `scheduler_run_id` with `400`. It used to return `409 STALE_RUN`, but architecture §6 says malformed input is 400.
- **`WireContractTest`** (27 tests, parsing real JSON) covers:
  - valid graphs: chain/join, multiple roots and sinks, ordering-only dependencies, the video DAG;
  - rejected graphs: empty, duplicate IDs, self-edge, unknown parent, cycle, invalid IDs, wrong schema version;
  - binding errors;
  - operation and parameter misuse;
  - strict JSON: no coercion, no floats as integers, no unknown fields, no duplicate keys, no trailing tokens, no lenient UUIDs;
  - replay equality and inequality, and the JSON round trip;
  - key namespaces and artifact descriptors;
  - required identity and claim fields.

The 6 existing `ManifestValidatorTest` tests are unchanged and still pass.

## Commands run

See `results/handoffs/step-02/COMMANDS.md`. Summary:

- `mvn -B verify` exited 0, with 41 JUnit tests passing (33 protocol, 8 scheduler).
- A mutation check confirmed the new tests fail on the old behavior.
- I demonstrated the contract against the real scheduler JAR over HTTP: valid manifest 201, replay 200, conflict 409, three rejections 400.

## How to demonstrate

Run `mvn -B verify -pl protocol`. Then start the scheduler JAR and POST the manifest from docs/api.md (expect 201), and POST it again with B's binding changed to `{"task_id":"A"}` (expect 400).

## Known unverified behavior

- Source-object existence at acceptance, the 1 MiB request limit, and the 503 path when storage is unavailable are HTTP-layer behaviors. They are documented but not tested here (Steps 4–5).
- Scheduler state transitions, claims and reports were not reviewed (Step 3).

## Architecture deviations

None. The missing-run-ID status change (409 → 400) brings the code into line with §6.

## Explain to the next teammate

- The ownership tuple is `(scheduler_run_id, job_id, task_id, attempt_no, worker_session_id)`. Start and report must match the current attempt's tuple exactly, or they get 409.
- Logical identity `(job_id, task_id)` never changes across retries, and `attempt_no` increases. Outputs live under `runs/<run>/jobs/<job>/tasks/<task>/attempts/<n>/`.
- The code intentionally cannot reassign a task held by a silent or crashed worker.

## Exact next step

Step 3 — Finish the scheduler domain state machine. First verification command: `mvn -B verify -pl protocol,scheduler`. Then review `SchedulerCoreTest`'s 8 existing tests against architecture §§4, 5, 7 and 11.
