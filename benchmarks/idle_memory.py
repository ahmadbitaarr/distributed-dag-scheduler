"""Scheduler heap growth while workers poll an idle system (native backend, run in the harness container).

    sh deploy/harness/run.sh sh -c 'mvn -B -q package -DskipTests && python3 -m benchmarks.idle_memory --workers 4 --seconds 120'

Every sample forces a full GC in the scheduler JVM (jcmd GC.run) and reads the live heap
(jcmd GC.heap_info), together with the scheduler's event count. The growth rate per idle
worker-hour bounds how long a deployment can idle before its in-memory history fills the heap.
"""
import argparse
import json
import re
import subprocess
import tempfile
import time
from tests.harness.api import benchmark_manifest, request
from tests.harness.runtime import NativeHarness


def live_heap_kib(pid):
    subprocess.run(["jcmd", str(pid), "GC.run"], capture_output=True, text=True, timeout=30)
    out = subprocess.run(["jcmd", str(pid), "GC.heap_info"], capture_output=True, text=True, timeout=30).stdout
    # Live heap = every generation's or region heap's "total ..., used NK" line (Serial: def new + tenured;
    # G1: garbage-first heap). Metaspace and class space are not heap and are excluded.
    lines = [l for l in out.splitlines() if re.search(r"(generation|garbage-first heap|heap)\s+total", l) and "Metaspace" not in l]
    used = [int(m.group(1)) for l in lines if (m := re.search(r"used (\d+)K", l))]
    return (sum(used) if used else None), [l.strip() for l in lines]


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--seconds", type=int, default=120)
    parser.add_argument("--every", type=int, default=20)
    parser.add_argument("--jobs", type=int, default=0, help="then run this many six-task jobs and measure heap per task")
    args = parser.parse_args(argv)
    with tempfile.TemporaryDirectory() as tmp, NativeHarness(tmp) as system:
        pid = system.processes["scheduler"].pid
        for _ in range(args.workers):
            system.start_worker()
        start = time.monotonic()
        samples = []
        while True:
            elapsed = time.monotonic() - start
            heap, raw = live_heap_kib(pid)
            _, metrics = request(system.scheduler, "/v1/metrics")
            sample = {"elapsed_s": round(elapsed, 1), "live_heap_kib": heap, "scheduler_events": metrics["scheduler_event_seq"], "heap_info": raw}
            samples.append(sample)
            print(json.dumps(sample), flush=True)
            if elapsed >= args.seconds:
                break
            time.sleep(args.every)
        first, last = samples[0], samples[-1]
        hours = (last["elapsed_s"] - first["elapsed_s"]) / 3600
        rate_mib_h = (last["live_heap_kib"] - first["live_heap_kib"]) / 1024 / hours
        events_h = (last["scheduler_events"] - first["scheduler_events"]) / hours
        new_events = last["scheduler_events"] - first["scheduler_events"]
        print(json.dumps({"workers": args.workers, "idle_live_heap_growth_mib_per_hour": round(rate_mib_h, 1),
                          "idle_events_per_hour": round(events_h),
                          "bytes_per_event": round((last["live_heap_kib"] - first["live_heap_kib"]) * 1024 / new_events) if new_events else None}))
        if args.jobs:
            jobs = []
            for _ in range(args.jobs):
                m = benchmark_manifest()
                system.api.submit(m)
                jobs.append(m["job_id"])
            for job in jobs:
                system.api.complete(job, timeout=600)
            heap, raw = live_heap_kib(pid)
            _, metrics = request(system.scheduler, "/v1/metrics")
            tasks = 6 * args.jobs
            per_task = (heap - last["live_heap_kib"]) * 1024 / tasks
            print(json.dumps({"jobs": args.jobs, "tasks": tasks, "live_heap_kib": heap, "heap_info": raw,
                              "events": metrics["scheduler_event_seq"], "events_per_task": round(metrics["scheduler_event_seq"] / tasks, 2),
                              "live_heap_bytes_per_completed_task": round(per_task),
                              "tasks_until_128_mib_heap_full": round((128 * 1024 * 1024 - heap * 1024) / per_task)}))


if __name__ == "__main__":
    main()
