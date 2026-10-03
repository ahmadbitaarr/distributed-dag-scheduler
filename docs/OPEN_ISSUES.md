# Open issues

This file records active Step 11 blockers plus retained historical limitations.
Resolved verification items remain documented so later work does not reopen them.

| ID | Status | Issue / evidence | Required action |
|---|---|---|---|
| S11-02 | RESOLVED — local Docker/Hokea verification | External local verification completed from a WSL-native filesystem. Compose regression passed with 2 PASS + 1 expected typed XFAIL; `make test` passed with 84 PASS + 1 expected XFAIL; `make fault-demo` failed only with the intentional `RecoveryNotObserved` oracle. The earlier OneDrive `/mnt/c` failure was an environment-path/cwd issue. | No further local implementation action required. Retain the successful WSL-native evidence as acceptance evidence. |
| S11-03 | OPEN — external course-runner environment mismatch | Course-cluster execution was attempted in `team-06`. Access, public immutable service images, runner launch, package transfer, pytest startup, and evidence copy-out succeeded. All 3 tests then errored during fixture setup before project service execution because the Hokea package installed in the course runner did not match pinned revision `427b94634b1736ba8e59d4977836162aa58bd2cb` (`Hokea source mismatch at check.py`). | Treat as an external course-runner environment mismatch. Do not relax the project pin or add compatibility logic. Use the correctly pinned course runner/environment if supplied by course staff. Evidence: `results/handoffs/step-11/acceptance-hokea-20261003T200759-f99f027a`. |
| S11-04 | RETAINED LIMITATION | Step 11 intentionally preserves the Step 10 crash-reassignment oracle. Silent/crashed worker reclamation remains absent in MS2, so the final expected fault result is `RecoveryNotObserved`. | Do not add leases, heartbeat expiry, ownership expiration, requeue/reclamation, automatic restart, replication or failover in Step 11. |
| S11-05 | RETAINED SCOPE BOUNDARY | Hokea integration is an orchestration/deployment adapter only. It must not change scheduler task/attempt semantics, production HTTP contracts, or add shared worker storage. | Keep Step 11 changes at the orchestration/evidence boundary. |
| S10-03 | RETAINED HISTORICAL LIMITATION | Explicit reuse of a container run label can overwrite host-side copied results; accepted external runs used fresh unique labels. | Continue using fresh labels for future reruns. Do not claim universal overwrite prevention. |
| S0-02 | RETAINED HISTORICAL | Earlier baseline/provenance coordination item from the accepted project history. | Historical only; do not reopen unless Planning identifies a contradiction. |
| S1-03a | RESOLVED / HISTORICAL | Earlier local toolchain/Maven-wrapper environment limitation. Docker-based verification is now available and Step 11's current Compose/Make gates have been completed. | Do not vendor host toolchains or alter project semantics. Docker harness remains the reproducible path for future reruns. |
| S12-01 | NOT STARTED | Step 12 work is outside the current accepted Step 11 boundary. | Do not start until Planning formally accepts Step 11. |
| S13-S15 | NOT STARTED | Later roadmap work remains outside the current Step 11 boundary. | Follow roadmap order after formal acceptance of preceding steps. |

## Resolved / retained facts

- **S11-01 — adapter/API-fit resolution:** exact pinned Hokea source was inspected
  and verified. Heterogeneous role images and worker readiness are handled at the
  adapter boundary without changing production semantics. Actual local container
  execution has now been completed externally; see resolved S11-02.
- Local Step 11 verification is complete. The successful WSL-native Compose,
  Hokea, Make acceptance, fault-demo, evidence validation and cleanup results are
  the local acceptance evidence.
- The earlier OneDrive `/mnt/c` Compose attempt is preserved as an
  environment-path/cwd failure and is not acceptance evidence.
- Course-cluster execution was genuinely attempted. It must not be described as
  passed or as `NOT VERIFIED`; it is **attempted and externally blocked** by the
  course runner's mismatched installed Hokea package.
- The cluster failure is not the intentional `RecoveryNotObserved` result because
  project service execution never began.
- Do not weaken `deploy/hokea/verify_api.py`, change the pinned Hokea revision, or
  add compatibility logic solely to accept the unknown course-runner package.
- Steps 0–10 remain accepted at
  `main @ bf0a7974dd63cc8cd1d9240177156d0a00bd26df`.
- Step 11 changes remain uncommitted until final Planning review.
