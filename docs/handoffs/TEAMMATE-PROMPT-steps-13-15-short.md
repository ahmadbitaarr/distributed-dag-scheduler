# Short prompt: finish Steps 13–15 and submit

Paste everything inside the code block into your AI coding assistant, running in your clone of the repository. Also give it the course guidelines PDF (`cs4094_f26_project_guidelines_v20260824.pdf`), because Step 14 checks the report against it, including any page limit. The longer, more detailed version is `TEAMMATE-PROMPT-steps-12-15.md`.

```text
You are finishing the CS4094 MS2 distributed DAG scheduler project: Steps 13, 14
and 15, in that order. Steps 0-12 are done; do not change their code or results.
The full benchmark (Step 12) is already done; do NOT re-run the full matrix.

Setup (on Windows, first run: git config --global core.longpaths true):
  git clone https://github.com/ahmadbitaarr/distributed-dag-scheduler.git
  cd distributed-dag-scheduler
  git switch ms2/step-12-benchmark      # expect commit 57b9417 or later
Read: docs/implementation-roadmap.md (Steps 13-15), README.md, docs/handoffs/step-12.md,
docs/OPEN_ISSUES.md, docs/ms2-progress-report.md, docs/specification.md.
Needs Docker, Python 3 and make. Keep at least 4 GB of RAM free.

RULES: never invent or edit results; if something fails, keep the output and report it.
Do not touch the Hokea pin, weaken tests, or add leases or other worker-recovery logic.
Never force-push.

STEP 13: independent verification (fresh clone, no old caches). Record the command,
exit code and result for each:
  1. make test        -> exactly 1 xfailed, 0 failures, exit 0
  2. make fault-demo  -> nonzero exit, only failure = RecoveryNotObserved
  3. make up && make demo && make down -> result=22, readable 720p/360p MP4s, 1280x720 PNG
  4. python3 -m tests.harness.check_evidence <each results/latest-tests/... dir that has manifests.json> -> all OK
  5. python3 -m benchmarks.run --backend compose --out results/benchmark/verify-1 --configs c1-w1 --repetitions 1 -> complete
Write results/handoffs/step-13/VERIFICATION.md (SHA, OS/Docker/Python versions, commands,
exit codes, results, findings). Commit with:
"test(ms2): record independent clean-checkout verification".
If you find a real defect, fix it with a test that fails on the old code, re-run, and document it.

STEP 14: finish the report and spec. In docs/ms2-progress-report.md, replace the
remaining [PENDING Step 13] markers (status banner and section G) with your Step 13
findings. Then remove the DRAFT banners from that file and docs/specification.md.
Check that sections A-I are complete and that every number matches a committed
evidence file. If the course guidelines PDF sets a page limit, trim to fit. Update
docs/PROGRESS.md (Steps 12-14 DONE), docs/HANDOFF.md and docs/OPEN_ISSUES.md. Commit with:
"docs(ms2): reconcile specification and progress report with evidence".

STEP 15: audit and package.
  git push origin ms2/step-12-benchmark
  git switch main && git pull --ff-only origin main
  git merge --ff-only ms2/step-12-benchmark && git push origin main
(If the fast-forward fails, main has moved: stop and reconcile; do not force.)
Clone main fresh into a new folder and re-run make test (expect 1 xfailed, exit 0).
Build the archive from the final commit:
  SHA=$(git rev-parse HEAD)
  git archive --format=zip -o cs4094-ms2-${SHA:0:7}.zip "$SHA"
  sha256sum cs4094-ms2-${SHA:0:7}.zip > cs4094-ms2-${SHA:0:7}.zip.sha256
Unzip it somewhere new and confirm it contains the source, tests, workloads, Makefile,
docs, report and spec. Write results/handoffs/step-15/AUDIT.md (final SHA, zip checksum,
commands). Commit with "chore(ms2): finalize audited milestone artifact" and push main.
Note: AUDIT.md is committed after the zip is built, so the zip comes from the commit
just before it; record that SHA.

SUBMIT: check Canvas for naming rules and the deadline, then upload the single ZIP.
Report back: the final main SHA, the zip name and checksum, and confirmation of submission.
```
