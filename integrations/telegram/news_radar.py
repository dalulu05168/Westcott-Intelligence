"""Official-feed candidate collector. NO ChatGPT task access and NO Telegram send.

Creates UNREVIEWED queue items only: an RSS headline is not evidence that a
market claim is true, nor that its image is safe to repost.
"""
import argparse
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
import hashlib
import html
import ipaddress
import json
import os
import re
import socket
import sys
from urllib import error, parse, request
import xml.etree.ElementTree as ET

FEEDS = (
    {"id": "fed_monetary", "source": "US Federal Reserve",
     "url": "https://www.federalreserve.gov/feeds/press_monetary.xml",
     "article_hosts": ("www.federalreserve.gov", "federalreserve.gov")},
    {"id": "ecb_press", "source": "European Central Bank",
     "url": "https://www.ecb.europa.eu/rss/press.html",
     "article_hosts": ("www.ecb.europa.eu", "ecb.europa.eu")},
)
MAX_FEED_BYTES = 1_200_000
MAX_PER_CYCLE = 12
MAX_AGE_HOURS = 36
SIGNAL = (
    "interest rate", "monetary policy", "federal funds", "bank", "fomc",
    "inflation", "financial stability", "deposit facility",
    "refinancing", "asset purchases", "rate decision", "liquidity",
    "policy decision", "rate cut", "rate increase", "emergency",
)


class RadarError(ValueError):
    pass


def check_url(value, hosts):
    if not isinstance(value, str) or len(value) > 2048 or any(ord(c) < 33 for c in value):
        raise RadarError("Invalid feed article URL.")
    x = parse.urlsplit(value)
    if x.scheme != "https" or x.username or x.password or x.fragment or not x.hostname:
        raise RadarError("Only exact-source HTTPS news pages may enter queue.")
    if x.hostname.lower().rstrip(".") not in hosts or x.port not in (None, 443):
        raise RadarError("Publisher link is not on the approved source domain.")
    return value


def parse_time(value):
    if not isinstance(value, str) or not value.strip():
        raise RadarError("Feed item lacks a publication timestamp.")
    try:
        value = value.strip()
        if "T" in value:
            time = datetime.fromisoformat(value.replace("Z", "+00:00"))
        else:
            time = parsedate_to_datetime(value)
        if time.tzinfo is None:
            raise RadarError("Timezone missing in feed date.")
        return time.astimezone(timezone.utc)
    except (ValueError, TypeError, IndexError, OverflowError):
        raise RadarError("Bad feed publication timestamp.") from None


def first_text(node, tags):
    for tag in tags:
        element = node.find(tag)
        if element is not None and element.text and element.text.strip():
            return html.unescape(element.text.strip())
    return ""


def extract_items(feed_xml, feed):
    if len(feed_xml) > MAX_FEED_BYTES or b"<!DOCTYPE" in feed_xml.upper() or b"<!ENTITY" in feed_xml.upper():
        raise RadarError("Oversized or potentially unsafe XML feed.")
    try:
        root = ET.fromstring(feed_xml)
    except ET.ParseError:
        raise RadarError("Malformed publisher XML feed.") from None
    tag = root.tag.rsplit("}", 1)[-1].lower()
    if tag not in ("rss", "feed", "rdf"):
        raise RadarError("Publisher returned non-RSS/Atom XML.")
    entries = root.findall(".//item")
    atom = False
    if not entries:
        entries = root.findall("{http://www.w3.org/2005/Atom}entry")
        atom = True
    if not entries:
        raise RadarError("Official feed had no parseable entries.")
    result = []
    for node in entries[:70]:
        title = first_text(node, ["title", "{http://www.w3.org/2005/Atom}title"])
        if atom:
            href = ""
            for link in node.findall("{http://www.w3.org/2005/Atom}link"):
                if link.get("rel", "alternate") == "alternate" and link.get("href"):
                    href = link.get("href")
                    break
            date = first_text(node, ["{http://www.w3.org/2005/Atom}published",
                                     "{http://www.w3.org/2005/Atom}updated"])
        else:
            href = first_text(node, ["link"])
            date = first_text(node, ["pubDate", "{http://purl.org/dc/elements/1.1/}date"])
        if not title or not href or not date:
            continue
        try:
            article = check_url(href, feed["article_hosts"])
            timestamp = parse_time(date)
        except RadarError:
            continue
        if len(title) > 300:
            continue
        result.append({"title": re.sub(r"\\s+", " ", title),
                       "article_url": article, "published_at": timestamp.isoformat(),
                       "source": feed["source"], "feed_id": feed["id"]})
    return result


def pick_candidates(items, now=None, max_age_hours=MAX_AGE_HOURS):
    now = now or datetime.now(timezone.utc)
    seen = set()
    choices = []
    for row in items:
        stamp = parse_time(row["published_at"])
        age = now - stamp
        if age < timedelta(minutes=-2) or age > timedelta(hours=max_age_hours):
            continue
        score = sum(1 for signal in SIGNAL if signal in row["title"].lower())
        if not score:
            continue
        # Do not strip potentially distinguishing URL paths or queries.
        uid = hashlib.sha256(row["article_url"].encode("utf-8")).hexdigest()
        if uid in seen:
            continue
        seen.add(uid)
        choices.append({**row, "id": uid[:40], "rank_signal_hits": score,
                        "intake_status": "UNREVIEWED",
                        "body_read": False, "numbers_checked": False,
                        "image_reuse_permission_verified": False,
                        "importance_confirmed": False,
                        "telegram_publishable": False})
    choices.sort(key=lambda x: (x["rank_signal_hits"], x["published_at"]), reverse=True)
    return choices[:MAX_PER_CYCLE]


class NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise RadarError("Feed redirected; approved URL needs separate inspection.")


def fetch_feed(feed):
    x = parse.urlsplit(feed["url"])
    if x.scheme != "https" or x.hostname not in feed["article_hosts"]:
        raise RadarError("Feed host not allowlisted.")
    try:
        addresses = socket.getaddrinfo(x.hostname, 443, type=socket.SOCK_STREAM)
        if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):
            raise RadarError("Feed host resolved to nonpublic IP.")
        req = request.Request(feed["url"], headers={"User-Agent": "WestcottOfficialRadar/1.0",
                                                    "Accept": "application/rss+xml,application/xml,text/xml"})
        with request.build_opener(NoRedirect()).open(req, timeout=15) as reply:
            data = reply.read(MAX_FEED_BYTES + 1)
        if len(data) > MAX_FEED_BYTES:
            raise RadarError("Oversized official feed.")
        return data
    except (OSError, error.URLError, error.HTTPError, ValueError) as exc:
        raise RadarError("Could not read official RSS feed: " + type(exc).__name__) from None


def inspect_candidate_image(row, inspector=None):
    """Publisher image candidate only; DO NOT treat og:image as a reuse license."""
    from source_media import SourceMediaError, inspect_article
    try:
        page = (inspector or inspect_article)(row["article_url"])
        if page.get("canonical_matches_article") is False:
            raise SourceMediaError("Publisher canonical differs from feed story.")
        return {**row, "original_image_candidate_url": page.get("image_candidate_url"),
                "image_origin": "publisher_og_metadata",
                "image_review_required": True, "image_reuse_permission_verified": False}
    except (SourceMediaError, ValueError):
        return {**row, "original_image_candidate_url": None,
                "image_origin": "metadata_unavailable",
                "image_review_required": True, "image_reuse_permission_verified": False}


def git_queue_file(row, token, repo):
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
        raise RadarError("Invalid GitHub repository identifier.")
    location = "news/candidates/" + row["id"] + ".json"
    url = "https://api.github.com/repos/" + repo + "/contents/" + location
    content = (json.dumps(row, ensure_ascii=False, indent=2) + "\\n").encode("utf-8")
    payload = json.dumps({
        "message": "Queue official news headline for human verification " + row["id"][:12],
        "branch": "main",
        "content": __import__("base64").b64encode(content).decode("ascii"),
    }).encode("utf-8")
    req = request.Request(url, payload, method="PUT", headers={
        "Authorization": "Bearer " + token, "Content-Type": "application/json",
        "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"})
    try:
        with request.urlopen(req, timeout=20) as response:
            data = json.load(response)
        if not (data.get("content") or {}).get("sha"):
            raise RadarError("GitHub did not acknowledge queue commit.")
        return "new"
    except error.HTTPError as e:
        # Without a SHA, Contents API can't overwrite existing paths: 422 is duplicate.
        if e.code == 422:
            return "existing"
        raise RadarError("Queue storage HTTP " + str(e.code)) from None
    except (OSError, ValueError):
        raise RadarError("Queue storage uncertain; do not assume stored.") from None


def collect(fetcher=fetch_feed, now=None):
    articles, errors, fetched = [], [], 0
    for feed in FEEDS:
        try:
            articles.extend(extract_items(fetcher(feed), feed))
            fetched += 1
        except RadarError as exc:
            errors.append({"source": feed["id"], "reason": str(exc)})
    if not fetched:
        raise RadarError("All official news RSS feeds failed.")
    return pick_candidates(articles, now), errors


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["dry-run", "queue"], required=True)
    args = parser.parse_args()
    try:
        items, errors = collect()
        counts = {"new": 0, "existing": 0}
        if args.mode == "queue":
            token, repo = os.environ.get("GITHUB_TOKEN", ""), os.environ.get("GITHUB_REPOSITORY", "")
            if not token or not repo or os.environ.get("GITHUB_REF_NAME") != "main":
                raise RadarError("Queue mode requires main, GITHUB_TOKEN and GITHUB_REPOSITORY.")
            for row in items:
                counts[git_queue_file(inspect_candidate_image(row), token, repo)] += 1
        # No Telegram secrets used; no news message ever sent.
        print(json.dumps({
            "status": "CANDIDATES_ONLY", "mode": args.mode,
            "sources_checked": len(FEEDS) - len(errors),
            "feed_errors": errors, "candidate_count": len(items),
            "queued": counts, "candidates": items,
            "limitations": "RSS titles are not verified original-body claims; no AI rewrite, no images reposted, no Telegram sends.",
        }, ensure_ascii=False))
        return 0
    except RadarError as exc:
        print(json.dumps({"status": "COLLECTION_FAILED", "error": str(exc)}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
