"""Merge recorded free web discoveries into an existing comparison, never approve/send.

The caller must actually perform the searches. This records their scope, not a
claim of exhaustive worldwide coverage or proof that a publisher is official.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
from datetime import timedelta

from editorial_policy import digest, instant
from news_radar import inspect_candidate_image, pick_candidates
from source_media import public_https

ROOT = Path(__file__).resolve().parents[2]
REGIONS = {'RO', 'FR', 'US', 'GLOBAL'}


def merge_search(edition, manifest, inspector=None, max_candidates=80):
    inspector = inspector or inspect_candidate_image
    searches = manifest.get('searches', [])
    start, end = instant(edition['window_start']), instant(edition['window_end'])
    if end - start != timedelta(hours=1):
        raise ValueError('Existing comparison must cover exactly one hour')
    if (not isinstance(searches, list) or not searches
            or {s.get('region') for s in searches} != REGIONS
            or any(s.get('status') != 'OK' or not str(s.get('query', '')).strip()
                   or not start <= instant(s['searched_at']) <= end + timedelta(minutes=20)
                   for s in searches)):
        raise ValueError('Complete recorded regional search required; errors cannot mean no news')
    articles = manifest.get('articles')
    if not isinstance(articles, list) or len(articles) > max_candidates:
        raise ValueError('Invalid article list or candidate limit exceeded')
    result = copy.deepcopy(edition)
    rows = result['candidates']
    seen = {r['article_url'] for r in rows}
    excluded = []
    for item in articles:
        url = public_https(item['article_url'])
        basis = public_https(item['publisher_basis_url'])
        published = instant(item['published_at'])
        if not str(item.get('source', '')).strip() or not str(item.get('title', '')).strip():
            raise ValueError('Discovery must identify publisher and title')
        if not start <= published < end:
            excluded.append({'article_url': url, 'published_at': item['published_at'],
                             'reason': 'OUTSIDE_WINDOW'})
            continue
        if url in seen:
            continue
        if len(rows) >= max_candidates:
            raise ValueError('Combined candidate limit exceeded; do not truncate ranking')
        seen.add(url)
        candidate = pick_candidates([{
            'article_url': url, 'published_at': published.isoformat(),
            'title': item['title'], 'source': item['source'],
            'feed_id': 'web_discovery', 'publisher_basis_url': basis,
            'source_authority_status': 'REQUIRES_INDEPENDENT_REVIEW',
        }], now=end, max_age_hours=1, limit=None,
            require_signal=False, group_attachments=False)[0]
        try:
            captured = inspector(candidate)
        except Exception as exc:
            captured = {**candidate, 'body_fetch_status': 'UNAVAILABLE',
                        'inspection_error': type(exc).__name__}
        # Inspection cannot promote the candidate, replace its identity/time,
        # or make a caller-supplied official-publisher assertion authoritative.
        captured.update({k: candidate[k] for k in candidate})
        rows.append(captured)
    bodies_complete = all(
        r.get('body_fetch_status') == 'FETCHED_FOR_REVIEW'
        and r.get('source_text_truncated') is False
        and isinstance(r.get('source_text_snapshot'), str)
        and bool(r['source_text_snapshot'].strip())
        and hashlib.sha256(r['source_text_snapshot'].encode()).hexdigest()
            == r.get('source_text_sha256') for r in rows)
    result['status'] = ('COMPLETE' if edition.get('status') == 'COMPLETE'
                        and not edition.get('truncated') and bodies_complete else 'INCOMPLETE')
    result['assessments_status'] = 'UNREVIEWED'
    result['telegram_publishable'] = False
    result['search_intake'] = {'manifest': copy.deepcopy(manifest),
                               'manifest_sha256': digest(manifest), 'excluded': excluded}
    result['ranking_scope'] = ('Configured feeds plus explicitly recorded web-search discoveries; '
                               'not exhaustive worldwide coverage; publisher authority unverified.')
    return result


def local_path(value, directory):
    path = (ROOT / value).resolve()
    if not path.is_relative_to(ROOT / directory) or path.suffix != '.json':
        raise ValueError('Expected JSON under ' + directory)
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--edition', required=True)
    parser.add_argument('--manifest', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    edition = local_path(args.edition, 'news/editions')
    manifest = local_path(args.manifest, 'news/searches')
    output = local_path(args.output, 'news/editions')
    if output.exists():
        raise ValueError('Output already exists; never overwrite comparison evidence')
    merged = merge_search(json.loads(edition.read_text(encoding='utf-8')),
                          json.loads(manifest.read_text(encoding='utf-8')))
    with output.open('x', encoding='utf-8') as handle:
        json.dump(merged, handle, ensure_ascii=False, indent=2)
        handle.write('\n')
    print(json.dumps({'status': merged['status'], 'candidates': len(merged['candidates']),
                      'output': args.output, 'telegram_publishable': False}))


if __name__ == '__main__':
    main()
