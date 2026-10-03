# Prompt for finishing MS2: Steps 12–15

Paste everything below the line into your AI coding assistant (Claude Code, Codex or similar), running **in your clone of the repository**. Also attach, or put in the repo root, the two course PDFs if you have them: `cs4094_f26_project_guidelines_v20260824.pdf` and the approved MS1 spec `CS4069 MS1 Specification.pdf`.

---

You are finishing the Virginia Tech CS4094 distributed DAG task scheduler, Milestone 2 (MS2). Step 12 is already done. Complete roadmap **Steps 13, 14 and 15**, in that order, one at a time.

## Repository and starting point

- Repo: https://github.com/ahmadbitaarr/distributed-dag-scheduler
- Work on **`main`**. It already contains Steps 0–11 (accepted) plus Step 12 (complete) and the Step 14 drafts. Commit each step to `main` and push with `git pull --ff-only` followed by `git push`. Never force-push.
- **Windows only:** run `git config --global core.longpaths true` *before* cloning or pulling. Some evidence paths exceed 260 characters, and checkout fails partway without this.

```bash
git clone https://github.com/ahmadbitaarr/distributed-dag-scheduler.git
cd distributed-dag-scheduler
git log --oneline -1          # you are on main
```

## Read first (in this order)

1. `docs/CS4094_MS2_Architecture.md`: the canonical architecture and IMPLEMENTATION CONTRACT, especially §13 (benchmark), §14 (evidence), §15 (deployment) and §19.
2. `docs/implementation-roadmap.md`: Steps 12–15 are your instructions. Follow them exactly.
3. `docs/PROGRESS.md`, `docs/HANDOFF.md`, `docs/OPEN_ISSUES.md`, and `docs/handoffs/step-10.md` / `step-11.md`.
4. `results/handoffs/step-12/`: the two aborted benchmark attempts and why they were aborted.
5. `docs/specification.md` and `docs/ms2-progress-report.md`: Step 14 drafts with `[PENDING ...]` markers.
6. `README.md` and `Makefile`.

Source priority: course guidelines > approved MS1 spec > architecture/IMPLEMENTATION CONTRACT > roadmap > lectures. If the contract conflicts with the two governing sources, stop and explain.

## Hard rules

- **Do not redo or redesign Steps 0–11.** They are accepted.
- Do **not** add leases, heartbeats, expiry scanning, automatic silent-worker requeue, scheduler replication or failover, or durable scheduler recovery. The worker-crash test must stay exactly **one strict XFAIL** in `make test`, limited to `RecoveryNotObserved`.
- The Step 11 course-cluster run was **blocked by an external issue**: the course runner's Hokea package does not match the pinned revision `427b94634b1736ba8e59d4977836162aa58bd2cb`. Do **not** relax the pin or work around it. Report cluster execution as **NOT VERIFIED (external runner mismatch)**.
- **Never invent, edit or "fix up" measurements or test results.** Record every run, including failed and censored ones. If a run is invalid because of the environment, keep it, explain it, and re-run into a *new* output directory.
- If you find a real product defect, return it to the affected step: fix it, add a test that fails on the old code, re-run the affected gates, and document it. Never weaken an assertion to make something pass.
- Commit each step separately with the suggested message from the roadmap. Push the branch. Never force-push.

## Machine requirements

- Linux or macOS is preferred. Windows works with Docker Desktop plus Git Bash.
- **At least 8 GB of free RAM while the benchmark runs.** Close browsers and chat apps, and don't use the machine during the run. On the original Windows host, under 1 GB of free memory caused system-wide stalls and Docker engine crashes (see `results/handoffs/step-12/aborted-*`).
- Docker Engine with Compose v2, Python 3.10+ (standard library only, for the benchmark and demo), and `make`. Java/Maven/pytest are **not** needed on the host: `make test` runs in the pinned harness container.

## Step 12: ALREADY DONE (skip it)

Step 12 was completed on 2026-10-03 (commit `7c14d01`, now on `main`):

- **45/45 runs complete:** 1,080 jobs and 6,480 tasks, with outputs and the in-flight bound verified.
- **Record and results:** `docs/handoffs/step-12.md` and `results/handoffs/step-12/full-20261003c/RESULTS.md`.
- **Your job:** review it as part of Step 13 and run only the short benchmark reproduction listed there. **Start at Step 13.**

<details><summary>Original Step 12 instructions (for reference only)</summary>

## Step 12: run the exact benchmark and keep raw measurements

The driver `benchmarks/run.py` is finished and smoke-tested. Its target is `make bench`: it builds the images, then runs the full matrix on capped Compose services.

- C ∈ {1, 4, 16} × W ∈ {1, 2, 4}, with 5 fresh repetitions each: **45 runs**.
- Each run: 4 warmup jobs, then 24 measured six-task jobs, with a 120 s measured-phase timeout.
- 1 CPU / 512 MiB per service.

1. Check the environment, and record the output:
   `docker version`, `docker compose version`, `docker info`, `python3 --version`, and free memory (`free -m` or the OS equivalent).
2. Smoke check first:
   ```bash
   docker compose -f deploy/compose/compose.yaml build
   python3 -m benchmarks.run --backend compose --out results/benchmark/smoke-$(date -u +%Y%m%dT%H%M%SZ) --configs c1-w1,c16-w4 --repetitions 1
   ```
   Both runs should be `complete` with 24/24 jobs.
