"""Read-only validation and lookup of Westcott member stock participation.

Records are reviewed fictional-story statements. This is NOT a broker trade ledger.
No writes, imports, external APIs, or messaging are performed.
"""
from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "memory/member-stock/ledger-v1.json"
CURATED = ROOT / "memory/curated/2026-10-16-dynamic-state.json"

ACTIONS = {
    "WATCH_ONLY", "CONDITIONAL_PLAN_NOT_PURCHASE", "ORDER_REPORTED_UNFILLED",
    "AUTHOR_MARKED_FOLLOW_RECOMMENDATION",
    "SELF_REPORTED_BUY", "SELF_REPORTED_ADD", "SELF_REPORTED_PARTIAL_SALE",
    "SELF_REPORTED_FULL_SALE", "SELF_REPORTED_HOLD_AND_PARTIAL_SALE",
}
LINK_STATES = {"NOT_ESTABLISHED", "LINKED_TO_REVIEWED_RECOMMENDATION"}


def _valid(condition: bool, reason: str) -> None:
    if not condition:
        raise ValueError(reason)


def load() -> tuple[dict, list]:
    data = json.loads(LEDGER.read_text(encoding="utf-8"))
    paths = data.get("source_curated_paths", [data["source_curated_path"]])
    approved = {"memory/curated/2026-10-16-dynamic-state.json", "memory/curated/2026-10-21-dynamic-state.json"}
    _valid(isinstance(paths, list) and bool(paths) and len(paths) == len(set(paths)), "INVALID_SOURCE_PATHS")
    _valid(all(p in approved for p in paths), "UNAPPROVED_CURATED_SOURCE")
    curated = [r for path in paths for r in json.loads((ROOT/path).read_text(encoding="utf-8"))]
    return data, curated


