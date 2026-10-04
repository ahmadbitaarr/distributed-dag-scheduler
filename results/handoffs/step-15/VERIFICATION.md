# Step 15 — final clean-source audit

Status: **PASS — runtime/content audit complete; supported-host results accepted by Planning.**
Audit date: 2026-10-04 UTC (2026-10-03 America/New_York at request).
Audited accepted source revision: `f4c5dceef533a98b195d7dfa2e54ec8cac788825` (Steps 0–14 accepted).
No Step 15 commit exists; the later user-created documentation commit is separate.

## Supported-host close-out — accepted by Planning

Source of these results: the user's supported-host verification summary supplied
2026-10-03 America/New_York, with explicit Planning acceptance and authorization
to finalize Step 15. These are user-reported external execution results, not new
runs in Work. Raw supported-host logs, exact host/tool versions, the interrupted
matrix's exit status and final cleanup command/exit were not supplied with this
summary; none are invented or added. The initial Work-host logs below remain
unchanged historical environment-limited evidence.

| Supported-host command | Exit | Reported result |
|---|---:|---|
| `make build` | 0 | Successful |
| `make up` | 0 | Successful |
| `make demo` | 0 | Successful |
| First `make down` | 0 | Successful |
| `make test` | 0 | 86 passed, exactly 1 expected XFAIL, 0 real failures |
| `make fault-demo` | 2 | Sole failure: `RecoveryNotObserved`; X RUNNING under killed worker A, Y BLOCKED, job RUNNING |
| Full `make bench` | Not supplied; interrupted | Started successfully and completed multiple configurations; manually interrupted due to submission deadline, not a complete matrix |
| Bounded command below | 0 | 24 completed jobs; error null |
| Final cleanup (exact command not supplied) | Not supplied | Completed successfully |

```bash
python3 -m benchmarks.run --backend compose --out results/benchmark/step15-verify --configs c1-w1 --repetitions 1
```

Bounded reproduction: **3.662895749764101 tasks/s**, job p50 **1596.4213 ms**,
scheduling p50 **32.58956 ms**, wall **74.7 s**, **24 completed jobs**, error **null**.
This is a separate supported-host Step 15 reproduction, not a replacement for or
addition to the accepted Step 12 45-run measurement dataset. Its normal-operation,
synthetic-workload and shared-host/resource qualifications remain; it establishes
no recovery-time measurement or general performance guarantee. Planning accepted
this bounded verification and the reported runtime results for Step 15 close-out.
No new full benchmark was run during this documentation-only turn.

Normal acceptance and visible fault behavior remain distinct: acceptance exits 0
with the single permitted strict typed XFAIL; fault-demo exits 2 from the actual
recovery-demanding oracle. Initial Work-host exit 2 failures were infrastructure
failures and are not reclassified as that intentional defect.

Close-out edits are limited to `README.md`, `docs/PROGRESS.md`, `docs/HANDOFF.md`,
`docs/OPEN_ISSUES.md`, `docs/handoffs/step-15.md`, and this `VERIFICATION.md`.
No implementation, existing test, benchmark methodology/data, PDF, architecture,
behavior, raw log, manifest, receipt or packaging script changed. The finalized
workspace ZIP is `distributed-dag-scheduler.zip` with the canonical root. The
unchanged `PACKAGE-RECEIPT.json` and post-package logs describe the earlier blocked
candidate only; their checksum does not identify this documentation-closeout ZIP.
The new ZIP checksum is supplied with delivery. A final post-commit submission
archive still belongs to the later user-controlled Git close-out.

## Origin and scope

Input: user-supplied clean `git archive`, `step15-input.zip`, 10,101,811 bytes.
Input SHA-256: `070f72f973e500501b3a9359dc7595a67318e9c3edad35a9d2a6bde55ef59bb5`.
The ZIP comment matches the accepted SHA, CRC validation succeeds, and there is
exactly one root: `distributed-dag-scheduler/`. This establishes supplied-archive
provenance, not independent remote repository authentication. No Git command,
GitHub authentication, credential/account-state use, Canvas action or course
cluster action was performed.

