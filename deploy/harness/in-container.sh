#!/usr/bin/env sh
# Runs inside dag-ms2/harness. Works on a container-local copy of the mounted
# repository (/work): host bind mounts, especially on Windows/macOS, make JVM
# start-up and log I/O slow enough to distort timing-sensitive tests.
# Each pytest invocation has a unique run directory. Copy failures remain ordinary errors.
set -u
rm -rf /tmp/src && mkdir -p /tmp/src
(cd /work && tar --exclude=./.git --exclude=./results/latest-tests --exclude='./*/target' -cf - .) | tar -C /tmp/src -xf -
cd /tmp/src
export MS2_EVIDENCE_DIR=/tmp/src/results/latest-tests
if [ "$#" -eq 0 ]; then
  set -- sh -c 'mvn -B -q verify && MS2_REQUIRE_XFAIL=1 pytest'
fi
"$@"
status=$?
mkdir -p /work/results/latest-tests
if [ -d results/latest-tests ]; then
  if ! cp -r results/latest-tests/. /work/results/latest-tests/; then
    echo "Evidence copy failed" >&2
    exit 2
  fi
fi
exit $status
