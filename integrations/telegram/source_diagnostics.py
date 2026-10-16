"""Read-only source diagnostics. No Telegram credentials or calls."""
import concurrent.futures
import json
import urllib.request
import urllib.error
from datetime import datetime, timezone
from news_radar import FEEDS, fetch_feed
from source_media import inspect_article, public_https, public_dns
from urllib.parse import urlsplit

class StopRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

def probe(item):
    name, url, kind = item
    result = {'name': name, 'url': url, 'kind': kind}
    try:
        if kind == 'feed':
            result['normal_bytes'] = len(fetch_feed(next(f for f in FEEDS if f['id'] == name)))
        else:
            page = inspect_article(url)
            result.update(body_chars=len(page['source_text']),
                canonical=page.get('canonical'), canonical_matches_article=page.get('canonical_matches_article'))
        result['normal_status'] = 'OK'
    except Exception as exc:
        result.update(normal_status='ERROR', error_type=type(exc).__name__, error=str(exc)[:300])
    try:
        public_https(url)
        public_dns(urlsplit(url).hostname)
        req = urllib.request.Request(url, headers={'User-Agent': 'WestcottArticlePreview/1.0'})
        with urllib.request.build_opener(StopRedirect()).open(req, timeout=20) as reply:
            data = reply.read(2000001)
            result.update(http_status=reply.status, content_type=reply.headers.get('Content-Type'),
                response_bytes=len(data), response_truncated=len(data)>2000000)
    except urllib.error.HTTPError as exc:
        result.update(http_status=exc.code, location=exc.headers.get('Location'))
    except Exception as exc:
        result.update(network_error=type(exc).__name__, network_detail=str(exc)[:300])
    return result

if __name__ == '__main__':
    items = [(f['id'], f['url'], 'feed') for f in FEEDS]
    items += [('eurostat_product', 'https://ec.europa.eu/eurostat/product?code=2-16102026-ap', 'article'),
        ('eurostat_article', 'https://ec.europa.eu/eurostat/web/products-euro-indicators/w/2-16102026-ap', 'article'),
        ('insee_article', 'https://www.insee.fr/fr/statistiques/9078876', 'article')]
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(probe, items))
    print(json.dumps({'executed_at':datetime.now(timezone.utc).isoformat(), 'results':results}, ensure_ascii=False))
