"""Manually reviewed publisher using original source article images, never generated art."""
import argparse
import base64
import hashlib
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
import re
import ipaddress
import sys
import urllib.error
import urllib.parse
import urllib.request

BASE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BASE / "scripts"))
import news_release_gate as gate
from bridge import send_group_news_from_official_article
from source_media import SourceMediaError, inspect_article
from editorial_policy import PolicyError, validate_release, COUNTRIES

EVENT_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{5,71}$")
FILE_RE = re.compile(r"^news/approved/[a-z0-9][a-z0-9_.-]{1,100}\.json$")
CONFIRM = "PUBLISH_REVIEWED_NEWS"


class PublicationError(RuntimeError):
    pass


def validate_public_https(value):
    if not isinstance(value, str) or len(value) > 2048:
        raise PublicationError("Image/article URL must be HTTPS with limited length.")
    parsed = urllib.parse.urlsplit(value)
    if (parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password
            or parsed.fragment or any(ord(c) < 32 for c in value)):
        raise PublicationError("Invalid original source HTTPS URL.")
    try:
        if parsed.port not in (None, 443):
            raise PublicationError("Nonstandard URL port not allowed.")
    except ValueError:
        raise PublicationError("Invalid URL port.") from None
    hostname = parsed.hostname.lower().rstrip(".")
    if (hostname == "localhost" or hostname.endswith((".local", ".internal"))
            or "." not in hostname):
        raise PublicationError("Nonpublic source hostname.")
    try:
        ip = ipaddress.ip_address(hostname)
    except ValueError:
        pass
    else:
        if not ip.is_global:
            raise PublicationError("Private/loopback source IP is not allowed.")
    return value


def select_original_image(ledger, selected_source_ids, default_source_id):
    """Allow photo upload only when directly matched to official source and reuse approved.

    Missing permission is NOT an instruction to scrape or copy: let Telegram render
    the original article's native link preview, if one is available.
    """
    sources = ledger["sources"]
    source_id = ledger.get("primary_article_source_id", default_source_id)
    if source_id not in selected_source_ids:
        raise PublicationError("Primary article must support a published claim.")
    article_url = validate_public_https(sources[source_id]["url"])
    metadata = ledger.get("original_image")
    if not metadata:
        return {"article_url": article_url, "image_url": None,
                "image_decision": "original_article_link_preview"}
    if not isinstance(metadata, dict):
        raise PublicationError("Invalid original_image metadata.")
    if metadata.get("source_id") != source_id:
        raise PublicationError("Image must be connected to selected primary article.")
    if metadata.get("article_url") != article_url:
        raise PublicationError("Image article URL does not match official evidence.")
    image_url = validate_public_https(metadata.get("image_url"))
    permitted = (
        metadata.get("matches_article_reviewed") is True
        and metadata.get("reuse_permission_verified") is True
        and isinstance(metadata.get("reviewed_by"), str)
        and bool(metadata["reviewed_by"].strip())
        and isinstance(metadata.get("rights_evidence_url"), str)
        and bool(metadata["rights_evidence_url"].strip())
    )
    if not permitted:
        return {"article_url": article_url, "image_url": None,
                "image_decision": "original_article_link_preview_rights_unverified"}
    validate_public_https(metadata["rights_evidence_url"])
    return {"article_url": article_url, "image_url": image_url,
            "image_decision": "verified_original_publisher_photo"}


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
    # Both Romanian-market and French-market releases must be Chinese, not
    # Romanian/French prose. Keep authentic company names, tickers and links.
    # This is a last-mile fail-closed check; the original-language evidence
    # excerpts remain unchanged and are not part of Telegram news body.
    if ledger.get("target_country") in COUNTRIES and any(
            len(re.findall(r"[\u3400-\u9fff]", fact)) < 2 for fact in facts):
        raise PublicationError("Country-specific Telegram news must be Chinese; no foreign-language story text.")
    # Derive URLs ONLY from the evidence for published claims.
    selected = set(ledger["publish_claim_ids"])
    urls = []
    selected_source_ids = set()
    for claim in ledger["claims"]:
        if claim["id"] not in selected:
            continue
        for evidence in claim.get("evidence", []):
            selected_source_ids.add(evidence["source_id"])
            source = ledger["sources"][evidence["source_id"]]
            if source.get("source_type") != "official":
                raise PublicationError("Every news claim requires an official primary-source URL.")
            published = gate.instant(source['published_at'])
            if now - published > timedelta(hours=36):
                raise PublicationError('Original article is older than 36 hours; do not recycle old news.')
            url = validate_public_https(source["url"])
            if url not in urls:
                urls.append(url)
    if not urls or len(urls) > 12:
        raise PublicationError("Source URLs missing or excessive.")
    # Source list is generated from the actual confirmed evidence, not from
    # free-form assistant text or unverified link labels.
    if any(ledger["sources"][source_id].get("source_type") != "official"
           for source_id in selected_source_ids):
        raise PublicationError("News has a nonofficial claimed evidence source.")
    text = "===== 资讯助理 =====\n\n" + "\n\n".join(facts)
    country = ledger.get('target_country')
    if country in COUNTRIES:
        marker, name = COUNTRIES[country]
        text = '===== 资讯助理 =====\n\n' + marker + ' ' + name + '\n\n' + '\n\n'.join(facts)
    text += "\n\n原始来源：\n" + "\n".join(urls)
    if len(text.encode("utf-8")) > 14000:
        raise PublicationError("News text is too long for concise Telegram release.")
    # Source page is the canonical visual context. No generated artwork is used.
    default_source_id = next(
        evidence["source_id"] for claim in ledger["claims"]
        if claim["id"] in selected
        for evidence in claim["evidence"]
    )
    media = select_original_image(ledger, selected_source_ids, default_source_id)
    ids = sorted(selected)
    fingerprint = hashlib.sha256(
        json.dumps({"country": country, "facts": sorted(set(" ".join(f.split()) for f in facts)),
                    "sources": sorted(urls)}, ensure_ascii=False,
                   sort_keys=True).encode("utf-8")
    ).hexdigest()
    claim_evidence_keys = []
    for claim in ledger['claims']:
        if claim['id'] not in selected:
            continue
        evidence_identity = sorted(set(
            (ledger['sources'][e['source_id']]['url'], ' '.join(e['excerpt'].split()))
            for e in claim['evidence']))
        claim_evidence_keys.append(hashlib.sha256(json.dumps(
            evidence_identity, ensure_ascii=False, sort_keys=True).encode('utf-8')).hexdigest())
    return {"event_id": event_id, "fingerprint": fingerprint,
            "target_country": country,
            "hourly_selection": ledger.get('hourly_selection'),
            "local_impact_claim_id": ledger.get('local_impact_claim_id'),
            "watch_next_claim_id": ledger.get('watch_next_claim_id'),
            "claim_kinds": {c['id']: c['kind'] for c in ledger['claims'] if c['id'] in selected},
            "claim_countries": {c['id']: c.get('target_country') for c in ledger['claims'] if c['id'] in selected},
            "claim_evidence_keys": sorted(set(claim_evidence_keys)),
            "ledger_digest": hashlib.sha256(json.dumps(ledger, ensure_ascii=False, sort_keys=True).encode('utf-8')).hexdigest(),
            "claim_ids": ids, "sources": urls, "media": media,
            "source_evidence": {url: [e['excerpt'] for c in ledger['claims']
                if c['id'] in selected for e in c['evidence']
                if ledger['sources'][e['source_id']]['url'] == url] for url in urls},
            "ledger": filename, "text": text}


