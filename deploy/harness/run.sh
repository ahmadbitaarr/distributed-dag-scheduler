#!/usr/bin/env sh
# Run a command inside the Linux harness container against the current checkout.
# Usage: deploy/harness/run.sh [command...]   (default: package, then the full pytest suite)
#   deploy/harness/run.sh mvn -B verify
#   deploy/harness/run.sh pytest -q tests/integration/test_api.py
# Evidence lands in results/latest-tests/ (gitignored); the command's exit status is returned.
set -eu
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
docker build -q -t dag-ms2/harness:0.2.0 -f "$ROOT/deploy/harness/Dockerfile" "$ROOT" >/dev/null
# Tie evidence to the tested source: commit, plus a marker when the tree has uncommitted changes.
REV=$(git -C "$ROOT" rev-parse HEAD 2>/dev/null || echo unknown)
if [ -n "$(git -C "$ROOT" status --porcelain 2>/dev/null)" ]; then REV="$REV+uncommitted"; fi
MSYS_NO_PATHCONV=1 exec docker run --rm -e MS2_SOURCE_REV="$REV" -v "$ROOT:/work" -v dag-ms2-m2:/root/.m2 dag-ms2/harness:0.2.0 \
  sh /work/deploy/harness/in-container.sh "$@"
