# MS3 run logs and evidence

Everything here was produced by the commands shown, on the source revision recorded in each file. Nothing was edited after the run, except that large raw logs were left out where a row says so, and text files are stored with LF line endings.

| Path | What it is |
|---|---|
| `make-test-3.log` | **The submitted full run** (`make test`, label `ms3-make-test-3`, clean source `966965e`): Maven output for all 77 JUnit tests, then pytest `-rA` for all 102 tests (102 passed, 0 failed, 0 expected failures, exit 0). |
| `junit-make-test-3.xml` | pytest JUnit XML for the same run (102 tests, 0 failures, 0 errors, 0 skipped). |
| `evidence-make-test-3/<test>/` | Per-test evidence from that run: `events.jsonl` (scheduler history), `snapshots.json`, `manifests.json`, `metrics.json`, `worker-N.jsonl`, `scheduler.jsonl`, `artifact-store.jsonl`, `metadata.json`, and test-specific files (`proxy-worker-N.jsonl` for network faults, `recovery.json`, `fault.json`, `gate.json` for the crash oracle). Stored artifact bytes (`runtime/`) are omitted. |
| `make-test-1.log` | An earlier full run, kept as a record: 101 passed and 1 failed, because `test_counters_gauges_and_snapshot_sequence_are_consistent` still expected MS2's exact counter list. |
| `make-test-2.log`, `junit-make-test-2.xml` | A second full run, 102 passed, on code from before the idle-polling memory fix; stamped `+uncommitted` only because this log file was being written inside the repository. Superseded by run 3. |
| `memory-probe/` | `benchmarks/idle_memory.py` output: scheduler live heap with 4 idle workers before the fix (+257 MiB/hour) and after (flat), and heap per completed task after 100 jobs (~10 KB). |
| `recovery-benchmark/` | **The submitted recovery experiment** (`make bench-recovery`, source `d4fcda9`, service code as tested): `environment.json`, `runs.csv`, `recoveries.csv` (one row per expired lease), `recovery_jobs.csv`, `summary.csv`/`summary.json`, the driver's `console.log`, and `runs/<run>/` with each run's scheduler history, snapshots, manifests, metrics and kill records (worker and Compose logs omitted for size). 17 of 18 runs complete; all 18 histories (503 jobs) pass the offline checker. |
| `perf-attribution/` | Same-day controls for the benchmark host: the unchanged MS2 code (`ms2-code-c1-w4/`, `benchmarks.run --configs c1-w4`) and the MS3 code with its artifact data outside OneDrive (`ms3-code-c1-w4-outside-onedrive/`; its compose and worker logs and event stream were left out for size, keeping snapshots, metrics and CSVs). Both ran at about 3 tasks/s, so the drop from Step 12's 6 tasks/s at C=1, W=4 comes from the host on October 29, not from MS3's code. |
| `aborted-recovery-run-idle-kills/` | The first recovery-benchmark attempt, stopped after 3 runs: at C=1 it killed workers that were idle (0 expired attempts), so it measured nothing. The driver was fixed in `cca922d`. Kept so no run is silently discarded. |
| `aborted-recovery-run-replacement-race/` | The third attempt (final service code, source `966965e`), complete except that in two C=16 crash runs the second replacement worker failed to start: both replacements were named `worker-5` because they overlapped (a driver race, fixed in `d4fcda9`). Both kills still happened and all 18 expired leases were recovered (detection 5.00–5.07 s, recovery 5.01–6.64 s), and every job finished correctly, but those two runs are marked censored. Kept with its console log and recovery rows. |
| `aborted-recovery-run-pre-memory-fix/` | The second attempt (fixed driver, source `cca922d`), stopped after 4 complete runs when the idle-polling memory fix changed the scheduler, so that the final benchmark would run on the final code. Its 4 rows (2 baseline, 2 crash runs, each crash run with 2 busy-worker kills that were recovered) are kept for comparison. |

Re-check every saved history offline (Python standard library only):

```bash
python3 - <<'PY'
from pathlib import Path
from tests.harness.check_evidence import check_directory
dirs = sorted(p.parent for p in Path("results/ms3-logs").rglob("manifests.json"))
print(sum(len(check_directory(d)) for d in dirs), "job histories in", len(dirs), "directories: no violations")
PY
```
