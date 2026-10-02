# Remaining Docker verification — one external-host sequence

These commands are instructions, not results observed in Work. Docker/Compose,
a working Docker daemon, make, Python 3.12 and pytest from `requirements.txt` must
be available on the host. Run from this project's root in Bash. Do not use a
Docker shim or replace the Make recipes with native commands: the remaining gate
is the actual container execution path.

Use the unchanged implementation's source ID only after its manifest validates.
Every run label below is fresh. The explicit-label copy-back caveat remains
documented; this procedure never reuses a label. Run this entire sequence on one
host, and retain its command logs and exported histories. No Git action occurs.

```bash
set -eu
python3 -m tests.harness.check_evidence results/handoffs/step-10/native-strict/test_worker_crash_reassignment
sha256sum -c results/handoffs/step-10/source-SHA256SUMS.txt
docker compose version
docker info
python3 -m pytest --version
export MS2_SOURCE_REV='9bfd6d339d754475bcf218179f1cffdd4c07eeb3+local-step10:sha256:83c1d8789c58643c2ea74015008c38e4a058957e6b0a477f0bfe9b881e7c62ae'
cs4094_tag=$(python3 -c 'import uuid; print(uuid.uuid4().hex)')
export CS4094_EXTERNAL_EVIDENCE="results/handoffs/step-10/external-$cs4094_tag"
mkdir "$CS4094_EXTERNAL_EVIDENCE"
mkdir "$CS4094_EXTERNAL_EVIDENCE/checks"
export CS4094_COMPOSE_LABEL="step10-compose-$cs4094_tag"
export CS4094_ACCEPTANCE_LABEL="step10-acceptance-$cs4094_tag"
export CS4094_DEMO_LABEL="step10-fault-demo-$cs4094_tag"
record_step10() {
  cs4094_check=$1
  shift
  python3 -c 'import json,os,sys; print(json.dumps({"argv":sys.argv[1:],"cwd":os.getcwd(),"environment":{k:os.environ.get(k) for k in ["MS2_SOURCE_REV","MS2_RUN_LABEL","MS2_BACKEND","MS2_REQUIRE_XFAIL"]}},indent=2))' "$@" > "$CS4094_EXTERNAL_EVIDENCE/checks/$cs4094_check.command.json"
  if "$@" > "$CS4094_EXTERNAL_EVIDENCE/checks/$cs4094_check.log" 2>&1; then
    cs4094_exit=0
  else
    cs4094_exit=$?
  fi
  printf '%s\n' "$cs4094_exit" > "$CS4094_EXTERNAL_EVIDENCE/checks/$cs4094_check.exit.txt"
  return "$cs4094_exit"
}
record_step10 compose-build docker compose -f deploy/compose/compose.yaml build
MS2_BACKEND=compose MS2_REQUIRE_XFAIL=1 MS2_RUN_LABEL="$CS4094_COMPOSE_LABEL" record_step10 compose-strict python3 -m pytest -q tests/faults/test_worker_crash.py
MS2_RUN_LABEL="$CS4094_ACCEPTANCE_LABEL" record_step10 make-test make test
if MS2_RUN_LABEL="$CS4094_DEMO_LABEL" record_step10 make-fault-demo make fault-demo; then
  printf '%s\n' 'Unexpected fault-demo success: stop and inspect.' >&2
  exit 1
fi
# The captured nonzero alone is insufficient: verify why it failed.
python3 - <<'CHECK_AND_RETAIN'
import json, os, pathlib, shutil
from tests.harness.check_evidence import check_directory
out=pathlib.Path(os.environ['CS4094_EXTERNAL_EVIDENCE'])
labels=[os.environ[k] for k in ['CS4094_COMPOSE_LABEL','CS4094_ACCEPTANCE_LABEL','CS4094_DEMO_LABEL']]
report=[]
for index,label in enumerate(labels):
    run=pathlib.Path('results/latest-tests')/label
    metadata=sorted(run.glob('*/metadata.json'))
    assert metadata, f'Missing metadata: {run}'
    xfails=[]
    for path in metadata:
        m=json.loads(path.read_text())
        assert m['cleanup_succeeded'] is True, path
        assert m['source_revision']==os.environ['MS2_SOURCE_REV'], path
        if m['xfail']: xfails.append(m['test'])
        is_fault=path.parent.name=='test_worker_crash_reassignment'
        if index==2:
            assert is_fault and not m['xfail'] and m['outcome']=='failed', path
        elif is_fault:
            assert m['xfail'] and m['outcome']=='skipped', path
        else:
            assert m['outcome']=='passed' and not m['xfail'], path
        jobs=check_directory(path.parent)
        if is_fault:
            assert len(jobs)==2, path
            trace=(path.parent/'oracle-traceback.txt').read_text()
            assert 'test_worker_crash.RecoveryNotObserved:' in trace, path
            fault=json.loads((path.parent/'fault.json').read_text())
            assert fault['signal']=='SIGKILL', path
            assert fault['exit_code']==(137 if index==0 else -9), path
            safety=json.loads((path.parent/'safety-checks.json').read_text())
            assert safety['history_check']=='PASS' and safety['b_session_distinct'] and safety['a_dead'] and safety['b_alive'] and safety['services_healthy'] and safety['faulted_attempt_unchanged'], path
        report.append({'run':label,'test':m['test'],'jobs_checked':len(jobs),'cleanup_succeeded':True})
    assert len(xfails)==(0 if index==2 else 1), (label,xfails)
    if index in (0,2):assert len(metadata)==1
    destination=out/label
    assert not destination.exists(), destination
    shutil.copytree(run,destination,ignore=shutil.ignore_patterns('runtime','__pycache__','.pytest_cache','target'))
# Distinguish the real demo's sole oracle failure from setup/cleanup errors.
demo=(out/'checks/make-fault-demo.log').read_text()
assert 'RecoveryNotObserved' in demo and '1 failed' in demo
assert not __import__('re').search(r'\b\d+ errors?\b',demo)
assert int((out/'checks/make-fault-demo.exit.txt').read_text())!=0
(out/'retained-evidence-check.json').write_text(json.dumps(report,indent=2)+'\n')
print('Retained',len(report),'test evidence directories; histories and cleanup passed.')
CHECK_AND_RETAIN
python3 -m tests.harness.check_evidence "$CS4094_EXTERNAL_EVIDENCE/$CS4094_COMPOSE_LABEL"/*/ "$CS4094_EXTERNAL_EVIDENCE/$CS4094_ACCEPTANCE_LABEL"/*/ "$CS4094_EXTERNAL_EVIDENCE/$CS4094_DEMO_LABEL"/*/ > "$CS4094_EXTERNAL_EVIDENCE/retained-offline.log" 2>&1
```

Inspect the complete command logs before marking Step 10 complete: Compose must
show exactly one typed XFAIL; actual `make test` must show passing JUnit and
ordinary pytest counts, exactly one expected XFAIL and no XPASS/errors; actual
`make fault-demo` must show only the final RecoveryNotObserved failure. Record
actual counts and Make exit code in coordination documents. The function returns
actual command status; the demo's expected nonzero is retained and examined, not
silenced by an unconditional success expression. The safety evidence JSON does
not replace inspection of raw events/snapshots, which remain in each run.

If any stage fails for a different reason, keep Step 10 BLOCKED, retain partial
logs/evidence, diagnose only that concrete problem and use new labels on retries.
No new source edits are needed merely to run this sequence. Do not begin Step 11.
