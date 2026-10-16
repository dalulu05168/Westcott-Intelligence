#!/usr/bin/env python3
"""Prepare an auditable Chinese morning opening and prior-US-session recap.

Editorial preview ONLY, never a Telegram sender. No Google Docs or member
dialogue is claimed, and no market numbers are fabricated.
"""
import argparse
from datetime import date, datetime, timedelta
import json
from pathlib import Path
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

BUCHAREST = ZoneInfo("Europe/Bucharest")
NEW_YORK = ZoneInfo("America/New_York")
INDEX_NAMES = {
    "DJIA": "道琼斯工业平均指数",
    "SPX": "标普500指数",
    "IXIC": "纳斯达克综合指数",
}

# Verify that every reported US index has its own index-owner source URL.
# A recognized domain does not replace current original-page fact review.
INDEX_OFFICIAL_HOSTS = {
    "DJIA": ("spglobal.com",),
    "SPX": ("spglobal.com",),
    "IXIC": ("nasdaq.com",),
}


def is_official_index_source(symbol, url):
    if not is_https(url):
        return False
    parsed = urlsplit(str(url))
    if parsed.port not in (None, 443) or parsed.fragment:
        return False
    host = parsed.hostname.lower().rstrip(".")
    return any(host == domain or host.endswith("." + domain)
               for domain in INDEX_OFFICIAL_HOSTS.get(symbol, ()))


def parse_iso(value):
    if not isinstance(value, str):
        raise ValueError("Expected ISO timestamp string")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("Timestamp must contain timezone")
    return parsed

def is_https(url):
    parsed = urlsplit(str(url))
    return parsed.scheme == "https" and bool(parsed.hostname) and not parsed.username

def validate_close(data, now):
    """Structural checks only: authenticity needs independent original-source review."""
    if not isinstance(data, dict) or data.get("market") != "US" or data.get("phase") != "REGULAR_CLOSE":
        raise ValueError("Expected US REGULAR_CLOSE snapshot")
    session_date = date.fromisoformat(data["session_date"])
    ny_date = now.astimezone(NEW_YORK).date()
    lag = (ny_date - session_date).days
    if not (1 <= lag <= 7) or session_date.weekday() >= 5:
        raise ValueError("Not a recent, prior US weekday trading session")
    if not any(is_official_index_source(symbol, data.get("source_url", ""))
               for symbol in INDEX_NAMES):
        raise ValueError("Snapshot source must belong to an official US index owner")
    source_at = parse_iso(data["source_checked_at"])
    if source_at > now + timedelta(minutes=5) or source_at < now - timedelta(days=8):
        raise ValueError("Invalid source check freshness")
    if data.get("review_status") != "REVIEWED" or not data.get("reviewed_by"):
        raise ValueError("No explicit fact-review record")
    if not data.get("evidence_reference") or not data.get("source_body_sha256"):
        raise ValueError("Missing traceable source evidence")
    rows = data.get("indices")
    if not isinstance(rows, list) or len(rows) != 3:
        raise ValueError("Exactly three indices must be supplied")
    found = {}
    for row in rows:
        symbol = row.get("symbol")
        if symbol not in INDEX_NAMES or symbol in found:
            raise ValueError("Unknown or duplicated index")
        close, previous, pct = row.get("close"), row.get("previous_close"), row.get("change_pct")
        if any(type(x) not in (float, int) for x in (close, previous, pct)):
            raise ValueError("Close, previous close and percent change must be numeric")
        if close <= 0 or previous <= 0 or abs(pct - (close / previous - 1) * 100) > .035:
            raise ValueError("Invalid or internally inconsistent market values")
        as_of = parse_iso(row["quote_as_of"])
        if as_of.astimezone(NEW_YORK).date() != session_date or as_of > now:
            raise ValueError("Quote timestamp not in the claimed market session")
        if row.get("phase") != "REGULAR_CLOSE" or not is_official_index_source(symbol, row.get("source_url", "")):
            raise ValueError("Unverifiable phase or missing official index-owner quote source")
        if not row.get("evidence_excerpt"):
            raise ValueError("Missing quote evidence excerpt")
        found[symbol] = row
    return session_date, found

