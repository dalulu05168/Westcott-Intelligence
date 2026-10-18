"""ELLERY WESTCOTT news V1.0 editorial completeness gate.

This checks reviewed-copy structure, not the truth of source claims. The existing
news_release_gate and live publisher source rechecks remain authoritative.
No scheduling, group, transport or approval semantics are changed here.
"""
import re
from datetime import datetime

VERSION = "ELLERY_WESTCOTT_NEWS_V1"
ROLES = ("event", "interpretation", "impact", "watch", "change")
HEADINGS = {
    "event": ("🌐 ELLERY WESTCOTT｜财经资讯快报", "📰 新闻主题：",
              "🕒 事件时间：", "🌍 市场地区：", "📊 影响程度：", "📌 事件概述"),
    "interpretation": ("🔍 核心解读",),
    "impact": ("📈 市场影响", "已证实反应：", "潜在影响：",
               "尚不确定：", "影响理由：", "影响周期："),
    "watch": ("🎯 后续关注重点",),
    "change": ("🔔 判断变化条件", "增强条件：", "减弱条件：", "验证依据："),
}
GENERIC = ("继续关注市场变化", "持续关注市场变化", "密切关注后续发展")


class NewsAnalysisError(ValueError):
    pass


def _meaningful(text, label, min_chars=3):
    segment = text.split(label, 1)[1].split("\n", 1)[0].strip() if label in text else ""
    if len(segment) < min_chars or segment in ("待定", "未知", "无", "N/A", "暂无"):
        raise NewsAnalysisError("NEWS_V1_EMPTY_FIELD:" + label)
    return segment


def validate_news_v1(ledger, approved_facts):
    """Fail closed for *new* releases at the reviewed-publisher boundary.

    Production workflows opt in explicitly. Historical test fixtures and legacy
    ledgers are not rewritten or silently promoted to a new standard.
    """
    if ledger.get("content_standard") != VERSION:
        raise NewsAnalysisError("NEWS_V1_STANDARD_REQUIRED")
    if ledger.get("target_country") not in ("RO", "FR"):
        raise NewsAnalysisError("NEWS_V1_COUNTRY_REQUIRED")
    section_claims = {}
    published = set(ledger.get("publish_claim_ids", ()))
    for claim in ledger.get("claims", ()):
        role = claim.get("content_section")
        if not role or claim.get("id") not in published:
            continue
        if role not in ROLES or role in section_claims:
            raise NewsAnalysisError("NEWS_V1_INVALID_OR_DUPLICATE_SECTION")
        section_claims[role] = claim
    if set(section_claims) != set(ROLES):
        raise NewsAnalysisError("NEWS_V1_MISSING_SECTION:" + ",".join(sorted(set(ROLES) - set(section_claims))))
    if len(approved_facts) != len(published):
        raise NewsAnalysisError("NEWS_V1_PUBLISH_IDS_MISMATCH")
    for role in ROLES:
        claim = section_claims[role]
        text = claim.get("text", "")
        if text not in approved_facts or len(text) > 4600:
            raise NewsAnalysisError("NEWS_V1_UNREVIEWED_SECTION:" + role)
        if claim.get("kind") != ("fact" if role == "event" else "analysis"):
            raise NewsAnalysisError("NEWS_V1_WRONG_CLAIM_KIND:" + role)
        if role != "event" and (
            claim.get("target_country") != ledger["target_country"]
            or claim.get("conditional") is not True
            or not claim.get("boundary_text")
        ):
            raise NewsAnalysisError("NEWS_V1_ANALYSIS_BOUNDARY:" + role)
        if not all(x in text for x in HEADINGS[role]):
            raise NewsAnalysisError("NEWS_V1_MISSING_FIELD:" + role)
        if any(x in text for x in GENERIC):
            raise NewsAnalysisError("NEWS_V1_GENERIC_FOLLOWUP:" + role)
        if "**" in text:
            raise NewsAnalysisError("NEWS_V1_MARKDOWN_BOLD_NOT_ALLOWED")
    if ledger.get("local_impact_claim_id") != section_claims["impact"]["id"]:
        raise NewsAnalysisError("NEWS_V1_IMPACT_ID_MISMATCH")
    if ledger.get("watch_next_claim_id") != section_claims["watch"]["id"]:
        raise NewsAnalysisError("NEWS_V1_WATCH_ID_MISMATCH")
    event = section_claims["event"]["text"]
    level = _meaningful(event, "📊 影响程度：", min_chars=1)
    if level not in ("高", "中", "低"):
        raise NewsAnalysisError("NEWS_V1_BAD_IMPACT_LEVEL")
    locality = _meaningful(event, "🌍 市场地区：")
    expected = "罗马尼亚" if ledger["target_country"] == "RO" else "法国"
    if expected not in locality:
        raise NewsAnalysisError("NEWS_V1_COUNTRY_MISMATCH")
    event_time = _meaningful(event, "🕒 事件时间：")
    # An explicit publication timestamp is acceptable if properly labeled;
    # an unverified guessed event time is not.
    if not (re.search(r"\d{4}-\d{2}-\d{2}", event_time)
            and ("官方发布时间" in event_time or "事件时间" in event_time)):
        raise NewsAnalysisError("NEWS_V1_UNVERIFIED_EVENT_TIME")
    for label in ("📰 新闻主题：",):
        _meaningful(event, label)
    impact = section_claims["impact"]["text"]
    for label in ("已证实反应：", "潜在影响：", "尚不确定：", "影响理由：", "影响周期："):
        _meaningful(impact, label)
    if not ("短期" in impact and "中期" in impact):
        raise NewsAnalysisError("NEWS_V1_IMPACT_HORIZON_MISSING")
    watch = section_claims["watch"]["text"]
    points = re.findall(r"(?m)^\s*([①②③])\s*(.+)$", watch)
    if len(points) not in (2, 3) or [p[0] for p in points] != ["①", "②", "③"][:len(points)]:
        raise NewsAnalysisError("NEWS_V1_WATCH_COUNT_OR_ORDER")
    for _, entry in points:
        if "｜观察时间/条件：" not in entry:
            raise NewsAnalysisError("NEWS_V1_WATCH_TRIGGER_REQUIRED")
        focus, trigger = entry.split("｜观察时间/条件：", 1)
        if len(focus.strip()) < 5 or len(trigger.strip()) < 5:
            raise NewsAnalysisError("NEWS_V1_WATCH_NOT_ACTIONABLE")
    change = section_claims["change"]["text"]
    for label in ("增强条件：", "减弱条件：", "验证依据："):
        _meaningful(change, label)
    return {"standard": VERSION, "sections": list(ROLES), "impact_level": level,
            "watch_point_count": len(points), "status": "STRUCTURE_VERIFIED_ONLY"}
