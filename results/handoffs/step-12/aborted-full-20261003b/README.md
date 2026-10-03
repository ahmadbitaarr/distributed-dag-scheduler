# Second aborted full-matrix attempt: 2026-10-03 (not a benchmark result)

- **Source:** branch `ms2/step-12-benchmark` at 9f53ada, which merges `main` at bf4f784. Service code, POMs, Dockerfiles and Compose are unchanged since the Step 9 gate (`git diff 2a89f8a` is empty for those paths).
- **Backend:** Compose (1 CPU / 512 MiB per service). Images were rebuilt immediately before the run.
- Free host memory was **1.9 GB** at launch. Chrome and Discord were still open.

| Run | Status | Notes |
|---|---|---|
| c1-w1-r1 | complete | 24/24 jobs, 1.62 tasks/s, job p50 1.93 s |
| c1-w1-r2 | error | `HistoryViolation: snapshot successes disagree with history`. This was a **checker false positive**, explained below. |
| c1-w1-r3 | censored | 22/24 jobs within the 120 s budget |

The operator stopped the matrix during `c1-w1-r4`.

## Host conditions

`host-memory.csv` sampled every 10 s during the attempt (42 samples). Free physical memory ranged from **370 to 1060 MB, median 728 MB**, out of 16 GB. Median host CPU load was 50%.

Combined with the first aborted attempt (`../aborted-full-20261003/`) and three Docker Desktop engine crashes, the cause is host memory pressure: Windows compresses and pages the Docker VM, and every service stalls at once. The verifying host could not provide stable conditions for the capped benchmark.

## The r2 error was a checker defect, not a system violation

- The run hit its 120 s budget with one job still RUNNING.
- The driver took that job's atomic snapshot, then read the event history a moment later. By then one more task of that job had succeeded.
- `check_history` compared the older snapshot's success count with *all* history successes and reported a violation.
- The exported snapshots, taken at teardown, agree with the history.

**Fix** (in `tests/harness/api.py`): a snapshot is compared only with the history prefix up to its own `snapshot_event_seq`. All other invariants are unchanged.

Regression tests in `tests/unit/test_history_checks.py`:

- `test_snapshot_older_than_history_is_consistent` fails on the old checker (confirmed by a mutation check).
- `test_older_snapshot_still_detects_a_missing_covered_success` shows real disagreements inside the covered prefix are still caught.

With the fix, a run like r2 is recorded as **censored**, not as an error.

These rows are kept unmodified, are not used as results, and are not replaced by invented samples.
