"""Read-only source health probe. No Telegram sends, no secrets, no automated claims.

Reports each source separately, article verification and official article-image presence
for a small set. Logs counts and failure reasons, not article content or private data.
"""
from __future__ import annotations
import json
from datetime import datetime, timezone
from urllib.parse import urlparse

from dual_market import (BVB_ISSUER_FEEDS, AMF_RSS, FR_GOV_RSS, FEEDS,
                         PARIS, SESSION, TZ, download_image, feed_items,
                         fetch_bvb, fetch_feed, fetch_original, official_image,
                         source_records)


def probe():
    stats = {}
    sources = ["BVB", "BVB_MARKET", "BVB_FIN", "AMF", "FR_GOV", "ECB", "FED"]
    all_items, failed = source_records()
    for source in sources:
        items = [x for x in all_items if x["source"] == source]
        latest = sorted(items, key=lambda x: x["published"], reverse=True)[:2]
        summary = {"feed_items": len(items), "reachable_feed": source not in failed,
                   "sample_article_verified": 0, "article_official_image": 0,
                   "image_downloaded": 0, "blocked_or_missing": []}
        for article in latest:
            try:
                original = fetch_original(article)
                if original is None:
                    summary["blocked_or_missing"].append("official_article_content_or_title")
                    continue
                summary["sample_article_verified"] += 1
                html, text = original
                url = official_image(html, article)
                if not url:
                    summary["blocked_or_missing"].append("official_article_image_metadata")
                    continue
                summary["article_official_image"] += 1
                image = download_image(url, article)
                if image:
                    summary["image_downloaded"] += 1
                else:
                    summary["blocked_or_missing"].append("image_format_size_or_access")
            except Exception as e:
                summary["blocked_or_missing"].append(type(e).__name__)
        stats[source] = summary
        print("SOURCE_HEALTH", source, json.dumps(summary, ensure_ascii=False))
    usable = sum(s["image_downloaded"] for s in stats.values())
    result = {"checked_at": datetime.now(timezone.utc).isoformat(),
              "total_candidates": len(all_items), "total_images_retrievable": usable,
              "sources_failed": failed, "summary": stats}
    with open("telegram-source-probe.json", "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    if not all_items:
        print("SOURCE_PROBE_WARNING: no official records accessible. No claims will be published.")
    if not usable:
        print("SOURCE_PROBE_WARNING: none of the sampled original articles had a usable official image.")
    print("SOURCE_PROBE_COMPLETED (read-only; no Telegram sends)")


if __name__ == "__main__":
    probe()
