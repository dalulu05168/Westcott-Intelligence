#!/usr/bin/env python3
"""Send *only* a dated, explicitly reviewed morning briefing to the fixed Telegram group.

No reviewed package -> no delivery. Atomic GitHub reservation before Telegram protects
against duplicates and ambiguous message status. No automatic retries after PENDING.
"""
import base64
from datetime import datetime, time
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import urllib.error
import urllib.request
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from morning_opening import build, parse_iso

TZ = ZoneInfo('Europe/Bucharest')
DESTINATION = '🌐~~~资讯快报'
BOT = 'NuvexaCheckBot'
DOC_ID = '1frtoFvohP3u2HfRzBPRZVLOzMfvnO-8Vi9iX3r5rmiM'
SPEAKER = re.compile(r'(?m)^[ \t]*(\d{1,2})(男|女)[：:]')


def check_package(package, now, root=ROOT):
    """Return the approved text; structural checks do not certify source authenticity."""
    local = now.astimezone(TZ)
    if local.weekday() >= 5 or not time(7, 0) <= local.time() <= time(8, 15):
        raise ValueError('Outside weekday morning delivery window')
    if not isinstance(package, dict) or package.get('status') != 'APPROVED_FOR_MORNING_GROUP':
        raise ValueError('Morning editorial approval absent')
    today = local.date().isoformat()
    if package.get('local_date') != today:
        raise ValueError('Morning package date mismatch')
    if package.get('target_group_title') != DESTINATION or package.get('bot_username') != BOT:
        raise ValueError('Wrong Telegram group or bot')
    review = package.get('editorial_approval') or {}
    if not isinstance(review, dict) or not str(review.get('approved_by', '')).strip():
        raise ValueError('Real editorial approver missing')
    if review.get('decision') != 'APPROVED' or not review.get('source_review_reference'):
        raise ValueError('Affirmative editorial decision/source evidence missing')
    approved_at = parse_iso(review.get('approved_at'))
    if approved_at.astimezone(TZ).date().isoformat() != today or approved_at > now:
        raise ValueError('Editorial approval timestamp invalid')
    story = package.get('formal_story') or {}
    if (not isinstance(story, dict) or story.get('document_id') != DOC_ID
            or not str(story.get('revision_id', '')).strip()):
        raise ValueError('Formal Google Docs revision missing')
    read_at = parse_iso(story.get('retrieved_at'))
    if read_at.astimezone(TZ).date().isoformat() != today or read_at > approved_at:
        raise ValueError('Formal story not checked before approval today')
    evidence = package.get('market_evidence')
    report = build(local, evidence)
    if report['status'] != 'READY_FOR_EDITORIAL_REVIEW':
        raise ValueError('US close evidence not accepted: ' + report['status'])
    source_at = parse_iso(evidence['source_checked_at'])
    if source_at.astimezone(TZ).date().isoformat() != today or source_at > approved_at:
        raise ValueError('US close evidence not checked before approval today')
    message = package.get('approved_text')
    if (not isinstance(message, str) or report['opening_draft'] not in message
            or report['us_recap_draft'] not in message):
        raise ValueError('Exact validated opening/index recap missing from approved text')
    if len(message.strip()) > 16000 or not message.lstrip().startswith('===== 资讯助理 ====='):
        raise ValueError('Approved Telegram message format/size invalid')
    roster_file = root / 'skills/p004-chat-suite/characters/final-identity-65.json'
    roster = {str(x['id']): x for x in json.loads(roster_file.read_text(encoding='utf-8'))['people']}
    speakers = SPEAKER.findall(message)
    if speakers:
        if review.get('member_dialogue_reviewed') is not True:
            raise ValueError('Member dialogue has not been reviewed')
        ids = {str(int(i)).zfill(2) for i, _ in speakers}
        approved_ids = {str(i).zfill(2) for i in review.get('member_ids', [])}
        if ids != approved_ids:
            raise ValueError('Member IDs differ from approved roles')
        for number, gender in speakers:
            ident = str(int(number)).zfill(2)
            if int(number) > 40 or ident not in roster or roster[ident]['gender'] != gender:
                raise ValueError('Unauthorized or mismatched member identity')
    return message.strip()


