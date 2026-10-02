# Current handoff — interrupted Step 10

Status: **BLOCKED; local checkpoint, not accepted Step 10.**

Accepted branch: `main`. Accepted pre-Step-10 baseline, supplied by the user:
`9bfd6d339d754475bcf218179f1cffdd4c07eeb3`. Steps 0–9 are accepted.
This ZIP has no Git metadata. No commit, push, pull, fetch, authentication or
GitHub API operation was performed. The user owns repository integration.

Read [handoffs/step-10.md](handoffs/step-10.md) for the complete continuation
record and [../results/handoffs/step-10/COMMANDS.md](../results/handoffs/step-10/COMMANDS.md)
for measured commands and commands still to run. Resume this checkpoint; do not
restore the earlier Step 0 tree or redo accepted Steps 1–9.

The local fault test now protects only gated A with a finite 120000 ms operation
timeout, verifies its original RUNNING attempt immediately after SIGKILL, checks
both histories, and proves B continues polling late in a monotonic 10-second
observation. Production sources and defaults are unchanged. The final oracle
still requires higher-attempt reassignment to B and raises only
`RecoveryNotObserved` when MS2 fails to provide it. The mark remains strict and
typed. `make fault-demo` invokes that same test with `--runxfail`.

Measured: 61 JUnit tests passed; 25 focused Python unit/history tests passed;
2 worker regressions passed (5 deselected); native fault oracle gave exactly
1 XFAIL, with successful cleanup; offline validation passed for both histories.
These are separate targeted runs, not a completed full acceptance gate.

Unfinished: Compose execution, full `make test`, and the real nonzero
`make fault-demo`. Docker is absent. Sandboxed Compose setup failed on socket
creation; the escalated retry was not executed because automatic approval review
hit the Work usage limit. The user then prioritized packaging over additional
verification. Also resolve/verify S10-03 if guaranteeing no overwrite for reused
explicit container run labels; always use fresh labels meanwhile.

First verification command (read-only, no services):

```bash
python3 -m tests.harness.check_evidence results/handoffs/step-10/native-strict/test_worker_crash_reassignment
```

Then follow the remaining Step 10 commands on a Docker-capable host. Preserve
ordinary failures, exact command exit statuses, unique evidence directories,
actual source identifiers and both job histories. Do not begin Step 11 until
Step 10 is verified and the user accepts it.

Architecture deviations: none. No leases, heartbeats, expiry/reassignment,
administrative requeue, scheduler replication/failover or durable scheduler
recovery may be added. A silent worker's ownership remains pinned in MS2.

After verification and the user's own commit/push, return the accepted full SHA,
branch, clean/dirty status and evidence locations. Suggested commit message:
`test(faults): demonstrate intentional MS2 crash-reassignment violation`.

Step 11 handoff only: verify/pin the actual course Hokea version (roadmap reference
`427b94634b1736ba8e59d4977836162aa58bd2cb`), then implement only its deployment
adapter and run the same functional/fault tests if cluster access is available.
No Step 11 implementation or external access was started.
