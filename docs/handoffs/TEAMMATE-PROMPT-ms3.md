# MS3: instructions for Ahmad

MS3 is implemented, tested and pushed to `main`. What is left for you:

1. **Required:** rewrite the MS3 reports and deliverables so they read like our own writing. Every fact, number and claim stays exactly the same.
2. **Optional:** recheck the work by running the tests (and, if you have time, the benchmark) on your Ubuntu machine.
3. **Required:** read the defense prep sheet, rebuild the zip from the final commit, and agree with Hasan on who submits on Canvas.

Paste everything below the line into your AI coding assistant (Claude Code, Codex or similar), running in your clone of the repository after `git pull origin main`.

---

You are helping finish CS4094 Milestone 3 for our distributed DAG task scheduler (repository root = current directory, branch `main`). The system and its evidence are complete. Do three things, in order, and stop to ask me if anything conflicts with these rules.

## Ground rules

- Do **not** change code, tests, benchmark drivers, deployment files, or anything under `results/`. There are two exceptions: rewording `results/ms3-logs/README.md` (Part 1), and adding new files under `results/ms3-logs/independent-check-*/` (Part 2).
- Do **not** change any claim, number, test name, file path, command, configuration value or source revision in the documents. Rewording is allowed; changing meaning is not. If you believe a statement is wrong, check it against the code and `results/ms3-logs/`, fix only the factual error, and list it in your final summary.
- Do not invent results. Do not edit historical MS2 material: `docs/CS4094_MS2_Architecture.md`, `docs/implementation-roadmap.md`, `docs/ms2-progress-report.md`, `docs/ms2-claim-evidence.md`, `docs/handoffs/step-*.md`, `docs/pdf/MS2-*.pdf`.

## Part 1 (required): humanize the MS3 deliverables

Rewrite these files completely, so they read as if written by our two-person student team rather than generated:

1. `docs/specification.md`: the MS3 specification (graded deliverable)
2. `docs/ms3-progress-report.md`: the MS3 progress report (graded deliverable)
3. `docs/test-matrix.md`: the test-to-property table (required by the course)
4. `README.md`: the first thing the red team reads
5. `results/ms3-logs/README.md`: the index of run logs. Rewording only; this one file under `results/` may be edited.
6. `docs/ms3-oral-defense.md`: our defense prep notes

How to write:

- Plain, direct sentences in first-person plural ("we chose…", "we measured…"). Vary sentence length. Say each thing once.
- Remove generated-text tells:
  - stacked em dashes;
  - words like "robust", "seamless", "leverage", "delve", "comprehensive", "ensure", "crucial";
  - everything grouped in threes;
  - every bullet starting with a bolded label;
  - perfectly parallel bullet lists;
  - "Key takeaway"/"In summary" lines;
  - sentences that only restate the previous one;
  - over-hedging.
- Prefer short paragraphs to long bullet lists where the text is an explanation. Keep tables: they are data. Keep code blocks and commands exactly as they are.
- Keep the quoted MS1 claims (the `>` blockquotes in the specification) **verbatim**.
- Keep the technical vocabulary exact: S1, S2, S3, L1, L2, P-REC, lease, heartbeat, attempt, `LEASE_EXPIRED`, `EXPIRED`, `LEASE_TIMEOUT_MS`, and every endpoint, event and test name.
- Keep the length about the same or shorter: specification at most 7 pages, progress report at most 6, test matrix about 4.

After rewriting, check that every one of these facts is still present and unchanged wherever it appeared before:

