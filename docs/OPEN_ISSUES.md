# MS2 open issues

| ID | Category / gate | Observation | Required next action |
|---|---|---|---|
| S0-02 | Historical provenance gap | Earlier build/native passes lack a Git SHA, a full tested-source manifest and run-time JAR fingerprints, so the exact tested revision is UNKNOWN. | Keep them historical only. Current evidence carries `source_revision` (Step 8 onward). |
| S1-02a | Historical environment note | The prior Windows verifier lacked make and ran recipes directly. This continuation executed both Make test targets on Linux, but Docker was absent and neither reached tests. | Successful actual Make execution remains part of the Docker gate S10-01; historical Windows results retain their original scope. |
| S1-03a | Toolchain | Maven is not vendored (there is no `mvnw`). The harness container pins Maven 3.9.9, so `make test` needs only Docker. | Optional: add a Maven wrapper for host builds. |
| S6-01 | Environment note | Running the suite directly on a Windows/OneDrive bind mount made JVM start-up take about 12 s and caused readiness time-outs. `deploy/harness/in-container.sh` runs on a container-local copy, which avoids this. | None. Use `deploy/harness/run.sh`. |
| S10-01 | BLOCKER — Docker environment | Docker CLI/socket remain absent. Compose capability commands exit 127. Actual `make test` and `make fault-demo` each exit 2 before tests (recipe Error 127). Full native pytest passed 62 + 1 XFAIL and native --runxfail failed only on RecoveryNotObserved, but these do not replace the Docker/Make gates. | Run `results/handoffs/step-10/continuation-20261002T213257-b330499c/EXTERNAL-VERIFICATION.md` on a Docker-capable host. Keep Step 10 BLOCKED until all required gates are observed. |
| S10-03 | Documented evidence-label limitation | Explicit reuse of a container run label can overwrite the host copy-back destination; the fixture guard applies only to an existing per-test directory. Every continuation run used a fresh unique label. | Continue using fresh labels. No source change is required for this milestone under the user's continuation instruction; do not claim universal overwrite prevention. |
| S11-01 | Missing/environment; Step 11 | The Hokea adapter is missing (`runtime.py` imports a nonexistent `hokea_adapter` when selected). Cluster access is unverified. | Write a version-grounded adapter and record cluster limitations at Step 11. |
| S12-01 | Unverified; Step 12 | The benchmark driver (`benchmarks/run.py`) has not run. The native harness does not enforce the 512 MiB limit; Compose does (verified at Step 1). | Run the exact matrix under Compose resource caps at Step 12. |
| S13-S15 | Final gates | Independent clean reproduction, revised specification, progress report, final docs and submission audit are not done. | Complete in order at Steps 13–15, using measured evidence. |

## Resolved

| ID | Resolution |
|---|---|
| S0-01 | Shared repository exists; Step 0 accepted at 82ca8bc. |
| S1-04 | User confirmed Steps 0–9 integrated and accepted on main at 9bfd6d339d754475bcf218179f1cffdd4c07eeb3. Historical handoffs were not rewritten. |
| S10-02 | Earlier Work approval-review usage interruption resolved for this continuation: temporary dependency restoration and local native service tests executed. Full native acceptance and native real failure are now verified. Docker absence remains S10-01. |
| S10-TIMEOUT | Gated A alone uses OPERATION_TIMEOUT_MS=120000. Post-kill assertions require the original RUNNING attempt with no receipt or retry. Production timeout remains 30000. |
| S1-01 | `mvn -B verify` passes (Step 1). |
| S1-02 | Dockerfiles, Compose, and Make targets up/demo/test/down exist. ComposeHarness ran real-container tests (Step 6), and a live Compose demo ran (Step 9). |
| S1-03 | Python 3.12.3 is verified in the harness container (Step 5). |
| S2-01 | Source existence, the 1 MiB limit and the storage-unavailable 503 are covered by `test_api.py` (Step 5). |
| S3-S8 | Core, API, artifact store, worker and client were reviewed and verified at Steps 3–8. Four defects were fixed, each confirmed by a mutation check: validator NPE → 503; lenient UUID keys; media-type replay; worker exiting on stale rejection. |
| S9-01 | The video DAG is verified (Step 9). The sample is now byte-reproducible from `workloads/video/generate.sh`, with checksums and provenance. |

No approved decision was changed to work around an issue. No leases, heartbeat expiry, scanner, automatic silent recovery, administrative requeue, scheduler replication/failover or durable scheduler recovery were introduced.
