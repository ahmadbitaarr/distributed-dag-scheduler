# Step 11 Course-Cluster Attempt — Post-Run Summary

> **Record type:** Post-run summary, not raw terminal output.
>
> The raw `hokea test` stdout/stderr was not retained as a standalone file. This summary records the observations captured immediately after the real course-cluster attempt and is paired with the preserved per-test `metadata.json` files in this evidence directory.

## Attempt

- Course namespace: `team-06`
- Runner namespace observed: `team-06-clients`
- Command executed: `~/CS4094/hokea/.venv/bin/hokea test --namespace team-06 -q`
- Observed runner Job: `hokea-test-20261003-160756-5c01`
- Pinned Hokea revision required by Step 11: `427b94634b1736ba8e59d4977836162aa58bd2cb`
- Step 11 source identifier: `step11-sha256:a9aab6b8f97e9734799689d82502ec2cb0da57886b49d8e87326f11aafd73fee`

## Immutable service images supplied

- Scheduler: `ghcr.io/ahmadbitaarr/scheduler@sha256:5b07b787f8a00d9c43212174c931442f902da897147cd562a868131b8ecdb271`
- Artifact store: `ghcr.io/ahmadbitaarr/artifact-store@sha256:76b36f919b3994f0ed1ca80e6eb04371f69c0c953cb4e7df78163adfcf416c76`
- Worker: `ghcr.io/ahmadbitaarr/worker@sha256:f6f5aad179837d6252a1b674b151b54342086fc914c04beeeb15c4f170674bc0`

All three packages were made public before the attempt because the course cluster does not use registry credentials for these service images.

## Observed cluster behavior

Hokea successfully:

1. accepted the authorized course-cluster request;
2. shipped the four-file runner package;
3. created the runner Job;
4. created the runner pod;
5. started pytest; and
6. copied the generated per-test evidence back to the repository.

Pytest then stopped during fixture setup for all three collected tests before any project service execution began.

Observed terminal error:

`RuntimeError: Hokea source mismatch at check.py; require 427b94634b1736ba8e59d4977836162aa58bd2cb`

Observed outcome:

- 3 errors
- 0 XFAIL
- command/pytest exit status: 1
- no scheduler/artifact-store/worker test workload was exercised
- the intentional `RecoveryNotObserved` oracle was not reached

The retained per-test metadata therefore records `outcome: "not-run"` and no scheduler run ID, which is consistent with failure during runner fixture setup rather than a project-service failure.

## Classification

**External course-runner environment mismatch.**

The Hokea package installed inside the course runner did not match the exact pinned Hokea source required by the frozen Step 11 contract. This result is not classified as:

- a Step 11 implementation defect;
- a GHCR/private-image failure;
- a Kubernetes authorization failure; or
- the intentional `RecoveryNotObserved` XFAIL.

No compatibility workaround was added. The project pin was not relaxed, and `deploy/hokea/verify_api.py` was not weakened.

If course staff supplies a runner/environment containing the required pinned Hokea bytes, the documented course sequence may be retried without changing Step 11 implementation source.
