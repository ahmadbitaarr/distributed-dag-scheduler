# MS2 sequential progress

Status: **STEP 14 DOCUMENTATION CLOSE-OUT COMPLETE LOCALLY — AWAITING USER REVIEW.**
Current step: **14 — Finish the revised specification and progress report**
Next step: **15 — Audit and package the milestone**, after user acceptance of Step 14.

Repository: https://github.com/ahmadbitaarr/distributed-dag-scheduler
Accepted baseline: **main @ bf43c619d00ee1658c5cb1eb297a5e1f59a2de8d**.
**Steps 0–13 are complete and accepted.** No Step 14 commit or push was performed.

Architecture: `docs/CS4094_MS2_Architecture.md`
SHA-256: `7d2f931bfcf308ccc2b32a899e8976e75656dab81f51b940df1aa136b37a8ef1`
Roadmap: `docs/implementation-roadmap.md`
SHA-256: `2ac8ef1944d425a7416eb8bff8ee143d856030b59832a7f08cbd450459c5b921`
Both remain unchanged. Earlier handoffs/evidence retain their original source and status
attribution; they are historical records, not the current workflow state.

| Step | Status | Commit / source attribution | Gate evidence |
|---|---|---|---|
| 0 — Shared baseline | DONE | 82ca8bc (+ 51a979a close-out) | results/handoffs/step-00/ |
| 1 — Build/deployment foundation | DONE | 7c74937 | `mvn -B verify` exit 0; images build; Compose healthy. results/handoffs/step-01/ |
| 2 — Wire contracts, DAG validation | DONE | f30fe57 | docs/api.md; 33 protocol JUnit tests. results/handoffs/step-02/ |
| 3 — Scheduler state machine | DONE | c4d538b | 20 scheduler JUnit tests, including the silent-owner pin and a concurrency stress test. results/handoffs/step-03/ |
| 4 — Immutable artifact store | DONE | 05a7928 | 8 real-HTTP JUnit tests. results/handoffs/step-04/ |
| 5 — Scheduler API | DONE | d72b887 | 8 API integration tests; harness container. results/handoffs/step-05/ |
| 6 — Worker, client, end to end | DONE | 9dd7a73 | 7 tests native, plus a Compose subset. results/handoffs/step-06/ |
| 7 — Functional happy path | DONE | d40f701 | 37 integration tests passed. results/handoffs/step-07/ |
| 8 — Evidence and history checks | DONE | 4d2f8c9 | 49 passed + 1 xfailed; offline check of 38 directories OK. results/handoffs/step-08/ |
| 9 — Video demonstration | DONE | see handoff message | pytest video, a live Compose demo, and the `make test` gate (61 JUnit; 49 passed + 1 xfailed). results/handoffs/step-09/ |
| 10 — Intentional worker-crash oracle | DONE / accepted | accepted baseline bf0a7974… | User acceptance plus preserved external Compose, Make acceptance and real Make failure under results/handoffs/step-10/external-9064f75356bf492aa6dd3189c72dc88c/ |
| 11 — Hokea adapter | DONE / accepted; course environment limitation retained | included in accepted main baseline | `results/handoffs/step-11/FINAL-RESULTS.md`; local Hokea, Compose and Make verified; cluster setup blocked by pinned-package mismatch |
| 12 — Performance experiment | DONE / accepted | measured clean source `8c5f3cb3c94ed9abdd18c4f178c0ef02e46ab1a3` | `docs/handoffs/step-12.md`; `results/handoffs/step-12/full-20261003c/`; all 45 measured runs complete |
| 13 — Independent verification | DONE / accepted | tested `f27aec9e1230b07c191f34f6a2278eafb0351f4f`; accepted close-out baseline `bf43c619…` | `results/handoffs/step-13/VERIFICATION.md` |
| 14 — Documentation close-out | DONE locally / awaiting user review | documentation changes against accepted baseline; no new accepted SHA | `docs/handoffs/step-14.md`; `results/handoffs/step-14/VERIFICATION.md`; final reports/PDFs |
| 15 — Milestone audit and package | NOT STARTED | | Next after Step 14 acceptance |

Step 13 independently verified a fresh Ubuntu checkout: `make test` gave 86 passes,
exactly one intentional XFAIL and no failures. `make fault-demo` was nonzero solely
because of `RecoveryNotObserved`; its exact shell exit code was not preserved.
Functional `result=22`, valid H.264 1280x720/640x360 MP4s, valid 1280x720 PNG,
40/40 generated evidence-directory checks and a one-repetition c1-w1 Compose
benchmark reproduction succeeded. No implementation changes were required.

Step 14 finalizes the A–I progress report and revised specification, preserves every
quoted intended MS1 semester claim, updates stale current workflow/deployment text,
adds an evidence matrix and completes evaluator instructions. Final PDFs replace
the earlier draft exports. Verification is documentation-only; runtime gates were
not rerun. See the Step 14 verification record for PDF checks and file comparison.

Retained limits: killed workers' RUNNING ownership is never reclaimed in MS2;
the task/job remain RUNNING and downstream tasks BLOCKED. The strict expected
failure remains narrowly typed. No leases, heartbeat expiry, scanning/requeue,
automatic worker recovery, scheduler replication/failover or durable recovery exist.

The Step 11 course run was attempted in `team-06` and stopped before project
service execution with `Hokea source mismatch at check.py`. The pin remains
`427b94634b1736ba8e59d4977836162aa58bd2cb`. This external environment limitation
does not reopen accepted Steps 0–13. Read `docs/OPEN_ISSUES.md` and
`deploy/hokea/CLUSTER-HANDOFF.md` before any user-controlled rerun.

Step 15 has not begun. Its first checkout check is `git status --short` in the user's
accepted repository, followed by recording `git rev-parse HEAD` and comparing the
accepted Step 14 SHA. The user controls all commit/push and authenticated actions.
