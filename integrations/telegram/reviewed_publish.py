"""Manually approved news-to-Telegram pipeline. Never schedules or scrapes news."""
import argparse
import base64
import hashlib
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

BASE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BASE / "scripts"))
import news_release_gate as gate
from image_background import render_background, select_topic
from bridge import send_group_news_with_image

EVENT_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{5,71}$")
FILE_RE = re.compile(r"^news/approved/[a-z0-9][a-z0-9_.-]{1,100}\\.json$")
CONFIRM = "PUBLISH_REVIEWED_NEWS"


class PublicationError(RuntimeError):
    pass


def prepare(ledger, filename, now=None):
    if not FILE_RE.fullmatch(filename):
        raise PublicationError("Ledger path must be news/approved/<filename>.json")
    event_id = ledger.get("event_id", "")
    if not isinstance(event_id, str) or not EVENT_RE.fullmatch(event_id):
        raise PublicationError("event_id must be a stable lowercase identifier.")
    checked = gate.evaluate(ledger)
    if checked["status"] != "PASS":
        raise PublicationError("Evidence gate did not PASS: " + ",".join(checked.get("errors", [])))
    now = now or datetime.now(timezone.utc)
    try:
        reviewed_at = gate.instant(ledger["executed_at"])
    except (KeyError, ValueError, TypeError):
        raise PublicationError("Missing evidence review execution time.") from None
    if reviewed_at > now or now - reviewed_at > timedelta(hours=36):
        raise PublicationError("News review is future-dated or older than 36 hours.")
    facts = checked["approved_facts"]
    if not facts or any(not isinstance(f, str) or not f.strip() for f in facts):
        raise PublicationError("No approved text.")
    # Derive URLs ONLY from the evidence for published claims.
    selected = set(ledger["publish_claim_ids"])
    urls = []
    for claim in ledger["claims"]:
        if claim["id"] not in selected:
            continue
        for evidence in claim.get("evidence", []):
            source = ledger["sources"][evidence["source_id"]]
            url = source["url"]
            if url not in urls:
                urls.append(url)
    if not urls or len(urls) > 12:
        raise PublicationError("Source URLs missing or excessive.")
    text = "===== 资讯助理 =====\\n\\n" + "\\n\\n".join(facts)
    text += "\\n\\n原始来源：\\n" + "\\n".join(urls)
    if len(text.encode("utf-8")) > 14000:
        raise PublicationError("News text is too long for concise Telegram release.")
    topic = select_topic(facts)
    ids = sorted(selected)
    fingerprint = hashlib.sha256(
        json.dumps({"claims": ids, "sources": sorted(urls)}, ensure_ascii=False,
                   sort_keys=True).encode("utf-8")
    ).hexdigest()
    return {"event_id": event_id, "fingerprint": fingerprint,
            "claim_ids": ids, "sources": urls, "topic": topic,
            "ledger": filename, "text": text}


def github_write(path, record, token, repo, sha=None):
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
        raise PublicationError("Invalid repository identifier.")
    url = "https://api.github.com/repos/" + repo + "/contents/" + path
    payload = {
        "message": "Record approved Telegram publication " + record["event_id"],
        "content": base64.b64encode(
            (json.dumps(record, ensure_ascii=False, indent=2) + "\\n").encode("utf-8")
        ).decode("ascii"),
        "branch": "main",
    }
    if sha:
        payload["sha"] = sha
    request = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"), method="PUT",
        headers={
            "Authorization": "Bearer " + token,
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            result = json.load(response)
    except urllib.error.HTTPError as exc:
        if exc.code in (409, 422):
            raise PublicationError("Publication already reserved or conflicting; do not retry.") from None
        raise PublicationError("Could not record publication; HTTP " + str(exc.code)) from None
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        raise PublicationError("Publication record failed; do not send.") from None
    sha_after = (result.get("content") or {}).get("sha")
    if not sha_after:
        raise PublicationError("GitHub reservation reply missing content sha.")
    return sha_after


def reserve(prepared, env, now=None):
    token = env.get("GITHUB_TOKEN", "").strip()
    repo = env.get("GITHUB_REPOSITORY", "").strip()
    if not token or not repo or env.get("GITHUB_REF_NAME") != "main":
        raise PublicationError("Publishing requires main branch and GITHUB_TOKEN.")
    path = "audit/telegram-delivery/" + prepared["fingerprint"][:40] + ".json"
    record = {
        "state": "PENDING_DO_NOT_RETRY",
        "event_id": prepared["event_id"],
        "fingerprint": prepared["fingerprint"],
        "claim_ids": prepared["claim_ids"],
        "evidence_urls": prepared["sources"],
        "ledger": prepared["ledger"],
        "image_topic": prepared["topic"],
        "reserved_at": (now or datetime.now(timezone.utc)).isoformat(),
        "message_ids": [],
    }
    sha = github_write(path, record, token, repo)
    return path, record, sha


def publish(prepared, image_bytes, env):
    if env.get("PUBLISH_CONFIRMATION") != CONFIRM:
        raise PublicationError("Explicit publish confirmation required.")
    path, record, sha = reserve(prepared, env)
    try:
        receipt = send_group_news_with_image(prepared["text"], image_bytes, env)
    except Exception:
        # PENDING remains committed; a human must reconcile Telegram before any retry.
        raise PublicationError("Delivery uncertain; pending audit blocks automatic retry.") from None
    record["state"] = "DELIVERED"
    record["photo_message_id"] = receipt["photo_message_id"]
    record["message_ids"] = receipt["message_ids"]
    record["group_title"] = receipt["group_title"]
    record["delivered_at"] = datetime.now(timezone.utc).isoformat()
    try:
        github_write(path, record, env["GITHUB_TOKEN"], env["GITHUB_REPOSITORY"], sha)
    except PublicationError:
        raise PublicationError("Telegram delivered but receipt update failed; reconcile PENDING manually.") from None
    return {"status": "DELIVERED", "event_id": prepared["event_id"],
            "topic": prepared["topic"], "photo_message_id": receipt["photo_message_id"],
            "message_ids": receipt["message_ids"], "audit_path": path}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["preview", "publish"], required=True)
    parser.add_argument("--ledger", required=True)
    args = parser.parse_args()
    try:
        # Path is resolved only after strict relative-path validation.
        if not FILE_RE.fullmatch(args.ledger):
            raise PublicationError("Invalid approved ledger path.")
        ledger = json.loads((BASE / args.ledger).read_text(encoding="utf-8"))
        prepared = prepare(ledger, args.ledger)
        png_bytes = render_background(prepared["topic"])
        Path("/tmp/westcott-news-preview.png").write_bytes(png_bytes)
        Path("/tmp/westcott-news-preview.txt").write_text(prepared["text"], encoding="utf-8")
        if args.mode == "preview":
            result = {"status": "PREVIEW_ONLY", "event_id": prepared["event_id"],
                      "topic": prepared["topic"], "image_px": "1600x900",
                      "claims": prepared["claim_ids"], "sources": prepared["sources"]}
        else:
            result = publish(prepared, png_bytes, os.environ)
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (PublicationError, ValueError, OSError, KeyError, TypeError) as exc:
        print(json.dumps({"status": "BLOCKED", "reason": str(exc)}, ensure_ascii=False),
              file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
