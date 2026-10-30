# MS3 documentation review

Reviewed the uploaded `distributed-dag-scheduler-main(3).zip` on October 29, 2026. No GitHub access, commits, pushes or Canvas actions were performed. This is a documentation review with offline evidence checks, not a fresh live-system acceptance run.

## What changed

Rewrote the specification, MS3 progress report, test matrix introduction/instructions, top-level README, MS3 evidence index and oral-defense notes for clearer explanations. Existing result tables, test identifiers, configuration values and source revisions were retained. The five quoted MS1 passages are verbatim. Existing fenced commands and examples were preserved except for the corrected offline-check command explained below. Historical MS2 files, software, tests, deployment files, benchmark drivers and raw evidence are byte-identical to the upload.

The three current PDF exports were regenerated and visually inspected: specification 5 pages, progress report 5 pages, test matrix 4 pages. This environment has no Chromium browser, so these exports were produced with a temporary ReportLab renderer from the same Markdown, rather than the unchanged Chromium-based `docs/pdf/build_pdfs.py`. That script remains available for the team's normal rebuild; pagination may differ. No temporary renderer was added to the project.

## Factual and scope corrections

- Replaced the unconditional claim that three consecutive lost heartbeats are always tolerated. `WorkerMain` uses `scheduleWithFixedDelay`, and `Transport` allows a 5-second request timeout. Request duration therefore adds to the 1-second wait and can consume a 5-second lease. Three lost heartbeats fit only with sufficiently prompt requests. Settings and measured test results are unchanged.
- Replaced claims that a same-day control conclusively rules out code effects. The C=1, W=4 control supports host variability; it cannot isolate every potential effect at other loads. All recorded throughput values remain unchanged.
- Described about 11,000 tasks as a capacity estimate from the memory probe, not a tested hard maximum. The retained probe estimates 11,850 from one 600-task sample; the existing rounded 11,000 figure is unchanged.
- Distinguished at-most-one recorded success from unconditional exactly-once execution or completion. Explained that saved-history checks cover the executions and evidence retained, rather than proving all possible schedules.
- Preserved P-REC and clarified that its tested lease + 2 s reassignment bound requires the stated responsive operating conditions and an idle polling worker. It is not a bound under arbitrary network delay or scheduler suspension. The 10.3 s queued recovery remains explicitly reported.
- Replaced a categorical claim that crashes never slow unaffected jobs with the actual comparison: observed medians were within 8% of the baseline.
- Corrected the evidence-index offline-check command. Its original recursive scan tried to check a performance-control directory whose event stream was intentionally omitted. The command now prints that directory as NOT CHECKED and checks the complete evidence. The original teammate handoff is retained unchanged; use the corrected command in `results/ms3-logs/README.md`.
- Clarified that 16 kills and 13 recovered orphaned tasks refer to the 8 completed crash runs, not to all attempted crash runs. The incomplete run is separate and is still excluded from aggregate performance results.

## Checks actually performed here

1. Read the selected Maven log: 33 protocol + 36 scheduler + 8 artifact-store JUnit tests = 77, no failures, BUILD SUCCESS.
2. Read `make-test-3.log` and its pytest XML: 102 tests, zero failures/errors/skips; the log records exit 0. These are the teammate's recorded live results, not new executions here.
3. Executed the existing offline checker on the submitted test evidence: 52 job histories in 52 directories, no violations.
4. Executed it on the selected recovery benchmark: 503 job histories in 18 directories, no violations. Worker logs are omitted from that benchmark evidence; the offline check uses the retained scheduler records and snapshots.
5. Recomputed the six recovery-summary rows from copies of `runs.csv`, `recovery_jobs.csv` and `recoveries.csv`, outside the repository. The regenerated JSON matches the committed summary exactly. Raw CSVs and summaries were not changed.
6. Executed the corrected recursive check: 555 histories passed, and the outside-OneDrive attribution-control folder was explicitly reported NOT CHECKED because its `events.jsonl` is absent.
7. Compared existing files against the input ZIP: only the six named Markdown documents and three MS3 PDF exports changed. Verified the original specification quotations and preserved command blocks, except for the documented command fix.
8. Opened and rendered all three PDFs, and inspected page layouts.

## Still for the team

Read the prose and check that both members can explain it in their own words. The use of “we” describes the team's documented project work, not a claim that this review reran it. No live `make test`, Compose demo, Hokea deployment or new performance experiment was run here. Hokea course-cluster execution remains unverified; one of the selected 18 benchmark runs remains incomplete. The archive is a reviewed working copy, not a claimed final Git commit. The team must perform any desired supported-host recheck, commit/push and final archive/submission steps itself.