All 1,692 original files were byte-identical to the input before edits. The
baseline per-file sizes, SHA-256 and modes are in `accepted-source-manifest.json`.
Only four current-status Markdown files are edited: README, PROGRESS, HANDOFF and
OPEN_ISSUES. New files are restricted to the Step 15 handoff/evidence directory.
All implementation, existing tests, benchmark tools/data, final PDFs, architecture,
roadmap and Step 0–14 historical handoffs/evidence remain byte-identical.

## Clean-source and required-content audit

`accepted-content-audit.json` records 1,692 files / 23,779,098 uncompressed file bytes.
No `.git`, credentials/configuration files, venv, Python/pytest caches, Maven
`target`, `.class`/`.jar`, runtime object directory, symlink, nested archive or
machine/account state was found. Common private-key, AWS/GitHub/Slack-token,
authenticated-URL and sensitive-assignment scans found zero candidates. This is
a signature/filename audit, not a guarantee against every possible secret.

Absolute-path review found 289 matching lines: 280 are historical records;
the other 9 are declared container paths or `/tmp/f.json` tutorial examples.
No active host-specific source dependency was found. Historical machine paths
in logs are retained as provenance; they are not bundled machine state.
Only four files exceed 1 MiB: the 1,554,682-byte committed synthetic sample and
three 1,321,890-byte historical video outputs. No unrelated large log was found.
No committed raw/summary evidence was removed.

Included: all five Java module source/test trees, pytest suites/oracle/harness,
functional/video workloads, build and deployment automation, API/evidence docs,
revised specification/progress report, evaluator README, benchmark tools,
accepted Step 12 measurements and intentionally committed Step 0–14 history.
Step 13 has its authoritative `results/handoffs/step-13/VERIFICATION.md`; there
was never a `docs/handoffs/step-13.md` in this input, and none was fabricated.

Final PDFs are unchanged and readable: `docs/pdf/MS2-Progress-Report.pdf` (6 pages)
and `docs/pdf/MS2-Revised-Specification.pdf` (4 pages); metadata identifies Step 14
finalized documentation. No draft PDF is present. `sha256sum -c SHA256SUMS` in
`workloads/video` passes both files. FFprobe observes H.264, 1280×720, 20 fps,
10.000000 s for the committed input; this is not a newly executed video DAG.
The input ZIP uses DOS metadata without Unix permission bits. Extracted files use
0644, directories 0755; those observed modes are preserved in the outputs.
The three source shell scripts have mode 0644 and
are invoked using `sh` by the documented workflows, so no executable bit is needed.

## Initial Work environment — historical

Ubuntu 24.04.3 LTS, Linux 6.18.44 x86_64; host Python 3.12.14 (system Python
3.12.3); GNU Make 4.3; FFmpeg/ffprobe 6.1.1-3ubuntu5; OpenJDK **17.0.20 JRE**.
Java 21 JDK/javac, Maven, Docker/Compose, pytest and Hokea are unavailable.
No dependencies were installed and no account or external service was used.
No deployment was started; there are no Step 15 service processes or containers
to clean up. The failed demo created only an empty output directory, omitted
from the archives. Resource caps cannot be observed/enforced without Docker.

## Initial Work evaluator commands and exit statuses — historical

Commands ran sequentially from THIS extracted source. `commands.json` and the
individual logs preserve exact commands and statuses. The wrapper itself returns
0 after recording results; it does not turn failed children into passing gates.
Environment: `PYTHONDONTWRITEBYTECODE=1`, `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`,
`MS2_SOURCE_REV=f4c5dceef533a98b195d7dfa2e54ec8cac788825`; no reused run label/backend/XFAIL overrides.
`run_commands.py` is the exact scratch-layout driver used before edits; retained
for review, not an additional product tool. Original invocation from the scratch
parent: `python3 step15-work/run_commands.py` (exit 0).

