# Step 11 handoff — Hokea adapter and cluster handoff

**Status: LOCAL IMPLEMENTATION/VERIFICATION COMPLETE — course-cluster execution
attempted and blocked by an external course-runner Hokea package mismatch.**
**Do not begin Step 12 until Planning formally accepts Step 11.**

## Baseline and authority

Accepted branch/baseline:
`main @ bf0a7974dd63cc8cd1d9240177156d0a00bd26df`. Steps 0–10 are accepted.
Step 11 changes are currently uncommitted in the canonical repository. Registry
publishing and the authorized course-cluster verification attempt were performed
by the user.

All 63 accepted implementation files still match the accepted Step 10 source
manifest. Canonical architecture and roadmap retain their prior hashes
(`docs/PROGRESS.md`). Historical Step 0–10 handoffs/evidence remain unchanged.

Final Step 11 implementation identifier:
`step11-sha256:a9aab6b8f97e9734799689d82502ec2cb0da57886b49d8e87326f11aafd73fee`.
It is the SHA-256 of the exact 70-file implementation manifest at
`results/handoffs/step-11/source-SHA256SUMS.txt`, not an accepted commit SHA.
Coordination/deployment prose and later external results are outside this
implementation manifest.

The earlier smoke run retains original source identifier
`step11-sha256:c457006d4edbf66b6eaca9f19380565e632b2d5dbbfd7630d45c0ba2e926e334`,
manifest and its only differing source file under `source-revisions/`.

## API decisions and implementation map

Pinned Hokea SHA: `427b94634b1736ba8e59d4977836162aa58bd2cb`.
Read `deploy/hokea/API.md` for primary pinned links and exact classes/functions.
Clean checkout HEAD and package hashes were verified. No silent upgrade.

| File / boundary | Implemented behavior |
|---|---|
| `tests/harness/runtime.py::harness` | Existing lazy hokea dispatch reused unchanged; Native/Compose unchanged. |
| `tests/conftest.py::system` | Existing evidence/export/outcome/cleanup fixture reused unchanged. |
| `tests/harness/hokea_adapter.py::verify_package`, `Factory` | Validate exact pinned package bytes; independent one-node role clusters; service image-only Kubernetes and inherited-image Dockerfile wrapper; strict Docker inspect/Kubernetes API observations. |
| `docker_config`, `worker_pod`, pinned inner manifest hooks | Shared HTTP network for Docker role instances; no worker port/source mount; bare Kubernetes Pod with Never restart/private emptyDir; worker headless service without ports. |
| `HokeaHarness.__enter__`, `_launch`, `_internal_url` | Store then scheduler; independent unique identities; existing image/env/ports 8081/8080; stable Docker-name/Kube-DNS URLs; real `/v1/health` waits. |
| `start_worker`, `worker_events`, `worker_running` | Separate env/session/identity per worker, process plus session-event readiness; no production HTTP server; strict original instance identity and live container state. |
| `kill_worker` | Target A alone; pre-delete complete log cache; Hokea hard kill; Docker SIGKILL/137/original ID/zero restart, Kubernetes strict old UID absence; normalized semantic evidence; detect recreated UID even if Pending. |
| `close`, `__exit__`, `Factory.release` | Existing Api.export plus original Node logs, supplemental fault records/ambient raw capture; reverse teardown attempts every cluster; own wrapper tags removed after down; errors propagate as ordinary failures. |
| `deploy/hokea/package_runner.py` | Four-file ConfigMap package below 900,000-byte budget; byte-preserving/checksummed nested payload; imports original fixture and tests in writable runner project; prevents package-output overwrite; digest requirement or explicit staff-preloaded acknowledgment. |
| `deploy/hokea/verify_api.py`, `HOKEA_API_SHA256.json` | Read-only CLI/package pin verification; no external account operation. |
| `tests/unit/test_hokea_adapter.py`, `test_hokea_packaging.py` | 21 fake/contract/collection tests: parameters, addressing, A gate isolation, B defaults, identity, kill, cached logs, cleanup, failure propagation, source pin, flat budget and exact oracle imports. |
| `tests/integration/test_hokea_smoke.py::test_service_exchange` | Real services, HTTP input PUT/HEAD/GET, worker GET/execute/PUT/report, output bytes 11, retained attempt session, history and evidence; backend-neutral. |

Heterogeneity is resolved with independently named clusters, preserving the three
existing role images. Readiness avoids the optional Hokea `/health` fixture:
workers need no inbound server. All storage is private ephemeral node storage;
worker outputs remain exclusively HTTP artifacts. Hokea retains orchestration
authority only; application state/attempt/retry semantics remain in the scheduler.

The Step 10 fault test is byte-identical. Only the adapter normalizes death
evidence. No alternate oracle, broadened XFAIL, recovery mechanism or lease was
added. Hokea collectors expect `type`, while project logs use `event_type`;
unmodified project stdout/history plus original Hokea raw capture are retained.

## Observed results

