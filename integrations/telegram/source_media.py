"""Inspect original publisher Open Graph image metadata; never generates or copies images."""
import html
import hashlib
from html.parser import HTMLParser
import ipaddress
import socket
import subprocess
import tempfile
from pathlib import Path
import urllib.error
import urllib.parse
import urllib.request

MAX_HTML = 2_097_152
MAX_PDF_TEXT = 262_144
MAX_PDF = 6_000_000


def pdf_markup(content):
    """Extract real PDF text for comparison; never turn a PDF page into a photo."""
    if not content.startswith(b'%PDF-') or len(content) > MAX_PDF:
        raise SourceMediaError('Invalid or oversized original PDF.')
    try:
        with tempfile.TemporaryDirectory(prefix='westcott-pdf-') as directory:
            source, target = Path(directory) / 'source.pdf', Path(directory) / 'body.txt'
            source.write_bytes(content)
            subprocess.run(['pdftotext', '-enc', 'UTF-8', str(source), str(target)],
                           check=True, timeout=15, capture_output=True)
            if target.stat().st_size > MAX_PDF_TEXT:
                raise SourceMediaError('Original PDF text exceeds review limit.')
            text = ' '.join(target.read_text(encoding='utf-8').split())
    except (OSError, subprocess.SubprocessError, UnicodeError):
        raise SourceMediaError('Original PDF text unavailable; scanned/encrypted files require review.') from None
    if len(text) < 80 or text.count('\ufffd') > len(text) // 100:
        raise SourceMediaError('Original PDF has insufficient readable text.')
    return '<html><head><title>Original official PDF</title></head><body><article>' + html.escape(text) + '</article></body></html>'


class SourceMediaError(ValueError):
    pass


def public_https(value):
    if not isinstance(value, str) or not 0 < len(value) <= 2048:
        raise SourceMediaError("Source URL must be a nonempty HTTPS URL.")
    if any(ord(c) < 33 for c in value):
        raise SourceMediaError("Whitespace/control characters in URL.")
    url = urllib.parse.urlsplit(value)
    if url.scheme != "https" or not url.hostname or url.username or url.password or url.fragment:
        raise SourceMediaError("Only public HTTPS URLs without credentials or fragments are allowed.")
    try:
        if url.port not in (None, 443):
            raise SourceMediaError("Nonstandard URL port.")
    except ValueError:
        raise SourceMediaError("Malformed URL port.") from None
    host = url.hostname.rstrip(".").lower()
    if not host or "." not in host or host.endswith((".local", ".internal", ".localhost")):
        raise SourceMediaError("Nonpublic hostname.")
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        if not ip.is_global:
            raise SourceMediaError("Nonpublic IP address.")
    return value


def public_dns(hostname):
    """Fail closed for private resolutions; does not claim DNS answers are permanent."""
    try:
        addresses = socket.getaddrinfo(hostname, 443, type=socket.SOCK_STREAM)
    except OSError:
        raise SourceMediaError("Publisher hostname cannot be resolved.") from None
    if not addresses:
        raise SourceMediaError("Publisher hostname has no addresses.")
    for addr in addresses:
        try:
            if not ipaddress.ip_address(addr[4][0]).is_global:
                raise SourceMediaError("Publisher hostname resolves to private address.")
        except ValueError:
            raise SourceMediaError("Bad publisher address.") from None


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise SourceMediaError("Publisher redirected; use a separately verified final article URL.")