def build(now, market_data=None):
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now requires timezone")
    local = now.astimezone(BUCHAREST)
    opening = ("===== 资讯助理 =====\n"
               "🌤️ 大家上午好，欢迎回到 ELLERY WESTCOTT 社群！\n"
               "今天的早间分享先从上一美股交易日的实际收盘情况开始，"
               "随后再看看有哪些值得关注的新变化。")
    report = {
        "task": "westcott-morning-opening-us-recap",
        "local_date": local.date().isoformat(),
        "prepared_at": local.isoformat(),
        "timezone": "Europe/Bucharest",
        "scheduled_time": "07:30",
        "status": "HELD_SOURCE_REQUIRED",
        "opening_draft": opening,
        "us_recap_draft": None,
        "unverified_market_data_used": False,
        "formal_google_docs_loaded": False,
        "member_dialogue_generated": False,
        "telegram_sent": False,
        "delivery_allowed": False,
        "reason": "缺少最近一个美股交易日的逐指数来源及审核凭据；仅准备助理开场候选稿。",
        "notes": [
            "必须复核当天正式 Google Docs 剧情后才能增加成员台词。",
            "代码的字段检查不等于原文真实性审核；结果不得自动发往 Telegram。"
        ],
    }
    if market_data is None:
        return report
    try:
        session_date, rows = validate_close(market_data, now)
    except (TypeError, ValueError, KeyError, OverflowError) as exc:
        report["status"] = "HELD_INVALID_MARKET_EVIDENCE"
        report["reason"] = "美股收盘材料未通过结构/时点检查：" + str(exc)
        return report
    statements = []
    for symbol in ("DJIA", "SPX", "IXIC"):
        pct = rows[symbol]["change_pct"]
        direction = "上涨" if pct > 0 else ("下跌" if pct < 0 else "持平")
        statements.append(f"{INDEX_NAMES[symbol]}{direction}{abs(pct):.2f}%")
    official_links = [
        INDEX_NAMES[symbol] + "：" + rows[symbol]["source_url"]
        for symbol in ("DJIA", "SPX", "IXIC")
    ]
    report["us_recap_draft"] = (
        f"===== 资讯助理 =====\n📊 {session_date:%Y年%m月%d日}美股常规交易时段收盘，"
        + "，".join(statements) + "。\n"
        + "以上是所提供审核材料中的收盘百分比；宏观及公司消息仍需逐条核实后再展开。"
        + "\\n\\n🔗 官方指数原始来源：\\n" + "\\n".join(official_links)
    )
    report["status"] = "READY_FOR_EDITORIAL_REVIEW"
    report["reason"] = (
        "已经读取一份具备来源、时间与审核字段的美股收盘快照；"
        "尚需核对原文、当天正式剧情及是否重复，不能自动发布。"
    )
    report["market_source_url"] = market_data["source_url"]
    report["market_session_date"] = session_date.isoformat()
    return report

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default="news/verified-market/us-close-latest.json",
                        help="Pre-reviewed market evidence JSON in the repository (optional)")
    parser.add_argument("--output", default="morning-review.json")
    parser.add_argument("--text-output", default="morning-review.txt")
    args = parser.parse_args()
    source = Path(args.source)
    data = None
    if source.is_file():
        try:
            data = json.loads(source.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            data = {"market": "INVALID_FILE"}
    result = build(datetime.now(BUCHAREST), data)
    Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    output_text = result["opening_draft"] + "\n\n"
    if result["us_recap_draft"]:
        output_text += result["us_recap_draft"] + "\n\n"
    output_text += f"内部状态：{result['status']}\n{result['reason']}\n未推送 Telegram；未更新正式剧情。\n"
    Path(args.text_output).write_text(output_text, encoding="utf-8")
    print("morning-opening-prep:", result["status"])
    print(result["reason"])
    # HELD is safe and expected; preserve a workflow artifact for audit.

if __name__ == "__main__":
    main()
