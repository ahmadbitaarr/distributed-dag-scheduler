"""The approved MS2 benchmark (architecture §13, roadmap Step 12). No fabricated results.

    python -m benchmarks.run --backend compose --out results/benchmark/<name>
    python -m benchmarks.run --backend compose --out ... --configs c1-w1 --repetitions 1   # smoke check

Matrix: C in {1,4,16} in-flight jobs x W in {1,2,4} one-slot workers x 5 fresh repetitions.
Each repetition: fresh scheduler/store/workers, 4 warmup jobs (excluded, same JVMs), then 24
measured six-task jobs (A=1; B/C/D add 1/2/3; E sums to 9; F formats "result=9\\n"; 100 ms
fixture waits) in a closed loop that keeps at most C jobs in flight. 120 s measured-phase timeout.

All timings come from the scheduler's own monotonic clock (snapshot *_elapsed_ns):
  job completion time = accepted -> job_completed; scheduling latency = READY -> ASSIGNED;
  throughput = measured logical successes / (last measured completion - first measured acceptance).
Completion is detected from the scheduler event stream (one cheap request per loop), so the
driver does not load the 1-CPU scheduler with per-job snapshot polling.

Every run is recorded, including failed or censored ones; an error in one run never discards others.
"""
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
import traceback
from datetime import datetime, timezone
from pathlib import Path
from tests.harness.api import benchmark_manifest, check_history, request
from tests.harness.runtime import harness

CONCURRENCY, WORKERS, REPETITIONS = [1, 4, 16], [1, 2, 4], 5
WARMUP_JOBS, MEASURED_JOBS, TASKS_PER_JOB, TIMEOUT_S = 4, 24, 6, 120
EXPECTED_RESULT = b"result=9\n"


def percentile(values, fraction):
    """Nearest-rank percentile: the smallest sample with at least `fraction` of samples <= it."""
    return sorted(values)[math.ceil(len(values) * fraction) - 1] if values else None


class EventCursor:
    """Incrementally reads the scheduler event stream; one request per poll."""
    def __init__(self, api):
        self.api, self.after, self.events = api, 0, []

    def poll(self):
        while True:
            status, page = request(self.api.scheduler, f"/v1/events?after={self.after}&limit=1000")
            assert status == 200 and page["scheduler_run_id"] == self.api.run_id
            new = page["events"]
            self.events.extend(new)
            self.after = page["next_after"]
            if not page["has_more"]:
                return new


def closed_loop(api, cursor, count, concurrency, timeout):
    """Keep at most `concurrency` jobs in flight until `count` jobs were submitted and finished."""
    active, finished, manifests, submitted = set(), [], {}, 0
    deadline = time.monotonic() + timeout
    while submitted < count or active:
        while submitted < count and len(active) < concurrency:
            m = benchmark_manifest()
            api.submit(m)
            active.add(m["job_id"])
            manifests[m["job_id"]] = m
            submitted += 1
        for e in cursor.poll():
            if e["event_type"] == "job_completed" and e["job_id"] in active:
                active.discard(e["job_id"])
                finished.append(e["job_id"])
        if time.monotonic() > deadline:
            return finished, sorted(active), manifests, count - submitted
        if active:
            time.sleep(0.02)
    return finished, [], manifests, 0


def max_in_flight(events, jobs):
    """Largest number of these jobs simultaneously between job_submitted and job_completed."""
    current = peak = 0
    for e in events:
        if e.get("job_id") in jobs and e["event_type"] == "job_submitted":
            current += 1
            peak = max(peak, current)
        elif e.get("job_id") in jobs and e["event_type"] == "job_completed":
            current -= 1
    return peak


def append_csv(path, rows, fields=None):
    if not rows:
        return
    exists = path.exists()
    with path.open("a", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields or list(rows[0]))
        if not exists:
            writer.writeheader()
        writer.writerows(rows)


def capture(command):
    try:
        p = subprocess.run(command, capture_output=True, text=True, timeout=30)
        return (p.stdout + p.stderr).strip()
    except (OSError, subprocess.SubprocessError) as error:
        return str(error)


