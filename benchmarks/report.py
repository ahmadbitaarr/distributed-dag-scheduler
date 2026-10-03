"""Render a benchmark output directory as Markdown tables (no new measurements).

    python -m benchmarks.report results/benchmark/<run>  > RESULTS.md

Reads runs.csv / jobs.csv / tasks.csv / environment.json written by benchmarks.run and
recomputes the per-configuration summary, so every reported number is traceable to raw samples.
Also breaks task time into scheduling (READY->ASSIGNED), start handshake (ASSIGNED->RUNNING)
and execution (RUNNING->SUCCEEDED), all on the scheduler's monotonic clock.
"""
import csv
import json
import statistics
import sys
from pathlib import Path
from benchmarks.run import CONCURRENCY, WORKERS, percentile, summarize


def fmt(value, digits=0):
    return "—" if value is None else f"{value:,.{digits}f}"


def main(argv):
    root = Path(argv[0])
    summaries = summarize(root)
    env = json.loads((root / "environment.json").read_text())
    with (root / "runs.csv").open() as f:
        runs = list(csv.DictReader(f))
    with (root / "tasks.csv").open() as f:
        tasks = list(csv.DictReader(f))
    complete = {r["configuration"] for r in runs if r["status"] == "complete"}
    out = [f"# Benchmark results: `{root.name}`", "",
           f"- Source revision: `{env.get('source_revision')}` (dirty tree: {env.get('source_dirty')})",
           f"- Backend: {env['backend']}; {env['resources']['service_cpu']}; {env['resources']['service_memory']}; "
           f"JVM {env['resources']['jvm_heap']}",
           f"- Docker: {env.get('docker')}; host VM: {env.get('docker_host')}",
           f"- Started {env['started_utc']}; finished {env.get('finished_utc', '(unfinished)')}",
           f"- Run statuses: {env.get('run_statuses', {})}",
           f"- Percentiles: {env['percentiles']}", "",
           "## Per configuration (complete runs only)", "",
           "| C | W | runs complete/total | job p50 ms | job p95 ms | median of run p95 ms | sched p50 ms | sched p95 ms | throughput mean tasks/s | stdev | min–max |",
           "|---|---|---|---|---|---|---|---|---|---|---|"]
    for s in summaries:
        out.append(f"| {s['concurrency']} | {s['workers']} | {s['complete_runs']}/{s['repetitions']} | {fmt(s['job_p50_ms'])} | "
                   f"{fmt(s['job_p95_ms'])} | {fmt(s['job_p95_ms_run_median'])} | {fmt(s['scheduling_p50_ms'], 1)} | "
                   f"{fmt(s['scheduling_p95_ms'])} | {fmt(s['throughput_mean'], 2)} | {fmt(s['throughput_stdev'], 2)} | "
                   f"{fmt(s['throughput_min'], 2)}–{fmt(s['throughput_max'], 2)} |")
    out += ["", "## Where task time goes (complete runs, medians in ms)", "",
            "| C | W | READY→ASSIGNED | ASSIGNED→RUNNING | RUNNING→SUCCEEDED |", "|---|---|---|---|---|"]
    for c in CONCURRENCY:
        for w in WORKERS:
            rows = [t for t in tasks if int(t["concurrency"]) == c and int(t["workers"]) == w and t["configuration"] in complete
                    and t["succeeded_elapsed_ns"]]
            if not rows:
                continue
            def med(a, b):
                return statistics.median((int(t[b]) - int(t[a])) / 1e6 for t in rows)
            out.append(f"| {c} | {w} | {fmt(med('ready_elapsed_ns', 'assigned_elapsed_ns'), 1)} | "
                       f"{fmt(med('assigned_elapsed_ns', 'started_elapsed_ns'), 1)} | {fmt(med('started_elapsed_ns', 'succeeded_elapsed_ns'), 1)} |")
    out += ["", "## Every run", "", "| run | status | jobs done | max in flight | tasks/s | job p50 ms | wall s | error |",
            "|---|---|---|---|---|---|---|---|"]
    for r in runs:
        tps = float(r["tasks_per_second"]) if r["tasks_per_second"] else None
        p50 = float(r["job_p50_ms"]) if r["job_p50_ms"] else None
        out.append(f"| {r['configuration']} | {r['status']} | {r['completed_jobs']} | {r['max_in_flight'] or '—'} | {fmt(tps, 2)} | "
                   f"{fmt(p50)} | {r['wall_seconds']} | {(r['error'] or '')[:80]} |")
    sys.stdout.reconfigure(encoding="utf-8")  # Windows consoles default to a legacy code page
    print("\n".join(out))


if __name__ == "__main__":
    main(sys.argv[1:])