def validate_ledger(ledger: dict, curated: list) -> dict:
    """Structural and provenance validation, not an assessment of statement truth."""
    _valid(isinstance(ledger, dict), "INVALID_LEDGER")
    _valid(ledger.get("schema") == "westcott-member-stock-participation-ledger-v1", "SCHEMA")
    _valid(ledger.get("timezone") == "Europe/Bucharest", "TIMEZONE")
    _valid(ledger.get("allowed_member_ids") == [1, 42], "ACTIVE_RANGE")
    _valid(ledger.get("completeness") in {"PARTIAL_VERIFIED_INITIAL_IMPORT_NOT_FULL_HISTORY", "PARTIAL_REVIEWED_FORMAL_IMPORT_NOT_FULL_HISTORY"}, "FALSE_COMPLETENESS")
    _valid(ledger.get("latest_google_doc_coverage") in {"NOT_SYNCED", "REVIEWED_THROUGH_2026_10_21_MORNING"}, "FALSE_DOC_SYNC")
    _valid(ledger.get("source_curated_path") == "memory/curated/2026-10-16-dynamic-state.json", "SOURCE_PATH")
    _valid(isinstance(curated, list), "INVALID_CURATED_SOURCE")
    source = {x["id"]: x for x in curated if isinstance(x, dict) and isinstance(x.get("id"), str)}
    ids = [f"{i:02d}" for i in range(1, 66)]
    by_member = ledger.get("by_member")
    _valid(isinstance(by_member, dict) and set(by_member) == set(ids), "ROSTER_INDEX_NOT_65")
    _valid(all(isinstance(by_member[i], list) for i in ids), "INVALID_MEMBER_INDEX")
    events = ledger.get("records")
    _valid(isinstance(events, list), "INVALID_EVENTS")
    seen = set()
    derived = {pid: [] for pid in ids}
    for event in events:
        _valid(isinstance(event, dict), "INVALID_EVENT")
        eid = event.get("id")
        _valid(isinstance(eid, str) and bool(eid) and eid not in seen, "DUPLICATE_OR_INVALID_EVENT_ID")
        seen.add(eid)
        pid = event.get("member_id")
        _valid(isinstance(pid, str) and pid in derived, "UNKNOWN_MEMBER:" + str(pid))
        _valid(1 <= int(pid) <= 42, "INACTIVE_MEMBER_CANNOT_PARTICIPATE:" + pid)
        try:
            event_date = date.fromisoformat(event.get("story_date", ""))
            cutoff = date.fromisoformat(ledger["source_cutoff"])
        except (TypeError, ValueError, KeyError):
            raise ValueError("INVALID_STORY_DATE:" + eid)
        _valid(event_date <= cutoff, "SOURCE_DATE_AFTER_CUTOFF:" + eid)
        _valid(event.get("action") in ACTIONS, "INVALID_ACTION:" + eid)
        _valid(isinstance(event.get("symbol"), str) and bool(event["symbol"]), "MISSING_SYMBOL:" + eid)
        _valid(event.get("source_class") == "REVIEWED_ADOPTED_STORY_SPEECH", "UNREVIEWED_SOURCE:" + eid)
        _valid(event.get("real_trade_verified") is False, "STORY_NOT_REAL_BROKER_PROOF:" + eid)
        _valid(event.get("actual_execution_time") is None, "FABRICATED_EXECUTION_TIME:" + eid)
        status = event.get("recommendation_link_status")
        _valid(status in LINK_STATES, "INVALID_RECOMMENDATION_STATUS:" + eid)
        if status == "NOT_ESTABLISHED":
            _valid(event.get("recommendation_id") is None, "UNSUPPORTED_RECOMMENDATION_LINK:" + eid)
        else:
            _valid(isinstance(event.get("recommendation_id"), str) and event["recommendation_id"], "MISSING_RECOMMENDATION_ID:" + eid)
            _valid(bool(event.get("recommendation_evidence_ids")), "NO_RECOMMENDATION_EVIDENCE:" + eid)
        for field in ("reported_quantity", "reported_price", "reported_currency"):
            if event.get(field) is not None:
                _valid(bool(event.get("numeric_evidence_ids")), "UNSUPPORTED_NUMERIC_FIELD:" + eid)
        _valid(event.get("outcome_or_position_estimate") is None, "UNVERIFIED_HOLDINGS_OR_PNL:" + eid)
        ref = event.get("source_curated_id")
        _valid(isinstance(ref, str) and ref in source, "UNREVIEWED_OR_MISSING_SOURCE:" + eid)
        accepted = source[ref]
        _valid(
            accepted.get("member_id") == pid
            and accepted.get("symbol") == event.get("symbol")
            and accepted.get("action") == event.get("action"),
            "SOURCE_IDENTITY_OR_ACTION_MISMATCH:" + eid,
        )
        original = accepted.get("evidence_ids", [])
        refs = event.get("source_evidence_ids")
        _valid(bool(refs) and refs == original and
               all(isinstance(x, str) for x in refs), "SOURCE_EVIDENCE_MISMATCH:" + eid)
        _valid(accepted.get("evidence_support_reviewed") is True and
               bool(accepted.get("reviewer")) and
               event.get("reviewer") == accepted.get("reviewer") and
               set(refs) == set(accepted.get("evidence_fingerprints", {})),
               "UNREVIEWED_OR_STALE_EVIDENCE:" + eid)
        if event.get("numeric_evidence_ids"):
            _valid(set(event["numeric_evidence_ids"]).issubset(set(refs)), "NUMBER_MISSING_SUPPORT:" + eid)
        _valid(all(x.startswith(event["story_date"].replace("-", "")) for x in refs), "SOURCE_DATE_MISMATCH:" + eid)
        if event["action"] == "AUTHOR_MARKED_FOLLOW_RECOMMENDATION":
            _valid(event.get("author_annotation") == "跟推荐买票", "MISSING_AUTHOR_ANNOTATION:" + eid)
            _valid(all(event.get(k) is None for k in ("reported_quantity", "reported_price", "reported_currency")), "ANNOTATION_NOT_FILL_PROOF:" + eid)
            day_path = ROOT / "memory/daily" / event["story_date"] / "day-memory.json"
            day = json.loads(day_path.read_text(encoding="utf-8"))
            messages = {r["id"]:r for r in day["messages"] if r["status"] == "ADOPTED_IN_USER_SUBMITTED_STORY"}
            _valid(all(ref in messages and messages[ref]["speaker_id"] == pid and "跟推荐买票" in messages[ref]["text"] for ref in refs), "ANNOTATION_SOURCE_MISSING:" + eid)
            _valid(all(ref in messages and messages[ref]["speaker_id"] == "news_assistant" and event["symbol"] in messages[ref]["text"] for ref in event.get("recommendation_evidence_ids", [])), "RECOMMENDATION_SOURCE_MISMATCH:" + eid)
        derived[pid].append(eid)
    _valid(by_member == derived, "MEMBER_INDEX_NOT_RECONCILED")
    return {"status": "PASS_STATIC_PROVENANCE_ONLY", "indexed_identities": len(ids),
            "reviewed_story_state_records": len(events),
            "members_with_records": sum(bool(derived[k]) for k in ids),
            "history_coverage": ledger["completeness"],
            "real_broker_trades_verified": 0}


def query(ledger: dict, *, member: str | None = None, symbol: str | None = None) -> dict:
    member = member.zfill(2) if member is not None else None
    if member is not None and member not in ledger["by_member"]:
        raise ValueError("UNKNOWN_MEMBER:" + member)
    if symbol is not None:
        symbol = symbol.upper().strip()
    events = [e for e in ledger["records"]
              if (member is None or e["member_id"] == member)
              and (symbol is None or e["symbol"].upper() == symbol)]
    return {"member_id": member, "symbol": symbol, "records": events,
            "coverage": ledger["completeness"],
            "note": "Reviewed fictional-story self-reports; not verified real executions."}


def main() -> None:
    parser = argparse.ArgumentParser(description="Read-only Westcott member stock participation register")
    parser.add_argument("--check", action="store_true", help="Validate provenance and index")
    parser.add_argument("--member", help="Member ID (01-65)")
    parser.add_argument("--symbol", help="Stock ticker")
    args = parser.parse_args()
    ledger, curated = load()
    validated = validate_ledger(ledger, curated)
    answer = validated if args.check or (args.member is None and args.symbol is None) else (
        {"validation": validated["status"], **query(ledger, member=args.member, symbol=args.symbol)}
    )
    print(json.dumps(answer, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