RUN_FIELDS = ["configuration", "concurrency", "workers", "repetition", "scheduler_run_id", "status", "error",
              "completed_jobs", "incomplete_jobs", "logical_successes", "max_in_flight", "correct_outputs",
              "batch_interval_ns", "tasks_per_second", "job_p50_ms", "job_p95_ms", "scheduling_p50_ms", "scheduling_p95_ms",
              "wall_seconds"]


def run_one(root, backend, c, w, repetition):
    tag = f"c{c}-w{w}-r{repetition}"
    common = {"configuration": tag, "concurrency": c, "workers": w, "repetition": repetition}
    row = {**common, "scheduler_run_id": None, "status": "error", "error": None, "completed_jobs": 0,
           "incomplete_jobs": MEASURED_JOBS}
    started = time.monotonic()
    job_rows, task_rows = [], []
    try:
        with harness(root / tag, backend) as system:
            row["scheduler_run_id"] = system.api.run_id
            common["scheduler_run_id"] = system.api.run_id
            for _ in range(w):
                system.start_worker()
            cursor = EventCursor(system.api)
            warm, unfinished, _, unsubmitted = closed_loop(system.api, cursor, WARMUP_JOBS, c, TIMEOUT_S)
            if len(warm) != WARMUP_JOBS or unfinished or unsubmitted:
                raise RuntimeError(f"warmup incomplete: {len(warm)}/{WARMUP_JOBS}")
            completed, unfinished, manifests, unsubmitted = closed_loop(system.api, cursor, MEASURED_JOBS, c, TIMEOUT_S)
            snapshots = [system.api.status(job) for job in completed + unfinished]
            cursor.poll()
            events = cursor.events
            correct = 0
            for snapshot in snapshots:
                check_history(manifests[snapshot["job_id"]], snapshot, events)
                if snapshot["state"] == "SUCCEEDED":
                    correct += system.api.get(snapshot["outputs"]["result"]) == EXPECTED_RESULT
                job_rows.append({**common, "job_id": snapshot["job_id"], "state": snapshot["state"],
                                 "accepted_elapsed_ns": snapshot["accepted_elapsed_ns"],
                                 "completed_elapsed_ns": snapshot["completed_elapsed_ns"],
                                 "completion_ms": snapshot["duration_ns"] / 1e6 if snapshot["duration_ns"] is not None else None})
                for name, task in snapshot["tasks"].items():
                    if len(task["attempts"]) > 1:
                        raise RuntimeError(f"unexpected retry of {name} in a fault-free run")
                    if not task["attempts"]:
                        continue
                    a = task["attempts"][0]
                    task_rows.append({**common, "job_id": snapshot["job_id"], "task_id": name, "state": task["state"],
                                      "ready_elapsed_ns": a["ready_elapsed_ns"], "assigned_elapsed_ns": a["assigned_elapsed_ns"],
                                      "started_elapsed_ns": a["started_elapsed_ns"], "succeeded_elapsed_ns": a["finished_elapsed_ns"],
                                      "scheduling_ms": (a["assigned_elapsed_ns"] - a["ready_elapsed_ns"]) / 1e6})
            measured = set(manifests)
            successes = sum(e["event_type"] == "task_succeeded" and e.get("job_id") in measured for e in events)
            completions = sum(e["event_type"] == "job_completed" and e.get("job_id") in measured for e in events)
            if any(e["event_type"] == "task_retried" for e in events):
                raise RuntimeError("task_retried in a fault-free run")
            peak = max_in_flight(events, measured)
            if peak > c:
                raise RuntimeError(f"closed loop exceeded C: {peak} > {c}")
            incomplete = len(unfinished) + unsubmitted
            done = [s for s in snapshots if s["state"] == "SUCCEEDED"]
            complete = (len(done) == MEASURED_JOBS and not incomplete and successes == MEASURED_JOBS * TASKS_PER_JOB
                        and completions == MEASURED_JOBS and correct == MEASURED_JOBS)
            batch_ns = (max(s["completed_elapsed_ns"] for s in done) - min(s["accepted_elapsed_ns"] for s in snapshots)) if done else None
            durations = [s["duration_ns"] / 1e6 for s in done]
            latencies = [r["scheduling_ms"] for r in task_rows]
            row.update({"status": "complete" if complete else "censored", "completed_jobs": len(done),
                        "incomplete_jobs": incomplete, "logical_successes": successes, "max_in_flight": peak,
                        "correct_outputs": correct, "batch_interval_ns": batch_ns,
                        "tasks_per_second": successes / (batch_ns / 1e9) if complete else None,
                        "job_p50_ms": percentile(durations, .5), "job_p95_ms": percentile(durations, .95),
                        "scheduling_p50_ms": percentile(latencies, .5), "scheduling_p95_ms": percentile(latencies, .95)})
    except Exception as error:  # record the failed run and keep going; nothing is discarded or replaced
        row["error"] = f"{type(error).__name__}: {error}"
        (root / tag).mkdir(parents=True, exist_ok=True)
        (root / tag / "benchmark-error.txt").write_text(traceback.format_exc())
    row["wall_seconds"] = round(time.monotonic() - started, 1)
    append_csv(root / "jobs.csv", job_rows)
    append_csv(root / "tasks.csv", task_rows)
    append_csv(root / "runs.csv", [row], RUN_FIELDS)
    return row


