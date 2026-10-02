#!/usr/bin/env sh
# Regenerates workloads/video/sample.mp4: a synthetic, project-owned 10 s 1280x720
# H.264 clip from FFmpeg's built-in testsrc2 source (no external media, no download).
# Run it in the pinned harness image (ffmpeg 6.1.1) from the repository root so the bytes match SHA256SUMS:
#   docker run --rm -v "$PWD:/work" -w /work dag-ms2/harness:0.2.0 sh workloads/video/generate.sh
# Bit-exact flags strip version strings; one thread keeps libx264 deterministic.
set -eu
OUT=${1:-workloads/video/sample.mp4}
ffmpeg -nostdin -hide_banner -loglevel error -y \
  -f lavfi -i "testsrc2=size=1280x720:rate=20:duration=10" \
  -c:v libx264 -preset medium -crf 28 -pix_fmt yuv420p -threads 1 \
  -map_metadata -1 -fflags +bitexact -flags:v +bitexact \
  -movflags +faststart "$OUT"
sha256sum "$OUT"
