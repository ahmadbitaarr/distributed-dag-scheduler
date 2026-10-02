# Step 07 — Functional DAG and full happy-path semantics

Status: DONE on branch ms2/step-07-functional (gate passed; not yet on main — push blocked, see S1-04).
Base commit: 9dd7a73 (Step 6). Writer: Hasanlm23123.

## Added

- `workloads/functional/functional.json`: the architecture §12 DAG. A=3, B=A+4 (7), C=A×5 (15), D=B+C (22), E=`result=22\n`.
- `workloads/functional/expected.json`: every task's exact output bytes.
- `workloads/functional/README.md`.
- `tests/integration/test_committed_functional_workload`: runs the committed file 3 times with 3 workers. For each job it checks every intermediate output (3/7/15/22/`result=22\n`), checks that outputs live under attempt 1's namespace, and runs the history check. Each of the 5 edges A→B, A→C, B→D, C→D and D→E is released exactly once per job.

## Checklist coverage on the current source

| Roadmap Step 7 requirement | Test |
|---|---|
| B and C concurrent on distinct sessions; D only after both | test_join_and_independent_branch_concurrency (both RUNNING simultaneously on different owners; each started before the other succeeded) |
| Job not SUCCEEDED while an unrelated task is unfinished | test_multiple_roots_sinks_and_all_tasks_required |
| Controlled attempt-1 failure, then attempt 2, one logical success | test_real_worker_failure_attempt_two |
| Real artifacts | test_committed_functional_workload, test_functional_multiple_jobs_workers |
| Duplicate, conflicting and stale reports | test_duplicate_conflicting_stale_reports_and_retry, test_stale_report_rejection_does_not_kill_the_worker |
| Submission and claim replay | test_submission_and_claim_receipts, test_cached_empty_claim_stays_empty |
| Exactly one dependency release | test_committed_functional_workload, test_duplicate_conflicting_stale_reports_and_retry |
| Simultaneous claims | test_simultaneous_claims_and_session_single_slot |
| Multiple jobs and workers | test_functional_multiple_jobs_workers (4 jobs, 3 workers), test_committed_functional_workload |

The checkpoint's 6 historically "selected" passes were re-run on the current source, together with every other integration case.

## Verification

Harness container, native backend, container-local copy:

`pytest -rA tests/integration` gave **37 passed in 294 s** (exit 0). Saved evidence:

- the full result list: `results/handoffs/step-07/pytest-integration.txt`;
- the functional job histories, snapshots and metrics: `results/handoffs/step-07/functional-evidence/`.

Architecture deviations: none.