def summarize(root):
    def load(name):
        path = root / name
        if not path.exists():
            return []
        with path.open() as f:
            return list(csv.DictReader(f))
    runs, jobs, tasks = load("runs.csv"), load("jobs.csv"), load("tasks.csv")
    complete_runs = {(r["configuration"]) for r in runs if r["status"] == "complete"}
    summaries = []
    for c in CONCURRENCY:
        for w in WORKERS:
            selected = [r for r in runs if int(r["concurrency"]) == c and int(r["workers"]) == w]
            if not selected:
                continue
            ok = lambda r: int(r["concurrency"]) == c and int(r["workers"]) == w and r["configuration"] in complete_runs
            times = [float(r["completion_ms"]) for r in jobs if ok(r) and r["completion_ms"]]
            latency = [float(r["scheduling_ms"]) for r in tasks if ok(r)]
            throughputs = [float(r["tasks_per_second"]) for r in selected if r["status"] == "complete"]
            run_p95 = [float(r["job_p95_ms"]) for r in selected if r["status"] == "complete"]
            summaries.append({
                "concurrency": c, "workers": w, "repetitions": len(selected),
                "complete_runs": sum(r["status"] == "complete" for r in selected),
                "censored_runs": sum(r["status"] == "censored" for r in selected),
                "error_runs": sum(r["status"] == "error" for r in selected),
                "jobs_pooled": len(times), "job_p50_ms": percentile(times, .5), "job_p95_ms": percentile(times, .95),
                "job_p95_ms_run_median": statistics.median(run_p95) if run_p95 else None,
                "tasks_pooled": len(latency), "scheduling_p50_ms": percentile(latency, .5), "scheduling_p95_ms": percentile(latency, .95),
                "throughput_mean": statistics.mean(throughputs) if throughputs else None,
                "throughput_stdev": statistics.stdev(throughputs) if len(throughputs) > 1 else None,
                "throughput_min": min(throughputs) if throughputs else None,
                "throughput_max": max(throughputs) if throughputs else None,
                "incomplete_jobs": sum(int(r["incomplete_jobs"]) for r in selected)})
    path = root / "summary.csv"
    path.unlink(missing_ok=True)
    append_csv(path, summaries)
    (root / "summary.json").write_text(json.dumps(summaries, indent=2))
    return summaries


