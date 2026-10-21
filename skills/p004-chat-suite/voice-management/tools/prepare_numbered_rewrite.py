#!/usr/bin/env python3
"""Build evidence-grounded character context for an LLM voice rewrite.

This program resolves identity, profile and historic voice evidence. It does NOT
generate rewritten dialogue by itself; the connected model does that next.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
ROSTER = ROOT / "characters/final-identity-65.json"
VOICE_INDEX = ROOT / "voice-management/voice-index-2026-10-21.json"
PROFILES = ROOT / "characters/profiles"

LINE = re.compile(r"^\s*(?P<id>\d{1,2})\s*(?P<gender>[男女])?\s*[：:]\s*(?P<body>.+?)\s*$")
VERB = re.compile(r"^\s*按\s*(?P<id>\d{1,2})\s*(?P<gender>[男女])?\s*口吻(?:改写|修改|改)?\s*[：:]\s*(?P<body>.+?)\s*$")
SPACE = re.compile(r"^\s*(?P<id>\d{1,2})\s*(?P<gender>[男女])\s+(?P<body>.+?)\s*$")

class VoiceInputError(ValueError):
    pass

def parse_lines(text: str) -> list[dict]:
    lines = []
    for lineno, raw in enumerate(text.splitlines(), 1):
        if not raw.strip():
            continue
        match = VERB.match(raw) or LINE.match(raw) or SPACE.match(raw)
        if match is None:
            raise VoiceInputError(f"第{lineno}行缺少可识别的编号标签：{raw}")
        number = int(match.group("id"))
        if number not in range(1, 66):
            raise VoiceInputError(f"第{lineno}行编号超出01—65范围：{number}")
        lines.append({"line": lineno, "id": f"{number:02d}",
                      "gender": match.group("gender"), "original": match.group("body")})
    if not lines:
        raise VoiceInputError("请输入带人物编号的原句")
    return lines

def load_context(text: str, root: Path = ROOT, *, evidence_limit: int = 9) -> dict:
    parsed = parse_lines(text)
    roster = json.loads((root / "characters/final-identity-65.json").read_text(encoding="utf-8-sig"))["people"]
    voices = json.loads((root / "voice-management/voice-index-2026-10-21.json").read_text(encoding="utf-8-sig"))["members"]
    if len(roster) != 65 or {x["id"] for x in roster} != {f"{n:02d}" for n in range(1, 66)}:
        raise VoiceInputError("最终身份表并非完整65人，停止人物解析")
    roster_by_id = {x["id"]: x for x in roster}
    voice_by_id = {x["id"]: x for x in voices}
    people = {}
    turns = []
    for item in parsed:
        ident = item["id"]
        r = roster_by_id[ident]
        if item["gender"] is not None and item["gender"] != r["gender"]:
            raise VoiceInputError(f"第{item['line']}行{ident}号性别不匹配：正式档为{r['gender']}")
        if ident not in people:
            profile_path = root / "characters/profiles" / f"{ident}.json"
            if not profile_path.is_file():
                raise VoiceInputError(f"缺少{ident}号详细人物档")
            p = json.loads(profile_path.read_text(encoding="utf-8-sig"))
            for key in ("id", "name", "gender", "age", "occupation", "investment_years",
                        "capital_scale", "student_seniority", "location", "background_note"):
                if p.get(key) != r.get(key):
                    raise VoiceInputError(f"{ident}号身份档案冲突：{key}")
            v = voice_by_id.get(ident, {}).get("voice", {})
            evidence = v.get("evidence", [])
            people[ident] = {
                "identity": {k: r.get(k) for k in ("id", "name", "nick", "gender", "age",
                    "occupation", "investment_years", "capital_scale", "student_seniority",
                    "location", "background_note")},
                "creative_personality_not_approved": {
                    "main_behavior": p.get("main_behavior"),
                    "secondary_behavior": p.get("secondary_behavior"),
                    "interest_triggers": p.get("interest_triggers", []),
                    "sentence_length_hint": p.get("voice", {}).get("sentence_length"),
                    "register_hint": p.get("voice", {}).get("register"),
                    "emoji_hint": p.get("voice", {}).get("emoji_style"),
                    "draft_status": p.get("voice", {}).get("voice_status"),
                },
                "historic_speech": {
                    "evidence_status": v.get("evidence_status", "NO_EVIDENCE"),
                    "observed_turns": v.get("observed_turns", 0),
                    "approved_style": v.get("approved_style", False),
                    "examples": evidence[:evidence_limit],
                },
                "participation": ("edit_text_only_not_authorized_in_story" if int(ident) > 42 else "active_eligible"),
            }
        turns.append({"label": f"{ident}{r['gender']}", "original": item["original"],
                      "line": item["line"], "person_id": ident})
    return {
        "mode": "VOICE_REWRITE_CONTEXT_ONLY",
        "source": "GitHub roster + profile per id + historical voice-index snapshot (not live Docs)",
        "instructions": [
            "Match the person's actual dialogue examples first, then cautiously use occupational context and unapproved personality hints.",
            "Do not treat draft traits or historical examples as user-approved mandatory catchphrases.",
            "Keep stance, uncertainty, numbers, dates, symbols, trading codes, facts and the original label intact.",
            "Do not invent jobs, family, trades, ownership, profits or market events; never transpose historical events into the new line.",
            "Different people must have distinct rhythms; avoid templated emoji and unnecessary rewriting.",
            "If evidence is absent, use conservative natural language and disclose limited confidence.",
            "Only return rewritten labeled turns; 43–65 may be edited on explicit request but not inserted into new official scenes.",
        ],
        "people": people,
        "turns": turns,
    }

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--text", help="Labeled dialogue; when absent, read from stdin")
    parser.add_argument("--evidence-limit", type=int, default=9)
    args = parser.parse_args(argv)
    if args.evidence_limit < 0:
        parser.error("--evidence-limit must be >= 0")
    original = args.text if args.text is not None else sys.stdin.read()
    try:
        result = load_context(original, evidence_limit=args.evidence_limit)
    except (VoiceInputError, FileNotFoundError, json.JSONDecodeError) as error:
        print(json.dumps({"error": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0

if __name__ == "__main__":
    sys.exit(main())