| Command / gate | Actual result |
|---|---|
| `python deploy/hokea/verify_api.py --package <clean pinned source package>` | exit 0, exact pin verified. |
| Focused adapter/packaging pytest | **21 passed**, exit 0 (final run 0.28 s). |
| Generator + flat package collection | exit 0, **85,703 bytes / 900,000**, exactly three original test imports. |
| New native smoke, corrected source | **1 passed**, exit 0 (5.52 s); real input/output bytes 7→11 over HTTP. |
| Full native pytest with `MS2_REQUIRE_XFAIL=1` | **84 passed + 1 typed RecoveryNotObserved XFAIL**, exit 0, 216.71 s; no XPASS or setup/teardown errors. |
| Native same fault oracle `--runxfail` | **1 failed only on final RecoveryNotObserved**, exit 1, 17.00 s; setup/probe/safety/export/cleanup succeeded. |
| Retained offline checker | **42 directories / 34 job histories valid**, exit 0, all cleanup true. Acceptance alone: 39 directories / 30 histories. |
| Current and accepted source checksum checks | 70/70 and 63/63 implementation-manifest files matched at the recorded implementation checkpoint. |
| External WSL-native Compose regression | **2 passed + 1 expected typed XFAIL**, exit 0; unchanged Step 11 source. |
| External WSL-native `make test` | **84 passed + 1 expected XFAIL**, exit 0. |
| External WSL-native `make fault-demo` | Failed only on the intentional final `RecoveryNotObserved` oracle, as expected. |
| Actual course cluster | **ATTEMPTED — external course-runner environment mismatch.** `team-06` access and public immutable service images succeeded; Hokea launched the runner, shipped the package, started pytest, and copied evidence back. All 3 tests errored during fixture setup before project service execution because the runner's installed Hokea package mismatched pinned revision `427b94634b1736ba8e59d4977836162aa58bd2cb` at `check.py`. |

The first native smoke reached successful worker/output exchange but had an
incorrect new assertion expecting a terminal task to retain `owner`. Terminal
ownership is correctly cleared by existing scheduler semantics. Only the new
smoke assertion changed to inspect the retained attempt identity. Failed run,
raw traceback and original source attribution were preserved; retry and full
suite then passed. An earlier development-only package collection check exposed
XFAIL-count enforcement during collection; the wrapper now omits that requirement
only for `--collect-only`, preserving strict actual-execution enforcement.

No JUnit rerun is claimed for the original implementation checkpoint. Prior
packaged Java binaries were reused only after all module Java/test source and
module/root POM bytes matched the accepted ZIP. `NATIVE-BINARIES.json` records
exact binary hashes and original provenance. The binaries/toolchains are excluded
from the returned project.

The external local WSL-native verification is the current local acceptance
evidence. The earlier OneDrive `/mnt/c` Compose attempt failed because of an
environment-path/stale-cwd issue and is not acceptance evidence.

## Evidence

`results/handoffs/step-11/` contains the implementation-time Step 11 records,
including `RESULTS.md`, `COMMANDS.json`, `SOURCE.json`, source manifests,
focused/full/fault JUnit XML, pin/source checks, environment metadata, package
records, historical corrected-source attribution and exported runs.

Actual local Hokea/Compose evidence and the attempted course-cluster evidence now
also exist. Successful WSL-native local verification is retained as acceptance
evidence. The course-cluster attempt is preserved at
`results/handoffs/step-11/acceptance-hokea-20261003T200759-f99f027a`; it records
the external runner Hokea package mismatch and is not passing acceptance evidence.

Do not reinterpret the cluster attempt as the intentional MS2 fault. All three
cluster tests stopped during fixture setup before project service execution, so
the expected `RecoveryNotObserved` oracle was never reached.

## Remaining Step 11 work

Local Step 11 implementation and verification are complete. The successful
WSL-native verification is the current local acceptance evidence; do not rerun
the completed local gates solely because the earlier OneDrive `/mnt/c` execution
encountered an environment-path/cwd failure.

Course-cluster execution was attempted using authorized `team-06` access and
public immutable scheduler, artifact-store, and worker images. The Hokea runner
launched successfully, but all three tests stopped during fixture setup before
project service execution because the Hokea package installed in the course
runner did not match pinned revision
`427b94634b1736ba8e59d4977836162aa58bd2cb`.

Per the frozen Step 11 contract, do not relax the Hokea pin, add compatibility
logic, or classify this as the intentional `RecoveryNotObserved` XFAIL. A future
course-cluster retry requires a course runner/environment containing the pinned
Hokea package or explicit course-provided material superseding that pin.

Step 11 is ready for final Planning review after this documentation/evidence
close-out. Do not start Step 12 until Step 11 is formally accepted.

Recommended eventual commit:
`deploy(hokea): adapt MS2 services and fault harness to course runtime`.

Architecture deviations: **none**. Intentional silent RUNNING-owner liveness
violation remains. Do not add leases, heartbeats/expiry/scanning/reclamation,
automatic requeue or A restart, scheduler replication/failover/durable recovery,
shared worker storage, or a production worker coordination HTTP server.
