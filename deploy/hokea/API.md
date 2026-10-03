# Hokea API grounding for Step 11

Required revision: `427b94634b1736ba8e59d4977836162aa58bd2cb`.
The existing public checkout was inspected read-only: `git rev-parse HEAD` returned
this full SHA and `git status --porcelain` was empty. No fetch, pull, account
authentication or upgrade was performed. `HOKEA_API_SHA256.json` records the exact
Python package hashes; `verify_api.py` and the adapter reject a package mismatch.
A source-hash check proves the inspected package bytes, not a running image's
build provenance. Actual image/container IDs are recorded when a run occurs.

| Pinned primary source | Behavior used |
|---|---|
| [cluster.py](https://github.com/spin-vt/hokea/blob/427b94634b1736ba8e59d4977836162aa58bd2cb/src/hokea/cluster.py) `Cluster.__init__`, `up`, `_build_image`, `_compose_config`, `Node.logs`, `kill`, `down` | Independently named Compose projects; one image per cluster; Dockerfile mode preserves an existing image's ENTRYPOINT; `up()` does not call `wait_healthy()`; full logs with `tail=-1`; kill uses `docker kill`; down removes own containers/networks/volumes. |
| [kube.py](https://github.com/spin-vt/hokea/blob/427b94634b1736ba8e59d4977836162aa58bd2cb/src/hokea/kube.py) `KubeCluster.__init__`, `_build_manifests`, `_pod_manifest`, `_peers_service_manifest`, `up`, `kill`, `_kubectl`, `down` | Independent prefixes in an explicit namespace; image-only mode; bare Pods with `restartPolicy: Never` and private `emptyDir` at `/data`; headless per-pod DNS; `up()` waits for Pod Ready, without an HTTP readiness probe; force pod deletion; label-scoped teardown. |
| [pytest_plugin.py](https://github.com/spin-vt/hokea/blob/427b94634b1736ba8e59d4977836162aa58bd2cb/src/hokea/pytest_plugin.py) `cluster` | This optional fixture calls `wait_healthy()` at `/health`; the project bypasses that fixture and uses its own `system` fixture. |
| [events.py](https://github.com/spin-vt/hokea/blob/427b94634b1736ba8e59d4977836162aa58bd2cb/src/hokea/events.py) collectors | Ambient capture retains raw stdout; typed Hokea event parsing expects `type`. Project events use `event_type`, so original Node logs and project history checking remain authoritative. No production event-schema change or fabricated translation is needed. |
| [runs.py](https://github.com/spin-vt/hokea/blob/427b94634b1736ba8e59d4977836162aa58bd2cb/src/hokea/runs.py) `FaultLog` | Original requested/done orchestration records are retained separately as supplemental fault timelines. |
| [runner.py](https://github.com/spin-vt/hokea/blob/427b94634b1736ba8e59d4977836162aa58bd2cb/src/hokea/runner.py) `package_files`, `job_manifest`, `cmd_test` | Only flat top-level regular files ship; archives and directories do not; text-byte budget 900,000; runner in `<team>-clients`, server namespace supplied via `--namespace`; fixed preloaded runner image `hokea-runner:2026.08.29.3`; copy-out only of `/project/runs/`. |
| [runner_entry.py](https://github.com/spin-vt/hokea/blob/427b94634b1736ba8e59d4977836162aa58bd2cb/src/hokea/runner_entry.py) `copy_project`, `run_pytest`, `main` | Copies ConfigMap files to writable `/project`, executes pytest, exposes exit/copy-out markers, and holds for copy-out. |

## The two API questions

Heterogeneous composition is supported by independent named clusters. The adapter
creates one store cluster, one scheduler cluster, and one cluster per worker,
with the existing three role images. Docker scheduler/workers join the store's
client network through the narrow pinned `_compose_config` hook. Kubernetes uses
fully qualified headless-service DNS in one explicitly named server namespace.
No application role is collapsed into a common image or process.

Readiness is separate from `up()`. The project waits for scheduler/store
`/v1/health` and for an existing live worker instance plus `worker_session_started`.
The probe and late claim/empty receipts prove B can perform work and keep polling.
Workers expose no HTTP server, published Docker port, or Kubernetes container port.
The worker headless service has no ports; its Pod still has private ephemeral
storage. The pinned Kubernetes manifest hooks preserve `restartPolicy: Never`.

## Kill semantics and limitations

Docker requires the original container ID, running=false, exit 137, zero restarts,
and original SIGKILL mechanism. Kubernetes requires successful force deletion,
strict API observation of the absent old Pod UID, and detection of a different UID
even if a recreated Pod is only Pending. Command/API errors propagate as errors;
they cannot become a false death observation. A's complete logs are sealed before
deletion because a deleted Pod's log address disappears.

The pinned Kubernetes `kill()` also checks HTTP unreachability; a worker already
has no HTTP API, so this is not its death proof. The adapter additionally checks
the API object. Force deletion cannot prove that a process on a partitioned node
has stopped; this limitation is explicit. This experiment assumes a healthy
course node and control plane and injects only worker-Pod deletion. No partition
test or stronger kubelet death guarantee is claimed.

The implementation uses private manifest/configuration hooks at this exact
revision, protected by source hashes. These hooks, multi-network DNS, empty
headless-service ports, container images, and actual teardown still require real
Docker/Kubernetes execution. Fake-unit success is not deployment success.
