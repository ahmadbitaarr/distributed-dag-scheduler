# Open issues and retained MS2 limitations

Steps 0–14 are complete and accepted at `f4c5dceef533a98b195d7dfa2e54ec8cac788825`.
Step 15 is PASS/runtime-content audit complete using the supported-host results
accepted by Planning. Initial Work-host failures remain historical environment-limited
evidence; existing raw evidence and Step 0–14 historical handoffs remain unchanged.

| ID | Status | Issue / evidence | Required action |
|---|---|---|---|
| S11-02 | RESOLVED — local Docker/Hokea verification | `results/handoffs/step-11/FINAL-RESULTS.md` records local Hokea success, WSL-native Compose 2 PASS + 1 typed XFAIL, Make 84 PASS + 1 XFAIL and the sole intentional fault-demo failure. The earlier OneDrive path failure is historical. | Do not reopen completed local gates. The latest independent gate is Step 13. |
| S11-03 | OPEN — external course-runner environment limitation | Course execution in `team-06` reached pytest but all 3 tests errored at setup before project services began: `Hokea source mismatch at check.py`, required pin `427b94634b1736ba8e59d4977836162aa58bd2cb`. See `results/handoffs/step-11/FINAL-RESULTS.md` and `acceptance-hokea-20261003T200759-f99f027a/CLUSTER-RESULT.md`. | A user-controlled rerun needs a correctly pinned staff-provided runner. Do not relax the pin or add compatibility logic. This is not the intentional XFAIL. |
| S11-04 | INTENTIONAL MS2 CORRECTNESS GAP | Silent/crashed-worker RUNNING ownership is never reclaimed. The task and job stay RUNNING; downstream tasks stay BLOCKED. Step 13 confirms the sole `RecoveryNotObserved` failure. | Preserve the typed strict XFAIL and real fault-demo failure. No MS2 leases, heartbeats, expiry/scanning/requeue, auto-restart, scheduler replication/failover or durable recovery. |
| S11-05 | RETAINED SCOPE BOUNDARY | Hokea remains a deployment/orchestration adapter; it does not change scheduler task/attempt semantics or HTTP contracts and does not share worker filesystems. | Keep the adapter and pin unchanged during documentation close-out. |
| S10-03 | RETAINED EVIDENCE LIMITATION | Reusing an explicit container run label can overwrite host copy-back evidence. | Use fresh labels for every run; do not claim universal overwrite prevention. |
| S0-02 | HISTORICAL | Earlier baseline/provenance coordination record. | Current source of truth is the accepted Step 14 revision above; retain original attribution. |
| S1-03a | RESOLVED / HISTORICAL | Earlier toolchain/Docker limitations were resolved by external verification. | Keep toolchains, credentials and machine configuration out of the project. |
| S12-01 | RESOLVED / accepted | The full benchmark completed 45/45 runs. Source/environment and aborted attempts are retained in `docs/handoffs/step-12.md` and `results/handoffs/step-12/`. | Keep measurements unchanged and host/synthetic-workload limits explicit. |
| S13-01 | RESOLVED / accepted | Independent fresh-checkout verification completed without implementation changes. `make test`: 86 PASS + 1 intentional XFAIL, 0 failures; 40/40 evidence checks. | Use `results/handoffs/step-13/VERIFICATION.md` for the observed results. Exact fault-demo shell exit was not preserved; report nonzero without inventing a code. |
| S15-01 | RESOLVED — supported-host results accepted by Planning | Step 15 runtime/content audit PASS: build/up/demo/first down/test exit 0; 86 PASS + 1 expected XFAIL, no real failures; fault-demo exit 2 solely from RecoveryNotObserved; cleanup successful. Bounded c1-w1 benchmark exit 0, 24 jobs. Full Step 15 matrix manually interrupted for deadline, not claimed complete. Initial Work-host failures remain historical. | Preserve accepted Step 12 data and initial logs. See `results/handoffs/step-15/VERIFICATION.md`. User controls later commit and final archive regeneration; Canvas-specific details remain unchecked. |

Scheduler state and artifact-store index are memory-only. Restart begins a new
scheduler run; the store does not reconstruct its index from retained disk files.
There is no scheduler durability, replication/failover or exactly-once external
effects guarantee. Honest workers, available services and the documented network/
timing assumptions still apply. Reported operation failures have no retry limit.

Course-cluster service behavior remains unverified, but the course attempt itself
was observed and externally blocked. Do not label it a pass, never-attempted work,
or `RecoveryNotObserved`. Do not weaken `deploy/hokea/verify_api.py`.
The independent Step 13 run also noted a transient connection-closed diagnostic
that caused no test failure. Its original verification record is preserved.
