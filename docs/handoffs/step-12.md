# Step 12 — Exact initial performance experiment

```text
Status: DONE on branch ms2/step-12-benchmark (gate passed; integrate into main via the team process)
Base: main @ bf4f7845ead5b1b51c2bc00ea7108e5ac33234b0 (Steps 0–11 accepted), merged into this branch
Measured source: 8c5f3cb3c94ed9abdd18c4f178c0ef02e46ab1a3 (clean tree). Service code, POMs,
  Dockerfiles and Compose are byte-identical to the Step 9 gate (empty diff since 2a89f8a).
Canonical architecture SHA-256: 7d2f931bfcf308ccc2b32a899e8976e75656dab81f51b940df1aa136b37a8ef1
```

## Result

All **45 of 45 measured runs completed**: 9 configurations × 5 fresh repetitions, with **0 censored and 0 error runs**.

- **Totals:** 180 warmup jobs (excluded), 1,080 measured jobs and 6,480 measured logical tasks, exactly the roadmap totals.
- **Per run:**
  - 24/24 jobs reached `job_completed`;
  - 144 `task_succeeded` events;
  - 24 correct `result=9` outputs, checked by downloading each one;
  - no `task_retried`;
  - every job history passed `check_history`.
- **In-flight bound:** the peak number of in-flight jobs, computed from scheduler events, equalled C in every run and never exceeded it.

Tables: `results/handoffs/step-12/full-20261003c/RESULTS.md`, regenerated from the raw CSVs by `python -m benchmarks.report results/handoffs/step-12/full-20261003c`.

| C | W | job p50 / p95 ms | scheduling p50 / p95 ms | throughput mean (sd) tasks/s |
|---|---|---|---|---|
| 1 | 1 | 1,398 / 1,454 | 5.7 / 450 | 4.20 (0.02) |
| 1 | 2 | 1,149 / 1,202 | 4.4 / 228 | 5.09 (0.06) |
| 1 | 4 | 961 / 1,027 | 4.9 / 80 | 6.04 (0.10) |
| 4 | 1 | 5,435 / 5,543 | 1,107 / 2,251 | 4.34 (0.01) |
| 4 | 2 | 2,800 / 2,921 | 459 / 1,133 | 8.31 (0.04) |
| 4 | 4 | 1,488 / 1,570 | 82 / 469 | 15.36 (0.04) |
| 16 | 1 | 19,561 / 21,889 | 3,934 / 9,731 | 4.35 (0.06) |
| 16 | 2 | 9,951 / 11,122 | 1,881 / 4,785 | 8.56 (0.03) |
| 16 | 4 | 5,151 / 5,718 | 834 / 2,329 | 16.69 (0.28) |

## Method

Implemented by `benchmarks/run.py`, `make bench`.

- **Deployment:** a fresh Compose deployment per repetition: scheduler, artifact store and W one-slot workers. Each service is capped at **1 CPU and 512 MiB**, with a 128 MiB JVM heap, 16 handler threads, `restart: no`, and a 100 ms worker poll interval.
- **Warmup and load:** 4 warmup jobs per repetition on the same JVMs (excluded), then 24 measured jobs. The closed loop keeps at most C jobs in flight.
- **Workload:** the six-task DAG. A=1; B, C and D add 1, 2 and 3; E sums them to 9; F formats `result=9\n`. Each task is a 100 ms fixture wait.
- **Timeout:** 120 s for the measured phase. No faults are injected.
- **Clock:** every metric comes from the scheduler's monotonic clock (snapshot `*_elapsed_ns`).
  - **Job completion time** runs from acceptance to `job_completed`.
  - **Scheduling latency** runs from READY to ASSIGNED, for initial attempts only.
  - **Throughput** is measured logical successes ÷ (last measured completion − first measured acceptance).
- **Aggregation:**
  - **Percentiles** use the nearest-rank method, pooling the samples of all complete runs in a configuration. The median of the per-run p95 values is also reported.
  - **Throughput** is reported as the mean, sample standard deviation, and min–max across the 5 run-level values.
  - Warmup jobs and duplicate messages are excluded.
- **Completion detection:** read incrementally from the event stream (one request per poll), so the driver does not load the 1-CPU scheduler with per-job snapshot polling.

## Observed behavior and bottlenecks

