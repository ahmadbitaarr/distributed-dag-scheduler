# Step 04 — Immutable artifact storage

Status: DONE on branch ms2/step-04-artifacts (gate passed; not yet on main — push blocked, see S1-04).
Base commit: c4d538b (Step 3). Writer: Hasanlm23123.

## Review and changes

The publication protocol in `ArtifactMain` already matches architecture §11:

- PUT stages the body to `stage-*.tmp` and checks it against the declared `Content-Length` and `X-Content-SHA256`.
- The object is published under a per-key lock into an in-memory completed-object index. Its bytes are moved to `object-<uuid>`.
- HEAD and GET consult only that index. A staging file is never visible, and it is deleted in a `finally` block.

Changes:

- **Fix:** a re-PUT of identical bytes with a different `Content-Type` used to return 200 and silently keep the old media type. The descriptor `(key, length, sha256, media_type)` is the immutable identity, so this now returns 409. A mutation check confirmed the new test fails on the old code.
- **Refactor (no behavior change):** `ArtifactMain.start(port, dataDir)` returns the server, so tests can run the real service on an ephemeral port. `main` calls it.

## Tests added: `ArtifactStoreTest` (8, real HTTP)

- **Round trip:** PUT 201 returns the descriptor. HEAD returns the length/hash/type headers, GET returns the bytes, and an identical replay returns 200.
- **Conflicts:** different bytes or a different media type under the same key get 409; the original bytes are kept.
- **Bad uploads:** a hash mismatch, missing hash, missing media type, bad key or traversal key gets 400. None of them publish, and none leave an object or staging file behind.
- **Oversize:** a declared `Content-Length` of 32 MiB + 1 gets 413 before the body is read.
- **Partial upload:** half of a 200 KB body is sent over a raw socket and held open. The staging file exists, but HEAD and GET return 404. After a mid-upload disconnect the object is still 404 and the staging file is removed. A later complete upload publishes normally.
- **Concurrent writers:** 12 writers with 3 distinct contents race on one key. Exactly one gets 201, the three identical replays get 200, the other eight get 409, and one object file results.
- **Persistence boundary:** published files remain on disk after the service stops. A restarted service has an empty index (404), so restart reconstruction is not claimed.
- **Errors:** health 200, wrong method 405, unknown path 404.

## Verification

`mvn -B verify -pl protocol,artifact-store` exited 0, with 8 artifact-store tests passing. Container health was verified at Step 1 and is re-verified in the Step 6+ Compose runs.

**Not claimed:** replication, power-loss durability, or reconstruction after a store restart. The "files survive a worker kill" claim is verified end to end at Step 10.
