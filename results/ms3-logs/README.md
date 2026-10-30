# MS3 run logs and evidence

We keep the selected MS3 run and earlier attempts here. Each record identifies the command and source revision used. We have not rewritten raw results. Some large logs and artifact bytes are omitted, as noted below; text files use LF line endings. An incomplete or superseded run remains labeled that way.

| Path | What it is |
|---|---|
| `make-test-5.log` | **The final full run** (October 30, label `ms3-make-test-5`, clean source `85b0ecb`, with the Hokea fix, the bounded re-run test and the combined chaos-test correction): Maven output for all 77 JUnit tests, then pytest `-rA` for all 107 tests (105 passed, 2 skipped, 0 failed, 0 expected failures, exit 0). The skipped tests need a real Hokea install; they pass in the course lab environment. |
| `junit-make-test-5.xml` | pytest JUnit XML for the same run (107 tests, 0 failures, 0 errors, 2 skipped). |
| `evidence-make-test-5/<test>/` | Per-test evidence from that run, in the same layout as `evidence-make-test-3/` below; the bounded re-run test adds `fault.json` and `rerun-window.json`. |
| `repeats-combined-chaos.log` | The final chaos test run five more times in fresh pytest sessions (code `85b0ecb`). |
| `hokea-cluster/repro-6104fa7/` | The course-cluster failure reproduced on October 30 with the unchanged `6104fa7` runner package (`hokea test --namespace team-06 -q -k test_service_exchange`): 1 error at setup, `Hokea source mismatch at check.py`. Launcher log, exit status and the copied-out `runs/`. |
| `hokea-cluster/closeout-611c1de/` | **The course-cluster run** after the adapter fix (`hokea test --namespace team-06 -v -rA`, source `611c1de`, the public MS3 images by digest): 4 passed in 130.6 s, launcher exit 0. `runs/<label>/<test>/` has each test's scheduler history, worker logs, snapshots and `hokea/metadata.json` (installed Hokea file hashes, pod identities, image references, cleanup); `runtime/` byte stores are omitted. The files the runner ships are unchanged in the final source. |
| `independent-check-ahmad/` | Ahmad's independent October 29 runs on `6104fa7`: the full run in which the chaos test failed (51 service-backed tests passed; that chaos history has no `lease_expired`), one plain rerun of the chaos test, and three reruns with his first correction (`+uncommitted`). Per-test evidence only; `runtime/` omitted. |
| `make-test-4.log`, `junit-make-test-4.xml`, `evidence-make-test-4/` | A full run of the closeout corrections before the documentation review was merged (clean source `bfa3b08`, 105 passed, 2 skipped). Superseded by run 5, whose chaos test combines both corrections. The `BrokenPipeError` in its chaos stderr is the fault proxy failing to answer the worker the test had just killed. |
| `repeats-chaos-and-bounded.log` | Repeats on the closeout code before the merge: chaos test 5 of 5, bounded re-run test 3 of 3. |
| `compose-demo.log` | October 30, the `make up`, `make demo`, `make down` commands on Docker Compose with three workers: all exit 0; functional job `result=22`, video job with all four outputs, history checks passed. |
| `make-test-3.log` | The full run submitted on October 29 (`make test`, label `ms3-make-test-3`, clean source `966965e`): Maven output for all 77 JUnit tests, then pytest `-rA` for all 102 tests (102 passed, 0 failed, 0 expected failures, exit 0). |
| `junit-make-test-3.xml` | pytest JUnit XML for the same run (102 tests, 0 failures, 0 errors, 0 skipped). |
| `evidence-make-test-3/<test>/` | Per-test evidence from that run: `events.jsonl` (scheduler history), `snapshots.json`, `manifests.json`, `metrics.json`, `worker-N.jsonl`, `scheduler.jsonl`, `artifact-store.jsonl`, `metadata.json`, and test-specific files (`proxy-worker-N.jsonl` for network faults, `recovery.json`, `fault.json`, `gate.json` for the crash oracle). Stored artifact bytes (`runtime/`) are omitted. |
| `make-test-1.log` | An earlier full run, kept as a record: 101 passed and 1 failed, because `test_counters_gauges_and_snapshot_sequence_are_consistent` still expected MS2's exact counter list. |
| `make-test-2.log`, `junit-make-test-2.xml` | A second full run, 102 passed, on code from before the idle-polling memory fix; stamped `+uncommitted` only because this log file was being written inside the repository. Superseded by run 3. |
| `memory-probe/` | `benchmarks/idle_memory.py` output: scheduler live heap with 4 idle workers before the fix (+257 MiB/hour) and after (flat), and heap per completed task after 100 jobs (~10 KB). |
| `recovery-benchmark/` | **The submitted recovery experiment** (`make bench-recovery`, source `d4fcda9`, service code as tested): `environment.json`, `runs.csv`, `recoveries.csv` (one row per expired lease), `recovery_jobs.csv`, `summary.csv`/`summary.json`, the driver's `console.log`, and `runs/<run>/` with each run's scheduler history, snapshots, manifests, metrics and kill records (worker and Compose logs omitted for size). 17 of 18 runs complete; all 18 histories (503 jobs) pass the offline checker. |
| `perf-attribution/` | Same-day controls for the benchmark host: the unchanged MS2 code (`ms2-code-c1-w4/`, `benchmarks.run --configs c1-w4`) and the MS3 code with its artifact data outside OneDrive (`ms3-code-c1-w4-outside-onedrive/`; its compose and worker logs and event stream were left out for size, keeping snapshots, metrics and CSVs). Both ran at about 3 tasks/s. This supports host variability as an explanation for the difference from Step 12's 6 tasks/s at C=1, W=4; it does not rule out every code-related effect. |
| `aborted-recovery-run-idle-kills/` | The first recovery-benchmark attempt, stopped after 3 runs: at C=1 it killed workers that were idle (0 expired attempts), so it measured nothing. The driver was fixed in `cca922d`. Kept so no run is silently discarded. |
| `aborted-recovery-run-replacement-race/` | The third attempt (final service code, source `966965e`), complete except that in two C=16 crash runs the second replacement worker failed to start: both replacements were named `worker-5` because they overlapped (a driver race, fixed in `d4fcda9`). Both kills still happened and all 18 expired leases were recovered (detection 5.00–5.07 s, recovery 5.01–6.64 s), and every job finished correctly, but those two runs are marked censored. Kept with its console log and recovery rows. |
| `aborted-recovery-run-pre-memory-fix/` | The second attempt (fixed driver, source `cca922d`), stopped after 4 complete runs when the idle-polling memory fix changed the scheduler, so that the final benchmark would run on the final code. Its 4 rows (2 baseline, 2 crash runs, each crash run with 2 busy-worker kills that were recovered) are kept for comparison. |

To recheck every retained history without starting services, run this with standard-library Python:

```bash
python3 - <<'PY'
from pathlib import Path
from tests.harness.check_evidence import check_directory
dirs = sorted(p.parent for p in Path("results/ms3-logs").rglob("manifests.json"))
checked = 0
for d in dirs:
    if not (d / "events.jsonl").is_file():
        print("NOT CHECKED (event stream omitted):", d)
        continue
    checked += len(check_directory(d))
print(checked, "job histories checked: no violations")
PY
```

The outside-OneDrive attribution control intentionally omits its event stream. The command reports that directory as NOT CHECKED; it cannot validate that control from snapshots alone. In this archive the test runs, cluster runs and selected benchmark provide 744 checked histories: 52, 53 and 53 from runs 3, 4 and 5, 7 from the course cluster, 76 from the independent check, and 503 from the benchmark.