| Command | Exit | Captured output |
|---|---:|---|
| `cat /etc/os-release` | 0 | `logs/os.log` |
| `uname -srmo` | 0 | `logs/kernel.log` |
| `java -version` | 0 | `logs/java.log` |
| `javac -version` | 127 | `logs/javac.log` |
| `mvn -version` | 127 | `logs/maven.log` |
| `python3 --version` | 0 | `logs/python.log` |
| `/usr/bin/python3 --version` | 0 | `logs/system-python.log` |
| `python3 -m pytest --version` | 1 | `logs/pytest.log` |
| `/usr/bin/python3 -m pytest --version` | 1 | `logs/system-pytest.log` |
| `ffmpeg -version` | 0 | `logs/ffmpeg.log` |
| `ffprobe -version` | 0 | `logs/ffprobe.log` |
| `make --version` | 0 | `logs/make.log` |
| `docker compose version` | 127 | `logs/compose.log` |
| `docker info` | 127 | `logs/docker-info.log` |
| `make build` | 2 | `logs/build.log` |
| `make up` | 2 | `logs/up.log` |
| `make demo` | 2 | `logs/demo.log` |
| `make down` | 2 | `logs/down-before-tests.log` |
| `make test` | 2 | `logs/test.log` |
| `make fault-demo` | 2 | `logs/fault-demo.log` |
| `make bench` | 2 | `logs/bench.log` |
| `make down` | 2 | `logs/down-final.log` |
| `python3 deploy/hokea/verify_api.py` | 2 | `logs/hokea-pin.log` |
| `cd workloads/video && sha256sum -c SHA256SUMS` | 0 | `logs/video-checksums.log` |
| `sha256sum docs/CS4094_MS2_Architecture.md docs/implementation-roadmap.md` | 0 | `logs/architecture-checksums.log` |
| `pdfinfo docs/pdf/MS2-Progress-Report.pdf` | 0 | `logs/report-pdf.log` |
| `pdfinfo docs/pdf/MS2-Revised-Specification.pdf` | 0 | `logs/specification-pdf.log` |
| `python3 -m pytest -q -p no:cacheprovider tests/unit` | 1 | `logs/unit-tests.log` |
| `python3 -m tests.harness.check_evidence results/handoffs/step-08/sample-history` | 0 | `logs/sample-evidence.log` |
| `ffprobe -v error -select_streams v:0 -show_entries stream=codec_name,width,height,r_frame_rate:format=duration -of json workloads/video/sample.mp4` | 0 | `logs/sample-media.log` |

`make build`: missing Maven (recipe 127, Make 2). `make up`, both `make down`,
`make test`, `make fault-demo`, `make bench`: missing Docker (recipe 127, Make 2).
`make demo`: scheduler connection refused after failed startup (Python 1, Make 2).
The separate host unit-test attempt exits 1 because pytest is not installed.
Hokea pin verification exits 2 because Hokea is not installed; no cluster check ran.

## Initial Work normal suite versus intentional fault — historical

**Initial Work normal suite: NOT VERIFIED in that environment.** `make test` did not reach JUnit/pytest;
no Work-host pass/XFAIL count was obtained. Historical Step 13 recorded 86 PASS + exactly
one strict typed XFAIL, unchanged and separately attributed.

**Initial Work fault-demo: NOT VERIFIED in that environment.** Exit 2 here is infrastructure
failure before the oracle, not `RecoveryNotObserved`, and does not satisfy the
demonstration gate. The unchanged test retains `strict=True`,
`raises=RecoveryNotObserved`; Make retains the separate `--runxfail` command.
Silent worker death still has no ownership reclamation mechanism. Source identity
and static inspection support preservation; new runtime behavior was not observed.

## Valid unaffected checks

From the scratch parent, with `PYTHONDONTWRITEBYTECODE=1`:

- `python3 step15-work/audit_source.py distributed-dag-scheduler step15-work/source-audit`
  — final exit 0; required content/exclusion/signature checks above.
- `python3 step15-work/offline_checks.py distributed-dag-scheduler step15-work/offline-final`
  — exit 0; uses the documented `check_directory` on every committed `manifests.json`.
  All **135 directories** return without exceptions: **84 nonempty directories,
  121 job histories; 51 empty-manifest directories** validate zero jobs and do not
  establish workload success. Includes historical aborted/setup runs without
  rewriting or relabeling their original outcomes. Per-directory counts are in
  `evidence-checks.json`.
