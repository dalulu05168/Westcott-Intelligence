#!/usr/bin/env python3
"""Fail-closed, offline evidence-receipt gate; NOT a truth or source-authenticity oracle."""
import argparse
import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import urlparse
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

HEX_SHA = re.compile(r"^[0-9a-f]{64}$")


def instant(value):
    value = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if value.utcoffset() is None:
        raise ValueError("timestamp must contain an offset")
    return value.astimezone(timezone.utc)


def https(url):
    try:
        parsed = urlparse(url)
        return parsed.scheme == "https" and bool(parsed.hostname) and not parsed.username
    except (TypeError, ValueError):
        return False


def validate(data, root, now=None):
    """Return machine-verifiable problems; an empty result is NOT proof that claims are true."""
    errors = []
    now = now or datetime.now(timezone.utc)
    if not isinstance(data, dict):
        return ["RECEIPT_NOT_OBJECT"]
    if data.get("version") != 1:
        errors.append("INVALID_VERSION")
    try:
        recorded = instant(data["recorded_at"])
        if recorded > now + timedelta(minutes=5) or now - recorded > timedelta(hours=24):
            errors.append("STALE_OR_FUTURE_RECEIPT")
    except (KeyError, TypeError, ValueError, AttributeError):
        recorded = None
        errors.append("INVALID_RECORDED_AT")
    actions = data.get("actions")
    if not isinstance(actions, list) or not actions:
        return errors + ["NO_ACTIONS"]
    seen = set()
    for idx, action in enumerate(actions):
        tag = f"ACTION_{idx}"
        if not isinstance(action, dict):
            errors.append(tag + "_INVALID")
            continue
        ident = action.get("id")
        if not isinstance(ident, str) or not ident or ident in seen:
            errors.append(tag + "_DUPLICATE_OR_MISSING_ID")
        seen.add(ident)
        if action.get("status") not in ("DONE", "BLOCKED", "NOT_REQUIRED"):
            errors.append(tag + "_INVALID_STATUS")
        if data.get("claim") == "COMPLETED" and action.get("status") != "DONE":
            errors.append(tag + "_INCOMPLETE")
        if action.get("status") != "DONE":
            continue
        evidence = action.get("evidence")
        if not isinstance(evidence, list) or not evidence:
            errors.append(tag + "_NO_EVIDENCE")
            continue
        for j, item in enumerate(evidence):
            key = f"{tag}_EVIDENCE_{j}"
            if not isinstance(item, dict) or item.get("kind") not in ("command", "source", "write_readback"):
                errors.append(key + "_INVALID_KIND")
                continue
            try:
                filepath = (root / item["path"]).resolve()
                if not filepath.is_relative_to(root.resolve()) or not filepath.is_file():
                    raise ValueError("unsafe or missing evidence")
                contents = filepath.read_bytes()
                digest = item["sha256"]
                if not isinstance(digest, str) or not HEX_SHA.fullmatch(digest) or hashlib.sha256(contents).hexdigest() != digest:
                    errors.append(key + "_SHA_MISMATCH")
                excerpt = item.get("must_contain")
                if not isinstance(excerpt, str) or not excerpt.strip() or excerpt not in contents.decode("utf-8"):
                    errors.append(key + "_EXCERPT_MISSING")
                if recorded is not None:
                    checked = instant(item["observed_at"])
                    if checked > recorded or recorded - checked > timedelta(hours=24):
                        errors.append(key + "_TIME_INVALID")
                if item["kind"] == "command" and (item.get("exit_code") != 0 or not item.get("command")):
                    errors.append(key + "_COMMAND_NOT_SUCCESSFUL")
                if item["kind"] == "source" and not https(item.get("url")):
                    errors.append(key + "_SOURCE_URL_INVALID")
                if item["kind"] == "write_readback" and not item.get("target"):
                    errors.append(key + "_TARGET_MISSING")
            except (KeyError, TypeError, ValueError, UnicodeError, OSError, AttributeError):
                errors.append(key + "_UNREADABLE_OR_INVALID")
    if data.get("claim") not in ("COMPLETED", "PARTIAL", "BLOCKED"):
        errors.append("INVALID_CLAIM")
    elif data["claim"] != "COMPLETED":
        errors.append("CLAIM_NOT_COMPLETED")
    if data.get("task_type") == "news":
        news = data.get("news")
        if not isinstance(news, dict):
            return errors + ["NEWS_METADATA_MISSING"]
        try:
            zone = ZoneInfo(news["market_timezone"])
            today = news["local_date"]
            for field in ("first_published_at", "event_at"):
                if instant(news[field]).astimezone(zone).date().isoformat() != today:
                    errors.append("NEWS_NOT_TARGET_LOCAL_DAY:" + field)
            values = news["indicators"]
            if not isinstance(values, list) or not values:
                errors.append("NEWS_NO_INDICATORS")
            else:
                for i, row in enumerate(values):
                    if not all(row.get(k) for k in ("name", "unit", "basis", "market_state", "source_url", "as_of")):
                        errors.append(f"INDICATOR_{i}_INCOMPLETE")
                    if not https(row.get("source_url")):
                        errors.append(f"INDICATOR_{i}_SOURCE_INVALID")
                    if instant(row["as_of"]) > recorded:
                        errors.append(f"INDICATOR_{i}_FUTURE")
                    a, b = Decimal(str(row["reported"])), Decimal(str(row["official"]))
                    if not a.is_finite() or not b.is_finite() or a != b:
                        errors.append(f"INDICATOR_{i}_MISMATCH")
            image = news.get("image")
            if image is not None and (not https(image.get("original_url")) or not https(image.get("article_url")) or
                                      image.get("same_event") is not True or image.get("reuse_rights_checked") is not True):
                errors.append("IMAGE_NOT_VERIFIED")
        except (KeyError, TypeError, ValueError, AttributeError, ZoneInfoNotFoundError, InvalidOperation):
            errors.append("NEWS_METADATA_INVALID")
    return sorted(set(errors))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("receipt", type=Path)
    parser.add_argument("--root", type=Path, default=Path("."))
    args = parser.parse_args()
    try:
        record = json.loads(args.receipt.read_text(encoding="utf-8"))
        errors = validate(record, args.root)
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        errors = ["RECEIPT_UNREADABLE:" + type(exc).__name__]
    print(json.dumps({"gate": "PASS" if not errors else "BLOCK", "errors": errors,
                      "limitation": "Offline format, evidence-file, numeric and date consistency only; independent original-source verification and human approval still required."}, ensure_ascii=False))
    return 0 if not errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