| Fact | Value |
|---|---|
| Test totals of the submitted run | 77 JUnit tests; pytest 102 passed, 0 failed, 0 expected failures; run `make-test-3`, clean source `966965e` |
| New tests | 16 lease JUnit tests + 1 idle-polling JUnit test; 13 new fault tests (14 with the MS2 crash oracle); 2 new checker tests |
| Lease settings | lease 5 s (`LEASE_TIMEOUT_MS` 5000), heartbeat every lease/5 = 1 s, expiry scan 100 ms; up to three consecutive lost heartbeats always tolerated |
| P-REC bound | never detected before the lease; reassigned within lease + 2 s when an idle worker is polling |
| Fault-test timings (run 3) | 10 expiries; detection 5.01–5.27 s; recovery 5.04–5.27 s with an idle worker, 6.04–6.05 s in the chaos run |
| Recovery benchmark | 17 of 18 runs complete; 16 kills, 13 orphaned tasks, all recovered; detection 5.00–5.09 s; recovery 5.00–5.10 s with a free worker, 10.3 s once when all workers were busy; 503 job histories pass the checker; source `d4fcda9` |
| Throughput (W = 4) | MS3 day: 4.4 / 14.8 / 11.9 tasks/s at C = 1 / 4 / 16; Step 12 (MS2): 6.0 / 15.4 / 16.7; same-day MS2-code control 3.06 tasks/s |
| Crash cost | jobs hit by a crash: median 6.3 / 6.9 / 11.4 s vs 1.0 / 1.7 / 6.0 s for the others; C = 4 throughput 14.8 → 9.7 tasks/s |
| Memory fix | idle heap grew 257 MiB/hour before the fix, flat after; about 10 KB per completed task; about 11,000 tasks per run with the 128 MiB heap |
| Defects fixed in MS3 | a replayed start for an expired attempt was acknowledged; idle polling grew memory (latent since MS2) |

Then rebuild the PDFs and check that they open and have sensible page counts:

```bash
python3 -m pip install markdown      # once
python3 docs/pdf/build_pdfs.py       # needs chromium, google-chrome or msedge
```

Commit with a message like `docs(ms3): rewrite MS3 reports in our own words; facts unchanged`.

## Part 2 (optional): recheck the work on this machine

Run any of these from the repository root. Write each log **outside** the repository (for example `/tmp`), so that the run is not stamped `+uncommitted`. Then copy the logs into a new folder `results/ms3-logs/independent-check-ahmad/`, together with a short `NOTES.md`. The notes should give the date, OS, `docker version`, the commit you tested (`git rev-parse HEAD`), each command, and its final line or exit code. Do not overwrite any existing file.

1. Full suite, the one command the red team will use (about 10–15 minutes after the first image build):
   `make test 2>&1 | tee /tmp/ms3-make-test.log` → expect `102 passed` and exit 0.
2. Deployment demo:
   `make up && make demo; make down` → expect `result=22` and `"history_checks": "passed"` in the printed summary.
3. Offline safety check of all committed evidence (Python standard library only):
   ```bash
   python3 - <<'PY'
   from pathlib import Path
   from tests.harness.check_evidence import check_directory
   dirs = sorted(p.parent for p in Path("results/ms3-logs").rglob("manifests.json"))
   print(sum(len(check_directory(d)) for d in dirs), "job histories in", len(dirs), "directories: no violations")
   PY
   ```
4. Only if there is time (about 30 minutes, quiet machine):
   `make bench-recovery 2>&1 | tee /tmp/ms3-bench-recovery.log`. Copy the new `results/benchmark/recovery-*/` CSV and summary files into your folder. Report recovery p50/max and throughput next to the numbers in the progress report §E. Do not replace the submitted results.

If anything fails, do **not** change tests or code to make it pass. Save the log, write what happened in `NOTES.md`, and tell Hasan. Commit the folder with a message like `results(ms3): independent recheck on <OS>`.

## Part 3 (required): finish and submit

1. Read `docs/ms3-oral-defense.md`. Either of us can be picked to give the 10-minute overview, and the questions are asked to individuals.
2. `git push origin main`.
3. Rebuild the submission zip from the final commit, because the PDFs and docs changed:
   ```bash
   git archive --format=zip --prefix=distributed-dag-scheduler/ -o ~/distributed-dag-scheduler-ms3.zip HEAD
   sha256sum ~/distributed-dag-scheduler-ms3.zip
   ```
4. Canvas submission: the zip, plus `docs/pdf/MS3-Specification.pdf`, `docs/pdf/MS3-Progress-Report.pdf` and `docs/pdf/MS3-Test-Matrix.pdf`. Agree with Hasan on **who** submits, so it happens exactly once and from the final commit.

Finish with a short summary for Hasan: files rewritten, any factual fixes, which optional checks ran and their results, the final commit hash, and the zip's SHA-256.