def confirm_original_evidence(prepared):
    """Re-read each original before any reservation or message side effect.

    Matching excerpts proves that reviewed evidence still exists, not that a
    translation or economic interpretation is automatically correct.
    """
    checked = []
    for url, excerpts in prepared['source_evidence'].items():
        try:
            page = inspect_article(url)
        except SourceMediaError:
            raise PublicationError('Original evidence is unavailable; no Telegram send.') from None
        if page.get('canonical_matches_article') is False:
            raise PublicationError('Original evidence canonical differs from reviewed article.')
        body = ' '.join(page.get('source_text', '').split())
        if not body or any(' '.join(excerpt.split()) not in body for excerpt in excerpts):
            raise PublicationError('Reviewed excerpt no longer matches original source body.')
        checked.append({'url': url, 'source_text_sha256': hashlib.sha256(body.encode('utf-8')).hexdigest(),
                        'checked_at': datetime.now(timezone.utc).isoformat()})
    return checked


def inspect_media_for_preview(prepared):
    """Read only original publisher metadata; no images are downloaded."""
    url = prepared["media"]["article_url"]
    try:
        candidate = inspect_article(url)
        selected = prepared["media"]["image_url"]
        candidate["selected_photo_matches_og_image"] = (
            candidate["image_candidate_url"] == selected if selected else None)
        return {"status": "INSPECTED", **candidate}
    except SourceMediaError as exc:
        return {"status": "UNAVAILABLE", "article_url": url,
                "image_candidate_url": None, "reason": str(exc)}


