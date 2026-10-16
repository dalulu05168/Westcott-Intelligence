#!/usr/bin/env python3
"""Build auditable writing context and check drafts; never send or adopt content.

Hashes prove local reads, not source authenticity. Semantic truth, voice quality,
state-change support and novelty across different sources still require review.
"""
import argparse
from datetime import date, datetime, timedelta
import hashlib
import json
from pathlib import Path
import re
import unicodedata
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

ROOT = Path(__file__).resolve().parents[1]
FORMAL_DOC_ID = '1frtoFvohP3u2HfRzBPRZVLOzMfvnO-8Vi9iX3r5rmiM'
ADOPTED = {'ADOPTED_IN_SUBMITTED_TRANSCRIPT', 'ADOPTED_IN_USER_SUBMITTED_STORY'}
LABEL = re.compile(r'(?m)^[ \t]*(?:(\d{1,2})[ \t]*([男女])[ \t]*(?:[:：]|(?=\n|$))|={2,}[ \t]*([^=\n]+?)[ \t]*={2,})[ \t]*')


def digest(value):
    return hashlib.sha256(value).hexdigest()


def normalized(value):
    return ' '.join(unicodedata.normalize('NFKC', value).split())


def read_json(root, path, hashes):
    data = (root / path).read_bytes()
    hashes[path] = digest(data)
    return json.loads(data)


def adapt_snapshot(snapshot, story_date):
    """Accept native Docs snapshots and archived formal snapshots without faking freshness."""
    if not isinstance(snapshot, dict):
        raise ValueError('INVALID_FORMAL_DOCUMENT_SNAPSHOT')
    if 'document_id' not in snapshot:
        return snapshot, True
    if snapshot.get('document_id') != FORMAL_DOC_ID or not snapshot.get('revision_id'):
        raise ValueError('INVALID_FORMAL_DOCUMENT_SNAPSHOT')
    if snapshot.get('date') != story_date or not snapshot.get('paragraphs'):
        raise ValueError('SNAPSHOT_DATE_UNVERIFIED')
    if not snapshot.get('date_attribution') or not snapshot.get('document_url'):
        raise ValueError('SNAPSHOT_DATE_UNVERIFIED')
    if not all(isinstance(p, dict) and isinstance(p.get('text'), str)
               and isinstance(p.get('paragraph_index'), int) for p in snapshot['paragraphs']):
        raise ValueError('EMPTY_OR_INCOMPLETE_FORMAL_SNAPSHOT')
    indexes = [p['paragraph_index'] for p in snapshot['paragraphs']]
    if indexes != list(range(indexes[0], indexes[0] + len(indexes))):
        raise ValueError('NONCONTIGUOUS_ARCHIVE_PARAGRAPHS')
    # Archived paragraph tab identifiers may be from an earlier Docs extraction.
    # One verified source tab is explicitly recorded in this immutable archive.
    archived_tab_ids = {p.get('tab_id') for p in snapshot['paragraphs']}
    if len(archived_tab_ids) != 1:
        raise ValueError('MULTIPLE_ARCHIVE_TABS_REQUIRE_REVIEW')
    return {'documentId': snapshot['document_id'], 'revisionId': snapshot['revision_id'],
            'tabs': [{'tabId': snapshot.get('tab_id', 't.0'),
                      'title': snapshot.get('tab_title', '')}],
            'paragraphs': [{'tabId': snapshot.get('tab_id', 't.0'),
                            'startIndex': p.get('start_index', p['paragraph_index']),
                            'text': p['text']} for p in snapshot['paragraphs']],
            '_verified_story_date': story_date,
            '_archived_source': True,
            '_date_attribution': snapshot['date_attribution']}, False


