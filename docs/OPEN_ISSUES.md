# MS2 open issues

| ID | Category / gate | Observation | Required next action |
|---|---|---|---|
| S1-04 | **BLOCKER — integration** | Push to origin is refused: HTTP 403, Hasanlm23123 has no write access to ahmadbitaarr/distributed-dag-scheduler. Steps 1–9 exist only as local commits on stacked branches `ms2/step-01-build-foundation` … `ms2/step-09-video`. | The repo owner grants write access. Then push the branches and fast-forward `main` to the Step 9 commit, in order. Never force-push. |
| S0-02 | Historical provenance gap | Earlier build/native passes lack a Git SHA, a full tested-source manifest and run-time JAR fingerprints, so the exact tested revision is UNKNOWN. | Keep them historical only. Current evidence carries `source_revision` (Step 8 onward). |
| S1-02a | Environment | `make` is not installed on the verifying Windows host, so each target's recipe was run directly (Compose `up`/`down`, `deploy/harness/run.sh`, `tests.harness.demo`). The Makefile itself has not been executed. | A teammate on Linux or macOS runs `make up demo down` and `make test` (Step 13). |
| S1-03a | Toolchain | Maven is not vendored (there is no `mvnw`). The harness container pins Maven 3.9.9, so `make test` needs only Docker. | Optional: add a Maven wrapper for host builds. |
| S6-01 | Environment note | Running the suite directly on a Windows/OneDrive bind mount made JVM start-up take about 12 s and caused readiness time-outs. `deploy/harness/in-container.sh` runs on a container-local copy, which avoids this. | None. Use `deploy/harness/run.sh`. |
| S10-01 | Intentional defect; Step 10 | Worker-crash reassignment is intentionally absent. The strict typed XFAIL oracle runs in every full suite (1 xfailed). Step 10 still needs `make fault-demo` (`--runxfail`) and its saved failing evidence. Caveat: the crash test's gate sits inside the worker's 30 s `OPERATION_TIMEOUT_MS`. If killing worker A took longer than that, X would fail over explicitly and the oracle would XPASS, which the strict marker turns into a failure. | At Step 10, give gated worker A an operation timeout longer than the test window and document why. |
| S11-01 | Missing/environment; Step 11 | The Hokea adapter is missing (`runtime.py` imports a nonexistent `hokea_adapter` when selected). Cluster access is unverified. | Write a version-grounded adapter and record cluster limitations at Step 11. |
| S12-01 | Unverified; Step 12 | The benchmark driver (`benchmarks/run.py`) has not run. The native harness does not enforce the 512 MiB limit; Compose does (verified at Step 1). | Run the exact matrix under Compose resource caps at Step 12. |
| S13-S15 | Final gates | Independent clean reproduction, revised specification, progress report, final docs and submission audit are not done. | Complete in order at Steps 13–15, using measured evidence. |

## Resolved

| ID | Resolution |
|---|---|
| S0-01 | Shared repository exists; Step 0 accepted at 82ca8bc. |
| S1-01 | `mvn -B verify` passes (Step 1). |
| S1-02 | Dockerfiles, Compose, and Make targets up/demo/test/down exist. ComposeHarness ran real-container tests (Step 6), and a live Compose demo ran (Step 9). |
| S1-03 | Python 3.12.3 is verified in the harness container (Step 5). |
| S2-01 | Source existence, the 1 MiB limit and the storage-unavailable 503 are covered by `test_api.py` (Step 5). |
| S3-S8 | Core, API, artifact store, worker and client were reviewed and verified at Steps 3–8. Four defects were fixed, each confirmed by a mutation check: validator NPE → 503; lenient UUID keys; media-type replay; worker exiting on stale rejection. |
| S9-01 | The video DAG is verified (Step 9). The sample is now byte-reproducible from `workloads/video/generate.sh`, with checksums and provenance. |

No approved decision was changed to work around an issue. No leases, heartbeat expiry, scanner, automatic silent recovery, administrative requeue, scheduler replication/failover or durable scheduler recovery were introduced.
