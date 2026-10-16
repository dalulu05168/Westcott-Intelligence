"""Capture the full one-hour official-source comparison set; never approve/send."""
import argparse
import base64
import hashlib
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import json
import os
from urllib import error, request
import news_radar as radar
from editorial_policy import digest


def feed_window_evidence(feed_xml, start, end):
    """Explain the window filter after strict feed validation; no approval."""
    root = radar.ET.fromstring(feed_xml)
    entries = root.findall('.//item')
    date_tags = ['pubDate', '{http://purl.org/dc/elements/1.1/}date']
    if not entries:
        entries = root.findall('{http://www.w3.org/2005/Atom}entry')
        date_tags = ['{http://www.w3.org/2005/Atom}published',
                     '{http://www.w3.org/2005/Atom}updated']
    stamps = [radar.parse_time(radar.first_text(node, date_tags)) for node in entries]
    return {
        'feed_sha256': hashlib.sha256(feed_xml).hexdigest(),
        'raw_entries': len(entries),
        'latest_published_at': max(stamps).isoformat(),
        'excluded_before_window': sum(stamp < start for stamp in stamps),
        'excluded_at_or_after_end': sum(stamp >= end for stamp in stamps),
        'in_window_entries': sum(start <= stamp < end for stamp in stamps),
    }


def collect_hour(feeds=None, fetcher=None, inspector=None, end=None, max_candidates=80):
    feeds = feeds or radar.FEEDS
    fetcher = fetcher or radar.fetch_feed
    inspector = inspector or radar.inspect_candidate_image
    end = (end or datetime.now(timezone.utc)).replace(second=0, microsecond=0)
    start = end - timedelta(hours=1)
    rows, coverage = [], []
    for feed in feeds:
        try:
            feed_xml = fetcher(feed)
            retrieved_at = datetime.now(timezone.utc).isoformat()
            items = radar.extract_items(feed_xml, feed, strict=True, window_start=start, window_end=end)
            rows.extend(items)
            coverage.append({'feed_id': feed['id'], 'status': 'OK', 'parsed_items': len(items),
                             'feed_url': feed['url'], 'retrieved_at': retrieved_at,
                             **feed_window_evidence(feed_xml, start, end)})
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
    # A cover-page link proves association, not equivalent disclosure content.
    # Keep PDF bodies independently visible and required for a complete comparison.
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



def readable_readiness(edition, edition_path=None):
    """Compact CI report; full source evidence remains stored in the edition file.

    Never dump large publisher bodies into Action logs, but identify which
    original evidence was unavailable so maintainers can actually fix it.
    """
    candidates = edition.get('candidates', [])
    unavailable = []
    for row in candidates:
        if (row.get('body_fetch_status') != 'FETCHED_FOR_REVIEW'
                or row.get('source_text_truncated') is not False):
            unavailable.append({
                'candidate_id': row.get('id'),
                'source': row.get('source'),
                'official_url': row.get('article_url'),
                'reason': row.get('body_fetch_error') or row.get('inspection_error')
                          or row.get('body_fetch_status') or 'UNVERIFIED',
            })
    feeds_failed = [{
        'feed_id': row.get('feed_id'),
        'status': row.get('status'),
        'reason': row.get('reason'),
    } for row in edition.get('coverage', []) if row.get('status') != 'OK']
    return {
        'status': 'OFFICIAL_HOURLY_EDITION_READINESS',
        'edition_status': edition.get('status'),
        'edition_path': edition_path,
        'edition_sha256': digest(edition),
        'time_window': {'start': edition.get('window_start'),
                        'end': edition.get('window_end')},
        'configured_sources': len(edition.get('required_feed_ids', [])),
        'sources_healthy': sum(row.get('status') == 'OK'
                               for row in edition.get('coverage', [])),
        'candidates_total': len(candidates),
        'candidates_unverified': len(unavailable),
        'unverified_details': unavailable,
        'feed_failures': feeds_failed,
        'source_windows': edition.get('coverage', []),
        'truncated': edition.get('truncated'),
        'assessments_status': edition.get('assessments_status'),
        'telegram_publishable': False,
        'messages_sent': 0,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=('dry-run', 'queue'), required=True)
    args = parser.parse_args()
    try:
        edition = collect_hour()
        path = store_edition(edition, os.environ) if args.mode == 'queue' else None
        print(json.dumps(readable_readiness(edition, path), ensure_ascii=False))
        return 0 if edition['status'] == 'COMPLETE' else 2
    except radar.RadarError as exc:
        print(json.dumps({'status': 'HELD', 'reason': str(exc)}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
