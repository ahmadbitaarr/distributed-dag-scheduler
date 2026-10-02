# Step 00 — Shared baseline (accepted)

```text
Project: CS4094 distributed DAG task scheduler / MS2
Step number and title: 0 — Establish the shared baseline without restarting
Status: DONE
Current writer: Step 0 preparer (see docs/handoffs/step-00.md)
Next teammate: Hasanlm23123 (Step 1)
Base commit: none (initial commit)
Accepted commit: 82ca8bc (82ca8bcbac2b967493aacdb1865afdde7d24cded) on origin/main
Canonical architecture path and checksum: docs/CS4094_MS2_Architecture.md,
  SHA-256 7d2f931bfcf308ccc2b32a899e8976e75656dab81f51b940df1aa136b37a8ef1 (committed LF blob)
```

## Behavior completed

The interrupted checkpoint was imported into the shared repository https://github.com/ahmadbitaarr/distributed-dag-scheduler as a single commit on `main`. The canonical architecture and roadmap are stored unchanged; coordination files and Step 0 evidence (results/handoffs/step-00/) were added. The earlier BLOCKED status (no repository / no GitHub access) is resolved: the repository exists and 82ca8bc is the accepted baseline.

Receiver verification at Step 1 start: `git rev-parse origin/main` returned 82ca8bcbac2b967493aacdb1865afdde7d24cded and `git show HEAD:<path> | sha256sum` reproduced both recorded checksums.

## Known unverified behavior

All implementation code (protocol, scheduler, worker, artifact-store, client, Python tests, benchmark) is an **unreviewed checkpoint**. Historical build/test evidence in results/handoffs/step-00/historical/ covers an earlier unversioned source and does not certify 82ca8bc. Architecture deviations introduced by Step 0: none.

## Explain to the next teammate

- Lifecycle: tasks BLOCKED → READY → ASSIGNED → RUNNING → SUCCEEDED; accepted explicit failure from ASSIGNED/RUNNING returns the task to the FIFO tail with a higher attempt number on reassignment. Jobs ACCEPTED → RUNNING → SUCCEEDED.
- Ownership/dependencies: the scheduler alone decides; one global mutex; a parent's accepted success satisfies child edges once; all tasks must succeed for job success.
- Intentionally absent: any reassignment from a silent/crashed worker (no leases, heartbeats, expiry, or auto-requeue). This is the MS2 liveness defect.

## Exact next step

Step 1 — Build, repository, and deployment foundation. First verification command from the repository root: `mvn -B verify`.
