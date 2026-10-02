# Historical evidence and source revision attribution

There was no Git repository when these commands ran. No Git SHA, full tested-source checksum manifest or run-time JAR fingerprint was recorded. Consequently the exact complete source revision tested cannot now be proven. Do not attach these passes to the Step 0 checkpoint identifier or any future accepted commit. This is an explicit provenance gap, not permission to invent a revision.

| Preserved evidence | Historical command / result | Source association that is supportable |
|---|---|---|
| `historical/build-proxy.log` | `mvn -B -U -ntp -s tmp/maven-settings.xml -f cs4094-ms2/pom.xml package`; BUILD SUCCESS, all five modules; each reports no tests to run | Earlier unversioned source, before the later HEAD/null-outcome edits and JUnit additions. Exact full revision UNKNOWN. The private proxy settings are excluded. |
| `historical/integration-first.log` and `historical/selected-native-tests/` | `python3 -m pytest -q cs4094-ms2/tests/integration/test_system.py -k 'functional_multiple or simultaneous or submission_and_claim or duplicate_conflicting or success_requires or staging'`; 6 passed, 15 deselected, 28.52s | Native harness launched module `target/<module>-0.2.0.jar` from the earlier successful package. Exact full tested source/binary revision UNKNOWN. Not current-source acceptance. |
| `historical/build-tests.log` | `mvn -B -ntp -s tmp/maven-settings.xml -f cs4094-ms2/pom.xml package`; BUILD FAILURE fetching `surefire-junit-platform:3.5.2`; scheduler/artifact-store/worker/client skipped | Later unversioned source; protocol main and test compilation recorded, JUnit engine never ran. Exact full revision UNKNOWN. This is an environment dependency-resolution failure. |

The Maven `-s` pathname is reconstructed from the preserved session setup; the logs themselves do not contain a complete shell command or authoritative exit-code receipt. BUILD SUCCESS/FAILURE and the pytest summary are recorded outcomes; numeric process exits were not preserved in these logs. Do not invent historical numeric exit codes or private environment prefixes.

Six recorded cases: `test_functional_multiple_jobs_workers`, `test_simultaneous_claims_and_session_single_slot`, `test_submission_and_claim_receipts`, `test_duplicate_conflicting_stale_reports_and_retry`, `test_success_requires_published_correct_outputs`, `test_artifact_staging_atomic_publication_and_conflicts`.

Native evidence contains snapshots, decision histories, metrics and raw service logs; it does not establish container caps, full video verification, fault demonstration, benchmarks or clean-clone deployment. Current retained JAR hashes are recorded in retained-binary-fingerprints.json as observations only; binaries are not imported. Checkpoint-source-SHA256SUMS.txt identifies the 37 preserved files NOW, not the source used by the earlier runs. Historical files are preserved byte-for-byte and will be covered by candidate-SHA256SUMS.txt.

After Step 0 is accepted, Step 1 must build the accepted source afresh and tie its evidence to its base commit plus source manifest. Step 0 does not rerun Maven or pytest.