def fetch_original_article(url, opener=None):
    url = public_https(url)
    public_dns(urllib.parse.urlsplit(url).hostname)
    handler = opener or urllib.request.build_opener(NoRedirect())
    request = urllib.request.Request(
        url, headers={"User-Agent": "WestcottArticlePreview/1.0",
                      "Accept": "text/html,application/xhtml+xml,application/pdf;q=0.9"}, method="GET")
    try:
        with handler.open(request, timeout=12) as response:
            content_type = response.headers.get("Content-Type", "").lower()
            if 'application/pdf' in content_type or urllib.parse.urlsplit(url).path.lower().endswith('.pdf'):
                return pdf_markup(response.read(MAX_PDF + 1))
            if not ("text/html" in content_type or "application/xhtml+xml" in content_type):
                raise SourceMediaError("Original article response is not HTML.")
            content = response.read(MAX_HTML + 1)
            if len(content) > MAX_HTML:
                raise SourceMediaError("Original article metadata exceeds safe page size.")
            encoding = response.headers.get_content_charset() or "utf-8"
            try:
                return content.decode(encoding, errors="replace")
            except LookupError:
                raise SourceMediaError("Unsupported publisher character encoding.") from None
    except SourceMediaError:
        raise
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError, ValueError):
        raise SourceMediaError("Original article could not be inspected (restricted/blocked/network).") from None