1. **Throughput is set by worker capacity, about 4.2 tasks/s per one-slot worker.** With C ≥ 4, going from W=1 to 2 to 4 gives 4.3 → 8.3–8.6 → 15.4–16.7 tasks/s, which is near-linear. At C=1, the DAG's own width limits parallelism: B, C and D are the only concurrent tasks, so W=2 and W=4 give 5.1 and 6.0 instead of 2× and 4×.
2. **The scheduler is not the bottleneck at this scale.**
   - With an idle worker available, the median READY→ASSIGNED time is 4–6 ms, which includes the 100 ms poll interval's effect on idle workers.
   - Larger scheduling latencies come only from queueing for busy workers. They grow with C/W, matching the closed-loop queue: about 1.1 s at C=4/W=1, about 3.9 s at C=16/W=1.
   - The median RUNNING→SUCCEEDED time stays flat at 172–188 ms from C=1 to C=16, so scheduler work does not slow execution.
3. **Per-task cost on the worker:** about 100 ms of operation, plus about 75–90 ms of HTTP artifact work (input GET with hash check, output PUT, and the scheduler's HEAD verification of outputs), plus the start acknowledgment round trip (median about 45 ms; 25 ms and 4 ms at C=1 with W=2 and W=4). Together with claiming, that sets the ~240 ms per-task cycle behind the ~4.2 tasks/s per-worker ceiling.
4. **Variance is low:** the throughput standard deviation is at most 0.28 tasks/s across repetitions.

No speedup or numeric target was promised, and none is claimed.

## Environment

All of this is recorded in `environment.json`:

- Windows 11 host with 12 logical CPUs and 16 GB RAM.
- Docker Desktop 27.1.1 (WSL2 backend), Compose v2.29.1.
- Driver: Python 3.13.1 on the host.
- **WSL2/Docker VM capped at 3 GB** through `%USERPROFILE%\.wslconfig` (`memory=3GB`, `autoMemoryReclaim=gradual`).

During the run, host free memory never fell below 1.9 GB (median 2.4 GB over 210 samples; see `host-memory.csv`).

## Limitations

- **Shared host.** All services, the driver and the Docker VM ran on one Windows machine, and Docker CPU caps share the host's 12 CPUs. Absolute numbers are specific to this host.
- **Synthetic waiting workload.** It characterizes coordination and HTTP overhead, not codec or CPU scaling.
- **Polling is included.** Worker polling (100 ms when idle) is part of the measured scheduling latency, as the architecture requires.
- **Recovery time is unmeasured** in MS2. The 10 s crash-test window is not a recovery measurement.
- **Environment sensitivity is real.** Two earlier full-matrix attempts on the same host without the VM cap were aborted. Free memory was 0.4–1 GB, the Docker VM was paged, and Docker crashed. Those attempts are kept unmodified as aborted records (`../../results/handoffs/step-12/aborted-full-20261003*/`) and are not used. The smoke run without the cap gave 1.6 tasks/s for C=1/W=1; the capped VM gives 4.2.

## Defect found and fixed during Step 12

`check_history` reported a false violation when a snapshot of a still-running job was compared with a later, longer history. This happened in a censored run of the second aborted attempt.

- **Fix:** snapshots are compared only with the history prefix up to their `snapshot_event_seq`.
- **Regression tests** were added. One fails on the old code, confirmed by a mutation check.
- **Re-check:** the full suite still gave `mvn -B verify` exit 0 and 86 passed + 1 xfailed.

Details: `results/handoffs/step-12/aborted-full-20261003b/README.md`.

## Commands (all exit 0)

```text
docker compose -f deploy/compose/compose.yaml build
python -m benchmarks.run --backend compose --out results/benchmark/smoke-20261003c --configs c1-w1,c16-w4 --repetitions 1   # 2/2 complete
python -m benchmarks.run --backend compose --out results/benchmark/full-20261003c                                          # 45/45 complete, BENCH_EXIT=0
python -m benchmarks.report results/handoffs/step-12/full-20261003c > results/handoffs/step-12/full-20261003c/RESULTS.md
```

The output directory was copied to `results/handoffs/step-12/full-20261003c/`: the raw `runs.csv`, `jobs.csv` and `tasks.csv`, plus `summary.csv`, `summary.json`, `environment.json`, `host-memory.csv`, `smoke-runs.csv` and `RESULTS.md`. Per-run harness directories, with events and logs for every run, remain in the gitignored `results/benchmark/full-20261003c/`.

Architecture deviations: none. No fault mechanism or scheduler behavior was changed.

## Next

Step 13, independent clean-checkout verification by another teammate. See `docs/handoffs/TEAMMATE-PROMPT-steps-12-15.md`. Step 12 is now done, so they can skip it and only run the short benchmark reproduction listed under Step 13.