def snapshot_messages(snapshot, story_date, roster):
    if snapshot.get('documentId') != FORMAL_DOC_ID or not snapshot.get('revisionId'):
        raise ValueError('INVALID_FORMAL_DOCUMENT_SNAPSHOT')
    stamp_value = snapshot.get('retrieved_at')
    if stamp_value is not None:
        stamp = datetime.fromisoformat(stamp_value.replace('Z', '+00:00'))
        if stamp.tzinfo is None:
            raise ValueError('SNAPSHOT_TIMEZONE_REQUIRED')
        from zoneinfo import ZoneInfo
        local = stamp.astimezone(ZoneInfo('Europe/Bucharest'))
        if local.date() > story_date:
            raise ValueError('FUTURE_SNAPSHOT')
        if local.date() != story_date:
            raise ValueError('SNAPSHOT_NOT_REFRESHED_ON_STORY_DATE')
    elif not snapshot.get('_archived_source'):
        raise ValueError('SNAPSHOT_RETRIEVAL_TIME_MISSING')
    tabs, paragraphs = snapshot.get('tabs'), snapshot.get('paragraphs')
    if (not isinstance(tabs, list) or not tabs or
            not isinstance(paragraphs, list) or not paragraphs or
            any(not isinstance(p, dict) or not isinstance(p.get('text'), str) for p in paragraphs)):
        raise ValueError('EMPTY_OR_INCOMPLETE_FORMAL_SNAPSHOT')
    if any(p.get('tabId') not in {t.get('tabId') for t in tabs} for p in paragraphs):
        raise ValueError('EMPTY_OR_INCOMPLETE_FORMAL_SNAPSHOT')
    days, conflicts = {}, []
    for tab in tabs:
        title = tab.get('title', '')
        match = re.fullmatch(r'(\d{1,2})/(\d{1,2})', title)
        if match:
            key = date(story_date.year, int(match.group(1)), int(match.group(2))).isoformat()
        elif snapshot.get('_verified_story_date') == story_date.isoformat():
            key = story_date.isoformat()
            conflicts.append({'type': 'DATE_ATTRIBUTION_REQUIRES_REVIEW',
                              'evidence': snapshot.get('_date_attribution')})
        else:
            raise ValueError('UNVERIFIED_DATE_BOUNDARY:' + title)
        if key > story_date.isoformat():
            continue
        if key in days:
            raise ValueError('DUPLICATE_DATE_TAB:' + key)
        pp = [p for p in paragraphs if p['tabId'] == tab['tabId']]
        days[key] = []
        text = '\n'.join(p['text'] for p in pp).replace('\x0b', '\n')
        matches = list(LABEL.finditer(text))
        for i, match in enumerate(matches):
            body = text[match.end():matches[i + 1].start() if i + 1 < len(matches) else len(text)].strip()
            if not body:
                continue
            raw_id = match.group(1)
            if raw_id:
                pid = f'{int(raw_id):02}'
                invalid = pid not in roster or roster[pid]['gender'] != match.group(2)
            else:
                label = re.sub(r'\s+', '', match.group(3) or '')
                pid = ('news_assistant' if '资讯助理' in label else
                       'teacher' if '先生' in label else
                       'investment_advisor' if '投资顾问' in label else
                       'consultant' if '咨询顾问' in label else None)
                invalid = pid is None
            mid = 'DOC-' + digest(f'{key}|{pid}|{i}|{body}'.encode())[:20]
            if invalid:
                conflicts.append({'id': mid, 'date': key, 'label': match.group(0), 'text': body})
                continue
            days[key].append({'id': mid, 'speaker_id': pid, 'text': body, 'date': key,
                              'kind': 'message', 'tab_id': tab['tabId'],
                              'source_revision': snapshot['revisionId'],
                              'status': 'PRESENT_IN_FORMAL_DOCUMENT',
                              'sequence': i})
    if not days:
        raise ValueError('EMPTY_OR_INCOMPLETE_FORMAL_SNAPSHOT')
    return days, conflicts