def environment(args):
    images = {}
    for name in ("scheduler", "artifact-store", "worker"):
        images[name] = capture(["docker", "image", "inspect", "--format", "{{.Id}} created {{.Created}}", f"dag-ms2/{name}:0.2.0"])
    return {"started_utc": datetime.now(timezone.utc).isoformat(), "command": sys.argv,
            "source_revision": os.environ.get("MS2_SOURCE_REV") or capture(["git", "rev-parse", "HEAD"]),
            "source_dirty": bool(capture(["git", "status", "--porcelain"])),
            "python": sys.version, "platform": platform.platform(), "host_cpu_count": os.cpu_count(),
            "backend": args.backend,
            "docker": capture(["docker", "version", "--format", "client {{.Client.Version}} server {{.Server.Version}}"]),
            "docker_host": capture(["docker", "info", "--format", "{{.OperatingSystem}}; {{.NCPU}} CPUs; {{.MemTotal}} bytes"]),
            "images": images,
            "resources": {"jvm_heap": "-Xmx128m (all services)", "handler_threads": 16,
                          "service_cpu": "Docker cpus: 1.0 per service" if args.backend == "compose" else "1 CPU via taskset affinity",
                          "service_memory": "Docker mem_limit: 512m per service" if args.backend == "compose" else "512 MiB NOT ENFORCED (native)",
                          "worker_slots": 1, "poll_interval_ms": 100},
            "contract": {"concurrency": CONCURRENCY, "workers": WORKERS, "warmup_jobs": WARMUP_JOBS, "measured_jobs": MEASURED_JOBS,
                         "tasks_per_job": TASKS_PER_JOB, "fixture_delay_ms": 100, "repetitions": REPETITIONS,
                         "measured_timeout_seconds": TIMEOUT_S},
            "percentiles": "nearest-rank; per-configuration p50/p95 pool the samples of complete runs; job_p95_ms_run_median is the median of per-run p95s",
            "limitations": ["Shared execution host: all services, the driver and the Docker VM share one machine",
                            "Synthetic waiting workload (100 ms sleeps); characterizes coordination, not codec or CPU scaling",
                            "Polling latency (100 ms worker poll interval) is part of measured scheduling latency",
                            "Recovery time is unmeasured in MS2; no faults are injected"]}


def main(argv=None):
    parser = argparse.ArgumentParser(description="MS2 benchmark matrix")
    parser.add_argument("--out", required=True)
    parser.add_argument("--backend", choices=["native", "compose"], default=os.environ.get("MS2_BACKEND", "compose"))
    parser.add_argument("--configs", default=None, help="comma-separated subset such as c1-w1,c16-w4 (smoke checks)")
    parser.add_argument("--repetitions", type=int, default=REPETITIONS)
    parser.add_argument("--summarize-only", action="store_true")
    args = parser.parse_args(argv)
    root = Path(args.out).resolve()
    if args.summarize_only:
        print(json.dumps(summarize(root), indent=2))
        return 0
    root.mkdir(parents=True, exist_ok=True)
    if (root / "runs.csv").exists():
        raise SystemExit("Output already contains runs.csv; use a new directory to preserve evidence")
    wanted = set(args.configs.split(",")) if args.configs else None
    metadata = environment(args)
    if wanted or args.repetitions != REPETITIONS:
        metadata["subset"] = {"configs": sorted(wanted) if wanted else "all", "repetitions": args.repetitions}
    (root / "environment.json").write_text(json.dumps(metadata, indent=2))
    statuses = []
    for c in CONCURRENCY:
        for w in WORKERS:
            if wanted and f"c{c}-w{w}" not in wanted:
                continue
            for repetition in range(1, args.repetitions + 1):
                row = run_one(root, args.backend, c, w, repetition)
                statuses.append(row["status"])
                summarize(root)
                print(json.dumps({k: row.get(k) for k in ("configuration", "status", "completed_jobs", "tasks_per_second",
                                                      "job_p50_ms", "scheduling_p50_ms", "wall_seconds", "error")}), flush=True)
    metadata["finished_utc"] = datetime.now(timezone.utc).isoformat()
    metadata["run_statuses"] = {s: statuses.count(s) for s in sorted(set(statuses))}
    (root / "environment.json").write_text(json.dumps(metadata, indent=2))
    return 0 if all(s == "complete" for s in statuses) else 1


if __name__ == "__main__":
    sys.exit(main())
