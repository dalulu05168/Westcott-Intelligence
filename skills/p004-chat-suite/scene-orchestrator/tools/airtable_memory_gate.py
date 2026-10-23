#!/usr/bin/env python3
"""Fail-closed Google Docs -> Airtable evidence reconciliation.

This is a pure local gate; it does NOT fetch Docs/Airtable, write records,
change ChatGPT Tasks, publish scenes, or validate financial claims. The caller
must supply independently fetched connector responses for the same run.

Input JSON:
  {"document": {"documentId": str, "revisionId": str, "tabId": str,
                "date": "YYYY-MM-DD", "paragraphs": [{"text":str}, ...]},
   "roster": {"people": [{"id":"01", "gender":"男"}, ...]},
   "records": [{"证据ID":str, "人物编号":str, "原话":str,
                "剧情日期":str, "正式页签":str,
                "原文段落索引":"p12—p13 (0起算)"}, ...]}
Record keys may be Chinese field names as shown (not Airtable field IDs).
The output is a proposed plan, never an authorization to mutate any source.
"""
import argparse
from collections import defaultdict
from hashlib import sha256
import json
import re
import sys

FORMAL_DOCUMENT_ID = "1frtoFvohP3u2HfRzBPRZVLOzMfvnO-8Vi9iX3r5rmiM"
MEMBER = re.compile(r"^\s*(\d{1,2})\s*(男|女)\s*[：:]")
STAFF = re.compile(r"^\s*={3,}\s*(?:资讯助理|助理|先生|教授|投资顾问|咨询顾问)\s*={3,}")
POSITION = re.compile(r"p(\d+)")
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def clean(text):
    return str(text).replace("\x0b", "\n").replace("\r\n", "\n").strip()


def validate_sources(document, roster):
    if document.get("documentId") != FORMAL_DOCUMENT_ID:
        raise ValueError("SOURCE_BLOCKED: not the official Google Doc")
    if not all(document.get(k) for k in ("revisionId", "tabId", "date")):
        raise ValueError("SOURCE_BLOCKED: missing revision, date or tab ID")
    if not DATE.fullmatch(document["date"]):
        raise ValueError("SOURCE_BLOCKED: invalid story date")
    if not isinstance(document.get("paragraphs"), list):
        raise ValueError("SOURCE_BLOCKED: no official paragraphs")
    people = roster.get("people")
    if not isinstance(people, list) or len(people) != 65:
        raise ValueError("SOURCE_BLOCKED: expected the 65-person official roster")
    genders = {p.get("id"): p.get("gender") for p in people}
    if len(genders) != 65 or sorted(genders) != [f"{i:02d}" for i in range(1, 66)]:
        raise ValueError("SOURCE_BLOCKED: non-unique or incomplete identities")
    if not all(genders[p] in ("男", "女") for p in genders):
        raise ValueError("SOURCE_BLOCKED: invalid genders")
    return genders


def extract(document, genders):
    """Preserve paragraphs and source positions; never invent a role or an event."""
    p = [clean(x.get("text", "") if isinstance(x, dict) else x)
         for x in document["paragraphs"]]
    out, issues = [], []
    index = 0
    while index < len(p):
        match = MEMBER.match(p[index])
        if not match:
            index += 1
            continue
        number = f"{int(match.group(1)):02d}"
        end = index + 1
        parts = [p[index][match.end():].strip()]
        while end < len(p) and not MEMBER.match(p[end]) and not STAFF.match(p[end]):
            if p[end]:
                parts.append(p[end])
            end += 1
        body = "\n".join(s for s in parts if s).strip()
        if genders.get(number) != match.group(2) or int(number) > 42:
            issues.append({"type":"ROLE_MISMATCH", "position":index, "member_id":number})
        elif not body:
            issues.append({"type":"EMPTY_MEMBER_SPEECH", "position":index, "member_id":number})
        else:
            out.append({"member_id":number, "text":body, "position":index,
                        "end_position":end - 1})
        index = end
    return out, issues


def source_index(row):
    match = POSITION.search(str(row.get("原文段落索引", "")))
    return int(match.group(1)) if match else None


def new_evidence_id(day, tab_id, member_id, body, occurrence):
    payload = "\0".join((day, tab_id, member_id, body)).encode("utf-8")
    digest = sha256(payload).hexdigest()[:16]
    return f"EW-{day.replace('-', '')}-H{digest}-{occurrence:02d}"


