# Step 2 verification record

Date: 2026-10-02. Host: Windows 11, OpenJDK 21.0.2, Maven 3.9.9.
Base commit: 7c74937015c2d96cb2be2bcd9adf7d3f900fc3c0 (Step 1, on ms2/step-01-build-foundation; not yet on main).
Tested source: the base commit plus the Step 2 changes, committed unchanged in the Step 2 commit.

| # | Command | Exit | Result |
|---|---|---|---|
| 1 | `mvn -B verify` | 0 | BUILD SUCCESS. protocol: 33 tests (6 ManifestValidatorTest + 27 WireContractTest). scheduler: 8 tests (SchedulerCoreTest). 0 failures/errors/skips. Log: `mvn-verify.log` |
| 2 | Mutation check (see below), then `mvn -B -q test -pl protocol` | 1 (expected) | 3 of 27 WireContractTest tests failed, as intended |
| 3 | `PORT=18080 java -Xmx128m -jar scheduler/target/scheduler-0.2.0.jar`, then 6 POSTs to `/v1/jobs` | — | See `http-manifest-demo.txt`: 201 valid, 200 replay, 409 conflict, 400 / 400 / 400 rejections. The process was stopped afterwards. |

## Mutation check

To confirm the new tests detect the bugs they target, I temporarily reverted three things in `ManifestValidator.java`:

- the null-binding guard,
- the final-binding null guard,
- the canonical-UUID check (back to lenient `UUID.fromString`).

Test results on the reverted code:

- `rejectsIncompleteParentBindingsAsBadInputNotServerError`: `NullPointerException`, which the HTTP layer maps to 503.
- `rejectsInvalidFinalBindings`: `NullPointerException`.
- `objectKeysUseCanonicalRestrictedNamespaces`: `inputs/1-1-1-1-1/clip.mp4` was accepted.

The file was then restored from a byte copy, and command 1 was re-run on the restored source.

## HTTP demonstration (run 8ac3e679-ca84-4711-a6e8-570b710acf01)

| Request | Result |
|---|---|
| Valid five-task functional manifest | 201 ACCEPTED |
| Same manifest with the tasks array reversed | 200 (semantic replay) |
| Same job_id with `amount` 4 → 40 | 409 CONFLICT |
| B's input binding missing `output_name` | 400 "Input binding needs a source or a parent output" |
| `"value": "3"` (string) | 400, no type coercion |
| Submission missing `scheduler_run_id` | 400 "scheduler_run_id required" (was 409 STALE_RUN before Step 2) |

## What this does not establish

- The source-artifact existence check at acceptance and the 1 MiB request limit belong to the HTTP layer. They were not exercised here; they are verified at Steps 4–5.
- The scheduler state machine, claims and reports were not reviewed in this step (Step 3).
