#!/usr/bin/env python3
"""Romania + prior US close morning candidate, requires separate reviewed BVB facts."""
import argparse
from datetime import datetime, timedelta
import json
from pathlib import Path
from urllib.parse import urlsplit

from morning_opening import BUCHAREST, build as build_us, is_https, parse_iso

RO_OFFICIAL_HOSTS=("bvb.ro","bnr.ro","insse.ro","mfinante.gov.ro","ecb.europa.eu")


def is_ro_primary(url):
    if not is_https(url):
        return False
    h=urlsplit(url).hostname.lower().rstrip(".")
    return any(h==d or h.endswith("."+d) for d in RO_OFFICIAL_HOSTS)


def validate_romania(evidence, now):
    if not isinstance(evidence,dict) or evidence.get("target_country")!="RO":
        raise ValueError("No Romania official source evidence")
    if evidence.get("review_status")!="REVIEWED" or not evidence.get("reviewed_by"):
        raise ValueError("Romanian claims are not reviewed")
    checked=parse_iso(evidence.get("source_checked_at"))
    if checked>now or now-checked>timedelta(hours=12):
        raise ValueError("Source check timestamp stale")
    events=evidence.get("events")
    if not isinstance(events,list) or not 1<=len(events)<=3:
        raise ValueError("Require one to three significant reviewed RO events")
    keys=set()
    for item in events:
        if not isinstance(item,dict) or item.get("target_country")!="RO" or item.get("material_new_fact") is not True:
            raise ValueError("Non-RO or immaterial event")
        if not is_ro_primary(item.get("source_url","")):
            raise ValueError("Original Romanian government/exchange URL required")
        pub=parse_iso(item.get("published_at"))
        if pub>now or now-pub>timedelta(days=5):
            raise ValueError("Old or future RO event")
        key=item.get("event_key")
        if not isinstance(key,str) or not 8<=len(key)<=160 or key in keys:
            raise ValueError("Duplicate or invalid event key")
        keys.add(key)
        sha=item.get("source_body_sha256")
        if not isinstance(sha,str) or len(sha)!=64 or any(c not in "0123456789abcdef" for c in sha):
            raise ValueError("Original RO source body sha256 required")
        for field in ("title_cn","fact_cn","source_excerpt","impact_cn","watch_cn"):
            if not isinstance(item.get(field),str) or not item[field].strip():
                raise ValueError("Missing reviewed field "+field)
        if not any(c in item["impact_cn"] for c in ("可能","如果","若","取决于","需观察","需要观察")):
            raise ValueError("Market transmission may not be asserted as certain")
    return events


def build(now, us_market=None, romania_evidence=None):
    local=now.astimezone(BUCHAREST)
    us=build_us(local, us_market)
    result={
        "task":"westcott-romania-us-morning",
        "local_date":local.date().isoformat(),
        "status":"HELD_SOURCE_REQUIRED","opening_draft":us["opening_draft"],
        "us_recap_draft":us["us_recap_draft"],
        "romania_draft":None,"delivery_allowed":False,"telegram_sent":False,
        "formal_google_docs_loaded":False,
        "reason":"美国或罗马尼亚官方事实证据未核实。"
    }
    if us["status"]!="READY_FOR_EDITORIAL_REVIEW":
        return result
    try:
        events=validate_romania(romania_evidence,local)
    except (ValueError,TypeError,KeyError):
        result["status"]="HELD_ROMANIA_EVIDENCE_REQUIRED"
        return result
    out=["🔵 罗马尼亚｜已核实的重要进展"]
    for row in events:
        out.extend(["📰 "+row["title_cn"].strip(),row["fact_cn"].strip(),
                    "对罗马尼亚市场的影响："+row["impact_cn"].strip(),
                    "后续关注："+row["watch_cn"].strip(),
                    "官方原文："+row["source_url"].strip()])
    result["romania_draft"]="\n\n".join(out)
    result["status"]="READY_FOR_EDITORIAL_REVIEW"
    result["reason"]="RO+US材料通过结构校验，仍需核对真实官网正文及当天正式剧情。"
    return result


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--us-source",default="news/verified-market/us-close-latest.json")
    parser.add_argument("--ro-source",default="news/verified-market/romania-morning-latest.json")
    parser.add_argument("--output",default="morning-romania-review.json")
    parser.add_argument("--text-output",default="morning-romania-review.txt")
    args=parser.parse_args()
    def read(path):
        try:
            return json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError,ValueError):
            return None
    result=build(datetime.now(BUCHAREST),read(args.us_source),read(args.ro_source))
    Path(args.output).write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    body="\n\n".join(x for x in (result["opening_draft"],result["us_recap_draft"],result["romania_draft"]) if x)
    Path(args.text_output).write_text(body+"\n\n内部状态："+result["status"]+
                                     "\n未经送达确认；仅候选稿。\n",encoding="utf-8")
    print("romania-us-morning:",result["status"])


if __name__=="__main__":
    main()
