# Step 11 Hokea orchestration

Current state: **LOCAL HOKEA/DOCKER VERIFICATION COMPLETE; COURSE EXECUTION ATTEMPTED AND BLOCKED BY AN EXTERNAL RUNNER PACKAGE MISMATCH.**

Steps 0–13 are accepted at `main @ bf43c619d00ee1658c5cb1eb297a5e1f59a2de8d`.
Step 14 closes documentation; Step 15 follows review. Local Step 11 observations
are in `results/handoffs/step-11/FINAL-RESULTS.md`; the latest independent suite
result is `results/handoffs/step-13/VERIFICATION.md`. Read [API.md](API.md) for
the unchanged API/pin and [CLUSTER-HANDOFF.md](CLUSTER-HANDOFF.md) for an optional
user-controlled rerun once staff supplies the correctly pinned course runner.

## Adapter contract

`tests/harness/runtime.py` already dispatches `MS2_BACKEND=hokea` lazily; neither it
nor the existing `tests/conftest.py` needed modification. `hokea_adapter.py` owns
only process control, addresses, readiness, logs and teardown. Existing `Api`,
HTTP contracts, functional workload, history checker and strict crash oracle
are reused. Production Java, Dockerfiles and Compose behavior are unchanged.

| Setting | Meaning |
|---|---|
| `MS2_BACKEND=hokea` | Select this adapter. |
| `MS2_HOKEA_RUNTIME=docker` or `kubernetes` | Docker default; explicit Kubernetes for the course runner. |
| `HOKEA_NAMESPACE` | Required explicit server namespace for Kubernetes. |
| `MS2_HOKEA_SCHEDULER_IMAGE` | Existing scheduler image, default `dag-ms2/scheduler:0.2.0`. |
| `MS2_HOKEA_ARTIFACT_STORE_IMAGE` | Existing store image, default `dag-ms2/artifact-store:0.2.0`. |
| `MS2_HOKEA_WORKER_IMAGE` | Existing worker image, default `dag-ms2/worker:0.2.0`. |
| `MS2_HOKEA_EXPOSE` | Kubernetes scheduler/store only; `internal` default, optional `nodeport` for a reachable external harness. Worker always internal. |
| `MS2_SOURCE_REV` | Exact current tested source identifier. A clean accepted checkout uses its actual `git rev-parse HEAD`; the Step 11 source manifest identifies only those historical runs. |
| `MS2_EVIDENCE_DIR` | Export root; default fixture behavior retained. Runner wrapper sets writable `/project/runs`. |
| `MS2_RUN_LABEL` | Optional fresh unique label; omit for automatic timestamp+UUID. Never reuse an explicit label. |
| `MS2_REQUIRE_XFAIL=1` | Require exactly one expected XFAIL for a selection containing the crash oracle. |

`HOKEA_TAKEOVER` must be unset. Each service cluster has one node, 1 CPU and
512 MiB. Docker uses a one-line `FROM <existing-image>` wrapper build through
Hokea's public Dockerfile mode, without source bind mounts or fault-tool installs.
The generated wrapper tag is removed after teardown; base images/build caches
are retained. Kubernetes uses existing images directly with private `emptyDir`.
Store runs first because scheduler startup needs its HTTP address. The existing
store image runs as root; scheduler/workers remain nonroot. Worker attempts use
private temporary directories and exchange all inputs/outputs over HTTP.

A and B have separate named clusters and worker sessions. A alone receives the
X gate and 120,000 ms operation timeout. B uses normal defaults. A is never
restarted. No scheduler ownership/recovery logic is implemented in this adapter.

## Reproducing completed local verification

The local gates below were completed in Step 11; they are rerun instructions, not
unexecuted acceptance work. Use fresh evidence labels/directories and the actual
current source. Step 13 separately verifies the normal Make suite. Use Python 3.12,
pytest 8.3.4 and an installed clean course Hokea checkout at the pinned SHA
(including its declared requests/PyYAML dependencies). Installing from a local
course checkout is sufficient; no registry upload or account authentication is
performed by the project. Check the package before any orchestration:

