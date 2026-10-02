#!/usr/bin/env sh
# Runs inside dag-ms2/harness. Works on a container-local copy of the mounted
# repository (/work): host bind mounts, especially on Windows/macOS, make JVM
# start-up and log I/O slow enough to distort timing-sensitive tests.
# Evidence is copied back to /work/results/latest-tests and the exit status is kept.
set -u
rm -rf /tmp/src && mkdir -p /tmp/src
(cd /work && tar --exclude=./.git --exclude=./results/latest-tests --exclude='./*/target' -cf - .) | tar -C /tmp/src -xf -
cd /tmp/src
export MS2_EVIDENCE_DIR=/tmp/src/results/latest-tests
if [ "$#" -eq 0 ]; then
  set -- sh -c 'mvn -B -q package -DskipTests && MS2_REQUIRE_XFAIL=1 pytest'
fi
"$@"
status=$?
mkdir -p /work/results/latest-tests
[ -d results/latest-tests ] && cp -r results/latest-tests/. /work/results/latest-tests/
exit $status
