# Current handoff — Step 14 documentation close-out

**Status: COMPLETE LOCALLY — AWAITING USER REVIEW. Steps 0–13 are accepted.**
Accepted repository: https://github.com/ahmadbitaarr/distributed-dag-scheduler
Accepted branch/baseline: `main @ bf43c619d00ee1658c5cb1eb297a5e1f59a2de8d`.
No Step 14 commit/push or authenticated GitHub/course action was performed.

The progress report and revised specification are finalized with the accepted
Step 13 findings. Intended MS1 quotations remain identical. README and Hokea
instructions now distinguish completed local verification from the external
course-runner mismatch. Final PDFs replace the draft exports. The command
walkthrough is in README; the evidence matrix is `docs/ms2-claim-evidence.md`.
Step 14 verification and review details are in `docs/handoffs/step-14.md` and
`results/handoffs/step-14/VERIFICATION.md`.

## Accepted verification to reuse

`results/handoffs/step-13/VERIFICATION.md` records a fresh Ubuntu checkout of
`f27aec9e1230b07c191f34f6a2278eafb0351f4f`: `make test` collected 87 pytest tests,
with 86 passes, exactly one intentional XFAIL and no failures. `make fault-demo`
returned nonzero solely from `RecoveryNotObserved`. Its exact shell exit code
was not preserved. Functional/media outputs, 40/40 generated evidence checks and
the one-repetition c1-w1 Compose benchmark succeeded without implementation changes.
Step 12's full 45-run benchmark remains separately attributed to its measured source.
No runtime tests were repeated for these documentation-only changes.

## Preserved semantics and limitations

The scheduler keeps in-memory state under one mutex. Tasks move from BLOCKED to
READY, ASSIGNED and RUNNING; accepted owner reports succeed or explicitly fail an
attempt. A reported failure requeues the task with a later attempt. Success releases
dependencies; a job succeeds only after all tasks succeed. Run/session/attempt
identity, immutable per-attempt outputs and replay receipts protect safety.

A silently killed worker cannot report, so its task remains RUNNING under that
session, downstream tasks remain BLOCKED, and the job remains RUNNING. B may
complete a probe and keep polling without reclaiming A's task. Preserve the strict
`raises=RecoveryNotObserved` XFAIL and the same `--runxfail` visible failure.
Add no leases, heartbeats, expiry scanning/requeue, worker auto-restart, scheduler
replication/failover, durable scheduler recovery or exactly-once external-effects claim.

Course-cluster execution was attempted, but project services never started because
the external runner's Hokea package mismatched frozen pin
`427b94634b1736ba8e59d4977836162aa58bd2cb`. This is an environment limitation,
not a successful course workload or the intentional fault result. Preserve
`results/handoffs/step-11/FINAL-RESULTS.md` and the original cluster evidence.

## Next: Step 15, after user acceptance

Suggested Step 14 commit message:
`docs(ms2): reconcile specification and progress report with evidence`.
The user performs commit/push and returns the full accepted SHA, branch,
clean/dirty status and push confirmation. No accepted Step 14 SHA is claimed yet.

The next teammate should read Roadmap Step 15 and this handoff, start with
`git status --short`, then record `git rev-parse HEAD` against the user-supplied
accepted Step 14 SHA. Step 15 audits the clean accepted repository and submission
contents, runs the documented packaged-source flow, records submission checksums
and exclusions, and checks current course submission requirements. The review
workspace archive from Step 14 does not certify that Step 15 has run, submit
anything, or certify unexecuted cluster checks. Step 15 has not begun.
