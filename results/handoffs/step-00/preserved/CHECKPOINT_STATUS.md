# Unreviewed implementation checkpoint — not an MS2 submission

The current requested deliverable is the sequential team workflow and implementation
roadmap. Partial Java/Python code produced earlier in this workspace is preserved
for review and reuse. It has not been independently verified or accepted as a
completed architecture implementation. No new service code was added after the
planning-only continuation scope was recovered.

Observed evidence:

- `evidence/build-proxy.log`: all five Maven modules built successfully at an earlier
  source revision. It contains no completed JUnit tests.
- `evidence/integration-first.log`: 6 passed, 15 deselected in 28.52 seconds.
- `evidence/selected-native-tests/`: snapshots, events, metrics, and raw service logs
  for those six tests. Runtime object-store scratch files are excluded.
- `evidence/build-tests.log`: a later build failed fetching the Maven JUnit provider
  because its environment-specific proxy connection was unavailable. No current
  full-suite result exists.

The six selected checks were executed with native Java processes, not containers.
They do not establish video verification, recovery-oracle behavior, benchmark
results, clean-clone deployment, or Hokea integration.

Normalized historical commands (environment-specific proxy/toolchain setup is not
part of the project and has not been packaged):

```bash
mvn -B -U -ntp -f cs4094-ms2/pom.xml package
python3 -m pytest -q cs4094-ms2/tests/integration/test_system.py -k 'functional_multiple or simultaneous or submission_and_claim or duplicate_conflicting or success_requires or staging'
mvn -B -ntp -f cs4094-ms2/pom.xml package
```

The Maven commands actually used an environment-specific `-s` proxy settings file;
that file is intentionally excluded. The first command succeeded before later
source/test additions. The last command did not run the new JUnit tests.

Missing/unverified: full tests; the hard-kill demonstration; full video workload
validation; benchmark execution; Docker/Compose/Hokea setup; complete README/API,
revised specification, progress report and clean-evaluator proof. The draft Python
Hokea factory references an adapter that has not been written. The checkpoint does
not yet contain the required complete Makefile or Compose configuration.

This package is a continuation aid. Do not submit it as a finished MS2 artifact or
use its draft implementation choices to override the canonical architecture.
