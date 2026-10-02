# MS2 wire contract, version 1

This file documents the HTTP/JSON contract the code implements. It follows architecture §§3 and 6, and the Java records in `protocol/src/main/java/edu/vt/dag/Model.java` define it. Step 2 verified the request schemas, identities and validation rules in this file (`ManifestValidatorTest`, `WireContractTest`). The scheduler and artifact HTTP behavior is listed here for reference; Steps 4–5 verify it end to end.

## General rules

- JSON over HTTP/1.1. Field names are `snake_case`. `schema_version` is `1`.
- Parsing is strict, using Jackson as configured in `Json.java`:
  - Unknown fields and duplicate keys are rejected.
  - Trailing tokens after the JSON value are rejected.
  - A string is never coerced to a number ("3" is not 3), and a float is never accepted as an integer.
  - Every violation is `400 INVALID_INPUT`.
- A JSON request body is limited to 1 MiB (`413 MANIFEST_TOO_LARGE`). This applies to every scheduler endpoint.
- Every error body has the shape `{"error":{"code":"<MACHINE_CODE>","message":"<text>"}}`. A rejected command changes no scheduler state.
- UUIDs use the canonical lowercase 36-character form. Identifiers (task IDs, input/output names, final output names) match `[A-Za-z0-9][A-Za-z0-9_.-]{0,63}` and must not contain `..`.

## Identities

| Identity | Form | Origin |
|---|---|---|
| `job_id` | UUID | Client-generated. A retry keeps the same ID. |
| `task_id` | identifier, unique within the job | Manifest. Logical identity is `(job_id, task_id)` and never changes on retry. |
| `attempt_no` | integer ≥ 1 | Scheduler. It increases by one for each new assignment of the logical task. |
| `worker_session_id` | UUID | Worker. A new one is generated each time the process starts. |
| `scheduler_run_id` | UUID | Scheduler. A new one is generated at startup. Messages from another run get `409 STALE_RUN`. |
| `claim_id` | UUID | Worker. One per claim cycle, reused on transport retries. |

**Ownership tuple** (`Identity`, carried by every start and report):

```json
{"scheduler_run_id":"<uuid>","job_id":"<uuid>","task_id":"B","attempt_no":2,"worker_session_id":"<uuid>"}
```

All five fields are required. A missing or zero `attempt_no` is `400` (`ManifestValidator.identity`). A tuple that doesn't match the current attempt's owner is `409`.

## Artifact references and namespaces

```json
{"key":"inputs/<uuid>/sample.mp4","length":123456,"sha256":"<64 lowercase hex>","media_type":"video/mp4"}
```

| Namespace | Key form |
|---|---|
| Source upload | `inputs/<asset_uuid>/<name>` |
| Attempt output | `runs/<run_id>/jobs/<job_id>/tasks/<task_id>/attempts/<n>/<output_name>`, where `n` is ≥ 1 with no leading zero |

Keys are at most 512 characters long and have exactly these segment counts; traversal is not allowed. `length` ranges from 0 to 32 MiB; anything larger is `413 ARTIFACT_TOO_LARGE`. Media type follows the form `type/subtype`. A manifest source binding must use the `inputs/` namespace.

## Job manifest

```json
{
  "schema_version": 1,
  "job_id": "6f1c2b9e-3d4a-4e5f-8a7b-0c1d2e3f4a5b",
  "tasks": [
    {"task_id":"A","operation":"fixture_write","parameters":{"value":3,"delay_ms":100},"parents":[],"inputs":{},"outputs":["value"]},
    {"task_id":"B","operation":"fixture_add","parameters":{"amount":4},"parents":["A"],"inputs":{"value":{"task_id":"A","output_name":"value"}},"outputs":["value"]},
    {"task_id":"C","operation":"fixture_multiply","parameters":{"amount":5},"parents":["A"],"inputs":{"value":{"task_id":"A","output_name":"value"}},"outputs":["value"]},
    {"task_id":"D","operation":"fixture_sum","parameters":{},"parents":["B","C"],"inputs":{"left":{"task_id":"B","output_name":"value"},"right":{"task_id":"C","output_name":"value"}},"outputs":["value"]},
    {"task_id":"E","operation":"fixture_format","parameters":{},"parents":["D"],"inputs":{"value":{"task_id":"D","output_name":"value"}},"outputs":["text"]}
  ],
  "final_outputs": {"result": {"task_id":"E","output_name":"text"}}
}
```