def build_context(root, story_date, member_ids, snapshot=None):
    root, day = Path(root), date.fromisoformat(story_date)
    if len(set(member_ids)) != len(member_ids):
        raise ValueError('DUPLICATE_CAST_ID')
    if any(not re.fullmatch(r'\d{2}', pid) or not 1 <= int(pid) <= 40 for pid in member_ids):
        raise ValueError('OUTSIDE_ACTIVE_RANGE:01-40')
    hashes = {}
    roster = {p['id']: p for p in read_json(root, 'skills/p004-chat-suite/characters/final-identity-65.json', hashes)['people']}
    days = {}
    for path in sorted((root / 'memory/daily').glob('*/day-memory.json')):
        data = read_json(root, path.relative_to(root).as_posix(), hashes)
        key = data.get('story_date') or path.parent.name
        if key > story_date:
            continue
        days[key] = [dict(m, date=key) for m in data['messages']
                     if m.get('status') in ADOPTED and m.get('speaker_id') in roster]
    original_days = {key: list(rows) for key, rows in days.items()}
    conflicts = []
    if snapshot is not None:
        snapshot, live_source = adapt_snapshot(snapshot, story_date)
        current, conflicts = snapshot_messages(snapshot, day, roster)
        for key, rows in current.items():
            # Retain an existing message ID only for a unique exact match in the same day.
            for row in rows:
                matches = [m for m in original_days.get(key, [])
                           if m['speaker_id'] == row['speaker_id'] and normalized(m['text']) == normalized(row['text'])]
                if len(matches) == 1:
                    row['id'] = matches[0]['id']
            days[key] = rows
    source = {m['id']: m for rows in days.values() for m in rows}
    members = {}
    for pid in member_ids:
        profile = read_json(root, f'skills/p004-chat-suite/characters/profiles/{pid}.json', hashes)
        for k, v in roster[pid].items():
            if profile.get(k) != v:
                raise ValueError('IDENTITY_PROFILE_CONFLICT:' + pid + ':' + k)
        mempath = f'memory/long-term/members/{pid}.json'
        if (root / mempath).exists():
            read_json(root, mempath, hashes)  # Read for audit; daily adopted evidence determines eligibility.
        history = sorted([m for m in source.values() if m['speaker_id'] == pid], key=lambda m: (m['date'], m['id']))
        members[pid] = {'identity': roster[pid], 'voice_reference': profile.get('voice', {}),
                        'voice_status': profile.get('voice', {}).get('voice_status'),
                        'history': history, 'history_status': 'LOADED_ADOPTED_EVIDENCE' if history else 'NO_ADOPTED_RECORDS_IN_LOADED_SOURCES',
                        'recent_examples': [m for m in history if m['date'] >= (day-timedelta(days=3)).isoformat()][-12:],
                        'state': {'knowledge': 'NOT_INFERRED', 'homework': 'NOT_INFERRED'}}
    relationship = read_json(root, 'memory/long-term/relationship-seeds.json', hashes)
    documented, candidates = [], []
    for seed in relationship.get('seeds', []):
        if not set(seed['member_ids']).issubset(member_ids):
            continue
        refs = seed.get('evidence_message_ids', [])
        if refs and all(mid in source for mid in refs):
            documented.append(seed)
        elif not refs:
            candidates.append(seed)
    return {'schema_version': 'editorial-execution-1.8', 'story_date': story_date,
            'active_member_range': '01-40', 'members': members,
            'documented_interactions': documented, 'candidate_pairings': candidates,
            'freshness': ('CURRENT_DOCUMENT_LOADED' if snapshot is not None and live_source else
                          'ARCHIVE_SNAPSHOT_REQUIRES_DOCUMENT_REFRESH' if snapshot is not None else
                          'ARCHIVE_ONLY_REQUIRES_DOCUMENT_REFRESH'),
            'snapshot_revision': snapshot.get('revisionId') if snapshot else None,
            'snapshot_sha256': digest(json.dumps(snapshot, sort_keys=True, ensure_ascii=False).encode()) if snapshot else None,
            'source_hashes': hashes, 'source_conflicts': conflicts,
            'limitation': 'Local read receipts do not prove a remote document is still latest. Refresh through Google Drive before each writing run.'}


