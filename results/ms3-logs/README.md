# MS3 run logs and evidence

Everything here was produced by the commands shown, on the source revision recorded in each file. Nothing was edited after the run.

| Path | What it is |
|---|---|
| `make-test-2.log` | **The submitted full run** (`make test`, label `ms3-make-test-2`, source `fdf5d02`): Maven output for all 76 JUnit tests, then pytest `-rA` for all 102 tests (102 passed, 0 failed, 0 expected failures, exit 0). |
| `junit-make-test-2.xml` | pytest JUnit XML for the same run (102 tests, 0 failures, 0 errors, 0 skipped). |
| `evidence-make-test-2/<test>/` | Per-test evidence from that run: `events.jsonl` (scheduler history), `snapshots.json`, `manifests.json`, `metrics.json`, `worker-N.jsonl`, `scheduler.jsonl`, `artifact-store.jsonl`, `metadata.json`, and test-specific files (`proxy-worker-N.jsonl` for network faults, `recovery.json`, `fault.json`, `gate.json` for the crash oracle). Stored artifact bytes (`runtime/`) are omitted. |
| `make-test-1.log` | The previous full run, kept as a record: 101 passed and 1 failed, because `test_counters_gauges_and_snapshot_sequence_are_consistent` still expected MS2's exact counter list. Only that test changed before run 2. |
| `recovery-benchmark/` | `make bench-recovery` output: `environment.json`, `runs.csv`, `recoveries.csv`, `recovery_jobs.csv`, `summary.csv`/`summary.json`, the driver's console log, and per-run evidence. |
| `perf-attribution/` | Same-day controls for the benchmark host: the unchanged MS2 code (`ms2-code-c1-w4/`, `benchmarks.run --configs c1-w4`) and the MS3 code with its artifact data outside OneDrive (`ms3-code-c1-w4-outside-onedrive/`). Both ran at about 3 tasks/s, so the drop from Step 12's 6 tasks/s at C=1, W=4 comes from the host on October 29, not from MS3's code. |
| `aborted-recovery-run-idle-kills/` | The first recovery-benchmark attempt, stopped after 3 runs: at C=1 it killed workers that were idle (0 expired attempts), so it measured nothing. The driver was fixed in `cca922d`. Kept so no run is silently discarded. |

Re-check every saved history offline (Python standard library only):

```bash
python3 - <<'PY'
from pathlib import Path
from tests.harness.check_evidence import check_directory
dirs = sorted(p.parent for p in Path("results/ms3-logs").rglob("manifests.json"))
print(sum(len(check_directory(d)) for d in dirs), "job histories in", len(dirs), "directories: no violations")
PY
```
