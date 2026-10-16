#!/usr/bin/env python3
"""Verified France + US morning briefing delivery to the existing Telegram group.

No approved package means HELD. No credentials exposed outside scheduled main.
A distinct French edition audit protects the Romania + US edition unchanged.
"""
from datetime import datetime, time
import hashlib
import json
import os
from pathlib import Path
import re
import sys

from morning_france_us import build as build_fr, FR_OPENING
from morning_opening import parse_iso
from morning_group_delivery import (
    ROOT, TZ, DESTINATION, BOT, DOC_ID, SPEAKER, reserve, record_delivery,
)

APPROVAL_DIR = 'approved-morning-france-us'
AUDIT_DIR = 'morning-france-us-delivery'


def check_france_package(package, now, root=ROOT):
    now = now.astimezone(TZ)
    if now.weekday() >= 5 or not time(7, 0) <= now.time() <= time(8, 15):
        raise ValueError('Not a weekday morning delivery window')
    if not isinstance(package, dict) or package.get('status') != 'APPROVED_FRANCE_US_MORNING':
        raise ValueError('France+US editorial approval missing')
    if package.get('local_date') != now.date().isoformat():
        raise ValueError('France+US date mismatch')
    if package.get('target_group_title') != DESTINATION or package.get('bot_username') != BOT:
        raise ValueError('Telegram group/bot mismatch')
    approval = package.get('editorial_approval') or {}
    if (not isinstance(approval, dict) or approval.get('decision') != 'APPROVED'
            or not str(approval.get('approved_by', '')).strip()
            or not str(approval.get('source_review_reference', '')).strip()
            or not str(approval.get('france_country_impact_review', '')).strip()
            or not str(approval.get('cross_edition_dedup_review', '')).strip()):
        raise ValueError('Missing human-approved French source, impact or cross-edition review')
    approved_at = parse_iso(approval.get('approved_at'))
    if approved_at > now or approved_at.astimezone(TZ).date() != now.date():
        raise ValueError('Approval must be this morning')
    story = package.get('formal_story') or {}
    if story.get('document_id') != DOC_ID or not str(story.get('revision_id', '')).strip():
        raise ValueError('Must read real formal Google Docs revision')
    story_at = parse_iso(story.get('retrieved_at'))
    if story_at > approved_at or story_at.astimezone(TZ).date() != now.date():
        raise ValueError('Formal story not read on current morning')
    us_market = package.get('us_market_evidence')
    fr_market = package.get('france_evidence')
    summary = build_fr(now, us_market, fr_market)
    if summary['status'] != 'READY_FOR_EDITORIAL_REVIEW':
        raise ValueError('France+US news evidence failed: ' + summary['status'])
    for evidence in (us_market, fr_market):
        checked = parse_iso(evidence['source_checked_at'])
        if checked > approved_at or checked.astimezone(TZ).date() != now.date():
            raise ValueError('Original sources not checked before morning approval')
    # Prevent replay of a French original that was already published via official news.
    delivered = set()
    for path in (root / 'audit/telegram-delivery').glob('*.json'):
        try:
            receipt = json.loads(path.read_text(encoding='utf-8'))
        except (ValueError, OSError):
            continue
        if receipt.get('state') == 'DELIVERED':
            delivered.update(str(u).split('#')[0].split('?')[0]
                for u in receipt.get('evidence_urls', []) if isinstance(u, str))
    for story in fr_market['events']:
        if story['source_url'].split('#')[0].split('?')[0] in delivered:
            raise ValueError('Previously delivered French source URL; requires genuinely new evidence')
    expected = '\n\n'.join([
        summary['opening_draft'], summary['us_recap_draft'], summary['france_draft']])
    message = package.get('approved_text')
    if not isinstance(message, str) or not message.startswith(expected):
        raise ValueError('France/US facts were modified or not present in the approved text')
    if len(message) > 16000:
        raise ValueError('Message too long')
    remainder = message[len(expected):].strip()
    if remainder:
        # Only optional reviewed member dialogue; prevent arbitrary appended claims.
        if not SPEAKER.search(remainder) or not re.match(r'^\d{1,2}[男女][：:]', remainder):
            raise ValueError('Unreviewed extra facts are not permitted')
        if approval.get('member_dialogue_reviewed') is not True:
            raise ValueError('Member dialogues not reviewed')
        roster_file = root / 'skills/p004-chat-suite/characters/final-identity-65.json'
        roster = {str(x['id']): x for x in json.loads(roster_file.read_text(encoding='utf-8'))['people']}
        actors = SPEAKER.findall(remainder)
        approved_ids = {str(x).zfill(2) for x in approval.get('member_ids', [])}
        actual_ids = {str(int(n)).zfill(2) for n, _ in actors}
        if not actors or actual_ids != approved_ids:
            raise ValueError('Unexpected member IDs')
        for num, gender in actors:
            key = str(int(num)).zfill(2)
            if int(num) > 40 or key not in roster or roster[key]['gender'] != gender:
                raise ValueError('Wrong member identity or gender')
    return message.strip()


def run(now=None, root=ROOT, env=None):
    now = now or datetime.now(TZ)
    env = os.environ if env is None else env
    if env.get('GITHUB_EVENT_NAME') != 'schedule' or env.get('GITHUB_REF_NAME') != 'main':
        print('HELD: FR+US delivery only on the scheduled main workflow')
        return 'HELD'
    today = now.astimezone(TZ).date().isoformat()
    approval_file = root / 'news' / APPROVAL_DIR / (today + '.json')
    if not approval_file.is_file():
        print('HELD: no France+US approved package for ' + today)
        return 'HELD'
    try:
        package = json.loads(approval_file.read_text(encoding='utf-8'))
        message = check_france_package(package, now, root)
    except (ValueError, TypeError, KeyError, OSError) as exc:
        print('HELD: FR+US validation blocked: ' + str(exc)[:200])
        return 'HELD'
    token = env.get('GH_TOKEN', '').strip()
    repo = env.get('GITHUB_REPOSITORY', '').strip()
    if not token or repo != 'dalulu05168/Westcott-Intelligence':
        raise RuntimeError('Missing or wrong GitHub audit credentials')
    if not env.get('TELEGRAM_BOT_TOKEN') or not env.get('TELEGRAM_CHAT_ID'):
        raise RuntimeError('Telegram bot/group credentials missing')
    fingerprint = hashlib.sha256(approval_file.read_bytes()).hexdigest()
    reservation = reserve(today, fingerprint, token, repo, audit_folder=AUDIT_DIR)
    if reservation is None:
        print('ALREADY_RESERVED: French morning delivery not retried')
        return 'ALREADY_RESERVED'
    sys.path.insert(0, str(root / 'integrations/telegram'))
    import bridge
    transport = dict(env)
    transport['TELEGRAM_EXPECTED_BOT_USERNAME'] = BOT
    transport['TELEGRAM_EXPECTED_GROUP_TITLE'] = DESTINATION
    receipt = bridge.send_group_news(message, transport)
    record_delivery(reservation, token, receipt)
    print('DELIVERED France+US message_ids:', receipt['message_ids'])
    return 'DELIVERED'


if __name__ == '__main__':
    run()
