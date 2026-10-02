# Step 00 — blocked baseline record

Status: BLOCKED. This is a continuation record, not an accepted GitHub handoff.
Repository: none established; branch: none; base commit: none; accepted commit: none.
Current writer: Codex for Step 0 preparation. Next teammate: not supplied.

## Work preserved and changed

All 37 checkpoint files matched the supplied ZIP before changes. No service, test, benchmark, POM or fixture contents were changed. docs/approved-architecture.md was renamed to docs/CS4094_MS2_Architecture.md with identical bytes. The approved roadmap was copied unchanged to docs/implementation-roadmap.md. Coordination files, .gitignore and Step 0 evidence were added. Original continuation ZIP remains untouched.

Canonical architecture SHA-256: 7d2f931bfcf308ccc2b32a899e8976e75656dab81f51b940df1aa136b37a8ef1.
Roadmap SHA-256: 2ac8ef1944d425a7416eb8bff8ee143d856030b59832a7f08cbd450459c5b921.

## Verification and limits

Archive CRC/path/checksum checks, supplied/canonical byte comparisons, original-source preservation and candidate exclusion/secret-pattern checks are the only gates run. Commands and results: results/handoffs/step-00/COMMANDS.md and verification.json. Candidate checksums and per-path inventory identify the reviewable prepared state. No Maven build, pytest run, runtime service, Docker deployment, crash injection or benchmark was started.

Historical evidence is preserved under results/handoffs/step-00/historical/. Earlier package success and six selected native passes belong to earlier unversioned source; an exact complete tested source revision cannot be recovered from the recorded evidence. The later JUnit attempt stopped at dependency resolution. See HISTORICAL_EVIDENCE.md and OPEN_ISSUES.md; do not label current source tested.

## System explanation for the receiver

Scheduler commands serialize through one memory-store monitor. Logical tasks progress BLOCKED → READY → ASSIGNED → RUNNING → SUCCEEDED. Accepted explicit failure from ASSIGNED/RUNNING returns a task to FIFO READY with a new attempt on reassignment. Attempts retain their owning run/job/task/attempt/session tuple and receipts. Parents' accepted success unlocks children; all tasks must succeed before the job succeeds. Workers poll with one slot and start acknowledgment before execution. Completed artifacts are immutable and attempt-namespaced.

Silent worker death intentionally leaves ownership stuck. Leases, heartbeat expiry, automatic silent recovery, scanners, administrative auto-requeue, scheduler failover and durable scheduler recovery remain absent. Worker-crash reassignment remains intentionally broken until MS3. Architecture deviations introduced by Step 0: none. Existing code remains subject to later contract review.

## Exact continuation order

1. User supplies an existing/new team repository URL and grants this GitHub connection repository access/write permission. No repository creation capability is currently available to this session; visible installed-account and repository lists are empty.
2. Resume Step 0, inspect remote history/default branch/process, then import the candidate without replacing existing history. Use ms2/step-00-baseline if available; do not invent an accepted branch before checking the remote.
3. Repeat Step 0 archive/content/preservation/exclusion checks against the actual staged tree. Resolve any collision, record real source identifiers, commit with suggested message docs(ms2): establish canonical baseline and sequential roadmap, push normally, integrate through the existing team process, and communicate the actual accepted SHA. Never force-push.
4. Only after Step 0 is DONE may the next teammate pull the accepted SHA and start Step 1. Exact Step 1 handoff: preserve all checkpoint implementation, resolve the normal Java 21/Maven build environment, complete the approved build/deployment foundation, and record a clean accepted-source build. First verification command from the shared repository root: `mvn -B verify`.

This record does not release Step 1. No real accepted SHA can be supplied until GitHub access is available and commit/push succeeds.