An input binding takes exactly one of two forms:

- `{"source": <artifact reference>}`: an uploaded source object.
- `{"task_id": <parent>, "output_name": <declared output of that parent>}`: a parent's accepted output.

A parent listed in `parents` but not bound in `inputs` is an ordering-only dependency.

### Operation allowlist

| Operation | Required input names | Output | Parameters |
|---|---|---|---|
| `fixture_write` | none | `value` | `value` (integer, required), `delay_ms` |
| `fixture_add`, `fixture_multiply` | `value` | `value` | `amount` (integer, required), `delay_ms` |
| `fixture_sum` | any non-empty set | `value` | `delay_ms` |
| `fixture_format` | `value` | `text` | `delay_ms` |
| `fixture_subtitles` | `srt` | `subtitles` | `delay_ms` |
| `video_inspect` | `video` | `metadata` | none |
| `video_transcode` | `video` | `video` | `height` ∈ {360, 720} (required) |
| `video_thumbnail` | `video` | `image` | none |
| `video_publish` | `video720`, `video360`, `image`, `subtitles` | `manifest` | none |

`delay_ms` ranges from 0 to 30000 and is allowed only on `fixture_*` operations. A parameter an operation doesn't use is rejected. Arbitrary commands are never accepted.

### Validation and limits

The following are rejected with `400`:

- An empty or missing task list, or a duplicate task ID.
- An unknown parent, a self-edge, a repeated parent, or a cycle (checked by topological pass).
- An invalid identifier.
- A binding to an undeclared parent or an undeclared output, an incomplete binding (missing `task_id` or `output_name`), or a binding that sets both a source and a parent.
- A source outside `inputs/`.
- An unsupported operation, or input/output names or parameters that don't match the allowlist.
- Missing or invalid `final_outputs`.
- A `schema_version` other than `1`.

The following are rejected with `413`: more than 128 tasks or more than 512 dependency edges (`DAG_TOO_LARGE`), a JSON body over 1 MiB, or an artifact over 32 MiB.

The scheduler also checks that each source object exists (via HEAD to the artifact store) before acceptance. That check is outside the scheduler mutex. Missing or mismatched objects are `400`, and an unreachable store is `503 ARTIFACT_UNAVAILABLE`, in which case the job is not accepted.

### Replay equality

The scheduler compares a resubmitted manifest with the stored one by **normalized typed** equality, not by raw JSON:

- The order of tasks, parents, outputs, input maps and final outputs is ignored, because they are sets or maps.
- Whitespace and key order are ignored.
- Parameter values and types are significant, as are operations, binding names and targets.

A replay with an equal manifest returns `200`. The same `job_id` with a different manifest returns `409 CONFLICT`.

## Scheduler endpoints

