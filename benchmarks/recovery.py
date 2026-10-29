"""MS3 recovery experiment: job completion, throughput and recovery time with worker crashes.

    python -m benchmarks.recovery --backend compose --out results/benchmark/recovery-<name>
    python -m benchmarks.recovery --backend compose --out ... --concurrency 4 --repetitions 1   # smoke check

Same workload and closed loop as benchmarks/run.py (six-task jobs, 100 ms fixture waits, 4 warmup
jobs then 24 measured jobs, at most C in flight), with W = 4 one-slot workers and C in {1, 4, 16}.
Each configuration runs in two modes on fresh deployments:

  baseline  no faults (the same code with leases and heartbeats, for a like-for-like comparison)
  crash     after 6 and after 14 measured completions, SIGKILL a worker that is executing a task,
            then start a replacement worker (a restarted machine: new process, new session)

Recovery time is measured on the scheduler's monotonic clock from the killed attempt's last sign
of life (its last accepted lease renewal) to the task's assignment to a new owner, and split into
detection (last sign of life -> lease_expired) and requeue (lease_expired -> new assignment).
The kill itself happens on another process's clock and is never subtracted from scheduler times.
Every run's histories are checked for the safety invariants; failed runs are recorded, not dropped.
"""
import argparse
import json
import os
import platform
import statistics
import sys
import threading
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from tests.harness.api import benchmark_manifest, check_history, request
from tests.harness.runtime import harness
from benchmarks.run import EventCursor, append_csv, capture, percentile, max_in_flight

CONCURRENCY, WORKERS, REPETITIONS = [1, 4, 16], 4, 3
WARMUP_JOBS, MEASURED_JOBS, TASKS_PER_JOB, TIMEOUT_S = 4, 24, 6, 180
KILL_AFTER_COMPLETIONS = [6, 14]
EXPECTED_RESULT = b"result=9\n"

RUN_FIELDS = ["configuration", "mode", "concurrency", "workers", "repetition", "scheduler_run_id", "status", "error",
              "completed_jobs", "incomplete_jobs", "logical_successes", "max_in_flight", "correct_outputs",
              "kills", "kills_holding_task", "expired_attempts", "lease_ms", "tasks_per_second",
              "job_p50_ms", "job_p95_ms", "affected_job_p50_ms", "unaffected_job_p50_ms",
              "recovery_p50_ms", "recovery_max_ms", "wall_seconds"]


class Owners:
    """Who holds which attempt right now, from the scheduler event stream."""
    def __init__(self):
        self.held = {}                       # session -> (job, task, attempt, started)

    def update(self, events):
        for e in events:
            kind, session = e["event_type"], e.get("worker_session_id")
            if kind == "task_assigned":
                self.held[session] = (e["job_id"], e["task_id"], e["attempt_no"], False)
            elif kind == "task_started" and session in self.held:
                self.held[session] = self.held[session][:3] + (True,)
            elif kind in ("task_succeeded", "task_failed", "lease_expired") and session in self.held \
                    and self.held[session][:3] == (e["job_id"], e["task_id"], e["attempt_no"]):
                del self.held[session]


