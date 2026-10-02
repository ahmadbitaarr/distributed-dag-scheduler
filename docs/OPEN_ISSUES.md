# MS2 open issues

| ID | Category / gate | Observation | Required next action |
|---|---|---|---|
| S0-01 | BLOCKER — Step 0 GitHub | Connected profile Abu7arb111 is visible, but installations/accounts/repositories are empty; no shared repo, branch or pushed SHA exists. | User supplies/creates the team repository and enables connected GitHub repository access/write permission. Resume Step 0 commit/push gate. |
| S0-02 | Historical provenance gap | Earlier build/native passes lack Git SHA, full tested-source manifest and run-time JAR fingerprints. Exact tested revision UNKNOWN. | Keep them historical only. Record fresh base commit/source manifest with new Step 1 build; do not retroactively certify checkpoint. |
| S1-01 | Environment — Step 1 | Latest recorded build stopped fetching Maven JUnit provider through unavailable private proxy; no JUnit tests ran. | Reproduce mvn -B verify in the normal build environment after Step 0 acceptance; exclude private proxy configuration. |
| S1-02 | Missing — Step 1 and service gates | No Makefile, Dockerfiles or Compose service files; Python Compose harness is only a draft. Docker/Compose availability unverified. | Complete at the ordered roadmap gates, preserving existing code. |
| S2-S8 | Unverified existing code | Protocol/core/API/artifact/worker/client and histories are drafts. Fourteen JUnit tests and remaining integration cases have no passing evidence. | Review/finish/verify at Steps 2–8; source existence is not DONE. |
| S9-01 | Missing/unverified — Step 9 | Video fixtures/operations exist; no verified video DAG or complete provenance/functional manifest documentation. | Verify approved functional/video pipelines at their roadmap gates. |
| S10-01 | Intentional defect / unexecuted oracle | Worker-crash reassignment is intentionally absent. Strict typed XFAIL draft has not run. | Keep recovery broken in MS2; demonstrate exactly as Step 10 specifies, not in Step 0. |
| S11-01 | Missing/environment — Step 11 | Hokea adapter missing; runtime.py imports nonexistent hokea_adapter when selected; cluster access unverified. | Version-ground adapter and record cluster limitations at Step 11. |
| S12-01 | Unverified/resource gap — Step 12 | Benchmark draft unexecuted; native harness does not enforce 512 MiB container memory limit. | Complete exact approved matrix/resource controls at Step 12. |
| S13-S15 | Missing final gates | Independent clean reproduction, revised specification, progress report, final docs and submission audit incomplete. | Complete in order at Steps 13–15, using measured evidence. |

No approved decision is changed to work around an issue. No leases, heartbeat expiry, scanner, automatic silent recovery, administrative requeue, scheduler replication/failover or durable scheduler recovery are introduced.
