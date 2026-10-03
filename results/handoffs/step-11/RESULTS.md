> **CURRENT STATUS:** This file is the original intermediate Step 11 result record and is retained for provenance. The authoritative final verification close-out is `FINAL-RESULTS.md`.

# Step 11 recorded local results

**BLOCKED — real Hokea/Docker and current Compose/Make gates unavailable.**
Course cluster **NOT VERIFIED**. No GitHub/registry/course authenticated action,
commit/push, production Java change, architecture change or Step 12 work.

Accepted source provenance: `main @ bf0a7974dd63cc8cd1d9240177156d0a00bd26df`
(user supplied; authoritative ZIP has no Git metadata). All 63 accepted source
manifest files still match. Final implementation source identifier:
`step11-sha256:a9aab6b8f97e9734799689d82502ec2cb0da57886b49d8e87326f11aafd73fee`.
`SOURCE.json` / `source-SHA256SUMS.txt` define its 70 exact implementation files.
Hokea exact clean public checkout and package pin:
`427b94634b1736ba8e59d4977836162aa58bd2cb`.

| Actual verification | Result | Raw output |
|---|---|---|
| Exact Hokea package check | exit 0 | pin-check.log |
| Hokea checkout HEAD / clean status | exact SHA, clean, exits 0 | hokea-head.log / hokea-clean.log |
| Final adapter + packaging tests | 21 PASS, exit 0, 0.28 s | adapter-unit-final.log / .xml |
| Final generator and collection | 85,703 bytes, three exact original test imports, exits 0 | runner-package.log / runner-collection.log |
| Corrected native real HTTP smoke | 1 PASS, exit 0, 5.52 s | native-smoke-retry.log |
| Full native acceptance | 84 PASS + 1 expected typed XFAIL, exit 0, 216.71 s | native-acceptance.log / .xml |
| Native real fault failure | 1 FAIL solely RecoveryNotObserved, exit 1, 17.00 s | native-fault-demo.log / .xml |
| Retained offline evidence | 42 directories / 34 histories valid, all cleanup true, exit 0 | retained-offline.log / EVIDENCE-CHECK.json |
| Current/accepted source checks | 70/70 and 63/63 match, exits 0 | source-check.log / accepted-source-check.log |
| Docker capability | CLI absent, each exit 127; socket absent | docker-compose-version.log / docker-info.log / ENVIRONMENT.json |
| Actual Make targets | each exit 2 before tests, Docker missing; gates UNSATISFIED | make-test.log / make-fault-demo.log |

Every recorded command, argument, cwd, explicit override, source identifier and
actual exit is in `COMMANDS.json`. Python tests used existing pytest 8.3.4 and
Java 21.0.8. Existing packaged Java binaries were fingerprinted/reused after exact
module source/POM comparison; **not rebuilt**. See `NATIVE-BINARIES.json`. Java
JUnit counts in Step 10 remain historical; no new JUnit/Java verification claim.

The first recorded native smoke failed on the new test's terminal `owner`
assertion after successful output exchange. Existing code clears terminal owner
correctly. The smoke now checks retained attempt session identity. Original
failed output, exported safe history, source ID/manifest and differing test source
are preserved under `native-smoke.log`, `runs/…-smoke/`, and
`source-revisions/c457006d…/`. First 21-test output is `adapter-unit.log` under
that original ID; final unit/full runs use the final ID above. The first failed
smoke is not counted as a successful gate.

Final acceptance has no ordinary failure/setup/teardown error or XPASS. Its lone
XFAIL is the unchanged strict `raises=RecoveryNotObserved` crash oracle. Native
visible failure has only that final failure, with A SIGKILL, original attempt
stuck, Y BLOCKED, fresh B probe, late healthy polling, safety and exports passing.
Both exported histories for that real failure passed offline validation.

Retained run mapping (raw export bytes copied unchanged; `runtime/` omitted):

| Label suffix under runs/ | Directories | Histories | Interpretation |
|---|---:|---:|---|
| `step11-20261003T174933-50c63001-smoke` | 1 | 1 | Historical first smoke assertion failure; safe history retained. |
| `step11-20261003T175026-5dbfb7d8-smoke-retry` | 1 | 1 | Corrected smoke PASS. |
| `step11-20261003T175026-5dbfb7d8-acceptance` | 39 | 30 | Full suite 84 PASS + 1 strict XFAIL. |
| `step11-20261003T175026-5dbfb7d8-fault-demo` | 1 | 2 | Real native final recovery failure. |

All 42 cleanup flags true. No runtime outcome or source attribution was edited.
`raw-runs/` was the actual execution destination; `runs/` is its retained promotion
without objects/caches. `runner-package/` uses **illustrative nonexistent image
digest references** solely to verify packaging and collection, not deployed
images or actual image provenance. Its generated `_project`/caches are omitted.

Actual local Hokea smoke/functional/crash and current Compose tests are **NOT RUN**,
because Docker is absent. They cannot be inferred from fakes, packaging, native
results or historical Step 10. No actual Hokea image/Pod/container/log/kill/
cleanup observation exists. Source pin and static API facts are in
`deploy/hokea/API.md`; remaining exact local gates are `deploy/hokea/README.md`.
Course user-command/prerequisite handoff is `deploy/hokea/CLUSTER-HANDOFF.md`.

Architecture deviations: **none**. Only orchestration/new tests/docs were added;
all existing correctness tests, Step 10 oracle, Native/Compose behavior, Java,
architecture, roadmap and Step 0–10 retained handoff/evidence bytes are unchanged.