| Endpoint | Request body | Success | Errors |
|---|---|---|---|
| `GET /v1/health` | none | 200 `{"ready":true,"scheduler_run_id":…}` | none |
| `POST /v1/jobs` | `{"scheduler_run_id","manifest"}` | 201 on first acceptance, 200 on identical replay: `{"scheduler_run_id","job_id","state","scheduler_event_seq"}` | 400, 409 (different manifest or stale run), 413, 503 |
| `GET /v1/jobs/{job_id}` | none | 200 atomic snapshot: `state`, `tasks{…attempts, owner, outputs}`, `counts`, `outputs`, `snapshot_event_seq` | 400 (bad UUID), 404 `JOB_NOT_FOUND` |
| `POST /v1/work/claim` | `{"scheduler_run_id","worker_session_id","claim_id"}` | 200 `Assignment`, or 204 when there is no work. A replayed claim returns its cached result. | 400, 409 |
| `POST /v1/attempts/start` | `Identity` | 200 `Ack` (new or replay) | 400, 409 |
| `POST /v1/attempts/report` | `{"identity","outcome":"SUCCESS"\|"FAILURE","outputs":{name:artifact},"error":{"code","message"}\|null}` | 200 `Ack` (new or exact replay) | 400, 409 (stale, conflicting or wrong state) |
| `GET /v1/events?after=&limit=` | none | 200 `{"scheduler_run_id","events":[…],"next_after","has_more"}`; `limit` ranges from 1 to 1000 | 400 |
| `GET /v1/metrics` | none | 200 with counters, `tasks_by_state`, `ready_queue_length`, `active_attempts`, and p50/p95 timing summaries | none |

`Assignment` has the fields `scheduler_run_id`, `identity`, `task` (task definition), `inputs` (resolved artifact references), `output_prefix` (the attempt namespace), `scheduler_event_seq`, and `disposition`.

`disposition` is `EXECUTE` for a claim the worker should run. A replayed claim whose attempt has already finished gets `TERMINAL_SUCCEEDED` or `TERMINAL_FAILED`, and the worker must not execute it again.

`Ack` has the fields `scheduler_run_id`, `scheduler_event_seq` and `disposition` (`ACCEPTED`).

Report rules:

- A **success** report needs `outputs` keyed exactly by the task's declared outputs, each under the attempt's `output_prefix`, and `error` must be null.
- A **failure** report needs empty `outputs` and an `error` whose `code` is an identifier and whose `message` is at most 2048 characters.

## Artifact store endpoints

| Endpoint | Request | Success | Errors |
|---|---|---|---|
| `GET /v1/health` | none | 200 `{"ready":true}` | none |
| `PUT /v1/objects/{key}` | Raw bytes, with the headers `Content-Length`, `X-Content-SHA256` and `Content-Type` | 201 for a new object, 200 for an identical replay; the body is the artifact reference | 400 (key, length or hash), 409 (key already holds different bytes), 413 |
| `HEAD /v1/objects/{key}` | none | 200 with the headers `Content-Length`, `X-Content-SHA256` and `Content-Type` | 404 `OBJECT_NOT_FOUND` until the object is published |
| `GET /v1/objects/{key}` | none | 200 with the completed bytes | 404 |

## Error codes

| HTTP | Code | Meaning |
|---|---|---|
| 400 | `INVALID_INPUT` | Malformed JSON, schema or type violation, failed validation, or a missing identity field |
| 404 | `NOT_FOUND`, `JOB_NOT_FOUND`, `OBJECT_NOT_FOUND` | Unknown endpoint, job (in this run) or published object |
| 405 | `METHOD_NOT_ALLOWED` | Wrong HTTP method |
| 409 | `CONFLICT` | Replay with different content, owner/attempt/state mismatch, or stale attempt |
| 409 | `STALE_RUN` | `scheduler_run_id` is not the current run |
| 413 | `MANIFEST_TOO_LARGE`, `DAG_TOO_LARGE`, `ARTIFACT_TOO_LARGE` | Over a limit |
| 503 | `ARTIFACT_UNAVAILABLE`, `OVERLOADED`, `SERVICE_UNAVAILABLE` | Transient. Retry with the same IDs. |

## Example rejection

Submitting the manifest above with task B's binding changed to `{"task_id":"A"}` (no `output_name`):

```http
HTTP/1.1 400
{"error":{"code":"INVALID_INPUT","message":"Input binding needs a source or a parent output"}}
```

Before Step 2, this input caused a `NullPointerException`, and the server reported it as `503 SERVICE_UNAVAILABLE`.
