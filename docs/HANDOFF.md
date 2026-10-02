# Step 09 — Concrete video-file demonstration

Status: DONE on branch ms2/step-09-video (gate passed; pushed to origin; not yet on main, see S1-04).
Base commit: 4d2f8c9 (Step 8). Writer: Hasanlm23123.

## Added and changed

- **`workloads/video/sample.mp4` regenerated** by the new `workloads/video/generate.sh`. It uses FFmpeg's `testsrc2`: 10 s, 1280×720, 20 fps, H.264 CRF 28, no audio, 1.55 MB. Bit-exact flags and one thread make it **byte-reproducible**: two independent generations in `dag-ms2/harness:0.2.0` (FFmpeg 6.1.1) gave the same SHA-256. The previous checkpoint sample was also synthetic FFmpeg 6.1 output, but its generation command was never recorded.
- **Provenance:** `workloads/video/SHA256SUMS` and `workloads/video/README.md` record provenance and license (project-owned, synthetic), label the subtitles as a fixture (no transcription or paid API), describe the DAG, and give reproduction steps.
- **`.gitattributes`: `*.srt -text`.** This Windows checkout had silently converted `fixture.srt` to CRLF, so its working-copy SHA-256 no longer matched the committed bytes. The subtitle output is compared byte for byte. The blob is unchanged.
- **`test_video_pipeline` strengthened:**
  - input checksums are verified against SHA256SUMS before upload;
  - `inspect` metadata shows 1280×720 and 10 s;
  - both transcodes are H.264 at 1280×720 and 640×360 with a 10 s duration (checked with ffprobe), and the publish metadata matches them;
  - the thumbnail is a real PNG with a 1280×720 IHDR;
  - the subtitles are byte-identical to the fixture;
  - all four published references equal the accepted branch outputs;
  - the four branches ran on at least 2 worker sessions;
  - each branch is assigned after `inspect` succeeds, and `publish` after all four branches;
  - the history check passes, and evidence goes to `video-demo.json`.
- **`tests/harness/demo.py`** drives a running deployment: it uploads the committed workloads, runs the functional and video DAGs, checks history and outputs, and writes everything to `results/demo/<timestamp>/` (gitignored).
- **`Makefile`:** `build`, `up` (Compose, `WORKERS=3`), `demo`, `test` (harness: `mvn -B verify` plus the full suite with exactly one XFAIL), and `down`. `fault-demo` and `bench` come at Steps 10 and 12.
- **README** gains Evaluator commands, Tests and Workloads sections.

## Verification

- **pytest (harness):** `test_video_pipeline` passed. Outputs: video720 h264 1280×720, 10.0 s; video360 h264 640×360, 10.0 s; thumbnail 1280×720 PNG; subtitles byte-identical. The branches ran on 3 distinct sessions, and the job took 4.7 s. Evidence: `results/handoffs/step-09/pytest-video/`.
- **Live Compose demo (real containers, 3 workers):**
  1. `docker compose … up -d --build --wait --scale worker=3 scheduler artifact-store worker` exited 0, with all containers healthy or running.
  2. `python -m tests.harness.demo` exited 0. Functional result `result=22`, video job 7.2 s, history checks passed.
  3. An independent ffprobe of the downloaded files: video720 `h264|1280|720 10.000000`, video360 `h264|640|360 10.000000`, thumbnail `png|1280|720`, subtitles byte-identical.
  4. `docker compose … down` exited 0.

  Evidence: `results/handoffs/step-09/compose-demo/`. (`make` is not installed on this Windows host, so the recipe commands were run directly; see S1-02a.)
- **Gate, equivalent to `make test` (harness):** `mvn -B verify` exited 0 with 61 JUnit tests passing (33 + 20 + 8). `MS2_REQUIRE_XFAIL=1 pytest` gave **49 passed, 1 xfailed** (exit 0). See `results/handoffs/step-09/make-test-gate.txt`.

The video is workload data; the scheduler remains the project. No runtime media download is needed.

Architecture deviations: none.

## Next

Step 10 — intentional worker-crash liveness failure. The oracle already runs as the single strict XFAIL. Still needed:

- `make fault-demo` with `--runxfail`, and its saved nonzero failure;
- the operation-timeout caveat in OPEN_ISSUES S10-01;
- a run of the same oracle under Compose.
