"""Re-check saved test evidence offline, without a running system.

    python -m tests.harness.check_evidence results/latest-tests/<test>   [more dirs...]

Each directory must contain the files the harness exports before teardown:
events.jsonl, snapshots.json and manifests.json. Optional files are worker-*.jsonl
(worker stdout events, raw lines kept) and evidence-boundary.json. Every job is
checked with check_history. The exit status is non-zero if any invariant is falsified.
"""
import json
import sys
from pathlib import Path
from tests.harness.api import HistoryViolation, check_history


def load_worker_events(directory):
    events = []
    for path in sorted(directory.glob("worker-*.jsonl")):
        for line in path.read_text().splitlines():
            try:
                value = json.loads(line)
            except json.JSONDecodeError:
                continue  # raw diagnostics interleaved with JSON events are kept but not parsed
            if isinstance(value, dict) and "event_type" in value:
                events.append(value)
    return events


def check_directory(directory):
    directory = Path(directory)
    events = [json.loads(line) for line in (directory / "events.jsonl").read_text().splitlines() if line.strip()]
    snapshots = json.loads((directory / "snapshots.json").read_text())
    manifests = json.loads((directory / "manifests.json").read_text())
    boundary_path = directory / "evidence-boundary.json"
    if boundary_path.exists():
        boundary = json.loads(boundary_path.read_text())
        if boundary["last_exported_event_seq"] != len(events):
            raise HistoryViolation("events.jsonl is truncated relative to evidence-boundary.json")
        if any(e["scheduler_run_id"] != boundary["scheduler_run_id"] for e in events):
            raise HistoryViolation("events from another scheduler run")
    worker_events = load_worker_events(directory)
    checked = []
    for job_id, manifest in manifests.items():
        if job_id not in snapshots:
            raise HistoryViolation(f"no snapshot exported for job {job_id}")
        check_history(manifest, snapshots[job_id], events, worker_events)
        checked.append(job_id)
    return checked


def main(argv):
    failed = False
    for directory in argv:
        try:
            jobs = check_directory(directory)
            print(f"OK    {directory}: {len(jobs)} job histories satisfy the safety invariants")
        except (HistoryViolation, FileNotFoundError, KeyError, json.JSONDecodeError) as error:
            failed = True
            print(f"FAIL  {directory}: {type(error).__name__}: {error}")
    return 1 if failed or not argv else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