3. Run the full matrix: `make bench`. It takes about 60–120 min, so leave the machine alone. Record a free-memory sample periodically, for example `free -m` every minute into a file.
4. Generate the tables: `python3 -m benchmarks.report results/benchmark/<run-dir> > results/handoffs/step-12/RESULTS.md`
5. **Validity check:**
   - All 45 runs should be `complete`.
   - If some are `censored` or `error`, read `<run>/benchmark-error.txt` and the per-run evidence.
   - A host-pressure problem means re-running the matrix in a new directory and keeping both.
   - A product problem must be fixed per the rules above.
6. Commit to `results/handoffs/step-12/<run-dir-name>/`: `runs.csv`, `jobs.csv`, `tasks.csv`, `summary.csv`, `summary.json`, `environment.json`, your environment and memory logs, and `RESULTS.md`. Don't commit the per-run raw directories; `results/benchmark/` is gitignored.
7. Write `docs/handoffs/step-12.md` covering:
   - exact commands, exit codes, host and Docker details, and run statuses;
   - the measurements, with the percentile method (nearest rank, pooled over complete runs) and throughput aggregation stated;
   - limitations: shared host, synthetic 100 ms waits, polling latency included, recovery time unmeasured;
   - observed bottlenecks. Smoke data suggests most task time is worker-side HTTP artifact I/O and output verification, not scheduling. Confirm or refute this from the "where task time goes" table.
8. Commit with `perf(ms2): record the approved initial benchmark matrix`.

</details>

## Step 13: independent clean-environment verification

Use a **fresh clone** in a new directory, without the caches or outputs from Step 12. Follow only the README and Makefile.

| Command | Expected result |
|---|---|
| `make test` | JUnit plus the full pytest suite, **exactly 1 xfailed**, exit 0. The last known result was 86 passed + 1 xfailed. |
| `make fault-demo` | **Nonzero exit**, with the single failure `RecoveryNotObserved` and evidence saved. |
| `make up`, `make demo`, `make down` | Demo outputs in `results/demo/<time>/`: `result=22`, readable 720p/360p MP4s, a 1280×720 PNG, and byte-identical subtitles. |
| `python3 -m tests.harness.check_evidence results/latest-tests/*/` | Every directory that has `manifests.json` reports OK. |
| A short benchmark reproduction: `python3 -m benchmarks.run --backend compose --out results/benchmark/verify-<time> --configs c1-w1 --repetitions 1` | `complete`. |

Also review the safety, state, retry, publication and fault assertions against the source. Write `results/handoffs/step-13/VERIFICATION.md` with the checkout SHA, environment, every command, exit codes, outcomes, and concrete findings. Commit with `test(ms2): record independent clean-checkout verification`.

## Step 14: finish the revised specification and progress report

- In `docs/specification.md` and `docs/ms2-progress-report.md`, resolve every `[PENDING ...]` marker using only committed evidence:
  - Step 10: accepted, with evidence under `results/handoffs/step-10/`.
  - Step 11: adapter done locally; cluster NOT VERIFIED (external Hokea runner mismatch).
  - Step 12: your numbers.
  - Step 13: your findings.
- Fill progress-report §E with the benchmark tables and observed bottlenecks.
- Remove the "DRAFT" banners only when nothing is pending.
- Check the report has sections **A–I**: capabilities, repository structure, tests and results, the intentional failure, the benchmark, deployment, limitations, deviations, and the MS3 handoff.
- Make sure every claim maps to a test or evidence path, and every number to a raw file. A stalled job must never be described as failed or completed.
- Update `README.md`, `docs/PROGRESS.md`, `docs/HANDOFF.md` and `docs/OPEN_ISSUES.md`.
- Commit with `docs(ms2): reconcile specification and progress report with evidence`.

## Step 15: audit and package

1. Make sure every Step 13–14 commit is pushed to `main`. Never force-push.
2. From a clean checkout of the final `main`, re-run `make test` and confirm `make fault-demo` still fails as intended.
3. Build one archive from the exact commit (tracked files only, so no caches or build outputs):
   ```bash
   SHA=$(git rev-parse HEAD)
   git archive --format=zip -o cs4094-ms2-${SHA:0:7}.zip "$SHA"
   sha256sum cs4094-ms2-${SHA:0:7}.zip > cs4094-ms2-${SHA:0:7}.zip.sha256
   ```
4. Unzip the archive somewhere new and confirm it extracts and contains the source, tests, workloads, Makefile, docs, specification, report and selected evidence.
5. Write `results/handoffs/step-15/AUDIT.md` with the final SHA, the archive checksum, the file count and the commands run. Commit with `chore(ms2): finalize audited milestone artifact`.
6. Hand the ZIP to the team for Canvas submission. Check Canvas for any naming requirements; Lecture 6 p. 2 says to submit a single ZIP or tar.gz.

## When you finish each step, report

1. The changes, and why they satisfy the step.
2. Exact commands, exit codes, results and evidence paths.
3. Remaining issues, unverified checks, and any architecture deviations.
4. The commit SHA and pushed branch.
