# MS3 closeout: corrections, verification and MS2-feedback status

Team-internal working record (October 30, 2026), written for Hasan and Ahmad. Not part of the reviewed documentation.

## Baseline and scope

- Started from `main @ 6104fa7` (identical to GitHub `main`). The input archive `CS4094_MS3_FINAL_SUBMISSION.zip`, with Ahmad's humanized documents, `docs/handoffs/ms3-documentation-review.md` and his chaos-test correction, was not available on this machine. Everything here is therefore relative to `6104fa7`. Before resubmitting, the sentence-level documentation edits listed below must be carried onto the ZIP's humanized documents (or the ZIP's documents onto this branch), and his chaos-test correction compared with commit `7a358bf`.
- Work is on the local branch `ms3/closeout`. Nothing was pushed to GitHub.
- No Java service code changed, so the public MS3 images built from `6104fa7` remain the images under test.

## MS2 feedback, item by item

| # | Feedback | Applies to MS3? | Status | What changed / evidence |
|---|---|---|---|---|
| S1 | No detection of dead workers | Yes | **Resolved** (MS3) | Leases + heartbeats (`SchedulerCore`, `WorkerMain`); `LeaseTest`; 15 fault tests; cluster runs |
| S2 | A dead worker's task is never re-scheduled | Yes | **Resolved** | Crash oracle and bounded re-run test pass natively and on the course cluster; recovery benchmark (13/13 orphaned tasks recovered) |
| S3 | All jobs lost if the scheduler crashes | Yes | **Not resolved** (documented) | Spec §2, §5; progress report §C, §G. Fixing it needs a write-ahead log or replication |
| 1a | Scheduler is a single point of failure; distribute it | Yes (ambition) | **Not resolved** | Architectural change (WAL or consensus), outside a closeout; stated as a limitation. Biggest grading risk |
| 1b | Detect stalled/crashed workers and reschedule | Yes | **Resolved** | As S1/S2; pause, partition and lost-heartbeat tests for "stalled" |
| 1c | Decide duplicate work vs missing work | Yes | **Resolved** | Spec §3 (at-least-once execution, exactly-once recorded completion), progress §C (lease length, fencing, late success rejected) |
| 1d | Which nodes hold which state | Yes | **Partly** | Spec §1 table states ownership (all decisions in the scheduler; workers stateless; store immutable), but state is still on one node |
| 2a | Load parameters and target loads | Yes | **Partly** | Spec §6 new paragraph names C, W, task duration; no target load is committed |
| 2b | SLOs | Yes | **Partly** | P-REC is the one commitment; throughput and job time are explicitly characterizations |
| 2c | Bottleneck (workers or scheduler) and why | Yes | **Partly** | Spec §6: workers at measured loads (throughput scales with W; 5 ms pickup); scheduler saturation point not measured |
| 2d | Define throughput and response time | Yes | **Resolved** | Spec §6 "Metrics" |
| 2e | Beyond what one scheduler can handle | Yes | **Partly** | Spec §6: no admission control, FIFO queueing, memory cap ~11,000 tasks (§1); no scale-out design |
| 3 | Artifact store "files remain on disk" is not what Hokea provides | Yes | **Resolved** | Spec §2 assumes the store is available; progress §G sentence corrected (it previously said files stay on disk) |
| 4a | Clean, readable code for the red team | Yes | Unchanged here | Only the Hokea adapter changed in code |
| 4b | Repetitive, unedited AI-generated documentation | Yes | **In Ahmad's ZIP** | His humanization pass is in the ZIP, not on this branch; edits here are sentence-level so they can be carried over |
| 4c | Results do not map to tests and docs | Yes | **Resolved** | `docs/test-matrix.md` (now with the new test), `results/ms3-logs/README.md` (every log and evidence directory described) |
| 4d | Label agent documentation | Yes | **Resolved** | README "Repository layout" now names `docs/handoffs/`, `HANDOFF.md`, `PROGRESS.md`, `OPEN_ISSUES.md` as agent working records |
| 4e | Code must run on Hokea; the pin is your bug | Yes | **Resolved and verified on the cluster** | See "Hokea" below |
| T | Implement and pass `test_crash_rerun_bounded.py` | Yes | **Resolved** | `tests/faults/test_crash_rerun_bounded.py`; passes natively (4 of 4: the full run plus 3 repeats; in the full run X was re-run 5.06 s after the kill) and on the cluster (re-run 4.5 s after pod deletion) |
| R1 | Distribute the scheduler | Ambition | **Not resolved** | As 1a |
| R2 | Detect worker and scheduler-node faults; no duplicated downstream work; worker detects scheduler failure; account for messaging overhead | Ambition | **Partly** | Worker faults and no duplicate downstream work: resolved (S3, children released only on an accepted success). Scheduler failure: a worker detects a restarted scheduler by its run ID and abandons the old attempt, but there is no failover. Messaging overhead: spec §6 now gives the request rates (idle 10 claims/s, busy 1 heartbeat/s per worker); not measured |
| R3 | Minimize `sleep()`; real video tasks; at least non-uniform sleeps | Ambition | **Not resolved** | Benchmarks still use uniform 100 ms fixture sleeps; real FFmpeg tasks run only in the video pipeline test |
| R4 | Scale: many jobs, overload, non-uniform job mix, tail latency, with faults | Ambition | **Partly** | C up to 16 with p95 job times, with and without crashes; overload behavior described; no non-uniform job mix |
| Q1–Q5 | Oral-defense questions | Defense | **Partly prepared** | `ms3-oral-defense.md` covers Q1 and Q2; Q3 (chain length, which resource saturates), Q4 (scheduler overhead vs task time; MS2 report §E has 45 ms start ack, 172–188 ms task time) and Q5 (specialized workers passing work directly) have no prepared answer |

## Hokea

**Root cause.** `tests/harness/hokea_adapter.py::verify_package` hashed all 14 files of the installed Hokea package and raised `Hokea source mismatch at <file>` unless every one equaled public commit `427b946`. The course runner image `hokea-runner:2026.08.29.3` (fixed by Hokea's own `runner.py`) was built on August 29 from pre-release source; the public repository's history starts at its September 8 "Initial release". Measured inside the runner: 7 of 14 files differ (`check.py`, `cluster.py`, `kube.py`, `net.py`, `runner.py`, `runs.py`, `workload.py`). The public package in the lab's WSL environment matches the pin exactly, so the pin file itself was correct; requiring it was the bug.

**Reproduced** on `team-06` with the unchanged `6104fa7` package: 1 error at setup, same message (`results/ms3-logs/hokea-cluster/repro-6104fa7/`).

**Fix** (`611c1de`). `describe_package` records the installed files' hashes and which differ from the reference, in every test's `hokea/metadata.json`. `verify_api` fails before any resource is created if Hokea lacks a class, method or constructor option the adapter calls. No correctness check, oracle or expected result changed. The runner package also ships the bounded re-run test.

**Cluster result** (`team-06`, runner `hokea-runner:2026.08.29.3`, images `ghcr.io/ahmadbitaarr/{scheduler,artifact-store,worker}` at the digests in the README): 4 passed in 130.6 s, launcher exit 0. Adapter and Hokea cleanup flags are true in all four tests, no pods were left in `team-06` or `team-06-clients`, and all 7 job histories pass the offline checker. Crash oracle: detection 5.01 s, expiry to new owner 0.56 s (one slow claim round trip), recovery 5.57 s. Bounded re-run test: X re-run 4.5 s after its pod was force-deleted, one success (attempt 2), job finished 24.9 s after the kill. The files the runner package ships are byte-identical at the final commit (`git diff 611c1de` over the package's file list is empty), so this run covers the final source. Evidence: `results/ms3-logs/hokea-cluster/closeout-611c1de/`.

## Chaos test

The intermittent failure Ahmad saw (101 passed, 1 failed on `lease_expired`) is an experiment flaw, not a system bug. The test killed `workers[0]` at 1.5 s and paused `workers[1]` at 2.5 s, then asserted that *some* lease expired. A worker between tasks (report acknowledged, next claim not yet answered, often lengthened by the proxy's injected delay and drops) holds no lease, so if both faults landed in such a gap nothing could expire. The fix (`7a358bf`) waits until each victim owns an unfinished attempt before the fault, waits 0.5 s for messages already inside the proxy, records the attempts each victim still owns, and requires every one of them to have a `lease_expired`. This is stronger than before: the old assertion passed if any lease expired anywhere. Ahmad's correction in the ZIP could not be compared; check that it does not simply drop or loosen the assertion. Result: passed in `make-test-4` and in 5 of 5 further fresh runs (`results/ms3-logs/repeats-chaos-and-bounded.log`).

## Verification results

| Check | Environment | Result |
|---|---|---|
| Build and JUnit (`mvn -B verify`) | Harness container (Linux, Docker Desktop 27.1.1), source `bfa3b08` | **77 passed**, 0 failed |
| Full pytest suite (`make test`, run 4) | Same | **105 passed, 2 skipped, 0 failed, 0 expected failures**, exit 0; 53 evidence directories |
| Hokea adapter and packaging unit tests, including the 2 that need real Hokea | WSL Ubuntu, the course lab's uv environment with public Hokea `427b946` | **25 passed** |
| Offline history checker over all saved evidence | `results/ms3-logs/` | **615 job histories in 127 directories, no violations** |
| Chaos campaign, repeated | Harness container | **5 of 5 passed** (6 of 6 with run 4) |
| Bounded re-run test, repeated | Harness container | **3 of 3 passed** (4 of 4 with run 4) |
| Course cluster, unchanged `6104fa7` package (reproduction) | `team-06`, runner `hokea-runner:2026.08.29.3` | 1 error at setup, as expected: `Hokea source mismatch at check.py` |
| Course cluster, fixed package (`611c1de`) | Same | **4 passed**, exit 0, cleanup succeeded, 7 histories pass |
| Compose deployment (`make up`, `make demo`, `make down` commands) | Docker Compose, 3 workers | **All exit 0**; `result=22`; video job with all four outputs; history checks passed |
| Recovery benchmark (`make bench-recovery`) | — | **Not re-executed.** Service code is unchanged since the measured revision; the October 29 results stand (17 of 18 runs complete, 13 of 13 orphaned tasks recovered) |
| Fault-free benchmark (`make bench`) | — | **Not re-executed** (MS2 Step 12 data, unchanged code paths) |
| `make faults`, `make fault-demo` | — | Not run separately; both are subsets of `make test`, which ran them |
| Hokea Docker mode (local) | — | Not executed; the Kubernetes run on the course cluster supersedes it |

Failed: none. Blocked: none.

## Files changed (branch `ms3/closeout`)

| File | Why |
|---|---|
| `tests/harness/hokea_adapter.py` | Byte-for-byte Hokea pin replaced by an API check plus recorded package provenance (root cause above) |
| `deploy/hokea/verify_api.py` | Uses the new check; reports differing files instead of failing |
| `deploy/hokea/package_runner.py` | Ships and imports the bounded re-run test |
| `tests/faults/test_crash_rerun_bounded.py` | New: the instructor's test, adapted only for MS3's idle-poll metric |
| `tests/faults/test_network_faults.py` | Chaos campaign faults land on a worker holding a task; every held attempt must expire |
| `tests/unit/test_hokea_adapter.py` | Pin test replaced by: differing runner recorded, missing API rejected, real Hokea provides the API |
| `tests/unit/test_hokea_packaging.py` | Expects 4 collected runner tests |
| `docs/specification.md` | §6 P-REC test reference, recovery approximation (claim round trip), load/bottleneck paragraph (feedback 2); §8 cluster; §9 change |
| `docs/ms3-progress-report.md` | Claim table, test counts, defects 3–4, §A closeout run, §D results, §F cluster, §G artifact store (feedback 3), §H |
| `docs/test-matrix.md` | New test row; chaos row; Hokea unit row; run reference |
| `docs/ms3-oral-defense.md` | Test counts; cluster Q&A |
| `README.md` | Test count; course-cluster commands; agent-doc label (feedback 4) |
| `results/ms3-logs/README.md` | Closeout run and cluster evidence rows |
| `deploy/hokea/README.md`, `CLUSTER-HANDOFF.md`, `docs/OPEN_ISSUES.md`, `docs/PROGRESS.md` | MS3 status notes; the "do not relax the pin" instruction withdrawn |
| `docs/pdf/*.pdf` | Rebuilt from the edited Markdown |
| `results/ms3-logs/hokea-cluster/`, `make-test-4.log`, `junit-make-test-4.xml`, `evidence-make-test-4/`, `repeats-chaos-and-bounded.log`, `compose-demo.log` | New evidence; the logs README's offline-check command also fixed (it crashed on a directory whose event stream was left out) |

## Remaining risks

1. **Scheduler is still a single in-memory node** (feedback 1a, R1, S3). The professor said this is why MS2 lost credit and that we are "on track for minimal ambition credit" without it. The spec scopes it out honestly, which satisfies MS3's "meets all declared specifications", but the ambition multiplier is decided at MS5. This is the largest risk, and it needs a design decision (WAL plus restart recovery is the smaller step; replication needs consensus).
2. **Benchmarks use uniform 100 ms sleeps** (R3, R4). Expect the professor to raise this; at minimum, non-uniform task durations and a mixed job population should come in MS4/MS5.
3. **The ZIP merge.** The humanized documents and Ahmad's chaos fix live only in the ZIP. If the ZIP is submitted unchanged, the Hokea fix, the new test and the corrected claims are missing. If this branch is submitted unchanged, the humanization is missing.
4. **Cluster coverage is four tests.** The other fault tests need the in-process proxy or SIGSTOP and run only natively.
5. **Timing.** Recovery assertions use a 2 s slack on the scheduler clock; on the cluster one requeue took 0.56 s (a slow claim round trip), well inside it.

## Resubmission recommendation

**Yes, with one condition.** The corrected branch is a meaningful improvement over the October 29 submission. It fixes the one bug the professor named outright (the Hokea pin), adds the one test he asked us to implement and pass, and verifies both on the course cluster rather than only locally. It also removes the artifact-store claim he objected to, labels the agent documents, fixes a flaky test without weakening it, and answers his load and bottleneck questions as far as our measurements allow.

The condition is the ZIP. Ahmad's humanized documents are not on this branch, and this branch's fixes are not in his ZIP. Before resubmitting: (1) take the ZIP's six humanized documents, (2) re-apply the sentence-level edits listed above to them (each is a sentence or a table row), (3) compare his chaos-test correction with `7a358bf` and keep the stronger one, (4) commit, rerun `make test`, and build the ZIP from that commit with `git archive --prefix=distributed-dag-scheduler/`. Pushing to GitHub needs Ahmad's agreement. The archive built from this branch (`distributed-dag-scheduler-ms3-closeout.zip`) is complete and verified, and it can be submitted as is if the merge cannot happen in time, at the cost of the humanization pass.