def reconcile(document, roster, records):
    genders = validate_sources(document, roster)
    observed, problems = extract(document, genders)
    date, tab_id = document["date"], document["tabId"]
    current = [x for x in records if x.get("剧情日期") == date]
    old_by_key = defaultdict(list)
    old_ids = set()
    for row in current:
        eid = row.get("证据ID")
        if not eid or eid in old_ids:
            problems.append({"type":"DUPLICATE_OR_MISSING_ID","evidence_id":eid})
            continue
        old_ids.add(eid)
        if row.get("正式页签") != tab_id:
            problems.append({"type":"WRONG_OFFICIAL_TAB","evidence_id":eid})
            continue
        if row.get("人物编号") not in genders:
            problems.append({"type":"UNKNOWN_STORED_ID","evidence_id":eid})
            continue
        old_by_key[(row["人物编号"], clean(row.get("原话", "")))].append(row)

    # Exact member+full-text multiset matching preserves existing evidence IDs
    # even if earlier paragraphs were inserted and source offsets have moved.
    for key in old_by_key:
        old_by_key[key].sort(key=lambda x: source_index(x) if source_index(x) is not None else -1)

    reused, moved, new, counts = [], [], [], defaultdict(int)
    for turn in observed:
        key = (turn["member_id"], turn["text"])
        counts[key] += 1  # Include reused copies: a later duplicate gets a distinct ID.
        if old_by_key[key]:
            # Prefer identical offset when multiple identical lines exist.
            candidates = old_by_key[key]
            same_index = next((i for i, x in enumerate(candidates)
                               if source_index(x) == turn["position"]), 0)
            saved = candidates.pop(same_index)
            reused.append(saved["证据ID"])
            prior_position = source_index(saved)
            if prior_position != turn["position"]:
                moved.append({"type":"MOVED_SAME_TEXT",
                              "evidence_id":saved["证据ID"],
                              "old_position":prior_position,
                              "new_position":turn["position"]})
        else:
            new.append({**turn, "date":date, "tab_id":tab_id,
                        "evidence_id":new_evidence_id(
                            date, tab_id, turn["member_id"], turn["text"], counts[key])})
    missing = [{"type":"MISSING_OR_EDITED","evidence_id":row["证据ID"],
                "member_id":row.get("人物编号"),"old_position":source_index(row)}
               for rows in old_by_key.values() for row in rows]
    problems.extend(missing)
    # New text may be a revision of old text. Never silently convert it to a
    # second adopted quote when previous adopted evidence became unmatchable.
    allowed = not problems
    status = "REVIEW_REQUIRED" if problems else ("CHANGES_PROPOSED" if new or moved
                                              else "NO_CHANGE")
    return {"status":status, "ready_to_create":new if allowed else [],
            "held_new":new if not allowed else [], "reused_ids":reused,
            "moved_for_review":moved, "conflicts":problems,
            "source_revision":document["revisionId"],
            "source_tab_id":tab_id, "date":date,
            "official_member_turns":len(observed),
            "stored_evidence_rows":len(current),
            "automatic_writes_executed":False,
            "published_or_adopted_by_this_script":False}


def member_context(records, member_id, limit=5):
    """Compact, source-attributed raw quotes for the five-Skill writing gate."""
    if not re.fullmatch(r"\d{2}", member_id):
        raise ValueError("member_id must be zero-padded NN")
    rows = [r for r in records if r.get("人物编号") == member_id
            and r.get("审核状态") == "已核对"
            and r.get("正式页签") and r.get("文档修订号")
            and r.get("原话") and r.get("证据ID")]
    rows.sort(key=lambda r:(r.get("剧情日期",""),source_index(r) or -1))
    return [{"证据ID":r["证据ID"],"日期":r["剧情日期"],
             "正式页签":r["正式页签"],"原话":r["原话"],
             "段落":r.get("原文段落索引"),"来源修订":r["文档修订号"]}
            for r in rows[-limit:]]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help="JSON snapshot: official Docs, roster, Airtable records")
    parser.add_argument("--member", help="emit most recent verified source quotes for NN")
    parser.add_argument("--strict", action="store_true",
                        help="exit 2 on any review-required condition")
    args = parser.parse_args()
    with open(args.input, encoding="utf-8") as stream:
        bundle = json.load(stream)
    result = reconcile(bundle["document"], bundle["roster"], bundle["records"])
    if args.member:
        result["member_context"] = member_context(bundle["records"], args.member)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if args.strict and result["conflicts"]:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