def check_receipt(context, root):
    errors = []
    for path, expected in context.get('source_hashes', {}).items():
        file = Path(root) / path
        if not file.is_file() or digest(file.read_bytes()) != expected:
            errors.append('SOURCE_CHANGED:' + path)
    if not context.get('source_hashes'):
        errors.append('NO_READ_RECEIPT')
    return errors


def validate_state_change(change, messages):
    refs = change.get('evidence_ids', [])
    return bool(refs) and change.get('evidence_support_reviewed') is True and all(mid in messages for mid in refs)


def evidence_keys(ledger):
    selected = set(ledger['publish_claim_ids'])
    keys = []
    for claim in ledger['claims']:
        if claim['id'] not in selected:
            continue
        refs = []
        for e in claim.get('evidence', []):
            url = urlsplit(ledger['sources'][e['source_id']]['url'])
            query = urlencode(sorted((k, v) for k, v in parse_qsl(url.query) if not k.lower().startswith('utm_') and k.lower() not in ('fbclid', 'gclid')))
            canonical = urlunsplit((url.scheme.lower(), url.netloc.lower(), url.path, query, ''))
            refs.append((canonical, normalized(e['excerpt'])))
        if not refs:
            raise ValueError('NO_EVIDENCE_FOR_SELECTED_CLAIM')
        keys.append(digest(json.dumps(sorted(set(refs)), ensure_ascii=False).encode()))
    return sorted(set(keys))


def new_evidence_keys(keys, history):
    used = {key for event in history if event.get('state') in ('ADOPTED', 'DELIVERED', 'RESERVED', 'CLAIM_RESERVED_DO_NOT_RETRY', 'PENDING_DO_NOT_RETRY') for key in event.get('evidence_keys', event.get('claim_evidence_keys', []))}
    return sorted(set(keys) - used)


