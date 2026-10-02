# Step 05 — Scheduler API, snapshots, events and metrics

Status: DONE on branch ms2/step-05-api (gate passed; not yet on main — push blocked, see S1-04).
Base commit: 05a7928 (Step 4). Writer: Hasanlm23123.

## Review

`SchedulerMain` wires each endpoint in architecture §6 to a core command. Submission flows as follows:

1. Structural validation.
2. A replay check under the mutex.
3. Source HEAD checks outside the mutex.
4. `submit`, which re-validates under the mutex.

Success reports use `prepareReport`, then output HEAD checks outside the mutex, then `report`. Events drain to stdout outside the mutex every 50 ms and again on shutdown. No API code change was needed.

## New: Linux harness container

`deploy/harness/Dockerfile` and `deploy/harness/run.sh` provide the on-demand harness/client container from architecture §15: Ubuntu 24.04, JDK 21.0.7, Maven 3.9.9, Python 3.12.3, pytest 8.3.4, ffmpeg 6.1.1. They run the existing pytest suite with the repository mounted.

This closes S1-03 (Python 3.12 unverified) and removes the need for a Linux host. It also gave the checkpoint pytest suite its first ever full run: **21 passed, 1 xfailed** (the intentional oracle).

## Tests added: `tests/integration/test_api.py` (8)

- **Health:** the response and the `X-Scheduler-Run-Id` header carry the current run ID.
- **Structured errors** (14 cases): unknown job 404, bad UUID 400, wrong methods 405, unknown path 404, bad event cursors and limits 400, malformed JSON 400, empty claim/start/report bodies 400.
- **Body limit:** a body over 1 MiB gets 413 `MANIFEST_TOO_LARGE`.
- **Stale run:** submission, claim and start from another run get 409 `STALE_RUN`, and no state changes.
- **Source checks:** an unpublished source, or one with the wrong hash, length or media type, gets 400 and creates no job. A correct source gets 201.
- **Storage down:** with the artifact service stopped, a submission with a source gets 503 `ARTIFACT_UNAVAILABLE`. No job, no `job_submitted` event, `accepted_jobs` stays 0.
- **Counters and history:** a scenario with an explicit failure, a duplicate receipt, a retry, a rejected report and a success gives exact counter values, exact gauges and `snapshot_event_seq` equal to the event count. The scenario emits every §14 decision event type. Walking events with page size 1 gives the same gap-free history, and every event has the §14 base fields.
- **Rejected commands** (wrong owner, early success, success from ASSIGNED) leave the job snapshot unchanged.

Harness hook added: `stop_artifacts()` on the native and Compose harnesses, used only by the storage-down test.

Architecture deviations: none.