- All committed Python files parse with `ast.parse`; shell scripts pass `sh -n`;
  all Maven POMs parse as XML (inside the offline command, exit 0).
- Existing single-history CLI check, video checksums, architecture hashes, PDF
  metadata and FFprobe commands also exit 0 as recorded in the table.

Audit-script development findings: an initial content check exited 1 because it
assumed a separate Step 13 docs handoff; inspection showed the accepted verification
record supplies it. The audit inventory was corrected, with no source addition.
The first offline aggregate exited 1 at an overly strong raw-byte CSV comparison:
`csv.writer` generated CRLF while committed `.gitattributes` preserves LF. Report
and JSON bytes already matched; comparison of CSV after CRLF→LF is identical.
The final audit explicitly records raw CSV inequality and normalized equality.
The first packaging precheck also stopped (exit 1, before creating an archive)
because it assumed Unix permission bits in the DOS-format input. It now preserves
the observed extraction modes, without changing project permissions.
These were audit assumptions, not application defects; no existing assertion or
test semantics were weakened. Original accepted bytes were never modified.

## Initial Work benchmark checks and accepted measurements — historical

**Initial Work `make bench`: BLOCKED, exit 2.** It fails at the Compose image build;
the measurement driver never starts. No new full or reduced matrix, throughput,
latency or recovery-time measurement is claimed. Accepted Step 12 files are untouched.

The existing `python3 -m benchmarks.report <scratch-copy>/full-20261003c` ran
inside the offline command (exit 0) on an isolated copy because it rewrites
summaries. Generated report and JSON match accepted bytes; CSV matches after LF
normalization. It confirms 45 complete runs, 1,080 jobs, 6,480 tasks and in-flight
bounds. This is an **offline integrity check**, not a benchmark reproduction.
`benchmark-integrity.json` preserves this distinction. The original shared-host,
synthetic-load, CPU/memory and no-recovery qualifications remain unchanged.

## Initial packaging and post-package receipt — historical

Candidate filename: `distributed-dag-scheduler-submission-candidate.zip`.
Review filename: `distributed-dag-scheduler.zip`. Each must have exactly one
`distributed-dag-scheduler/` root. Neither archive is placed inside the project.
The candidate is a pre-commit snapshot of this audited source plus the proposed
Step 15 documentation available before archive creation, **not an accepted final
post-commit submission** and not a passing runtime certification.

The review workspace additionally contains `PACKAGE-RECEIPT.json` in this evidence
directory, written after candidate creation. It records the candidate's exact
byte size/SHA-256, layout/CRC/content/mode extraction validation, fresh-extraction
smoke commands/exits and the exact review-only file list. It is detached from the
candidate to avoid asking an archive to contain its own cryptographic checksum.
The candidate deliberately does not contain that later receipt or its logs.
The final response also supplies both archive SHA-256 values; neither archive
contains a copy of itself or another ZIP. `package_archives.py` records the
packaging/extraction procedure and checks that protected files remain unchanged.

## Remaining limitations and close-out

Step 15 is **PASS/runtime-content audit complete** based on the initial content/
packaging checks and subsequent supported-host results accepted by Planning above.
The initial Work-host limitation remains recorded, not an open close-out blocker.
The full Step 15 benchmark was interrupted; only the bounded reproduction completed.
Accepted Step 12 measurements remain separate and unchanged. No runtime gate or
full benchmark is rerun in this tiny documentation close-out.

Hokea/course service execution: **NOT VERIFIED**; accepted historical course
attempt remains blocked by the external runner/package mismatch. No authorized
course environment is present and no rerun was attempted. Current Canvas naming,
location and packaging details remain unchecked; no submission occurred.

Architecture/behavior changes: **none**. No leases, heartbeats/expiry, automatic
requeue, scheduler durability/replication, exactly-once external effects or MS3
work. The stalled task/job remain RUNNING and descendants BLOCKED. No Git
operation was performed. User review and a later user-created Step 15 commit
must precede regeneration from any final accepted revision.

Suggested commit message: `chore(ms2): finalize audited milestone artifact`.
