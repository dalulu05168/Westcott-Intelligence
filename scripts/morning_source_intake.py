#!/usr/bin/env python3
"""Official morning news evidence bridge (FR, RO, US), no review, no Telegram.

Runs before the morning editor. It NEVER synthesizes index quotes, translates
claims as confirmed, or claims to have read the formal Google Doc.
"""
import argparse
import base64
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
import hashlib
import json
import os
from pathlib import Path
import re
import sys
from urllib import error, request
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "integrations/telegram"))
import news_radar

BUCHAREST = ZoneInfo("Europe/Bucharest")
MARKET_SCOPES = {
    "bvb_market": ["RO"],
    "bvb_announcements": ["RO"],
    "insee_conjuncture": ["FR"],
    "ecb_press": ["RO", "FR"],
    "eurostat_releases": ["RO", "FR"],
    "fed_monetary": ["US"],
    "bls_cpi": ["US"],
    "bls_employment": ["US"],
}
MAX_PER_FEED = 5
MAX_SNIPPET = 4500


def build(now, fetcher=None, inspector=None):
    """Purely evidence-candidate collection; fail closed on access errors."""
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("Timezone required")
    fetcher = fetcher or news_radar.fetch_feed
    inspector = inspector or news_radar.inspect_candidate_image
    local = now.astimezone(BUCHAREST)
    since = now.astimezone(timezone.utc) - timedelta(hours=48)
    errors, candidates, coverage, seen = [], [], [], set()
    for feed in news_radar.FEEDS:
        country = MARKET_SCOPES.get(feed["id"])
        if not country:
            continue
        try:
            items = news_radar.extract_items(fetcher(feed), feed, strict=True)
            items = [item for item in items if since <= news_radar.parse_time(item["published_at"]) <= now]
            items.sort(key=lambda x: x["published_at"], reverse=True)
            coverage.append({"feed_id":feed["id"],"status":"OK","recent_entries":len(items)})
            for item in items[:MAX_PER_FEED]:
                if item["article_url"] in seen:
                    continue
                seen.add(item["article_url"])
                verified = inspector(item)
                accessible = (verified.get("body_fetch_status") == "FETCHED_FOR_REVIEW"
                              and verified.get("source_text_truncated") is False
                              and bool(verified.get("source_text_sha256")))
                candidates.append({
                    "id":hashlib.sha256(item["article_url"].encode()).hexdigest()[:40],
                    "source_id":feed["id"],
                    "market_scopes":country,
                    "headline_original":item["title"],
                    "published_at":item["published_at"],
                    "official_article_url":item["article_url"],
                    "origin":feed["source"],
                    "source_body_sha256":verified.get("source_text_sha256") if accessible else None,
                    "source_excerpt_original":verified.get("source_text_snapshot","")[:MAX_SNIPPET] if accessible else None,
                    "evidence_status":"BODY_CAPTURED_UNREVIEWED" if accessible else "SOURCE_BODY_UNAVAILABLE",
                    "source_body_error":verified.get("body_fetch_error") if not accessible else None,
                    "editorial_review_required":True,
                    "market_impact_reviewed":False,
                    "telegram_publishable":False,
                })
        except (news_radar.RadarError, TypeError, ValueError, OSError) as exc:
            errors.append({"feed_id":feed["id"],"error_type":type(exc).__name__})
            coverage.append({"feed_id":feed["id"],"status":"ERROR"})
    candidates.sort(key=lambda v:(v["published_at"],v["id"]),reverse=True)
    return {
        "status":"OFFICIAL_INTAKE_INCOMPLETE_UNREVIEWED" if errors else "OFFICIAL_INTAKE_UNREVIEWED",
        "local_date":local.date().isoformat(),
        "collected_at":now.astimezone(timezone.utc).isoformat(),
        "timezone":"Europe/Bucharest",
        "source_window_hours":48,
        "market_scopes":["RO","FR","US"],
        "coverage":coverage,
        "feed_errors":errors,
        "candidates":candidates,
        "us_index_close_snapshot_ready":False,
        "google_docs_current_revision_loaded":False,
        "review_status":"UNREVIEWED",
        "delivery_allowed":False,
        "telegram_sent":False,
        "purpose":"Material for human/ChatGPT source-based editorial review, not market quote certification.",
    }


def save_github(document, env, sender=None):
    """Append-only official raw-intake provenance. No overwrite/no Telegram."""
    if env.get("GITHUB_REF_NAME") != "main":
        raise ValueError("Only main may store official morning intake")
    token=env.get("GITHUB_TOKEN","").strip()
    repo=env.get("GITHUB_REPOSITORY","")
    if not token or not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+",repo):
        raise ValueError("GitHub token or repository missing")
    path="news/morning-intake/"+document["local_date"]+".json"
    encoded=base64.b64encode((json.dumps(document,ensure_ascii=False,indent=2)+"\n").encode()).decode()
    url="https://api.github.com/repos/"+repo+"/contents/"+path
    body=json.dumps({"message":"Capture unreviewed official morning news sources "+document["local_date"],
                     "content":encoded,"branch":"main"}).encode()
    req=request.Request(url,body,headers={"Authorization":"Bearer "+token,
          "Accept":"application/vnd.github+json","Content-Type":"application/json"},method="PUT")
    try:
        with (sender or request.urlopen)(req,timeout=25) as response:
            obj=json.load(response)
        if not (obj.get("content") or {}).get("sha"):
            raise ValueError("GitHub did not acknowledge source-intake commit")
    except error.HTTPError as exc:
        if exc.code in (409,422):
            return {"status":"ALREADY_RESERVED","path":path}
        raise ValueError("Morning intake failed HTTP "+str(exc.code)) from None
    except (OSError,ValueError):
        raise ValueError("Morning intake commit not confirmed; cannot assert stored") from None
    return {"status":"SOURCE_INTAKE_STORED_UNREVIEWED","path":path}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--mode",choices=("dry-run","queue"),default="dry-run")
    args=parser.parse_args()
    now=datetime.now(timezone.utc)
    report=build(now)
    summary={
        "status":report["status"],
        "local_date":report["local_date"],
        "coverage":report["coverage"],
        "candidate_count":len(report["candidates"]),
        "source_bodies_captured":sum(x["evidence_status"]=="BODY_CAPTURED_UNREVIEWED" for x in report["candidates"]),
        "us_index_close_snapshot_ready":False,
        "google_docs_current_revision_loaded":False,
        "telegram_sent":False,
    }
    if args.mode=="queue":
        result=save_github(report,os.environ)
        summary.update(result)
    print(json.dumps(summary,ensure_ascii=False))
    # A read-only PR diagnostic can complete while honestly reporting failures.
    # Scheduled intake signals partial source coverage as an actionable failure.
    return 0 if args.mode=="dry-run" else (0 if all(c["status"]=="OK" for c in report["coverage"]) else 2)


if __name__=="__main__":
    raise SystemExit(main())
