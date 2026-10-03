# Step 11 Final Verification Close-Out

**Status: LOCAL IMPLEMENTATION/VERIFICATION COMPLETE. COURSE-CLUSTER EXECUTION ATTEMPTED — BLOCKED BY EXTERNAL COURSE-RUNNER HOKEA PACKAGE MISMATCH.**

This file is the authoritative final Step 11 verification close-out. The older `RESULTS.md` is retained as the original intermediate Work-generated record and should not be read as the current Step 11 status.

## Accepted baseline and scope

- Accepted pre-Step-11 baseline: `main @ bf0a7974dd63cc8cd1d9240177156d0a00bd26df`
- Steps 0–10 accepted before Step 11.
- Step 11 source identifier: `step11-sha256:a9aab6b8f97e9734799689d82502ec2cb0da57886b49d8e87326f11aafd73fee`
- Pinned Hokea revision: `427b94634b1736ba8e59d4977836162aa58bd2cb`
- No production Java, accepted fault-oracle semantics, Native/Compose implementation, architecture, or roadmap changes were introduced by the Step 11 orchestration work.

## Local Hokea verification

Focused Step 11 Hokea/unit verification completed successfully.

Observed retained Hokea behavior includes:

- service-exchange smoke: PASS;
- committed functional workload: PASS;
- concurrency regression: PASS;
- worker-crash reassignment test: expected XFAIL;
- cleanup recorded as successful.

The crash evidence preserves the intended MS2 limitation: after worker A is hard-killed, the unfinished RUNNING task is not reclaimed for worker B, and the final typed oracle is `RecoveryNotObserved`.

## WSL-native Compose and Make verification

The earlier Compose attempt from the Windows OneDrive `/mnt/c` path encountered an environment-specific stale current-working-directory/bind-mount problem. That failed path attempt is retained for provenance but is **not** acceptance evidence.

Using the same Step 11 source from a WSL-native filesystem:

- Compose regression: **2 passed, 1 expected typed XFAIL**
- `make test`: **84 passed, 1 expected XFAIL**
- `make fault-demo`: failed only with the intentional **`RecoveryNotObserved`** oracle
- retained evidence/history validation: PASS
- cleanup: successful

No project-source change was made to work around the OneDrive/WSL path issue.

## Course-cluster attempt

A real authorized course-cluster attempt was performed in namespace `team-06`.

Immutable public service images supplied:

- `ghcr.io/ahmadbitaarr/scheduler@sha256:5b07b787f8a00d9c43212174c931442f902da897147cd562a868131b8ecdb271`
- `ghcr.io/ahmadbitaarr/artifact-store@sha256:76b36f919b3994f0ed1ca80e6eb04371f69c0c953cb4e7df78163adfcf416c76`
- `ghcr.io/ahmadbitaarr/worker@sha256:f6f5aad179837d6252a1b674b151b54342086fc914c04beeeb15c4f170674bc0`

Hokea created the runner Job, shipped the package, started pytest, and copied evidence back. All three collected tests then errored during fixture setup **before any project service execution began** because the Hokea package installed in the course runner did not match the frozen pinned revision.

Observed error:

`RuntimeError: Hokea source mismatch at check.py; require 427b94634b1736ba8e59d4977836162aa58bd2cb`

Observed cluster-attempt result:

- **3 errors**
- **0 XFAIL**
- exit status **1**
- no project service workload executed
- intentional `RecoveryNotObserved` oracle not reached

Detailed post-run evidence is preserved under:

`results/handoffs/step-11/acceptance-hokea-20261003T200759-f99f027a/CLUSTER-RESULT.md`

The existing per-test `metadata.json` files remain unchanged and record `outcome: "not-run"`, consistent with the runner failure occurring before project services started.

## Final classification

The course-cluster failure is an **external course-runner environment mismatch**, not a Step 11 implementation defect.

The project did **not**:

- relax the pinned Hokea revision;
- weaken `deploy/hokea/verify_api.py`;
- add compatibility logic for the unknown runner package;
- change the accepted crash oracle; or
- introduce leases, heartbeat expiry, automatic reclamation/requeue, scheduler failover, or durable recovery.

S11-03 therefore remains an external environment issue. Local Step 11 implementation and verification are complete. Step 12 must not begin until Planning formally accepts Step 11.
