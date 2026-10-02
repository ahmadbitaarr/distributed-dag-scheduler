"""Run the functional and video demonstrations against a running deployment (`make up`).

    python3 -m tests.harness.demo [--scheduler URL] [--artifacts URL] [--out DIR]

Uploads the committed workloads, submits both DAGs, waits for success, and writes every
output plus snapshots and a summary to results/demo/<UTC timestamp>/. Standard library only.
Exits non-zero if either job does not succeed in time or an output check fails.
"""
import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from tests.harness.api import Api, check_history, uid, video_manifest
from tests.harness.runtime import ROOT


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--scheduler", default="http://127.0.0.1:8080")
    parser.add_argument("--artifacts", default="http://127.0.0.1:8081")
    parser.add_argument("--out", default=None)
    parser.add_argument("--timeout", type=float, default=180)
    args = parser.parse_args(argv)
    out = Path(args.out or ROOT / "results/demo" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    out.mkdir(parents=True, exist_ok=True)
    api = Api(args.scheduler, args.artifacts)
    print(f"scheduler run {api.run_id}; writing outputs to {out}")

    functional = json.loads((ROOT / "workloads/functional/functional.json").read_text())
    functional["job_id"] = uid()
    video_dir = ROOT / "workloads/video"
    sums = dict(reversed(line.split()) for line in (video_dir / "SHA256SUMS").read_text().splitlines())
    for name, digest in sums.items():
        if hashlib.sha256((video_dir / name).read_bytes()).hexdigest() != digest:
            raise SystemExit(f"{name} does not match workloads/video/SHA256SUMS")
    video = api.put((video_dir / "sample.mp4").read_bytes(), f"inputs/{uid()}/sample.mp4", "video/mp4")
    subtitles = api.put((video_dir / "fixture.srt").read_bytes(), f"inputs/{uid()}/fixture.srt", "application/x-subrip")
    video_job = video_manifest(video, subtitles)
    (out / "manifest-functional.json").write_text(json.dumps(functional, indent=2))
    (out / "manifest.json").write_text(json.dumps(video_job, indent=2))

    for m in (functional, video_job):
        api.submit(m)
        print(f"submitted {m['job_id']} ({len(m['tasks'])} tasks)")
    snapshots = {m["job_id"]: api.complete(m["job_id"], args.timeout) for m in (functional, video_job)}
    events = api.events()
    for m in (functional, video_job):
        check_history(m, snapshots[m["job_id"]], events)

    result = api.get(snapshots[functional["job_id"]]["outputs"]["result"])
    (out / "functional-result.txt").write_bytes(result)
    if result != b"result=22\n":
        raise SystemExit(f"functional result was {result!r}")

    video_snapshot = snapshots[video_job["job_id"]]
    publication = json.loads(api.get(video_snapshot["outputs"]["result"]))
    (out / "publication.json").write_text(json.dumps(publication, indent=2))
    files = {"video720": "video720.mp4", "video360": "video360.mp4", "image": "thumbnail.png", "subtitles": "subtitles.srt"}
    for name, filename in files.items():
        (out / filename).write_bytes(api.get(publication["artifacts"][name]))
    if (out / "subtitles.srt").read_bytes() != (video_dir / "fixture.srt").read_bytes():
        raise SystemExit("published subtitles differ from the fixture")

    (out / "snapshots.json").write_text(json.dumps(snapshots, indent=2))
    (out / "events.jsonl").write_text("".join(json.dumps(e) + "\n" for e in events))
    summary = {"scheduler_run_id": api.run_id, "functional": {"job_id": functional["job_id"], "result": result.decode()},
               "video": {"job_id": video_job["job_id"], "duration_ms": video_snapshot["duration_ns"] / 1e6,
                         "outputs": {n: publication["artifacts"][n]["key"] for n in files}},
               "history_checks": "passed"}
    (out / "summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
