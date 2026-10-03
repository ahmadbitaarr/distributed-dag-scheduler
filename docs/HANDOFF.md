# Current handoff — Step 11 local verification complete

**Status: LOCAL IMPLEMENTATION/VERIFICATION COMPLETE. Course-cluster execution was attempted and blocked by an external course-runner Hokea package mismatch. Do not start Step 12.**
Accepted `main @ bf0a7974dd63cc8cd1d9240177156d0a00bd26df`; Steps 0–10 accepted.

The canonical repository remains based on accepted
`main @ bf0a7974dd63cc8cd1d9240177156d0a00bd26df`. Step 11 changes are currently
uncommitted. The user performed the registry publishing and authorized
course-cluster verification attempt.

The prior coordination files contained stale Step 10 blocked text. They are now
updated to the user's explicit accepted baseline and the completed external
Step 10 evidence. Historical handoffs/results were preserved. Do not redo those
steps.

New orchestration code: `tests/harness/hokea_adapter.py`; pinned Hokea package hashes,
API verifier and flat runner generator under `deploy/hokea/`; 21 focused tests plus
one service-exchange smoke check. No production Java, Native/Compose implementation,
existing correctness test, architecture or roadmap changed. Runtime's Hokea dispatch
was already present and is reused unchanged.

Observed: 21 focused PASS; full native **84 PASS + 1 RecoveryNotObserved XFAIL**,
exit 0; same native `--runxfail` **1 final RecoveryNotObserved failure**, exit 1,
with setup/probe/safety/export/cleanup all successful. Offline **42 directories /
34 histories valid**; all cleanup true. New native HTTP-exchange smoke passes.
First smoke's incorrect terminal-owner assertion was corrected; the original failed
run and original source attribution are retained separately. Source manifests and
accepted 63-file manifest pass. Production JARs were reused only after comparing
all Java/module source and POM bytes to the accepted ZIP; hashes/provenance recorded.

**External local Step 11 verification is complete.** Using the unchanged source
from a WSL-native filesystem, the Compose regression completed with 2 passed and
1 expected typed XFAIL. `make test` completed with 84 passed and 1 expected XFAIL.
`make fault-demo` failed only with the intentional `RecoveryNotObserved` oracle.
The earlier OneDrive `/mnt/c` Compose failure was an environment-path/cwd issue
and is not acceptance evidence.

**Course-cluster execution was attempted.** Authorized access to `team-06` worked,
and public immutable GHCR images were provided for all three services. Hokea
created the runner Job, shipped the package, started pytest, and copied evidence
back. All three tests then errored during fixture setup before any project service
execution because the Hokea package installed in the course runner did not match
the pinned revision `427b94634b1736ba8e59d4977836162aa58bd2cb`
(`Hokea source mismatch at check.py`). Per the frozen Step 11 contract, this is
an external course-runner environment mismatch; the project pin is not relaxed
and the result is not classified as the intentional `RecoveryNotObserved` XFAIL.
Evidence is preserved at
`results/handoffs/step-11/acceptance-hokea-20261003T200759-f99f027a`.

No local verification remains. If course staff provides the correctly pinned
runner/environment, rerun the documented course sequence in
`deploy/hokea/CLUSTER-HANDOFF.md` using the already-published immutable images.
Until then, preserve the course-runner mismatch as the remaining external
environment blocker.

Read `docs/handoffs/step-11.md` and `results/handoffs/step-11/RESULTS.md` for source
attribution, commands/exits and limitations. Architecture deviations: none.
RUNNING ownership reclamation remains intentionally absent; add no recovery,
leases, heartbeats, expiry/requeue, worker HTTP server or shared worker filesystem.

Recommended eventual commit message:
`deploy(hokea): adapt MS2 services and fault harness to course runtime`.
After Planning accepts Step 11, the user can perform the normal personal
commit/push flow and return the full SHA, branch, clean/dirty status and push
confirmation. No Step 12 handoff yet.
