#!/usr/bin/env python3
"""Rebuild the inline 65-person persona-memory snapshot and all five prepared task prompts.

Does not call ChatGPT Tasks or change schedules. Only USER-ADOPTED source messages
already stored in memory/long-term/members/*.json are projected.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

from validate_runtime_context import ROOT, BEGIN, END, validate

SUITE = ROOT / "skills/p004-chat-suite/references"
SCHEDULED = ROOT / "integrations/chatgpt-scheduled"
CONTEXT = SUITE / "runtime-context-v1.5.2.txt"
MANIFEST = SCHEDULED / "UPDATE-EXISTING-TASKS.json"
TAG = "ADOPTED_MEMORY_CONFIRMED"
START, STOP = "[" + TAG + "]", "[/" + TAG + "]"


def records_from_members():
    rows = []
    for path in sorted((ROOT / "memory/long-term/members").glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        if data["id"] != path.stem or not re.fullmatch(r"\d{2}", path.stem):
            raise ValueError("Member file/ID mismatch: " + str(path))
        for entry in data.get("observed_in_submitted_story", []):
            rows.append({"id": path.stem, **{
                key: entry[key] for key in ("message_id", "node", "kind", "text")}})
    return rows


def replace_once(text, start, stop, replacement):
    if text.count(start) != 1 or text.count(stop) != 1:
        raise ValueError("Missing/duplicate context delimiter")
    a, b = text.index(start), text.index(stop) + len(stop)
    if b < a:
        raise ValueError("Invalid context order")
    return text[:a] + replacement + text[b:]


def sha256(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def render_context(original, rows):
    encoded = "\n".join(json.dumps(row, ensure_ascii=False,
                                     separators=(",", ":")) for row in rows)
    return replace_once(original, START, STOP, START + "\n" + encoded + "\n" + STOP)


def prepare():
    rows = records_from_members()
    original = CONTEXT.read_bytes().decode("utf-8")
    context = render_context(original, rows)
    # Checks identity/voice projections, all 77+ adopted records and their daily
    # sources. Review-only or excluded messages cannot pass this comparison.
    result = validate(context)
    if result["adopted_memory_entries"] != len(rows):
        raise ValueError("Unexpected adopted-history count")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if len(manifest["updates"]) != 5:
        raise ValueError("Expected exactly the original five prepared tasks")
    generated = {CONTEXT: context}
    for task in manifest["updates"]:
        path = SCHEDULED / task["file"]
        body = path.read_bytes().decode("utf-8")
        replacement = replace_once(body, BEGIN, END, context)
        generated[path] = replacement
        if task.get("context_version") != "v1.5.2":
            task["context_version"] = "v1.5.2"
        task["prompt_sha256"] = sha256(replacement)
        task["prompt_characters"] = len(replacement)
        task["prompt_utf8_bytes"] = len(replacement.encode("utf-8"))
    manifest["status"] = "PREPARED_NOT_APPLIED"
    manifest["online_application"] = "NOT_PERFORMED"
    manifest["confirmed_adopted_member_entries"] = len(rows)
    manifest["confirmed_adopted_member_count"] = len(set(row["id"] for row in rows))
    manifest["excluded_or_review_unadopted"] = True
    generated[MANIFEST] = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    return generated, len(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true",
                      help="fail if any prepared context, prompt or checksum is stale")
    mode.add_argument("--write", action="store_true",
                      help="refresh the existing prepared package, NEVER online Tasks")
    args = parser.parse_args()
    generated, count = prepare()
    # GitHub line endings may be CRLF; compare content semantically but enforce
    # all characters, history and hashes. --write uses consistent LF.
    changed = [p for p, value in generated.items()
               if p.read_bytes().decode("utf-8") != value]
    if args.write:
        for path in changed:
            path.write_text(generated[path], encoding="utf-8", newline="\n")
    elif changed:
        raise SystemExit("STALE prepared file(s): " +
                         ", ".join(str(p.relative_to(ROOT)) for p in changed))
    print(f"PASS: 65 canonical identities; {count} adopted member events; "
          f"five synchronized prepared prompts; {len(changed)} {'written' if args.write else 'stale files'}")


if __name__ == "__main__":
    main()