def confirm_original_photo_source(prepared):
    """Fail closed if a licensed photo cannot be matched to publisher metadata."""
    photo = prepared["media"]["image_url"]
    if not photo:
        return None
    try:
        metadata = inspect_article(prepared["media"]["article_url"])
    except SourceMediaError:
        raise PublicationError(
            "Cannot inspect original article image; no Telegram send or audit reservation."
        ) from None
    matching = {item['url'] for item in metadata.get('article_image_candidates', [])}
    matching.add(metadata.get('image_candidate_url'))
    if photo not in matching:
        raise PublicationError("Selected image differs from original article image metadata.")
    if metadata["canonical_matches_article"] is False:
        raise PublicationError("Publisher canonical URL differs from reviewed article.")
    return metadata


def github_write(path, record, token, repo, sha=None):
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
        raise PublicationError("Invalid repository identifier.")
    url = "https://api.github.com/repos/" + repo + "/contents/" + path
    payload = {
        "message": "Record approved Telegram publication " + record["event_id"],
        "content": base64.b64encode(
            (json.dumps(record, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
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


def check_delivery_hour(acceptance, country, now=None):
    if not acceptance.get('quota_hour_key'):
        return
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    actual = country + '-' + current.strftime('%Y%m%dT%H')
    # Leave headroom for target verification and the bounded Telegram request.
    if acceptance['quota_hour_key'] != actual or current.minute >= 58:
        raise PublicationError('Delivery hour changed or closing; leave PENDING and do not send.')


def reserve(prepared, env, now=None):
    token = env.get("GITHUB_TOKEN", "").strip()
    repo = env.get("GITHUB_REPOSITORY", "").strip()
    if not token or not repo or env.get("GITHUB_REF_NAME") != "main":
        raise PublicationError("Publishing requires main branch and GITHUB_TOKEN.")
    acceptance = prepared.get('editorial_acceptance')
    if acceptance and acceptance.get('quota_hour_key'):
        actual = prepared['target_country'] + '-' + (now or datetime.now(timezone.utc)).astimezone(timezone.utc).strftime('%Y%m%dT%H')
        if acceptance['quota_hour_key'] != actual:
            raise PublicationError('Delivery hour changed after acceptance; revalidate without sending.')
    path = "audit/telegram-delivery/" + prepared["fingerprint"][:40] + ".json"
    country = prepared.get('target_country')
    claim_prefix = 'audit/telegram-claims/' + (country + '/' if country in COUNTRIES else '')
    claim_paths = [claim_prefix + key + '.json' for key in prepared['claim_evidence_keys']]
    record = {
        "state": "PENDING_DO_NOT_RETRY",
        "event_id": prepared["event_id"],
        "fingerprint": prepared["fingerprint"],
        "claim_ids": prepared["claim_ids"],
        "claim_evidence_keys": prepared['claim_evidence_keys'],
        "claim_reservation_paths": claim_paths,
        "editorial_acceptance": prepared.get('editorial_acceptance'),
        "evidence_urls": prepared["sources"],
        "ledger": prepared["ledger"],
        "ledger_digest": prepared.get('ledger_digest'),
        "original_article_url": prepared["media"]["article_url"],
        "original_image_url": prepared["media"]["image_url"],
        "image_decision": prepared["media"]["image_decision"],
        "reserved_at": (now or datetime.now(timezone.utc)).isoformat(),
        "message_ids": [],
        "source_rechecks": prepared.get('source_rechecks', []),
    }
    sha = github_write(path, record, token, repo)
    acceptance = prepared.get('editorial_acceptance')
    if acceptance:
        if acceptance.get('event_lock_key'):
            github_write('audit/telegram-events/' + country + '/' + acceptance['event_lock_key'] + '.json', {
                'event_id': prepared['event_id'], 'state': 'EVENT_RESERVED_DO_NOT_RETRY',
                'delivery_audit': path, 'reserved_at': record['reserved_at'],
            }, token, repo)
        github_write('audit/telegram-slots/' + acceptance['slot_key'] + '.json', {
            'event_id': prepared['event_id'], 'state': 'SLOT_RESERVED_DO_NOT_RETRY',
            'delivery_audit': path, 'reserved_at': record['reserved_at'],
            'target_country': country, 'window_end': acceptance['window_end'],
        }, token, repo)
    # Create-only atomic claims prevent rewritten copy, renamed files/IDs and
    # mixed old/new claim sets from escaping an earlier ambiguous delivery.
    # If any claim already exists, leave this parent PENDING and send nothing.
    for claim_path in claim_paths:
        github_write(claim_path, {
            'event_id': prepared['event_id'], 'state': 'CLAIM_RESERVED_DO_NOT_RETRY',
            'delivery_audit': path, 'reserved_at': record['reserved_at'],
        }, token, repo)
    return path, record, sha


def github_store_asset(path, data, token, repo):
    """Save preview directly in the repo; avoids Actions artifact storage quota."""
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
        raise PublicationError("Invalid GitHub repository.")
    url = "https://api.github.com/repos/" + repo + "/contents/" + path
    headers = {"Authorization": "Bearer " + token,
               "Accept": "application/vnd.github+json",
               "X-GitHub-Api-Version": "2022-11-28"}
    existing_sha = None
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=20) as response:
            current = json.load(response)
        old_bytes = base64.b64decode(current.get("content", "").replace("\\n", ""))
        if old_bytes == data:
            return "https://github.com/" + repo + "/blob/main/" + path
        raise PublicationError("Existing preview conflicts with reviewed content; refuse overwrite.")
    except urllib.error.HTTPError as exc:
        if exc.code != 404:
            raise PublicationError("Could not inspect preview file; HTTP " + str(exc.code)) from None
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        raise PublicationError("Could not inspect preview file.") from None
    payload = {"message": "Save reviewed 16:9 preview " + path.rsplit("/", 1)[-1],
               "content": base64.b64encode(data).decode("ascii"), "branch": "main"}
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"), method="PUT",
        headers={**headers, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=25) as response:
            created = json.load(response)
    except urllib.error.HTTPError as exc:
        raise PublicationError("Could not save preview; HTTP " + str(exc.code)) from None
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        raise PublicationError("Could not save preview.") from None
    if not (created.get("content") or {}).get("sha"):
        raise PublicationError("Missing preview commit acknowledgment.")
    return "https://github.com/" + repo + "/blob/main/" + path


def save_preview(prepared, env):
    token, repo = env.get("GITHUB_TOKEN", "").strip(), env.get("GITHUB_REPOSITORY", "").strip()
    if not token or not repo or env.get("GITHUB_REF_NAME") != "main":
        raise PublicationError("Preview requires main branch GITHUB_TOKEN.")
    base = "news/previews/" + prepared["fingerprint"][:40]
    text_url = github_store_asset(base + ".txt", prepared["text"].encode("utf-8"), token, repo)
    return {"status": "PREVIEW_ONLY", "event_id": prepared["event_id"],
            "original_article_url": prepared["media"]["article_url"],
            "original_image_url": prepared["media"]["image_url"],
            "image_decision": prepared["media"]["image_decision"],
            "official_page_metadata": inspect_media_for_preview(prepared),
            "text_url": text_url}


def publish(prepared, env):
    # Check the exact URLs before reservations or any Telegram side effect.
    if (not prepared.get("sources")
            or any(url not in prepared.get("text", "") for url in prepared["sources"])
            or prepared.get("media", {}).get("article_url") not in prepared.get("sources", [])):
        raise PublicationError("Official source URL absent from the publishable news message.")
    if env.get("PUBLISH_CONFIRMATION") != CONFIRM:
        raise PublicationError("Explicit publish confirmation required.")
    try:
        acceptance = validate_release(prepared, BASE)
    except PolicyError as exc:
        raise PublicationError(str(exc)) from None
    prepared = {**prepared, 'editorial_acceptance': acceptance}
    prepared = {**prepared, 'source_rechecks': confirm_original_evidence(prepared)}
    confirm_original_photo_source(prepared)
    path, record, sha = reserve(prepared, env)
    check_delivery_hour(acceptance, prepared['target_country'])
    try:
        receipt = send_group_news_from_official_article(
            prepared["text"], prepared["media"]["article_url"],
            prepared["media"]["image_url"], env)
    except Exception:
        # PENDING remains committed; a human must reconcile Telegram before any retry.
        raise PublicationError("Delivery uncertain; pending audit blocks automatic retry.") from None
    record["state"] = "DELIVERED"
    record["photo_message_id"] = receipt["photo_message_id"]
    record["image_delivery"] = receipt["image_delivery"]
    record["message_ids"] = receipt["message_ids"]
    record["group_title"] = receipt["group_title"]
    record["delivered_at"] = datetime.now(timezone.utc).isoformat()
    try:
        github_write(path, record, env["GITHUB_TOKEN"], env["GITHUB_REPOSITORY"], sha)
    except PublicationError:
        raise PublicationError("Telegram delivered but receipt update failed; reconcile PENDING manually.") from None
    return {"status": "DELIVERED", "event_id": prepared["event_id"],
            "image_delivery": receipt["image_delivery"],
            "photo_message_id": receipt["photo_message_id"],
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
        if args.mode == "preview":
            result = save_preview(prepared, os.environ)
        else:
            result = publish(prepared, os.environ)
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (PublicationError, ValueError, OSError, KeyError, TypeError) as exc:
        print(json.dumps({"status": "BLOCKED", "reason": str(exc)}, ensure_ascii=False),
              file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())


