# MS2 claim-to-test and evidence matrix

Step 14 reconciles documentation against accepted `main @ bf43c619d00ee1658c5cb1eb297a5e1f59a2de8d`.
The quoted MS1 semester claims in `specification.md` are unchanged. The table below
describes current MS2 support and the checks that can falsify it; it does not claim
support for the deferred semester recovery mechanisms.

| Current claim / boundary | Existing checks | Accepted evidence |
|---|---|---|
| Valid manifests, limits and strict wire types; invalid submissions leave state unchanged | `ManifestValidatorTest`, `WireContractTest`; `test_api.py`; `test_invalid_dags_never_accepted`, `test_strict_json_types_and_unknown_fields` in `test_system.py` | Steps 2 and 5 under `results/handoffs/`; independent full gate in Step 13 |
| Dependency-safe execution, parallel branches, joins, one active attempt per session and all-task job success | `SchedulerStateMachineTest`; `test_join_and_independent_branch_concurrency`, `test_multiple_roots_sinks_and_all_tasks_required`, `test_simultaneous_claims_and_session_single_slot` | Steps 3 and 7; Step 13 full gate |
| Completion requires acknowledged start and a current-owner success report with published, matching outputs | `SchedulerCoreTest`, `SchedulerStateMachineTest`; `test_success_requires_published_correct_outputs`; `test_worker_has_one_slot_and_starts_only_after_ack` | Steps 3, 6 and 7; Step 13 full gate |
| Logical success is recorded once; reports/claims replay safely and stale attempts cannot change state | `test_submission_and_claim_receipts`, `test_duplicate_conflicting_stale_reports_and_retry`, `test_lost_report_ack_is_replayed_not_reexecuted` | Steps 7 and 8; Step 13 full gate |
| Immutable artifact publication; no partial reads or conflicting overwrite | `ArtifactStoreTest`; `test_artifact_staging_atomic_publication_and_conflicts` | Steps 4 and 7; Step 13 full gate |
| Explicit failure is retried with a later attempt; no retry limit | `test_real_worker_failure_attempt_two`; scheduler failure-transition tests | Steps 3 and 7; Step 13 full gate; an always-failing job is not claimed to finish |
| Histories detect unsafe behavior, gaps and snapshot inconsistencies | `tests/unit/test_history_checks.py`; `tests/harness/api.py:check_history`; `tests/harness/check_evidence.py` | Step 8 sample history; Step 12 checker regression record; Step 13 records 40/40 generated evidence directories valid |
| CLI upload/submit/status/fetch and five-task functional result | `test_java_client_upload_submit_status_fetch`; `test_committed_functional_workload` | Steps 6 and 7; Step 13 demo `result=22` |
| Video inspect/transcode/thumbnail/subtitle fixture/publish manifest | `test_video_pipeline`; `tests/harness/demo.py` | Step 9; Step 13: H.264 1280x720 and 640x360 MP4s, PNG 1280x720 and subtitles |
| Worker-crash ownership reclamation is intentionally missing, while safety holds | `tests/faults/test_worker_crash.py::test_worker_crash_reassignment`; `tests/unit/test_fault_oracle.py`; strict `raises=RecoveryNotObserved` | Step 10 gate/kill/probe/late-polling/safety exports; Step 13: one XFAIL under normal tests, sole real recovery failure under `make fault-demo` |
| Local Hokea adapter can control the same services and oracle without changing scheduler semantics | `tests/unit/test_hokea_adapter.py`, `test_hokea_packaging.py`, `test_hokea_smoke.py`; existing functional/concurrency/fault selections | `results/handoffs/step-11/FINAL-RESULTS.md`; course attempt stopped at package verification before service execution |
| Normal-operation benchmark completes the prescribed matrix, with host-specific synthetic results | `benchmarks/run.py` and `benchmarks/report.py`; output/history and in-flight checks | Step 12 clean measured source `8c5f3cb3c94ed9abdd18c4f178c0ef02e46ab1a3`, 45 runs, 1,080 measured jobs, 6,480 tasks; separate Step 13 c1-w1 one-repetition reproduction |
| Scheduler restart creates a new empty run; old messages are rejected rather than recovering state | `test_stale_run_is_rejected_everywhere`; `test_worker_abandons_old_run_and_joins_the_new_one` | Steps 5–7; no durable restart, replication/failover or exactly-once external-effects claim |

Test filenames without a full path above are under `tests/integration/`. Java tests
are in the module `src/test/java/edu/vt/dag/` directories. Earlier raw logs and
source manifests retain their original attribution. The Step 13 record is
`results/handoffs/step-13/VERIFICATION.md`: it summarizes a fresh Ubuntu checkout
of `f27aec9e1230b07c191f34f6a2278eafb0351f4f`, not a new run on the documentation
workspace. Its generated evidence remains at the original checkout's ignored
`results/latest-tests`; no missing Step 13 runtime files have been fabricated.

## Numeric attribution

| Reported quantities | Authoritative committed source |
|---|---|
| 128 tasks, 512 edges, 1 MiB manifest, 32 MiB artifact; schema and identity rules | `docs/api.md`, `protocol/src/main/java/edu/vt/dag/ManifestValidator.java`, wire/validator tests |
| 61 JUnit tests | `results/handoffs/step-10/checks/focused-java/command.log`: protocol 33, scheduler 20, store 8; not a Step 13 JUnit count |
| 87 pytest collected; 86 PASS, 1 intentional XFAIL, 0 failures; 40/40 evidence directories; Ubuntu/Docker/Compose/Python versions | `results/handoffs/step-13/VERIFICATION.md` |
| Fault window 10 seconds; only `RecoveryNotObserved`; nonzero Step 13 fault-demo | Existing fault test and Step 13 record. Exact Step 13 shell exit code was not preserved. |
| Functional result and media types/dimensions | Functional manifest/expected bytes; Step 13 functional/media section; Step 9 evidence |
| C/W matrix, repetitions, warmup/measurement counts, 1 CPU / 512 MiB, metric percentiles and throughput | `results/handoffs/step-12/full-20261003c/{environment.json,runs.csv,jobs.csv,tasks.csv,summary.csv,summary.json,RESULTS.md}`; `docs/handoffs/step-12.md` |
| Approximate 240 ms worker cycle and operation/HTTP/start cost discussion | Step 12 handoff/RESULTS timing interpretation; rounded estimates, not separate component instrumentation |
| Host RAM/CPU, VM cap, free memory and aborted-run descriptions | Step 12 handoff, `full-20261003c/environment.json`, `host-memory.csv` and retained aborted-run records |
| Local Hokea 84 PASS + 1 XFAIL and course setup mismatch | `results/handoffs/step-11/FINAL-RESULTS.md` and retained external evidence |
| Independent c1-w1 one-repetition throughput and p50s | Step 13 benchmark section; not pooled with the Step 12 matrix |

The evaluator command walkthrough is in [README.md](../README.md). Final reports
are `docs/ms2-progress-report.md`, `docs/specification.md` and the matching PDFs
under `docs/pdf/`. MS3 extension points are described in report Section I and
specification Section 8 only; no recovery mechanism is implemented here.
