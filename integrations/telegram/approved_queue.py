"""Drain reviewed ledgers only. No candidate can promote itself to approved."""
import json
import hashlib
import os
from pathlib import Path
import reviewed_publish as publisher


def drain(root, env):
    results = []
    # Persisted delivered AND ambiguous attempts are terminal for an identical
    # ledger. A fresh checkout must not retry yesterday's successful release.
    terminal = set()
    for audit in (root / 'audit/telegram-delivery').glob('*.json'):
        record = json.loads(audit.read_text(encoding='utf-8'))
        if record.get('ledger') and record.get('ledger_digest'):
            terminal.add((record['ledger'], record['ledger_digest']))
    for path in sorted((root / 'news/approved').glob('*.json')):
        relative = path.relative_to(root).as_posix()
        try:
            ledger = json.loads(path.read_text(encoding='utf-8'))
            digest = hashlib.sha256(json.dumps(ledger, ensure_ascii=False, sort_keys=True).encode('utf-8')).hexdigest()
            if (relative, digest) in terminal:
                results.append({'ledger': relative, 'status': 'ALREADY_RESERVED'})
                continue
            prepared = publisher.prepare(ledger, relative)
            audit = root / 'audit/telegram-delivery' / (prepared['fingerprint'][:40] + '.json')
            if audit.exists():
                results.append({'ledger': relative, 'status': 'ALREADY_RESERVED'})
                continue
            receipt = publisher.publish(prepared, env)
            results.append({'ledger': relative, **receipt})
        except (publisher.PublicationError, ValueError, KeyError, TypeError, OSError) as exc:
            results.append({'ledger': relative, 'status': 'HELD', 'reason': str(exc)})
    return results


if __name__ == '__main__':
    results = drain(Path(__file__).resolve().parents[2], os.environ)
    print(json.dumps({'status': 'REVIEWED_QUEUE_CHECKED', 'results': results}, ensure_ascii=False))
    raise SystemExit(1 if any(r['status'] == 'HELD' for r in results) else 0)