```bash
cd /path/to/distributed-dag-scheduler
python3 deploy/hokea/verify_api.py
docker compose version
docker info
python3 -m pytest -q tests/unit/test_hokea_adapter.py tests/unit/test_hokea_packaging.py
docker compose -f deploy/compose/compose.yaml build
export MS2_SOURCE_REV="$(git rev-parse HEAD)"  # clean accepted checkout only
export MS2_BACKEND=hokea MS2_HOKEA_RUNTIME=docker
export MS2_EVIDENCE_DIR=results/handoffs/step-11/external-local-hokea
# Each invocation automatically gets a fresh timestamp+UUID label.
unset MS2_RUN_LABEL MS2_REQUIRE_XFAIL HOKEA_TAKEOVER
python3 -m pytest -q tests/integration/test_hokea_smoke.py
python3 -m pytest -q tests/integration/test_functional_workload.py
MS2_REQUIRE_XFAIL=1 python3 -m pytest -q tests/faults/test_worker_crash.py
```

Require smoke 1 PASS, functional 1 PASS (three jobs, all intermediate bytes and
final `result=22\n`), fault exactly 1 typed `RecoveryNotObserved` XFAIL, exits 0,
zero ordinary failures/errors/XPASS, project and Hokea cleanup flags true. The
functional oracle checks all dependency edges and histories. For explicit
concurrency regression additionally run the unchanged
`tests/integration/test_system.py::test_join_and_independent_branch_concurrency`
through Hokea; this checks actual branch interval overlap and join ordering.

Validate every exported directory, without editing its runtime evidence:

```bash
python3 - <<'PY'
from pathlib import Path
from tests.harness.check_evidence import check_directory
root = Path('results/handoffs/step-11/external-local-hokea')
for path in sorted(root.rglob('manifests.json')):
    print(path.parent, check_directory(path.parent))
PY
```

Retain stdout/stderr, exact command/overrides/exit, source ID, images, fault,
snapshots, probe, safety checks, all JSONL events, Hokea metadata/fault timeline/raw
capture and cleanup. Exclude `runtime/` when promoting evidence. Hokea typed event
exports may be empty because our event field is `event_type`; complete project
logs plus original ambient `.raw` files are retained instead.

For a new reproduction, the following unchanged regressions can be run on the same host:

```bash
unset MS2_BACKEND MS2_HOKEA_RUNTIME MS2_EVIDENCE_DIR MS2_REQUIRE_XFAIL MS2_RUN_LABEL
MS2_BACKEND=compose MS2_REQUIRE_XFAIL=1 python3 -m pytest -q \
  tests/integration/test_hokea_smoke.py \
  tests/integration/test_functional_workload.py \
  tests/faults/test_worker_crash.py
make test
make fault-demo
```

Compose selection should give 2 PASS + 1 typed XFAIL. `make test` must pass all
ordinary tests and exactly one typed XFAIL. `make fault-demo` must actually fail
only on final `RecoveryNotObserved`; any build/setup/safety/export/cleanup failure
does not satisfy that gate. Record the actual Make exit. Retain and check exported
histories. Historical Step 10 results do not substitute for these Step 11 runs.

## Evidence and cleanup

Per-test project export is unchanged: `events.jsonl`, manifests, snapshots,
metrics, worker logs and `evidence-boundary.json`. Fault export additionally
contains gate/before/after snapshots, `fault.json`, observation window, B probe,
late polling, health, safety checks, oracle result and traceback.
`hokea/metadata.json` adds the pin, runtime, namespace, requested role image refs,
actual observed container/Pod identities/image IDs, launch env and death evidence.
`hokea/<role>/faults.jsonl` and `events/` contain original supplemental Hokea data.
Cleanup runs in reverse worker→scheduler→store order, attempts every resource,
and propagates errors as ordinary errors. Export failure also runs cleanup.

No blanket prune or namespace deletion is used. After an interrupted run, inspect
metadata for exact run-owned names and clean only those. Cluster instructions are
in [CLUSTER-HANDOFF.md](CLUSTER-HANDOFF.md). Local emergency commands are
`docker compose -p <recorded-hokea-prefix> -f <retained-runtime-compose.yaml> down
--volumes --remove-orphans` per worker, scheduler, then store, followed by
`docker image rm <same-prefix>-img`. Do not remove base images or unrelated runs.
