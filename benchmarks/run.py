"""The approved 9-configuration, 5-repetition MS2 experiment. No fabricated results."""
import argparse
import csv
import json
import math
import os
import platform
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from tests.harness.api import benchmark_manifest, check_history
from tests.harness.runtime import harness


def percentile(values, fraction):
    return sorted(values)[math.ceil(len(values) * fraction) - 1] if values else None


def closed_loop(api, count, concurrency, timeout):
    active, finished, manifests = {}, [], {}
    submitted = 0
    deadline = time.monotonic() + timeout
    while submitted < count or active:
        while submitted < count and len(active) < concurrency:
            m = benchmark_manifest()
            active[api.submit(m)] = m
            manifests[m["job_id"]] = m
            submitted += 1
        for job in list(active):
            snapshot = api.status(job)
            if snapshot["state"] == "SUCCEEDED":
                finished.append(snapshot)
                del active[job]
        if time.monotonic() > deadline:
            return finished, [api.status(job) for job in active], manifests, count - submitted
        if active:
            time.sleep(0.01)
    return finished, [], manifests, 0


def append_csv(path, rows):
    if not rows:
        return
    exists = path.exists()
    with path.open("a", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        if not exists:
            writer.writeheader()
        writer.writerows(rows)


def capture(command):
    try:
        p = subprocess.run(command, capture_output=True, text=True, timeout=10)
        return (p.stdout + p.stderr).strip()
    except OSError as error:
        return str(error)


def summarize(root):
    with (root / "runs.csv").open() as f:
        runs = list(csv.DictReader(f))
    with (root / "jobs.csv").open() as f:
        jobs = list(csv.DictReader(f))
    with (root / "tasks.csv").open() as f:
        tasks = list(csv.DictReader(f))
    summaries = []
    for c in [1, 4, 16]:
        for w in [1, 2, 4]:
            selected = [r for r in runs if int(r["concurrency"]) == c and int(r["workers"]) == w]
            if not selected:
                continue
            matching = lambda r: int(r["concurrency"]) == c and int(r["workers"]) == w
            times = [float(r["completion_ms"]) for r in jobs if matching(r) and r["completion_ms"]]
            latency = [float(r["scheduling_ms"]) for r in tasks if matching(r)]
            throughputs = [float(r["tasks_per_second"]) for r in selected if r["status"] == "complete"]
            summaries.append({"concurrency": c, "workers": w, "repetitions": len(selected),
                              "job_p50_ms": percentile(times, .5), "job_p95_ms": percentile(times, .95),
                              "scheduling_p50_ms": percentile(latency, .5), "scheduling_p95_ms": percentile(latency, .95),
                              "throughput_mean": statistics.mean(throughputs) if throughputs else None,
                              "throughput_stdev": statistics.stdev(throughputs) if len(throughputs) > 1 else 0,
                              "throughput_min": min(throughputs) if throughputs else None,
                              "throughput_max": max(throughputs) if throughputs else None,
                              "incomplete_jobs": sum(int(r["incomplete_jobs"]) for r in selected),
                              "error_runs": sum(r["status"] != "complete" for r in selected)})
    path = root / "summary.csv"
    path.unlink(missing_ok=True)
    append_csv(path, summaries)
    (root / "summary.json").write_text(json.dumps(summaries, indent=2))
    return summaries


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="results/benchmark")
    parser.add_argument("--backend", choices=["native", "compose"], default=os.environ.get("MS2_BACKEND", "native"))
    args = parser.parse_args()
    root = Path(args.out).resolve()
    root.mkdir(parents=True, exist_ok=True)
    if (root / "runs.csv").exists():
        raise SystemExit("Output already contains runs.csv; use a new directory to preserve evidence")
    metadata = {"started_utc": datetime.now(timezone.utc).isoformat(), "command": sys.argv,
                "python": sys.version, "platform": platform.platform(), "cpu_count": os.cpu_count(),
                "cpu_affinity": sorted(os.sched_getaffinity(0)) if hasattr(os, "sched_getaffinity") else None,
                "java": capture([os.environ.get("JAVA", "java"), "-version"]), "ffmpeg": capture(["ffmpeg", "-version"]),
                "backend": args.backend, "jvm_heap_mib": 128, "service_cpu_limit": "1 CPU via affinity" if args.backend == "native" else "Docker cpus: 1",
                "service_memory_limit": "512 MiB NOT ENFORCED in native mode" if args.backend == "native" else "Docker mem_limit: 512m",
                "contract": {"concurrency": [1, 4, 16], "workers": [1, 2, 4], "warmup": 4, "measured_jobs": 24, "tasks_per_job": 6, "delay_ms": 100, "repetitions": 5, "timeout_seconds": 120},
                "limitations": ["Shared execution host", "Synthetic waiting workload; not codec or CPU scaling", "Recovery time unmeasured"]}
    (root / "environment.json").write_text(json.dumps(metadata, indent=2))
    any_errors = False
    for c in [1, 4, 16]:
        for w in [1, 2, 4]:
            for repetition in range(1, 6):
                tag = f"c{c}-w{w}-r{repetition}"
                with harness(root / tag, args.backend) as system:
                    for _ in range(w):
                        system.start_worker()
                    warm, unfinished, _, unsubmitted = closed_loop(system.api, 4, c, 120)
                    assert len(warm) == 4 and not unfinished and not unsubmitted, "Warmup failure"
                    completed, unfinished, manifests, unsubmitted = closed_loop(system.api, 24, c, 120)
                    snapshots = completed + unfinished
                    events = system.api.events()
                    common = {"configuration": tag, "concurrency": c, "workers": w, "repetition": repetition, "scheduler_run_id": system.api.run_id}
                    job_rows, task_rows = [], []
                    for snapshot in snapshots:
                        check_history(manifests[snapshot["job_id"]], snapshot, events)
                        job_rows.append({**common, "job_id": snapshot["job_id"], "state": snapshot["state"], "accepted_elapsed_ns": snapshot["accepted_elapsed_ns"],
                                         "completed_elapsed_ns": snapshot["completed_elapsed_ns"], "completion_ms": snapshot["duration_ns"] / 1e6 if snapshot["duration_ns"] is not None else None})
                        for name, task in snapshot["tasks"].items():
                            assert len(task["attempts"]) <= 1, "Unexpected retry in fault-free benchmark"
                            if not task["attempts"]:
                                continue
                            attempt = task["attempts"][0]
                            task_rows.append({**common, "job_id": snapshot["job_id"], "task_id": name, "state": task["state"],
                                              "ready_elapsed_ns": attempt["ready_elapsed_ns"], "assigned_elapsed_ns": attempt["assigned_elapsed_ns"],
                                              "started_elapsed_ns": attempt["started_elapsed_ns"], "succeeded_elapsed_ns": attempt["finished_elapsed_ns"],
                                              "scheduling_ms": (attempt["assigned_elapsed_ns"] - attempt["ready_elapsed_ns"]) / 1e6})
                    incomplete = len(unfinished) + unsubmitted
                    status = "complete" if len(completed) == 24 and not incomplete else "censored"
                    any_errors |= status != "complete"
                    batch_ns = max(s["completed_elapsed_ns"] for s in completed) - min(s["accepted_elapsed_ns"] for s in completed) if status == "complete" else None
                    durations = [s["duration_ns"] / 1e6 for s in completed]
                    latencies = [r["scheduling_ms"] for r in task_rows]
                    append_csv(root / "jobs.csv", job_rows)
                    append_csv(root / "tasks.csv", task_rows)
                    append_csv(root / "runs.csv", [{**common, "status": status, "completed_jobs": len(completed), "incomplete_jobs": incomplete,
                                                   "logical_successes": sum(t["state"] == "SUCCEEDED" for s in snapshots for t in s["tasks"].values()),
                                                   "batch_interval_ns": batch_ns, "tasks_per_second": 144 / (batch_ns / 1e9) if batch_ns else None,
                                                   "job_p50_ms": percentile(durations, .5), "job_p95_ms": percentile(durations, .95),
                                                   "scheduling_p50_ms": percentile(latencies, .5), "scheduling_p95_ms": percentile(latencies, .95)}])
                    summarize(root)
                    print(json.dumps({"run": tag, "status": status, "completed_jobs": len(completed), "throughput": 144 / (batch_ns / 1e9) if batch_ns else None}), flush=True)
    metadata["finished_utc"] = datetime.now(timezone.utc).isoformat()
    (root / "environment.json").write_text(json.dumps(metadata, indent=2))
    if any_errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