def review_scene(scene, context, approved_claim_ids=()):
    errors, warnings, seen = [], [], {}
    if not isinstance(scene, list):
        return {'status': 'BLOCK', 'errors': ['INVALID_SCENE_SHAPE'], 'warnings': [], 'publication_allowed': False}
    if not scene:
        errors.append('EMPTY_SCENE')
    for turn in scene:
        if (not isinstance(turn, dict) or not isinstance(turn.get('id'), str)
                or not isinstance(turn.get('speaker_id'), str)
                or not isinstance(turn.get('text'), str)
                or not isinstance(turn.get('reply_to', ''), str)
                or not isinstance(turn.get('memory_refs', []), list)
                or not all(isinstance(x, str) for x in turn.get('memory_refs', []))
                or not isinstance(turn.get('claim_ids', []), list)
                or not all(isinstance(x, str) for x in turn.get('claim_ids', []))):
            return {'status': 'BLOCK', 'errors': ['INVALID_SCENE_SHAPE'], 'warnings': [], 'publication_allowed': False}
    if context.get('freshness') != 'CURRENT_DOCUMENT_LOADED':
        errors.append('CURRENT_DOCUMENT_NOT_LOADED')
    if context.get('source_conflicts'):
        warnings.append('FORMAL_SOURCE_HAS_QUARANTINED_LABELS')
    count, replies = 0, 0
    for turn in scene:
        tid, pid, text = turn.get('id'), turn.get('speaker_id'), turn.get('text', '')
        if not tid or tid in seen:
            errors.append('MISSING_OR_DUPLICATE_TURN_ID:' + str(tid))
        if not isinstance(text, str) or not text.strip():
            errors.append('EMPTY_TURN:' + str(tid)); text = ''
        if '**' in text or '__' in text:
            errors.append('BOLD_IN_COPY_TEXT:' + str(tid))
        target = turn.get('reply_to')
        if target and target not in seen:
            errors.append('INVALID_REPLY_TARGET:' + str(tid))
        if pid not in ('teacher', 'news_assistant', 'investment_advisor', 'consultant'):
            count += 1
            member = context.get('members', {}).get(pid)
            if not member:
                errors.append('MEMBER_CONTEXT_NOT_LOADED:' + str(tid))
            else:
                if turn.get('gender') != member['identity']['gender']:
                    errors.append('GENDER_MISMATCH:' + str(tid))
                refs = turn.get('memory_refs', [])
                valid = {m['id'] for m in member['history']}
                if not isinstance(refs, list) or any(mid not in valid for mid in refs):
                    errors.append('UNSUPPORTED_MEMORY:' + str(tid))
                if re.search(r'我(?:昨天|之前|上次)|上次我|昨天我', text) and not refs:
                    errors.append('CALLBACK_WITHOUT_EVIDENCE:' + str(tid))
            if target in seen and seen[target].get('speaker_id') in context.get('members', {}) and seen[target].get('speaker_id') != pid:
                replies += 1
        if any(cid not in approved_claim_ids for cid in turn.get('claim_ids', [])):
            errors.append('UNAPPROVED_FACT_REFERENCE:' + str(tid))
        if any(normalized(text) == normalized(prev.get('text', '')) for prev in seen.values()):
            warnings.append('REPEATED_TURN:' + str(tid))
        seen[tid] = turn
    if count >= 5 and replies == 0:
        warnings.append('ALL_MEMBER_TURNS_ORBIT_HOST_REVIEW_REQUIRED')
    return {'status': 'BLOCK' if errors else 'EDITORIAL_REVIEW_REQUIRED', 'errors': errors,
            'warnings': warnings, 'member_to_member_replies': replies,
            'semantic_checks_required': ['numeric and causal claim coverage', 'voice and knowledge consistency', 'course progress and homework support', 'news novelty across different sources'],
            'publication_allowed': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--date', required=True)
    parser.add_argument('--members', required=True, help='Comma-separated zero-padded IDs')
    parser.add_argument('--snapshot', help='JSON with documentId, revisionId, retrieved_at, tabs and paragraphs')
    parser.add_argument('--scene', help='Draft JSON array; never sends or adopts it')
    parser.add_argument('--ledger', help='Reviewed news ledger for existing fact gate')
    parser.add_argument('--event-history', help='Array of adopted/delivered evidence-key records')
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    snapshot = json.loads(Path(args.snapshot).read_text()) if args.snapshot else None
    context = build_context(ROOT, args.date, args.members.split(','), snapshot)
    output = {'context': context, 'receipt_errors': check_receipt(context, ROOT)}
    claims = []
    if args.ledger:
        from news_release_gate import evaluate
        ledger = json.loads(Path(args.ledger).read_text())
        output['fact_gate'] = evaluate(ledger)
        if output['fact_gate']['status'] == 'PASS':
            claims = ledger['publish_claim_ids']
            keys = evidence_keys(ledger)
            history = json.loads(Path(args.event_history).read_text()) if args.event_history else None
            output['news_novelty'] = {'evidence_keys': keys,
                'new_evidence_keys': new_evidence_keys(keys, history) if history is not None else [],
                'status': 'HISTORY_NOT_LOADED' if history is None else ('NEW_EVIDENCE_REQUIRES_SEMANTIC_REVIEW' if new_evidence_keys(keys, history) else 'NO_NEW_EVIDENCE')}
    if args.scene:
        output['scene_review'] = review_scene(json.loads(Path(args.scene).read_text()), context, claims)
    Path(args.output).write_text(json.dumps(output, ensure_ascii=False, indent=2)+'\n')
    blocked = output['receipt_errors'] or context['freshness'] != 'CURRENT_DOCUMENT_LOADED' or output.get('scene_review', {}).get('errors')
    blocked = blocked or ('fact_gate' in output and output['fact_gate']['status'] != 'PASS')
    blocked = blocked or ('news_novelty' in output and output['news_novelty']['status'] in ('HISTORY_NOT_LOADED', 'NO_NEW_EVIDENCE'))
    print('BLOCK' if blocked else 'CONTEXT_READY_FOR_EDITORIAL_REVIEW_NOT_PUBLICATION')
    return 2 if blocked else 0


if __name__ == '__main__':
    raise SystemExit(main())