class HeadMetadata(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.meta = {}
        self.canonical = None
        self.title = ""
        self.in_title = False
        self.in_head = True

    def handle_starttag(self, tag, attrs):
        if not self.in_head:
            return
        attributes = {k.lower(): v for k, v in attrs if k and isinstance(v, str)}
        if tag == "meta":
            key = (attributes.get("property") or attributes.get("name") or "").lower()
            val = attributes.get("content", "").strip()
            if key and val and key not in self.meta:
                self.meta[key] = val
        elif tag == "link" and "canonical" in attributes.get("rel", "").lower().split():
            self.canonical = self.canonical or attributes.get("href")
        elif tag == "title":
            self.in_title = True

    def handle_data(self, data):
        if self.in_title:
            self.title += data

    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False
        if tag == "head":
            self.in_head = False


class VisibleBody(HTMLParser):
    """Extract a review snapshot, never certify the claims it contains."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ignored = []
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag in ('head', 'script', 'style', 'noscript', 'template'):
            self.ignored.append(tag)

    def handle_endtag(self, tag):
        if self.ignored and tag == self.ignored[-1]:
            self.ignored.pop()
        elif not self.ignored:
            self.parts.append(' ')

    def handle_data(self, data):
        if not self.ignored:
            self.parts.append(data)


class ArticleImages(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.depth = 0
        self.excluded = 0
        self.images = []

    def handle_starttag(self, tag, attrs):
        if tag in ('article', 'main'):
            self.depth += 1
        if tag in ('nav', 'header', 'footer', 'script', 'noscript'):
            self.excluded += 1
        if tag == 'img' and self.depth and not self.excluded:
            data = dict(attrs)
            src = data.get('src') or data.get('data-src')
            if src:
                self.images.append({'url': src, 'alt': data.get('alt', ''),
                                    'origin': 'original_article_body'})

    def handle_endtag(self, tag):
        if tag in ('article', 'main'):
            self.depth = max(0, self.depth - 1)
        if tag in ('nav', 'header', 'footer', 'script', 'noscript'):
            self.excluded = max(0, self.excluded - 1)


class LinkedDocuments(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.urls = []

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            href = dict(attrs).get('href', '')
            if urllib.parse.urlsplit(href).path.lower().endswith('.pdf'):
                self.urls.append(href)


def inspect_markup(article_url, markup):
    article_url = public_https(article_url)
    parser = HeadMetadata()
    parser.feed(markup[:MAX_HTML])
    canonical = parser.canonical or parser.meta.get("og:url")
    # A canonical URL mismatch is a signal for human review, not evidence of identity.
    canonical = urllib.parse.urljoin(article_url, canonical) if canonical else None
    canonical_valid = False
    if canonical:
        try:
            canonical = public_https(canonical)
            article = urllib.parse.urlsplit(article_url)
            canon = urllib.parse.urlsplit(canonical)
            canonical_valid = (article.hostname == canon.hostname and
                               article.path.rstrip("/") == canon.path.rstrip("/") and
                               article.query == canon.query)
        except SourceMediaError:
            canonical = None
    origin = None
    origin_key = None
    for key in ("og:image:secure_url", "og:image", "twitter:image"):
        if parser.meta.get(key):
            possible = urllib.parse.urljoin(article_url, html.unescape(parser.meta[key]))
            try:
                origin = public_https(possible)
                origin_key = key
                break
            except SourceMediaError:
                continue
    body = VisibleBody()
    body.feed(markup[:MAX_HTML])
    source_text = ' '.join(''.join(body.parts).split())
    images = ArticleImages()
    images.feed(markup[:MAX_HTML])
    body_images, seen_images = [], set()
    for item in images.images:
        try:
            url = public_https(urllib.parse.urljoin(article_url, item['url']))
        except SourceMediaError:
            continue
        if url not in seen_images:
            body_images.append({**item, 'url': url})
            seen_images.add(url)
    documents = LinkedDocuments()
    documents.feed(markup[:MAX_HTML])
    linked_docs = []
    for href in documents.urls:
        try:
            document_url = urllib.parse.urljoin(article_url, href).replace(' ', '%20')
            parts = urllib.parse.urlsplit(document_url)
            if parts.scheme in ('http', 'https') and parts.netloc in ('bvb.ro', 'www.bvb.ro'):
                document_url = urllib.parse.urlunsplit(('https', 'bvb.ro', parts.path, parts.query, parts.fragment))
            linked_docs.append(public_https(document_url))
        except SourceMediaError:
            continue
    return {
        "linked_document_urls": sorted(set(linked_docs)),
        "article_image_candidates": body_images,
        "source_text": source_text,
        "source_text_sha256": hashlib.sha256(source_text.encode('utf-8')).hexdigest(),
        "article_url": article_url,
        "title": (parser.meta.get("og:title") or parser.meta.get("twitter:title")
                  or parser.title).strip()[:300],
        "canonical_url": canonical,
        "canonical_matches_article": canonical_valid if canonical else None,
        "image_candidate_url": origin,
        "image_metadata_field": origin_key,
        "verified_for_reuse": False,
        "inspection_note": (
            "Original-page metadata only; a candidate is NOT proof of story-image "
            "accuracy or reproduction permission. Human review required."
        ),
    }


def inspect_article(article_url, fetcher=None):
    markup = (fetcher or fetch_original_article)(article_url)
    return inspect_markup(article_url, markup)

def inspect_news_url(value, fetcher=None):
    """Accept either publisher article URLs or direct publisher-hosted image URLs.

    A direct image URL is recognized as such without attempting HTML parsing.
    It is NOT proof the image belongs to any particular news report, that
    the bytes are retrievable, or that it can legally be republished.
    """
    value = public_https(value)
    path = urllib.parse.urlsplit(value).path.lower()
    extensions = (".jpg", ".jpeg", ".png", ".webp", ".gif", ".avif")
    if path.endswith(extensions):
        return {
            "status": "IMAGE_URL_RECOGNIZED",
            "input_type": "direct_image_url",
            "image_candidate_url": value,
            "article_url": None,
            "image_url_syntax_checked": True,
            "image_bytes_checked": False,
            "matches_news_article": False,
            "verified_for_reuse": False,
            "inspection_note": (
                "This is an image URL, not a news article. URL form recognized; "
                "no news-to-image match or reproduction permission was verified."
            ),
        }
    return {"status": "ARTICLE_METADATA_INSPECTED",
            "input_type": "article_url",
            **inspect_article(value, fetcher=fetcher)}


def main():
    import argparse
    import json
    parser = argparse.ArgumentParser(description="Inspect publisher article metadata or recognize a direct news image URL")
    parser.add_argument("--article-url", required=True)
    args = parser.parse_args()
    try:
        metadata = inspect_news_url(args.article_url)
        print(json.dumps(metadata, ensure_ascii=False))
        return 0
    except SourceMediaError as exc:
        print(json.dumps({"status": "UNAVAILABLE", "reason": str(exc)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())


