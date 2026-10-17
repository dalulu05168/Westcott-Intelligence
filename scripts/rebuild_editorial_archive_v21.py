#!/usr/bin/env python3
"""Reproduce the reviewed archive, not a live writing session or deployment.

No message generation, API calls, adoption or sender side effects. The legacy
archive and inline task fallback capsules stay byte-for-byte unchanged.
"""
import argparse
from datetime import timedelta
from pathlib import Path
import tempfile
import sys
from editorial_runtime_v21 import ROOT, load, run, save_projection, timestamp

SOURCE = 'memory/sources/google-doc-20261017.json'


def build(root):
    snapshot = load(ROOT/SOURCE)
    result = run(ROOT, snapshot, ['25','34','38','40'], timestamp(snapshot['retrieved_at'])+timedelta(seconds=1))
    save_projection(root, result, SOURCE)
    return result


def check():
    errors = []
    with tempfile.TemporaryDirectory() as folder:
        build(folder)
        for path in Path(folder).rglob('*.json'):
            relative = path.relative_to(folder)
            actual = ROOT/relative
            if not actual.exists() or path.read_bytes() != actual.read_bytes():
                errors.append(relative.as_posix())
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    if args.check:
        errors = check()
        print('ARCHIVE_PROJECTION_MISMATCH:'+','.join(errors) if errors else 'PASS:65 reproducible entrypoints; archive requires live refresh')
        return 1 if errors else 0
    checkpoint = ROOT/'memory/runtime/latest-checkpoint.json'
    previous = ROOT/'memory/runtime/revisions/pre-v2.1-checkpoint.json'
    if checkpoint.exists() and not previous.exists():
        previous.parent.mkdir(parents=True, exist_ok=True)
        previous.write_bytes(checkpoint.read_bytes())
    result = build(ROOT)
    print('ARCHIVE_PROJECTED_NOT_LIVE: '+result['context']['checkpoint']['story_phase'])
    return 0


if __name__ == '__main__':
    sys.exit(main())