def run_one(root, backend, c, mode, repetition):
    tag = f"{mode}-c{c}-w{WORKERS}-r{repetition}"
    common = {"configuration": tag, "mode": mode, "concurrency": c, "workers": WORKERS, "repetition": repetition}
    row = {**common, "status": "error", "error": None, "completed_jobs": 0, "incomplete_jobs": MEASURED_JOBS, "kills": 0}
    started = time.monotonic()
    recoveries, jobs_rows, kills = [], [], []
    try:
        with harness(root / tag, backend) as system:
            row["scheduler_run_id"] = common["scheduler_run_id"] = system.api.run_id
            sessions = {}
            for _ in range(WORKERS):
                name = system.start_worker()
                sessions[system.worker_session(name)] = name
            cursor, owners = EventCursor(system.api), Owners()
            pending_kills = list(KILL_AFTER_COMPLETIONS) if mode == "crash" else []
            threads, armed, killed_sessions = [], {}, set()

            kill_lock = threading.Lock()

            def crash_and_replace(victim, session, holding):
                # Serialized: the harness names a new worker from its worker count, so two overlapping
                # replacements would collide. The kill is recorded before the replacement is attempted.
                with kill_lock:
                    record = {"worker": victim, "session": session, "holding": holding,
                              "kill_requested_utc": datetime.now(timezone.utc).isoformat()}
                    record.update(system.kill_worker(victim))
                    kills.append(record)
                    try:
                        replacement = system.start_worker()
                        sessions[system.worker_session(replacement)] = replacement
                        record["replacement"] = replacement
                    except Exception as error:      # recorded, and the run is marked censored below
                        record["replacement_error"] = f"{type(error).__name__}: {error}"

            def loop(count, measured):
                active, finished, manifests, submitted = set(), [], {}, 0
                deadline = time.monotonic() + TIMEOUT_S
                while submitted < count or active:
                    while submitted < count and len(active) < c:
                        m = benchmark_manifest()
                        system.api.submit(m)
                        active.add(m["job_id"])
                        manifests[m["job_id"]] = m
                        submitted += 1
                    new = cursor.poll()
                    owners.update(new)
                    for e in new:
                        if e["event_type"] == "job_completed" and e["job_id"] in active:
                            active.discard(e["job_id"])
                            finished.append(e["job_id"])
                    if measured and pending_kills and len(finished) >= pending_kills[0]:
                        # Kill a worker that is executing a task (the case recovery is about). Right after a
                        # completion every worker may be idle, so wait for one to start; never block the loop.
                        armed.setdefault(pending_kills[0], time.monotonic())
                        live = [s for s in list(sessions) if s not in killed_sessions]
                        running = [s for s in live if owners.held.get(s, (0, 0, 0, False))[3]]
                        if running or time.monotonic() - armed[pending_kills[0]] > 10:
                            victim = (running or live)[0]
                            pending_kills.pop(0)
                            killed_sessions.add(victim)
                            thread = threading.Thread(target=crash_and_replace, args=(sessions[victim], victim, owners.held.get(victim)))
                            thread.start()
                            threads.append(thread)
                    if time.monotonic() > deadline:
                        return finished, sorted(active), manifests, count - submitted
                    if active:
                        time.sleep(0.02)
                return finished, [], manifests, 0

            warm, unfinished, _, unsubmitted = loop(WARMUP_JOBS, False)
            if len(warm) != WARMUP_JOBS or unfinished or unsubmitted:
                raise RuntimeError(f"warmup incomplete: {len(warm)}/{WARMUP_JOBS}")
            completed, unfinished, manifests, unsubmitted = loop(MEASURED_JOBS, True)
            for thread in threads:
                thread.join(timeout=60)
            snapshots = [system.api.status(job) for job in completed + unfinished]
            cursor.poll()
            events = cursor.events
            status, metrics = request(system.scheduler, "/v1/metrics")
            lease_ms = metrics["lease_ns"] / 1e6
            correct, affected, unaffected = 0, [], []
            for snapshot in snapshots:
                check_history(manifests[snapshot["job_id"]], snapshot, events)
                expired = any(a["state"] == "EXPIRED" for t in snapshot["tasks"].values() for a in t["attempts"])
                if snapshot["state"] == "SUCCEEDED":
                    correct += system.api.get(snapshot["outputs"]["result"]) == EXPECTED_RESULT
                    (affected if expired else unaffected).append(snapshot["duration_ns"] / 1e6)
                jobs_rows.append({**common, "job_id": snapshot["job_id"], "state": snapshot["state"], "affected_by_fault": expired,
                                  "completion_ms": snapshot["duration_ns"] / 1e6 if snapshot["duration_ns"] is not None else None})
            measured = set(manifests)
            assigned = {(e["job_id"], e["task_id"], e["attempt_no"]): e for e in events if e["event_type"] == "task_assigned"}
            for e in events:
                if e["event_type"] == "lease_expired" and e["job_id"] in measured:
                    nxt = assigned.get((e["job_id"], e["task_id"], e["attempt_no"] + 1))
                    recoveries.append({**common, "job_id": e["job_id"], "task_id": e["task_id"], "expired_attempt": e["attempt_no"],
                                       "expired_from": e["old_state"], "lease_ms": lease_ms,
                                       "detection_ms": (e["elapsed_ns"] - e["last_alive_elapsed_ns"]) / 1e6,
                                       "requeue_to_assign_ms": (nxt["assigned_elapsed_ns"] - e["elapsed_ns"]) / 1e6 if nxt else None,
                                       "recovery_ms": (nxt["assigned_elapsed_ns"] - e["last_alive_elapsed_ns"]) / 1e6 if nxt else None})
            keys = [(e["job_id"], e["task_id"]) for e in events if e["event_type"] == "task_succeeded" and e["job_id"] in measured]
            if len(keys) != len(set(keys)):
                raise RuntimeError("duplicate logical completion")
            peak = max_in_flight(events, measured)
            done = [s for s in snapshots if s["state"] == "SUCCEEDED"]
            incomplete = len(unfinished) + unsubmitted
            complete = (len(done) == MEASURED_JOBS and not incomplete and len(keys) == MEASURED_JOBS * TASKS_PER_JOB
                        and correct == MEASURED_JOBS and peak <= c and len(kills) == len(KILL_AFTER_COMPLETIONS if mode == "crash" else [])
                        and not any("replacement_error" in k for k in kills))
            batch_ns = (max(s["completed_elapsed_ns"] for s in done) - min(s["accepted_elapsed_ns"] for s in snapshots)) if done else None
            durations = [s["duration_ns"] / 1e6 for s in done]
            rec = [r["recovery_ms"] for r in recoveries if r["recovery_ms"] is not None]
            row.update({"status": "complete" if complete else "censored", "completed_jobs": len(done), "incomplete_jobs": incomplete,
                        "logical_successes": len(keys), "max_in_flight": peak, "correct_outputs": correct,
                        "kills": len(kills), "kills_holding_task": sum(k["holding"] is not None for k in kills),
                        "expired_attempts": len(recoveries), "lease_ms": lease_ms,
                        "tasks_per_second": len(keys) / (batch_ns / 1e9) if complete else None,
                        "job_p50_ms": percentile(durations, .5), "job_p95_ms": percentile(durations, .95),
                        "affected_job_p50_ms": percentile(affected, .5), "unaffected_job_p50_ms": percentile(unaffected, .5),
                        "recovery_p50_ms": percentile(rec, .5), "recovery_max_ms": max(rec) if rec else None})
            (root / tag / "kills.json").write_text(json.dumps(kills, indent=2, default=str))
    except Exception as error:   # record the failed run and keep going
        row["error"] = f"{type(error).__name__}: {error}"
        (root / tag).mkdir(parents=True, exist_ok=True)
        (root / tag / "benchmark-error.txt").write_text(traceback.format_exc())
    row["wall_seconds"] = round(time.monotonic() - started, 1)
    append_csv(root / "recovery_jobs.csv", jobs_rows)
    append_csv(root / "recoveries.csv", recoveries)
    append_csv(root / "runs.csv", [row], RUN_FIELDS)
    return row