def github_request(method, url, token, payload=None):
    headers = {'Authorization': 'Bearer ' + token, 'Accept': 'application/vnd.github+json',
               'X-GitHub-Api-Version': '2022-11-28'}
    data = None
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode('utf-8')
        headers['Content-Type'] = 'application/json'
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=25) as resp:
        return json.load(resp)


def reserve(today, fingerprint, token, repo, audit_folder='morning-opening-delivery'):
    """A pre-existing PENDING/DELIVERED audit always prevents a second send."""
    if audit_folder not in ('morning-opening-delivery', 'morning-france-us-delivery'):
        raise ValueError('Invalid audited morning edition')
    uri = f'https://api.github.com/repos/{repo}/contents/audit/{audit_folder}/{today}.json'
    try:
        github_request('GET', uri, token)
        return None
    except urllib.error.HTTPError as exc:
        if exc.code != 404:
            raise
    record = {'state': 'PENDING', 'date': today, 'sha256': fingerprint,
              'group_title': DESTINATION, 'reserved_at': datetime.now(TZ).isoformat()}
    encoded = base64.b64encode((json.dumps(record, ensure_ascii=False, indent=2) + '\n').encode()).decode()
    try:
        created = github_request('PUT', uri, token, {
            'message': 'audit: reserve morning group delivery ' + today,
            'content': encoded, 'branch': 'main'})
    except urllib.error.HTTPError as exc:
        if exc.code in (409, 422):
            return None
        raise
    return uri, created['content']['sha'], record


def record_delivery(reservation, token, receipt):
    uri, sha, record = reservation
    record.update({'state': 'DELIVERED', 'message_ids': receipt['message_ids'],
                   'delivered_at': datetime.now(TZ).isoformat(),
                   'group_id': receipt['group_id']})
    encoded = base64.b64encode((json.dumps(record, ensure_ascii=False, indent=2) + '\n').encode()).decode()
    github_request('PUT', uri, token, {'message': 'audit: confirm morning delivery ' + record['date'],
                                       'content': encoded, 'sha': sha, 'branch': 'main'})


def run(now=None, root=ROOT, env=None):
    now = now or datetime.now(TZ)
    env = os.environ if env is None else env
    if env.get('GITHUB_EVENT_NAME') != 'schedule' or env.get('GITHUB_REF_NAME') != 'main':
        print('HELD: only scheduled main workflow may deliver')
        return 'HELD'
    today = now.astimezone(TZ).date().isoformat()
    approval_file = root / 'news/approved-morning' / (today + '.json')
    if not approval_file.is_file():
        print('HELD: no approved morning package for ' + today)
        return 'HELD'
    try:
        package = json.loads(approval_file.read_text(encoding='utf-8'))
        message = check_package(package, now, root)
    except (ValueError, TypeError, KeyError, OSError) as exc:
        print('HELD: morning package validation failed: ' + str(exc)[:180])
        return 'HELD'
    token = env.get('GH_TOKEN', '').strip()
    repo = env.get('GITHUB_REPOSITORY', '').strip()
    if not token or repo != 'dalulu05168/Westcott-Intelligence':
        raise RuntimeError('GitHub audit credentials/repository missing or incorrect')
    if not env.get('TELEGRAM_BOT_TOKEN') or not env.get('TELEGRAM_CHAT_ID'):
        raise RuntimeError('Telegram group credentials missing')
    fingerprint = hashlib.sha256(approval_file.read_bytes()).hexdigest()
    reservation = reserve(today, fingerprint, token, repo)
    if reservation is None:
        print('ALREADY_RESERVED: no retries of PENDING/DELIVERED')
        return 'ALREADY_RESERVED'
    sys.path.insert(0, str(root / 'integrations/telegram'))
    import bridge
    transport_env = dict(env)
    transport_env['TELEGRAM_EXPECTED_BOT_USERNAME'] = BOT
    transport_env['TELEGRAM_EXPECTED_GROUP_TITLE'] = DESTINATION
    # A network error after reservation leaves PENDING. Never auto-retry.
    receipt = bridge.send_group_news(message, transport_env)
    record_delivery(reservation, token, receipt)
    print('DELIVERED with Telegram message_ids:', receipt['message_ids'])
    return 'DELIVERED'


if __name__ == '__main__':
    run()
