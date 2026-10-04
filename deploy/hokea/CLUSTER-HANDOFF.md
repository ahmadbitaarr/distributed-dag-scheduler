# User-controlled course rerun — external runner mismatch

The user attempted course execution during Step 11 in `team-06`, using public
immutable GHCR images. Hokea launched the runner, transferred the package, started
pytest and copied evidence out. All three tests errored during fixture setup,
before project services started, because the runner package mismatched pinned
Hokea `427b94634b1736ba8e59d4977836162aa58bd2cb` (`Hokea source mismatch at check.py`).
This was an external environment limitation, not the intentional XFAIL. Local
Hokea/Docker verification is complete; Steps 0–13 are accepted.

See `results/handoffs/step-11/FINAL-RESULTS.md` and the preserved
`acceptance-hokea-20261003T200759-f99f027a/CLUSTER-RESULT.md` for the observed attempt.
The sequence below is a **future user-controlled rerun**, conditional on a correctly
pinned staff-provided runner and authorized access. No course/GitHub authenticated
action was performed in Step 14. Do not relax the package pin.

## Required prerequisites

- Your authorized course kubeconfig/access and actual server namespace, here
  represented by `team-NN`. Paired client namespace is `team-NN-clients` unless
  staff supplies another (`--client-namespace` supports the override).
- A locally installed clean Hokea source package at
  `427b94634b1736ba8e59d4977836162aa58bd2cb`, with its declared dependencies and
  pytest. `python3 deploy/hokea/verify_api.py` must pass.
- The course's preloaded `hokea-runner:2026.08.29.3`, including the **same pinned
  Hokea package**. The adapter verifies package bytes inside the runner before
  creating server resources. A runner mismatch is an ordinary error; ask staff
  to supply the correct image rather than change the pin silently.
- Existing server/client namespaces and course runner ServiceAccount/RBAC as
  required by pinned `runner.py`. The runner needs server Pod/service creation,
  read/log, force deletion and own-label cleanup. Hokea also observes Chaos Mesh
  resources; use staff-provided permissions/configuration. Its internal-mode
  preflight expects server namespace fault injection enabled and client observer
  namespace protected. Do not grant permissions or change namespaces in this task.
- Course capacity: up to five simultaneous 1-CPU, 512-MiB service Pods for the
  functional test (store + scheduler + three workers), plus the runner. Tests
  run sequentially and clean up after each. The fault run uses A then fresh B.
- **Three independently pullable immutable service image references**, e.g.
  `registry.example/team-NN/scheduler@sha256:<64-hex>`, corresponding to these
  unchanged Dockerfiles and implementation. Laptop-only `dag-ms2/...:0.2.0`
  tags are not assumed available on course nodes. Staff-preloaded immutable
  content is an alternative; `--allow-preloaded-tags` is an explicit acknowledgment
  when staff requires tags. Record actual image IDs, not only requested tags.
- A healthy course node/control plane for the force-deletion experiment. API
  deletion is not a physical death guarantee for a partitioned node.

## Exact package and execution sequence

Run these yourself from a clean, approved copy of the complete project. Substitute
only your authorized namespace, paths, and real immutable images. This generator
does not access any account, registry or cluster and does not rebuild the tests.

```bash
cd /path/to/distributed-dag-scheduler
python3 deploy/hokea/verify_api.py
export TEAM_NAMESPACE=team-NN
export SCHEDULER_IMAGE='registry.example/team-NN/scheduler@sha256:<64-hex>'
export ARTIFACT_IMAGE='registry.example/team-NN/artifact-store@sha256:<64-hex>'
export WORKER_IMAGE='registry.example/team-NN/worker@sha256:<64-hex>'
export STEP11_SOURCE="$(git rev-parse HEAD)"  # exact clean accepted source for this rerun
export STEP11_PACKAGE="$(mktemp -d)/runner"
python3 deploy/hokea/package_runner.py \
  --out "$STEP11_PACKAGE" --source-revision "$STEP11_SOURCE" \
  --scheduler-image "$SCHEDULER_IMAGE" \
  --artifact-store-image "$ARTIFACT_IMAGE" --worker-image "$WORKER_IMAGE"
cd "$STEP11_PACKAGE"
python3 -m pytest --collect-only -q
unset HOKEA_TAKEOVER MS2_RUN_LABEL
hokea test --namespace "$TEAM_NAMESPACE" -q
```

