"""Capture the full one-hour official-source comparison set; never approve/send."""
import argparse
import base64
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import json
import os
from urllib import error, request
import news_radar as radar
from editorial_policy import digest


def collect_hour(feeds=None, fetcher=None, inspector=None, end=None, max_candidates=80):
    feeds = feeds or radar.FEEDS
    fetcher = fetcher or radar.fetch_feed
    inspector = inspector or radar.inspect_candidate_image
    end = (end or datetime.now(timezone.utc)).replace(second=0, microsecond=0)
    start = end - timedelta(hours=1)
    rows, coverage = [], []
    for feed in feeds:
        try:
            items = radar.extract_items(fetcher(feed), feed, strict=True, window_start=start, window_end=end)
            rows.extend(items)
            coverage.append({'feed_id': feed['id'], 'status': 'OK', 'parsed_items': len(items)})
        except radar.RadarError as exc:
            coverage.append({'feed_id': feed['id'], 'status': 'ERROR', 'reason': str(exc)})
    # No keyword prefilter or top-12 truncation before country impact comparison.
    rows = [r for r in rows if start <= radar.parse_time(r['published_at']) < end]
    candidates = radar.pick_candidates(rows, end, max_age_hours=1, limit=None,
                                       require_signal=False, group_attachments=False)
    truncated = len(candidates) > max_candidates
    candidates = candidates[:max_candidates]
    def inspect(row):
        try:
            return inspector(row)
        except Exception as exc:
            return {**row, 'body_fetch_status': 'UNAVAILABLE', 'inspection_error': type(exc).__name__}
    with ThreadPoolExecutor(max_workers=4) as pool:
        candidates = list(pool.map(inspect, candidates))
    parents = {}
    for parent in candidates:
        if parent.get('body_fetch_status') != 'FETCHED_FOR_REVIEW':
            continue
        for child in candidates:
            if (child['article_url'] in parent.get('linked_document_urls', [])
                    and child['title'] == parent['title'] and child['source'] == parent['source']
                    and child['published_at'] == parent['published_at']):
                parents.setdefault(child['article_url'], []).append(parent)
    attached = set()
    for child_url, linked_parents in parents.items():
        if len(linked_parents) == 1:
            linked_parents[0].setdefault('verified_attachment_urls', []).append(child_url)
            attached.add(child_url)
    candidates = [c for c in candidates if c['article_url'] not in attached]
    complete = (not truncated and all(c['status'] == 'OK' for c in coverage)
                and all(c.get('body_fetch_status') == 'FETCHED_FOR_REVIEW'
                        and c.get('source_text_truncated') is False for c in candidates))
    return {'status': 'COMPLETE' if complete else 'INCOMPLETE',
            'window_start': start.isoformat(), 'window_end': end.isoformat(),
            'captured_at': datetime.now(timezone.utc).isoformat(),
            'required_feed_ids': [f['id'] for f in feeds], 'coverage': coverage,
            'truncated': truncated, 'candidates': candidates,
            'assessments_status': 'UNREVIEWED', 'telegram_publishable': False,
            'ranking_scope': 'Configured official sources only; not a claim of global exhaustive coverage.'}


def store_edition(edition, env):
    if env.get('GITHUB_REF_NAME') != 'main':
        raise radar.RadarError('Only main can commit official hourly editions.')
    token, repo = env.get('GITHUB_TOKEN', ''), env.get('GITHUB_REPOSITORY', '')
    import re
    if not token or not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repo):
        raise radar.RadarError('GitHub credentials/repository missing.')
    ident = radar.parse_time(edition['window_end']).strftime('%Y%m%dt%H%Mz')
    path = 'news/editions/' + ident + '.json'
    payload = {'message': 'Capture unreviewed hourly official-source edition ' + ident,
               'branch': 'main', 'content': base64.b64encode(
                   (json.dumps(edition, ensure_ascii=False, indent=2) + '\n').encode()).decode()}
    req = request.Request('https://api.github.com/repos/' + repo + '/contents/' + path,
        json.dumps(payload).encode(), method='PUT', headers={'Authorization': 'Bearer ' + token,
        'Accept': 'application/vnd.github+json', 'Content-Type': 'application/json'})
    try:
        with request.urlopen(req, timeout=25) as reply:
            saved = json.load(reply)
        if not (saved.get('content') or {}).get('sha'):
            raise radar.RadarError('Edition commit was not acknowledged.')
    except error.HTTPError as exc:
        raise radar.RadarError('Hourly edition storage HTTP ' + str(exc.code) + '; no overwrite or send.') from None
    except (OSError, ValueError):
        raise radar.RadarError('Hourly edition storage uncertain; no send.') from None
    return path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=('dry-run', 'queue'), required=True)
    args = parser.parse_args()
    try:
        edition = collect_hour()
        path = store_edition(edition, os.environ) if args.mode == 'queue' else None
        print(json.dumps({'status': 'UNREVIEWED_HOURLY_EDITION', 'edition_path': path,
            'edition_sha256': digest(edition), 'edition': edition}, ensure_ascii=False))
        return 0 if edition['status'] == 'COMPLETE' else 2
    except radar.RadarError as exc:
        print(json.dumps({'status': 'HELD', 'reason': str(exc)}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
