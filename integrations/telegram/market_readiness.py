"""Read-only market source readiness; never sends messages or approves prices."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
import os
from urllib import error, parse, request
from source_media import NoRedirect, public_https, public_dns, VisibleBody

SOURCES = (
    ('RO_BET_PAGE', 'https://www.bvb.ro/TradingAndStatistics/Trading/CurrentTradingDay'),
    ('RO_BET_SERVICE', 'https://ws.bvb.ro/BVBDelayedWS/Intraday.asmx/GetIndex?code=BET'),
    ('FR_CAC40_PAGE', 'https://live.euronext.com/en/product/indices/FR0003500008-XPAR'),
    ('US_NASDAQ_PAGE', 'https://www.nasdaq.com/market-activity/index/comp?as=json'),
)
MAX_RESPONSE = 800000


def assess_response(status, content_type, body):
    text = body[:MAX_RESPONSE].lower()
    if status in (401, 403) or any(x in text for x in
            (b'permission denied', b'permissiondenied', b'web page blocked', b'access denied')):
        state = 'PUBLISHER_ACCESS_DENIED'
    elif status != 200:
        state = 'HTTP_UNAVAILABLE'
    else:
        # Page title, generic quote widget and HTTP 200 are not authenticated
        # observations of instrument/value/as_of/session/delay/baseline.
        state = 'NO_VERIFIED_QUOTE'
    return {'status': state, 'http_status': status, 'content_type': content_type,
            'response_bytes': len(body), 'response_sha256': hashlib.sha256(body).hexdigest(),
            'truncated': len(body) > MAX_RESPONSE, 'publishable': False}


def credential_status(env):
    return {'TWELVE_DATA_API_KEY': {
        'configured': bool(env.get('TWELVE_DATA_API_KEY', '').strip()),
        'coverage_verified': False, 'redistribution_verified': False,
        'note': 'Presence alone does not verify BET/CAC40/US index coverage or rights.'}}


def probe(item):
    name, url = item
    result = {'source': name, 'url': url, 'publishable': False,
              'retrieved_at': datetime.now(timezone.utc).isoformat()}
    try:
        public_https(url)
        public_dns(parse.urlsplit(url).hostname)
        req = request.Request(url, headers={'User-Agent': 'WestcottMarketReadiness/1.0'})
        with request.build_opener(NoRedirect()).open(req, timeout=18) as reply:
            body = reply.read(MAX_RESPONSE + 1)
            result.update(assess_response(reply.status, reply.headers.get('Content-Type', ''), body))
            if name == 'RO_BET_PAGE' and reply.status == 200 and not result['truncated']:
                parser = VisibleBody()
                parser.feed(body.decode(reply.headers.get_content_charset() or 'utf-8', errors='replace'))
                text = ' '.join(' '.join(parser.parts).split())
                result.update(source_text_snapshot=text[:80000], source_text_truncated=len(text)>80000,
                    server_date=reply.headers.get('Date'), cache_age=reply.headers.get('Age'))
    except error.HTTPError as exc:
        result.update(assess_response(exc.code, exc.headers.get('Content-Type', ''),
                                      exc.read(MAX_RESPONSE + 1)))
    except Exception as exc:
        # Do not persist arbitrary exception text/credentials or publisher instructions.
        result.update(status='UNAVAILABLE', error_type=type(exc).__name__)
    return result


def main():
    with ThreadPoolExecutor(max_workers=4) as pool:
        checks = list(pool.map(probe, SOURCES))
    print(json.dumps({'status': 'NOT_READY', 'executed_at': datetime.now(timezone.utc).isoformat(),
        'purpose': 'Read-only diagnosis; no quote approval or Telegram delivery',
        'credentials': credential_status(os.environ), 'checks': checks,
        'required_before_release': ['verified instrument identity and point/price units',
            'source quote timestamp and delay, distinct from retrieval time',
            'exchange session/calendar and previous close baseline',
            'data coverage and redistribution authorization',
            'reviewed quote ledger and live recheck before existing publisher']}, ensure_ascii=False))


if __name__ == '__main__':
    main()
