"""Step 0 content/exclusion checks only; no build, runtime or product tests."""
import argparse, hashlib, json, re, subprocess, zipfile
from pathlib import Path, PurePosixPath

p = argparse.ArgumentParser()
p.add_argument('--repository', type=Path, required=True)
p.add_argument('--pack', type=Path, required=True)
p.add_argument('--architecture', type=Path, required=True)
p.add_argument('--roadmap', type=Path, required=True)
a = p.parse_args()
r = a.repository.resolve()
e = r / 'results/handoffs/step-00'
sha = lambda data: hashlib.sha256(data).hexdigest()
records = []
for args in [['git', '-C', str(r), 'rev-parse', '--show-toplevel'], ['git', '-C', str(r), 'remote', '-v']]:
    result = subprocess.run(args, capture_output=True, text=True)
    records.append({'argv': args, 'exit_code': result.returncode, 'stdout': result.stdout, 'stderr': result.stderr})
assert all(x['exit_code'] == 128 for x in records), 'Git state changed: inspect actual repository before continuing'
with zipfile.ZipFile(a.pack) as z:
    names = z.namelist()
    assert z.testzip() is None
    assert len(names) == len(set(names))
    assert all(not PurePosixPath(n).is_absolute() and '..' not in PurePosixPath(n).parts for n in names)
    checksum_rows = z.read('SHA256SUMS.txt').decode().splitlines()
    for line in checksum_rows:
        expected, name = line.split('  ', 1)
        assert sha(z.read(name)) == expected, name
    original = {n.removeprefix('checkpoint/cs4094-ms2/'): z.read(n) for n in names if n.startswith('checkpoint/cs4094-ms2/')}
    canonical = r / 'docs/CS4094_MS2_Architecture.md'
    assert canonical.read_bytes() == a.architecture.read_bytes() == z.read('sources/CS4094_MS2_Architecture.md')
    assert (r / 'docs/implementation-roadmap.md').read_bytes() == a.roadmap.read_bytes() == z.read('CS4094_MS2_Implementation_Roadmap.md')
    for name, data in original.items():
        destination = 'docs/CS4094_MS2_Architecture.md' if name == 'docs/approved-architecture.md' else name
        assert (r / destination).read_bytes() == data, destination
    assert not (r / 'docs/approved-architecture.md').exists()
    for name in names:
        if name.startswith('evidence/'):
            assert (e / 'historical' / name.removeprefix('evidence/')).read_bytes() == z.read(name)

base_paths = set(original) - {'docs/approved-architecture.md'}
base_paths.add('docs/CS4094_MS2_Architecture.md')
additional = {'.gitignore', 'docs/implementation-roadmap.md', 'docs/PROGRESS.md', 'docs/HANDOFF.md', 'docs/handoffs/step-00.md', 'docs/OPEN_ISSUES.md'}
excluded, candidates = [], []
for f in sorted(r.rglob('*')):
    if not f.is_file():
        continue
    rel = f.relative_to(r).as_posix()
    parts = PurePosixPath(rel).parts
    forbidden = any(x in {'target', '__pycache__', '.pytest_cache', '.runtime', 'runtime', '.venv', 'node_modules', 'toolchain', '.git'} for x in parts) or f.suffix in {'.class', '.jar', '.pyc', '.pem', '.key'} or f.name in {'maven-settings.xml', 'settings.xml', '.env', '.DS_Store', 'dependency-reduced-pom.xml'}
    if forbidden:
        excluded.append(rel)
        continue
    assert rel in base_paths | additional or rel.startswith('results/handoffs/step-00/'), 'Unreviewed extra file: ' + rel
    assert not f.is_symlink(), 'Candidate symlink: ' + rel
    candidates.append(rel)

rules = {
    'private_key_header': re.compile(rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE' + rb' KEY-----'),
    'github_token': re.compile(rb'gh[pousr]_' + rb'[A-Za-z0-9]{30,}'),
    'github_fine_grained_token': re.compile(rb'github_pat_' + rb'[A-Za-z0-9_]{40,}'),
    'aws_access_key': re.compile(rb'AK' + rb'IA[0-9A-Z]{16}'),
    'openai_key': re.compile(rb'sk-' + rb'(?:proj-)?[A-Za-z0-9_-]{40,}'),
}
findings = []
for rel in candidates:
    if Path(rel).suffix == '.mp4':
        continue  # Preserved workload fixture; verified byte-for-byte, not executable/configuration.
    data = (r / rel).read_bytes()
    for name, pattern in rules.items():
        if pattern.search(data):
            findings.append({'path': rel, 'rule': name})
assert not findings, 'Review potential secrets before import'
exclusion = {'excluded_local_files': excluded, 'excluded_count': len(excluded), 'secret_pattern_findings': findings, 'scope': 'explicit candidate allowlist; common credential signatures only, not proof against every possible secret', 'historical_log_machine_paths': 'retained as provenance text only; no proxy settings, toolchains, runtime objects or generated binaries included', 'git_index_exists': False, 'nothing_committed_or_pushed': True}
(e / 'exclusion-review.json').write_text(json.dumps(exclusion, indent=2) + '\n')
report = {'result': 'PASS for local Step 0 checks; shared baseline BLOCKED', 'archive_entries': len(names), 'archive_hash_entries_verified': len(checksum_rows), 'source_files_preserved': len(original), 'canonical_architecture_sha256': sha(canonical.read_bytes()), 'approved_roadmap_sha256': sha((r / 'docs/implementation-roadmap.md').read_bytes()), 'historical_evidence': 'byte-identical to supplied pack; exact tested source revision unknown', 'repository_checks': records, 'generated_builds_secrets_runtime_toolchains_proxy_files_promoted': False, 'architecture_changes': 'none', 'build_or_product_test_commands_run': [], 'git_commit_push_commands_run': []}
(e / 'verification.json').write_text(json.dumps(report, indent=2) + '\n')
all_candidates = sorted(set(candidates) | {'results/handoffs/step-00/exclusion-review.json', 'results/handoffs/step-00/verification.json'})
all_candidates = [x for x in all_candidates if not x.endswith('/candidate-SHA256SUMS.txt') and not x.endswith('/candidate-files.txt')]
(e / 'candidate-files.txt').write_text('\n'.join(all_candidates) + '\n')
(e / 'candidate-SHA256SUMS.txt').write_text(''.join(f'{sha((r / rel).read_bytes())}  {rel}\n' for rel in all_candidates))
print(json.dumps({'local_step0_checks': 'PASS', 'step0_status': 'BLOCKED', 'source_files_preserved': len(original), 'archive_hash_entries_verified': len(checksum_rows), 'excluded_local_files': len(excluded), 'candidate_file_count': len(all_candidates), 'secret_pattern_findings': 0, 'git_checks_exit_codes': [x['exit_code'] for x in records], 'new_builds_or_tests': 0, 'commits_or_pushes': 0}, indent=2))