def summarize(root):
    import csv
    def load(name):
        path = root / name
        return list(csv.DictReader(path.open())) if path.exists() else []
    runs, jobs, recs = load("runs.csv"), load("recovery_jobs.csv"), load("recoveries.csv")
    complete = {r["configuration"] for r in runs if r["status"] == "complete"}
    out = []
    for c in CONCURRENCY:
        for mode in ("baseline", "crash"):
            selected = [r for r in runs if int(r["concurrency"]) == c and r["mode"] == mode]
            if not selected:
                continue
            ok = lambda r: int(r["concurrency"]) == c and r["mode"] == mode and r["configuration"] in complete
            times = [float(r["completion_ms"]) for r in jobs if ok(r) and r["completion_ms"]]
            hit = [float(r["completion_ms"]) for r in jobs if ok(r) and r["completion_ms"] and r["affected_by_fault"] == "True"]
            rec = [float(r["recovery_ms"]) for r in recs if ok(r) and r["recovery_ms"]]
            det = [float(r["detection_ms"]) for r in recs if ok(r)]
            req = [float(r["requeue_to_assign_ms"]) for r in recs if ok(r) and r["requeue_to_assign_ms"]]
            tput = [float(r["tasks_per_second"]) for r in selected if r["status"] == "complete"]
            out.append({"concurrency": c, "workers": WORKERS, "mode": mode, "repetitions": len(selected),
                        "complete_runs": sum(r["status"] == "complete" for r in selected),
                        "jobs_pooled": len(times), "job_p50_ms": percentile(times, .5), "job_p95_ms": percentile(times, .95),
                        "affected_jobs": len(hit), "affected_job_p50_ms": percentile(hit, .5), "affected_job_max_ms": max(hit) if hit else None,
                        "recoveries": len(rec), "recovery_p50_ms": percentile(rec, .5), "recovery_p95_ms": percentile(rec, .95),
                        "recovery_max_ms": max(rec) if rec else None, "detection_p50_ms": percentile(det, .5),
                        "requeue_p50_ms": percentile(req, .5), "requeue_max_ms": max(req) if req else None,
                        "throughput_mean": statistics.mean(tput) if tput else None,
                        "throughput_stdev": statistics.stdev(tput) if len(tput) > 1 else None})
    (root / "summary.json").write_text(json.dumps(out, indent=2))
    (root / "summary.csv").unlink(missing_ok=True)
    append_csv(root / "summary.csv", out)
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description="MS3 recovery experiment")
    parser.add_argument("--out", required=True)
    parser.add_argument("--backend", choices=["native", "compose"], default=os.environ.get("MS2_BACKEND", "compose"))
    parser.add_argument("--concurrency", default=None, help="comma-separated subset of 1,4,16")
    parser.add_argument("--modes", default="baseline,crash")
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
    levels = [int(x) for x in args.concurrency.split(",")] if args.concurrency else CONCURRENCY
    modes = args.modes.split(",")
    metadata = {"started_utc": datetime.now(timezone.utc).isoformat(), "command": sys.argv,
                "source_revision": os.environ.get("MS2_SOURCE_REV") or capture(["git", "rev-parse", "HEAD"]),
                "source_dirty": bool(capture(["git", "status", "--porcelain"])), "python": sys.version,
                "platform": platform.platform(), "host_cpu_count": os.cpu_count(), "backend": args.backend,
                "docker": capture(["docker", "version", "--format", "client {{.Client.Version}} server {{.Server.Version}}"]),
                "docker_host": capture(["docker", "info", "--format", "{{.OperatingSystem}}; {{.NCPU}} CPUs; {{.MemTotal}} bytes"]),
                "contract": {"concurrency": levels, "workers": WORKERS, "modes": modes, "repetitions": args.repetitions,
                             "warmup_jobs": WARMUP_JOBS, "measured_jobs": MEASURED_JOBS, "tasks_per_job": TASKS_PER_JOB,
                             "fixture_delay_ms": 100, "kill_after_measured_completions": KILL_AFTER_COMPLETIONS,
                             "fault": "SIGKILL of a worker executing a task (else any live worker), then a replacement worker",
                             "lease_timeout_ms": "scheduler default (5000) unless LEASE_TIMEOUT_MS is set",
                             "measured_timeout_seconds": TIMEOUT_S},
                "percentiles": "nearest-rank, pooled over complete runs"}
    (root / "environment.json").write_text(json.dumps(metadata, indent=2))
    statuses = []
    for c in levels:
        for repetition in range(1, args.repetitions + 1):
            for mode in modes:
                row = run_one(root, args.backend, c, mode, repetition)
                statuses.append(row["status"])
                summarize(root)
                print(json.dumps({k: row.get(k) for k in ("configuration", "status", "completed_jobs", "kills", "kills_holding_task",
                                                      "expired_attempts", "tasks_per_second", "job_p50_ms", "recovery_p50_ms",
                                                      "recovery_max_ms", "wall_seconds", "error")}), flush=True)
    metadata["finished_utc"] = datetime.now(timezone.utc).isoformat()
    metadata["run_statuses"] = {s: statuses.count(s) for s in sorted(set(statuses))}
    (root / "environment.json").write_text(json.dumps(metadata, indent=2))
    return 0 if all(s == "complete" for s in statuses) else 1


if __name__ == "__main__":
    sys.exit(main())
