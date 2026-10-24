"""Export allowlisted repository evidence. No credentials, sending or adoption."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
from datetime import datetime, timezone
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]


def build(root=ROOT, commit=None):
    manifest = []
    def read(path):
        raw = (root / path).read_bytes()
        manifest.append({'path': path, 'sha256': hashlib.sha256(raw).hexdigest()})
        return raw.decode('utf-8-sig')
    def obj(path):
        return json.loads(read(path))
    if not commit:
        commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
        # Local changes must not masquerade as a clean committed revision.
        dirty = bool(subprocess.check_output(['git', 'status', '--porcelain'], cwd=root, text=True).strip())
    else:
        dirty = False
    rules = obj('memory/user-rules/confirmed-20261024.json')
    identity = obj('skills/p004-chat-suite/characters/final-identity-65.json')['people']
    voice = obj('skills/p004-chat-suite/voice-management/voice-index-2026-10-21.json')
    members = []
    for person in identity:
        mid = person['id']
        profile = obj(f'skills/p004-chat-suite/characters/profiles/{mid}.json')
        memory_path = f'memory/long-term/members/{mid}.json'
        memory = obj(memory_path) if (root / memory_path).exists() else None
        evidence = next((m for m in voice['members'] if m['id'] == mid), None)
        members.append({'identity': person, 'profile_draft': profile, 'voice_snapshot': evidence,
                        'long_term': memory, 'source_path': memory_path if memory else None})
    skills = {role: read(f'skills/p004-{role}/SKILL.md')
              for role in ['director', 'writer', 'teacher', 'assistant', 'members']}
    days = []
    for file in sorted((root / 'memory/daily').glob('*/day-memory.json')):
        path = file.relative_to(root).as_posix()
        days.append({'path': path, 'snapshot': obj(path)})
    editions = []
    for file in sorted((root / 'news/editions').glob('*.json'))[-250:]:
        path = file.relative_to(root).as_posix()
        editions.append({'path': path, 'edition': obj(path)})
    return {'schema': 'westcott.repository-export.v1', 'repository': 'dalulu05168/Westcott-Intelligence',
            'commit': commit, 'dirty_worktree': dirty, 'exported_at': datetime.now(timezone.utc).isoformat(),
            'rules': rules, 'skills': skills, 'members': members, 'days': days, 'news_editions': editions,
            'voice_source': voice['source_doc'], 'manifest': manifest,
            'boundaries': ['Repository archive, not live Google Docs.',
                           'Profile voices are drafts; observed quotes are dated story evidence.',
                           'News intake and image candidates are UNREVIEWED, not verified facts.',
                           'No real trades, external messages or adoption are implied.']}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--output', required=True)
    p.add_argument('--sync', action='store_true')
    args = p.parse_args()
    data = build(commit=os.environ.get('GITHUB_SHA'))
    payload = json.dumps(data, ensure_ascii=False, separators=(',', ':')).encode()
    Path(args.output).write_bytes(payload)
    print(f'Exported {len(data["members"])} identities, {len(data["days"])} dated snapshots; {len(payload)} bytes.')
    if args.sync:
        key = os.environ.get('WESTCOTT_SOURCE_SYNC_KEY', '')
        if len(key) < 32:
            raise SystemExit('Sync credential missing; export prepared but not delivered.')
        req = Request('https://westcott-source-bridge.dalulu05168.workers.dev/internal/repository', payload,
                      headers={'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json'}, method='POST')
        with urlopen(req, timeout=60) as response:
            receipt = json.load(response)
        if receipt.get('stored') is not True or receipt.get('commit') != data['commit']:
            raise SystemExit('No matching storage receipt; delivery not confirmed.')
        print('Repository export acknowledged: ' + receipt['commit'])


if __name__ == '__main__':
    main()
