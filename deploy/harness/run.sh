#!/usr/bin/env sh
# Run a command inside the Linux harness container with the repository mounted.
# Usage: deploy/harness/run.sh [command...]   (default: build, then the pytest suite)
#   deploy/harness/run.sh mvn -B verify
#   deploy/harness/run.sh pytest -k functional
set -eu
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
docker build -q -t dag-ms2/harness:0.2.0 -f "$ROOT/deploy/harness/Dockerfile" "$ROOT" >/dev/null
if [ "$#" -eq 0 ]; then
  set -- sh -c 'mvn -B -q package -DskipTests && MS2_REQUIRE_XFAIL=1 pytest'
fi
exec docker run --rm -v "$ROOT:/work" -v dag-ms2-m2:/root/.m2 dag-ms2/harness:0.2.0 "$@"