The collection check imports exactly three tests, without starting anything.
Only for collection, the wrapper does not require an executed XFAIL. For real
execution it sets `MS2_BACKEND=hokea`, Kubernetes/internal addressing, exactly
one required XFAIL, source ID and image references from the generated payload.
The runner Job itself gets `HOKEA_NAMESPACE` from the Hokea CLI. User kubeconfig
stays on the user machine; the runner uses its existing course ServiceAccount.
No credentials, kubeconfig or registry configuration enter the package.

The flat package contains only `conftest.py`, `test_entry.py`, `pytest.ini` and
`payload.json`, below the pinned 900,000-byte ConfigMap budget. The payload
contains exact nested source bytes and checksums. On the runner, the bootstrap
checks and unpacks them under writable `/project/_project`, then imports the
existing project fixture and original test functions. The Step 10 oracle has
one definition and remains unchanged.

## Expected results and evidence

Real run success: exit 0, **2 passed + 1 strict typed `RecoveryNotObserved`
XFAIL**, zero ordinary failures/errors/XPASS, successful setup/export/cleanup.
Smoke: real scheduler/store health, input PUT/HEAD/GET, worker GET input, execute,
PUT output, report and output bytes `11`. Functional: three original committed
`A -> {B,C} -> D -> E` jobs and final bytes `result=22\n`, all intermediates,
dependencies and histories valid. Fault: A gate after acknowledged start, old
Pod hard-deleted, original X attempt still RUNNING under A, Y BLOCKED, distinct B,
successful probe, late healthy polling, valid safety histories, final recovery
demand raises exactly the existing expected exception.

Hokea copies `/project/runs/<fresh-label>/` back to `$STEP11_PACKAGE/runs/`.
Each test has its own subdirectory. Expect three exported directories and six
job histories in total. Save full launcher stdout/stderr and actual exit, the
generator report/payload, image provenance, source ID and namespace. Do not
interpret running Pods alone as success. Check every `metadata.json` and
`hokea/metadata.json` cleanup flag, probe/safety JSON and original fault traceback.
Before evidence promotion, remove `runtime/` copies while retaining supplemental
Hokea metadata/faults/raw capture and all project exports. Do not edit outcomes
or source attribution in runtime evidence.

Back at the full project, validate copied-out history directories:

```bash
cd /path/to/distributed-dag-scheduler
python3 - "$STEP11_PACKAGE/runs" <<'PY'
import sys
from pathlib import Path
from tests.harness.check_evidence import check_directory
for manifest in sorted(Path(sys.argv[1]).rglob('manifests.json')):
    directory = manifest.parent
    print(directory, check_directory(directory))
PY
```

For branch concurrency inspect functional scheduler sequences for each job:
both B/C starts before the other branch succeeds; D starts after both successes,
E after D. If no overlapping branch interval is observed, the local unchanged
concurrency regression named in README must be run and its results retained
before claiming that concurrency is verified through Hokea. Do not invent an
additional Hokea-only semantic oracle or change scheduling to obtain overlap.

## Cleanup and interruption

Normal cleanup is adapter-owned, reverse order, per unique run prefix. Hokea CLI
then cleans its runner Job/ConfigMap after copying evidence. A cleanup error is
an ordinary failure even if pytest reports the intentional XFAIL.

If interrupted, first inspect the preserved per-test
`hokea/metadata.json.records[].node`: it contains `hokea-<name>-node1`.
The exact service cluster name is that string with `hokea-` and `-node1` removed.
For each recorded worker, then scheduler, then store, use:

```bash
hokea k8s down --namespace "$TEAM_NAMESPACE" --name '<exact-recorded-name>'
```

Run from a directory with no unrelated `.hokea/k8s-<name>.json` state file (pinned
CLI state-file namespace can override the argument). This sweeps only the named
Hokea cluster labels. Never delete the namespace or all team Pods. If the launcher
was interrupted before copy-out, follow its printed `kubectl cp` instruction to
retrieve `/project/runs/` from the runner before cleaning that runner. Preserve
its original diagnostics; do not mark an incomplete copy or ambiguous death PASS.

Return exact commands/exits/counts, logs, source/actual image IDs, namespace,
cleanup states and copied evidence to the planning/review chat. The earlier course attempt remains **externally blocked**, and course service
behavior remains **unverified**, until a correctly pinned rerun actually produces
these observations. A successful local run does not substitute for course results.
