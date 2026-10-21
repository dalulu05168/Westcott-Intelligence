#!/usr/bin/env python3
"""Evidence-first context controller. Does not generate, adopt or send messages.

Native Docs input can be fetched with --fetch-google-docs and an ephemeral
GOOGLE_ACCESS_TOKEN, or supplied by the connected Drive reader. File receipts
remain attributed to their supplied provenance; they are not proof of authenticity.
"""
import argparse
import copy
from collections import Counter
from datetime import date, datetime, timezone
from difflib import SequenceMatcher
import hashlib
import json
import os
from pathlib import Path
import re
import urllib.request
from zoneinfo import ZoneInfo

from editorial_execution import ADOPTED, normalized, review_scene, evidence_keys, new_evidence_keys

ROOT = Path(__file__).resolve().parents[1]
POLICY = 'config/editorial-policy-v2.1.json'
BOUNDARY = re.compile(r'(?m)^\s*(\d{1,2})/(\d{1,2})\s*$')
LABEL = re.compile(r'(?m)^[ \t]*(?:(\d{1,2})[ \t]*([男女])?[ \t]*[:：]?[ \t]*$|={2,}[ \t]*([^=\n]+?)[ \t]*={2,}[ \t]*)')
CLOSE = re.compile(r'(?m)^[ \t]*🌙[ \t]*感谢Jonathan先生')


def sha(value):
    return hashlib.sha256(value).hexdigest()


def source_digest(snapshot):
    # Retrieval time is a read receipt, not a document edit. Label decisions may
    # survive a re-read only when revision AND the complete text are unchanged.
    content = {k: snapshot.get(k) for k in ('documentId', 'revisionId', 'tabs', 'paragraphs')}
    return sha(json.dumps(content, sort_keys=True, ensure_ascii=False).encode())


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


def timestamp(value):
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if result.tzinfo is None:
        raise ValueError('TIMEZONE_REQUIRED')
    return result


def fetch_document(policy):
    token = os.environ.get('GOOGLE_ACCESS_TOKEN')
    if not token:
        raise ValueError('GOOGLE_ACCESS_TOKEN_REQUIRED_OR_USE_CONNECTED_DRIVE_SNAPSHOT')
    url = 'https://docs.googleapis.com/v1/documents/'+policy['document_id']+'?includeTabsContent=true'
    request = urllib.request.Request(url, headers={'Authorization': 'Bearer '+token})
    with urllib.request.urlopen(request, timeout=30) as response:
        document = json.load(response)
    # Never serialize the request, token or headers.
    document['retrieved_at'] = datetime.now(timezone.utc).isoformat()
    document['source_kind'] = 'GOOGLE_DOCS_API_READ'
    return document


def normalize_document(document):
    if 'paragraphs' in document:
        return document
    result = {k: document.get(k) for k in ('documentId', 'revisionId', 'retrieved_at', 'source_kind')}
    result['document_url'] = document.get('document_url')
    result.update(tabs=[], paragraphs=[])

    def paragraphs(items, tid):
        for item in items or []:
            if 'paragraph' in item:
                result['paragraphs'].append({'tabId': tid, 'startIndex': item.get('startIndex', 0),
                    'text': ''.join(e.get('textRun', {}).get('content', '') for e in item['paragraph'].get('elements', []))})
            for row in item.get('table', {}).get('tableRows', []):
                for cell in row.get('tableCells', []):
                    paragraphs(cell.get('content'), tid)

    def tabs(items):
        for tab in items:
            props = tab.get('tabProperties', tab)
            tid = props['tabId']
            result['tabs'].append({'tabId': tid, 'title': props.get('title', '')})
            paragraphs(tab.get('documentTab', tab).get('body', {}).get('content'), tid)
            tabs(tab.get('childTabs', []))
    tabs(document.get('tabs', []))
    return result


def validate_snapshot(snapshot, policy, now, revision_check=None):
    errors = []
    if snapshot.get('documentId') != policy['document_id'] or not snapshot.get('revisionId'):
        errors.append('WRONG_DOCUMENT_OR_MISSING_REVISION')
    try:
        age = (now-timestamp(snapshot['retrieved_at'])).total_seconds()
        if age < 0 or age > policy['snapshot_max_age_seconds']:
            errors.append('SNAPSHOT_STALE_OR_FUTURE')
    except (ValueError, KeyError, TypeError):
        errors.append('INVALID_SNAPSHOT_TIME')
    tabs = snapshot.get('tabs', [])
    ids = [t.get('tabId') for t in tabs]
    if not ids or len(ids) != len(set(ids)) or not snapshot.get('paragraphs'):
        errors.append('EMPTY_OR_DUPLICATE_SOURCE_TABS')
    if any(p.get('tabId') not in ids or not isinstance(p.get('text'), str) for p in snapshot.get('paragraphs', [])):
        errors.append('INVALID_SOURCE_PARAGRAPH')
    if revision_check is None:
        errors.append('LATEST_REVISION_NOT_RECHECKED')
    else:
        try:
            check_age = (now-timestamp(revision_check['retrieved_at'])).total_seconds()
            if check_age < 0 or check_age > policy['snapshot_max_age_seconds']:
                errors.append('REVISION_CHECK_STALE_OR_FUTURE')
            if timestamp(revision_check['retrieved_at']) < timestamp(snapshot['retrieved_at']):
                errors.append('REVISION_CHECK_PRECEDES_READ')
            if (revision_check.get('documentId'), revision_check.get('revisionId')) != (snapshot.get('documentId'), snapshot.get('revisionId')):
                errors.append('DOCUMENT_CHANGED_DURING_READ')
        except (ValueError, KeyError, TypeError):
            errors.append('INVALID_REVISION_CHECK')
    return errors


def compact(text):
    return ''.join(c for c in normalized(text) if c.isalnum())


def evidence_fingerprint(day, speaker, text):
    return sha(json.dumps([day, speaker, normalized(text)], ensure_ascii=False).encode())


def label_fingerprint(day, speaker, gender, label, text):
    return sha(json.dumps([day, speaker, gender, label, normalized(text)], ensure_ascii=False).encode())


def parse_snapshot(snapshot, roster, year, decisions=None):
    """Date tabs or explicit date headings; empty parent/placeholders are ignored.

    Missing genders are quarantined. Unlabelled closing text is split out so it
    cannot become the preceding member's statement. Corrections need a reviewed
    decision tied to the exact snapshot digest and generated source block ID.
    """
    decisions = decisions or {}
    digest = source_digest(snapshot)
    if decisions and (decisions.get('snapshot_sha256') != digest or not decisions.get('reviewer')):
        raise ValueError('REVIEW_DECISIONS_SOURCE_MISMATCH')
    overrides = decisions.get('blocks', {})
    days = {}
    for tab in snapshot['tabs']:
        text = ''.join(p['text'].replace('\x0b', '\n') for p in snapshot['paragraphs'] if p['tabId'] == tab['tabId'])
        if not text.strip():
            continue
        dm = re.fullmatch(r'(\d{1,2})/(\d{1,2})', tab['title'])
        chunks = []
        if dm:
            chunks.append((date(year, int(dm[1]), int(dm[2])).isoformat(), text, 0))
        else:
            bounds = list(BOUNDARY.finditer(text))
            if not bounds:
                raise ValueError('NONEMPTY_UNDATED_TAB:'+tab['tabId'])
            if text[:bounds[0].start()].strip():
                raise ValueError('UNATTRIBUTED_TEXT_BEFORE_DATE')
            for i, m in enumerate(bounds):
                chunks.append((date(year, int(m[1]), int(m[2])).isoformat(),
                               text[m.end():bounds[i+1].start() if i+1<len(bounds) else len(text)], m.end()))
        for day, body, offset in chunks:
            matches = list(LABEL.finditer(body))
            if not matches:
                if body.strip():
                    raise ValueError('NONEMPTY_DATE_WITHOUT_ROLES:'+day)
                continue
            if day in days:
                raise ValueError('DUPLICATE_STORY_DATE:'+day)
            rows = []
            phase = 'UNSPECIFIED'
            for i, m in enumerate(matches):
                raw = body[m.end():matches[i+1].start() if i+1<len(matches) else len(body)].strip()
                pid = f'{int(m[1]):02}' if m[1] else {'资讯助理':'news_assistant', '先生':'teacher',
                    '投资顾问':'investment_advisor', '咨询顾问':'consultant'}.get(m[3].strip(), 'unknown_staff')
                pieces = [(pid, raw, m[2], m[0].strip(), False)]
                unlabelled = CLOSE.search(raw)
                if unlabelled and pid != 'news_assistant':
                    pieces = [(pid, raw[:unlabelled.start()].strip(), m[2], m[0].strip(), False),
                              ('unknown_staff', raw[unlabelled.start():].strip(), None, '', True)]
                for part, (speaker, content, gender, label, inferred) in enumerate(pieces):
                    mid = f'{day.replace("-", "")}-{tab["tabId"]}-B{i+1:03}-{part}'
                    decision = overrides.get(mid, {})
                    warnings = []
                    label_key = label_fingerprint(day, speaker, gender, label, content)
                    status = 'PRESENT_IN_FORMAL_DOCUMENT'
                    if not content:
                        status = 'EXCLUDED_EMPTY'
                        if speaker in roster and gender != roster[speaker]['gender']:
                            warnings.append('EMPTY_LABEL_IDENTITY_CONFLICT_NOT_A_MESSAGE')
                    elif speaker in roster and gender != roster[speaker]['gender']:
                        status = 'REVIEW_LABEL_REQUIRED'
                    elif speaker == 'unknown_staff':
                        status = 'REVIEW_LABEL_REQUIRED'
                    if decision:
                        target = decision.get('speaker_id')
                        if (decision.get('action') != 'CONFIRM_LABEL' or not decision.get('reason')
                                or (speaker in roster and target != speaker)
                                or target not in set(roster) | {'news_assistant', 'teacher', 'investment_advisor', 'consultant'}
                                or (target in roster and decision.get('gender') != roster[target]['gender'])):
                            raise ValueError('INVALID_LABEL_REVIEW:'+mid)
                        speaker = target
                        gender = decision.get('gender')
                        status = 'PRESENT_IN_FORMAL_DOCUMENT'
                        warnings.append('REVIEWED_LABEL_WITH_ORIGINAL_PRESERVED')
                    if speaker == 'news_assistant':
                        if re.search(r'(早上好|上午好)', content[:150]): phase = 'MORNING'
                        elif '下午好' in content[:150]: phase = 'AFTERNOON'
                        elif '晚上好' in content[:150]: phase = 'EVENING'
                    rows.append({'id': mid, 'speaker_id': speaker, 'gender': gender, 'text': content,
                        'evidence_fingerprint': evidence_fingerprint(day, speaker, content),
                        'label_fingerprint': label_key,
                        'source_label': label, 'source_tab_id': tab['tabId'], 'source_offset': offset+m.start(),
                        'source_revision': snapshot['revisionId'], 'date': day, 'node': phase, 'kind': 'message',
                        'status': status, 'unlabelled_fragment': inferred, 'warnings': warnings,
                        'fictional_only': True, 'real_trade_not_inferred': True})
            seen = {}
            for row in rows:
                if row['status'] != 'PRESENT_IN_FORMAL_DOCUMENT': continue
                key = (row['speaker_id'], compact(row['text']))
                if key in seen:
                    row['status'] = 'EXCLUDED_DUPLICATE'
                    row['duplicate_of'] = seen[key]
                else:
                    seen[key] = row['id']
            days[day] = rows
    return days, digest


def checkpoint(days, snapshot, digest):
    if not days: raise ValueError('NO_STORY_MESSAGES')
    day = max(days)
    rows = days[day]
    effective = [r for r in rows if r['status'] == 'PRESENT_IN_FORMAL_DOCUMENT']
    if not effective: raise ValueError('NO_EFFECTIVE_STORY_MESSAGES')
    last = effective[-1]
    closed = last['speaker_id'] == 'news_assistant' and bool(re.search(r'交流.*结束|交流.*到这里|晚安|下午再见|晚上见', last['text']))
    unresolved_tail = any(r['status'].startswith('REVIEW') for r in rows[rows.index(last)+1:])
    counts = {}
    for phase in ('MORNING', 'AFTERNOON', 'EVENING', 'UNSPECIFIED'):
        group = [r for r in rows if r['node'] == phase]
        if group:
            counts[phase] = {'labelled_raw': sum(not r['unlabelled_fragment'] for r in group),
                'unlabelled_fragments': sum(r['unlabelled_fragment'] for r in group),
                'effective': sum(r['status'] == 'PRESENT_IN_FORMAL_DOCUMENT' for r in group),
                'excluded': sum(r['status'].startswith('EXCLUDED') for r in group),
                'review_required': sum(r['status'].startswith('REVIEW') for r in group)}
    return {'rules_version': '2.1', 'story_date': day, 'story_tab_id': last['source_tab_id'],
        'story_phase': last['node']+('_CLOSED' if closed and not unresolved_tail else '_REVIEW_REQUIRED' if unresolved_tail else '_OPEN'),
        'last_adopted_message_id': last['id'], 'last_adopted_speaker': last['speaker_id'],
        'last_adopted_excerpt': last['text'], 'document_revision_id': snapshot['revisionId'],
        'retrieved_at': snapshot['retrieved_at'], 'source_sha256': digest, 'counts': counts,
        'quarantined_blocks': [r['id'] for r in rows if r['status'].startswith('REVIEW')],
        'source_anomalies': [{'id': r['id'], 'label': r['source_label'], 'warnings': r['warnings']}
                             for r in rows if 'EMPTY_LABEL_IDENTITY_CONFLICT_NOT_A_MESSAGE' in r['warnings']],
        'freshness': 'HISTORICAL_READ_REQUIRES_REFRESH_BEFORE_WRITING', 'delivery': 'NOT_VERIFIED'}


def member_context(root, roster, days, cast, hashes):
    sources = {}
    for path in sorted((root/'memory/daily').glob('*/day-memory.json')):
        raw = path.read_bytes(); hashes[path.relative_to(root).as_posix()] = sha(raw)
        data = json.loads(raw)
        key = data.get('story_date', path.parent.name)
        sources[key] = [dict(r, date=key) for r in data['messages'] if r.get('status') in ADOPTED]
    # Current formal view replaces, never adds to, an older same-day archive.
    for day, rows in days.items():
        sources[day] = [r for r in rows if r['status'] == 'PRESENT_IN_FORMAL_DOCUMENT']
    selected = {}
    for pid in roster:
        profile_path = f'skills/p004-chat-suite/characters/profiles/{pid}.json'
        raw = (root/profile_path).read_bytes(); hashes[profile_path] = sha(raw)
        profile = json.loads(raw)
        if any(profile.get(k) != v for k, v in roster[pid].items()):
            raise ValueError('PROFILE_IDENTITY_CONFLICT:'+pid)
        path = root/f'memory/long-term/members/{pid}.json'
        history = [r for day in sorted(sources) for r in sources[day] if r.get('speaker_id') == pid]
        access = 'NO_SEPARATE_FILE'
        if path.exists():
            raw = path.read_bytes(); hashes[path.relative_to(root).as_posix()] = sha(raw)
            old = json.loads(raw)
            if old.get('id') != pid or old.get('name') != roster[pid]['name']:
                raise ValueError('MEMORY_IDENTITY_CONFLICT:'+pid)
            access = 'READ_AND_CROSSCHECKED_AGAINST_EFFECTIVE_DAILY_VIEW'
            # Unmatched long-term entries never override a refreshed formal day.
        selected[pid] = {'identity': roster[pid], 'voice_reference': profile['voice'], 'history': history,
            'history_status': 'LOADED_ADOPTED_EVIDENCE' if history else 'NO_CONFIRMED_HISTORY_IN_LOADED_SOURCES',
            'memory_access': access, 'recent_examples': history[-12:],
            'state': {'knowledge': 'NOT_INFERRED', 'homework': 'NOT_INFERRED'},
            'relationship': 'ONLY_EXPLICIT_EVIDENCE_NOT_COAPPEARANCE'}
    index = {pid: {'id': pid, 'name': m['identity']['name'], 'active': 1 <= int(pid) <= 40,
        'profile_path': f'skills/p004-chat-suite/characters/profiles/{pid}.json',
        'legacy_memory_path': f'memory/long-term/members/{pid}.json' if (root/f'memory/long-term/members/{pid}.json').exists() else None,
        'derived_memory_path': f'memory/derived/v2.1/members/{pid}.json',
        'history_status': m['history_status'], 'memory_access': m['memory_access'],
        'evidence_ids': [r['id'] for r in m['history']], 'state': m['state']} for pid, m in selected.items()}
    return {pid: selected[pid] for pid in cast}, index, sources


def reviewed_states(records, sources, roster):
    """Validate evidence links, not their semantic truth. Reviewer stays explicit."""
    messages = {r['id']: r for rows in sources.values() for r in rows}
    accepted = []
    for original in records or []:
        record = copy.deepcopy(original)
        refs = record.get('evidence_ids', [])
        pid = record.get('member_id')
        fingerprints = record.get('evidence_fingerprints', {})
        rebound = []
        for ref in refs:
            expected = fingerprints.get(ref)
            if not expected:
                raise ValueError('STATE_EVIDENCE_MISSING_OR_WITHDRAWN:'+str(record.get('id')))
            current = messages.get(ref)
            actual = (current.get('evidence_fingerprint') or evidence_fingerprint(current['date'], current['speaker_id'], current['text'])) if current else None
            if actual == expected:
                rebound.append(ref)
                continue
            matches = [r['id'] for r in messages.values()
                       if (r.get('evidence_fingerprint') or evidence_fingerprint(r['date'], r['speaker_id'], r['text'])) == expected]
            if len(matches) != 1:
                raise ValueError('STATE_EVIDENCE_MISSING_OR_WITHDRAWN:'+str(record.get('id')))
            rebound.append(matches[0])
        if rebound != refs:
            record['original_evidence_ids'] = refs
            record['evidence_ids'] = rebound
            record['reference_status'] = 'EXACT_CONTENT_RELINKED_AFTER_SOURCE_INSERTION'
        refs = rebound
        if (not record.get('reviewer') or record.get('evidence_support_reviewed') is not True
                or not refs or any(ref not in messages for ref in refs)):
            raise ValueError('STATE_EVIDENCE_MISSING_OR_WITHDRAWN:'+str(record.get('id')))
        if pid is not None and (pid not in roster or any(messages[ref]['speaker_id'] != pid for ref in refs)):
            raise ValueError('STATE_EVIDENCE_WRONG_MEMBER:'+str(record.get('id')))
        if record.get('real_trade_verified') is not False:
            raise ValueError('STORY_CANNOT_VERIFY_REAL_TRADE')
        accepted.append(record)
    return accepted


def emoji_findings(scene):
    """Review obvious repeated final emojis. Never infer a person's emotions."""
    suffix = re.compile(r'([\U0001F300-\U0001FAFF\u2600-\u27BF])\ufe0f?
    warnings = []
    member_run_lengths = []; run = 0
    for turn in scene:
        if turn['speaker_id'] == 'news_assistant':
            if run: member_run_lengths.append(run)
            run = 0
        elif turn['speaker_id'].isdigit(): run += 1
    if run: member_run_lengths.append(run)
    if len(member_run_lengths) >= 3 and len(set(member_run_lengths[-3:])) == 1:
        warnings.append('REPEATED_HOST_MEMBER_CADENCE_REVIEW_NOT_AUTOMATIC_REJECTION')
    for i, turn in enumerate(scene):
        for earlier in scene[:i]:
            a, b = compact(turn['text']), compact(earlier['text'])
            if min(len(a), len(b)) >= 20 and SequenceMatcher(None, a, b).ratio() > .90:
                warnings.append('SIMILAR_WORDING:'+turn['id'])
    emoji_review = emoji_findings(scene)
    warnings.extend('EMOJI_PATTERN_REVIEW:' + issue['code'] + ':' + ','.join(issue['turn_ids']) for issue in emoji_review)
    return {'warnings': sorted(set(warnings)), 'emoji_review': emoji_review,
        'semantic_status': 'PENDING_HUMAN_REVIEW',
        'rubric': ['distinct voices', 'reply motivation and target', 'emotion and knowledge continuity',
                   'topic progression', 'name and GIF use without quotas'], 'automatically_approved': False}


def delivery_status(receipt=None):
    if not receipt: return 'NO_RECEIPT'
    if receipt.get('platform') == 'telegram' and receipt.get('message_id'):
        return 'PLATFORM_ACCEPTED_DELIVERY_AND_READ_UNKNOWN'
    return 'UNVERIFIED_RECEIPT'


def run(root, snapshot, cast, now, revision_check=None, decisions=None, scene=None, ledger=None, event_history=None, state_records=None):
    root = Path(root); policy = load(root/POLICY)
    hashes = {POLICY: sha((root/POLICY).read_bytes())}
    roster_path = 'skills/p004-chat-suite/characters/final-identity-65.json'
    raw = (root/roster_path).read_bytes(); hashes[roster_path] = sha(raw)
    roster = {p['id']: p for p in json.loads(raw)['people']}
    lo, hi = policy['active_ids']
    if len(cast) != len(set(cast)) or any(pid not in roster or not lo <= int(pid) <= hi for pid in cast):
        raise ValueError('INVALID_OR_OUTSIDE_ACTIVE_CAST')
    snapshot = normalize_document(snapshot)
    if decisions is None:
        # Reuse reviewed label attribution only for the exact unchanged source.
        candidates = []
        for path in sorted((root/'memory/sources').glob('*-review.json')):
            raw = path.read_bytes(); hashes[path.relative_to(root).as_posix()] = sha(raw)
            candidates.append(json.loads(raw))
        decisions = next((d for d in candidates if d.get('snapshot_sha256') == source_digest(snapshot)), None)
        if decisions is None:
            raw_days, _ = parse_snapshot(snapshot, roster, now.astimezone(ZoneInfo(policy['timezone'])).year)
            by_fingerprint = {}
            for candidate in candidates:
                if not candidate.get('reviewer'): continue
                for old in candidate.get('blocks', {}).values():
                    key = old.get('label_fingerprint')
                    if key: by_fingerprint.setdefault(key, []).append(old)
            rebound = {}
            for row in (r for rows in raw_days.values() for r in rows):
                matches = by_fingerprint.get(row['label_fingerprint'], [])
                targets = {(m.get('speaker_id'), m.get('gender')) for m in matches}
                if len(targets) > 1: raise ValueError('AMBIGUOUS_PRIOR_LABEL_REVIEW')
                if matches: rebound[row['id']] = matches[0]
            decisions = {'snapshot_sha256': source_digest(snapshot),
                'reviewer': 'REUSED_EXACT_UNCHANGED_LABEL_REVIEWS', 'blocks': rebound} if rebound else {}
    errors = validate_snapshot(snapshot, policy, now, revision_check)
    days, digest = parse_snapshot(snapshot, roster, now.astimezone(ZoneInfo(policy['timezone'])).year, decisions)
    if any(date.fromisoformat(day) > now.astimezone(ZoneInfo(policy['timezone'])).date() for day in days):
        errors.append('FUTURE_STORY_CONTENT')
    current = checkpoint(days, snapshot, digest)
    if current['quarantined_blocks']: errors.append('LATEST_DAY_HAS_UNREVIEWED_LABELS')
    members, index, sources = member_context(root, roster, days, cast, hashes)
    if state_records is None:
        state_records = []
        for path in sorted((root/'memory/curated').glob('*-dynamic-state.json')):
            raw = path.read_bytes(); hashes[path.relative_to(root).as_posix()] = sha(raw)
            state_records.extend(json.loads(raw))
    states = reviewed_states(state_records, sources, roster)
    for pid, member in members.items():
        member['reviewed_dynamic_records'] = [r for r in states if r.get('member_id') == pid]
    context = {'schema_version': 'editorial-runtime-2.1', 'members': members, 'source_hashes': hashes,
        'freshness': 'CURRENT_DOCUMENT_LOADED' if not errors else 'REQUIRES_REFRESH_OR_REVIEW',
        'source_conflicts': current['quarantined_blocks'], 'checkpoint': current,
        'snapshot_revision': snapshot['revisionId'], 'snapshot_sha256': digest}
    for role in ('chat-suite', 'director', 'writer', 'teacher', 'assistant', 'members'):
        path = f'skills/p004-{role}/SKILL.md'
        hashes[path] = sha((root/path).read_bytes())
    guide = 'skills/p004-chat-suite/references/runtime-v2.1.md'
    raw = (root/guide).read_bytes(); hashes[guide] = sha(raw)
    context['execution_rules'] = raw.decode('utf-8')
    relation_path = root/'memory/long-term/relationship-seeds.json'
    if relation_path.exists():
        raw = relation_path.read_bytes(); hashes[relation_path.relative_to(root).as_posix()] = sha(raw)
        context['relationship_records'] = json.loads(raw)
        context['relationship_note'] = 'Source IDs must be relinked before treating a candidate or old exchange as a current established relationship.'
    fact = {'status': 'NOT_REQUESTED', 'truth_certified': False}; claims = []
    if ledger is not None:
        from news_release_gate import evaluate
        fact = evaluate(ledger); fact['truth_certified'] = False
        if fact['status'] != 'PASS': errors.append('FACT_GATE_BLOCKED')
        else:
            keys = evidence_keys(ledger)
            if event_history is None: errors.append('NEWS_HISTORY_NOT_LOADED')
            elif not new_evidence_keys(keys, event_history): errors.append('NO_NEW_NEWS_EVIDENCE')
            claims = ledger['publish_claim_ids']
    review = None
    if scene is not None:
        review = review_scene(scene, context, claims)
        errors.extend(review['errors'])
        if not review['errors']:
            review['quality'] = quality_signals(scene)
            if review['quality']['emoji_review']:
                errors.append('EMOJI_PATTERN_REVIEW_REQUIRED')
        for turn in scene if isinstance(scene, list) and all(isinstance(t, dict) and 'speaker_id' in t and 'text' in t and 'id' in t for t in scene) else []:
            assertion = turn.get('action_assertion')
            if assertion:
                matching = [r for r in states if r.get('member_id') == turn['speaker_id']
                            and r.get('symbol') == assertion.get('symbol')
                            and r.get('action') == assertion.get('action')
                            and set(r['evidence_ids']).issubset(turn.get('memory_refs', []))]
                if not matching: errors.append('UNSUPPORTED_STORY_ACTION:'+turn['id'])
                if assertion.get('quantity') is not None and not any(r.get('quantity') == assertion['quantity'] for r in matching):
                    errors.append('UNSUPPORTED_QUANTITY:'+turn['id'])
            if turn.get('kind') == 'financial_fact' and not turn.get('claim_ids'):
                errors.append('FINANCIAL_FACT_WITHOUT_CLAIM:'+turn['id'])
            if turn.get('kind') == 'quote':
                quote = turn.get('quote', {})
                price = quote.get('price')
                import math
                if (isinstance(price, bool) or not isinstance(price, (int, float)) or not math.isfinite(price)
                        or not quote.get('as_of') or not quote.get('source_url') or not turn.get('claim_ids')):
                    errors.append('INVALID_OR_MISSING_QUOTE:'+turn['id'])
            if turn.get('kind') == 'course_start' and any(r.get('course_id') == turn.get('course_id')
                    and r.get('course_status') == 'COMPLETED_IN_FORMAL_STORY' for r in states):
                errors.append('COMPLETED_COURSE_RESTART_REQUIRES_EXPLICIT_REVIEW')
    return {'version': '2.1', 'status': 'BLOCK' if errors else 'CONTEXT_READY_FOR_HUMAN_REVIEW',
        'errors': sorted(set(errors)), 'context': context, 'member_index': index, 'scene_review': review,
        'states': {'facts': fact, 'story': 'CANDIDATE_NOT_ADOPTED', 'delivery': delivery_status()},
        'effective_history': sources, 'reviewed_dynamic_records': states,
        'runtime': {'online_tasks_updated': False, 'sending_enabled': False}, 'publication_allowed': False}


def save_projection(root, result, source_path):
    """Explicit archival projection only; readiness is never persisted as live."""
    root = Path(root)
    archive_only_errors = {'SNAPSHOT_STALE_OR_FUTURE', 'LATEST_REVISION_NOT_RECHECKED', 'REVISION_CHECK_STALE_OR_FUTURE'}
    if set(result['errors']) - archive_only_errors:
        raise ValueError('UNREVIEWED_OR_INVALID_SOURCE_CANNOT_UPDATE_PROJECTION')
    folder = root/'memory/derived/v2.1'
    write(folder/'member-index.json', {'schema': '65-member-entrypoints-v2.1',
        'source_snapshot': source_path, 'source_sha256': result['context']['snapshot_sha256'],
        'members': result['member_index'], 'freshness': 'ARCHIVE_REQUIRES_LIVE_REFRESH'})
    write(folder/'effective-history.json', result['effective_history'])
    for pid, entry in result['member_index'].items():
        records = [r for rows in result['effective_history'].values() for r in rows if r.get('speaker_id') == pid]
        write(folder/f'members/{pid}.json', {'identity': entry,
            'evidence_store': 'memory/derived/v2.1/effective-history.json',
            'evidence_ids': [r['id'] for r in records], 'recent_examples': records[-12:],
            'dynamic_records': [r for r in result['reviewed_dynamic_records'] if r.get('member_id') == pid],
            'real_trade_verified': False, 'source_snapshot': source_path})
    check = dict(result['context']['checkpoint'], source_snapshot_path=source_path)
    write(root/'memory/runtime/latest-checkpoint.json', check)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--snapshot'); p.add_argument('--fetch-google-docs', action='store_true')
    p.add_argument('--revision-check'); p.add_argument('--decisions'); p.add_argument('--members', default='')
    p.add_argument('--scene'); p.add_argument('--ledger'); p.add_argument('--event-history')
    p.add_argument('--curated-state')
    p.add_argument('--output', required=True)
    p.add_argument('--date', help='Planned story date; does not change retrieval freshness')
    args = p.parse_args()
    if bool(args.snapshot) == args.fetch_google_docs: p.error('Choose exactly one source mode')
    policy = load(ROOT/POLICY)
    native = fetch_document(policy) if args.fetch_google_docs else load(args.snapshot)
    check = fetch_document(policy) if args.fetch_google_docs else load(args.revision_check) if args.revision_check else None
    def optional(path): return load(path) if path else None
    try:
        result = run(ROOT, native, args.members.split(',') if args.members else [], datetime.now(timezone.utc), check,
                     optional(args.decisions), optional(args.scene), optional(args.ledger), optional(args.event_history), optional(args.curated_state))
    except (ValueError, KeyError, TypeError) as error:
        write(args.output, {'version':'2.1', 'status':'BLOCK', 'errors':[str(error)], 'publication_allowed':False})
        print('BLOCK'); return 2
    if args.date:
        planned = date.fromisoformat(args.date)
        result['planned_story_date'] = args.date
        result['planned_activity'] = ('WEEKLY_REVIEW_AND_OUTLOOK' if planned.weekday() == 6 else
            'TECHNICAL_CLASS_AND_US_QUIZ' if planned.weekday() in (0, 2, 4) else
            'PRINCIPLES_CLASS_AND_KNOWLEDGE_QUIZ' if planned.weekday() in (1, 3) else 'NO_FIXED_ACTIVITY')
    result['input_file_receipts'] = {path: sha(Path(path).read_bytes()) for path in
        (args.snapshot, args.revision_check, args.decisions, args.curated_state, args.scene, args.ledger, args.event_history) if path}
    write(args.output, result)
    print(result['status'])
    return 2 if result['errors'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
)

    def ending(turn):
        match = suffix.search(turn.get('text', '').strip())
        return match.group(1) if match else None

    def member(turn):
        return isinstance(turn, dict) and str(turn.get('speaker_id', '')).isdigit()

    findings = []
    # Repeated ending by the same speaker in three of their last four turns.
    speakers = sorted({str(t['speaker_id']) for t in scene if member(t)})
    for speaker in speakers:
        own = [t for t in scene if member(t) and str(t['speaker_id']) == speaker]
        for i in range(2, len(own)):
            window = own[max(0, i - 3):i + 1]
            suffixes = [(t['id'], ending(t)) for t in window]
            for value in sorted({v for _, v in suffixes if v}):
                repeated = [tid for tid, e in suffixes if e == value]
                if len(repeated) >= 3:
                    findings.append({'code': 'REPEATED_SPEAKER_EMOJI_ENDING',
                                     'member_ids': [speaker], 'turn_ids': repeated,
                                     'emoji': value, 'severity': 'REVIEW'})
                    break
            if any(f['code'] == 'REPEATED_SPEAKER_EMOJI_ENDING' and
                   f['member_ids'] == [speaker] for f in findings):
                break
    # Identical endings passed across at least two speakers in three adjacent turns.
    for i in range(2, len(scene)):
        window = scene[i-2:i+1]
        if not all(member(t) for t in window):
            continue
        endings = [ending(t) for t in window]
        if endings[0] and len(set(endings)) == 1 and len({str(t['speaker_id']) for t in window}) >= 2:
            findings.append({'code': 'CROSS_SPEAKER_EMOJI_CHAIN',
                             'member_ids': [str(t['speaker_id']) for t in window],
                             'turn_ids': [t['id'] for t in window],
                             'emoji': endings[0], 'severity': 'REVIEW'})
    return findings


def quality_signals(scene):
    warnings = []
    member_run_lengths = []; run = 0
    for turn in scene:
        if turn['speaker_id'] == 'news_assistant':
            if run: member_run_lengths.append(run)
            run = 0
        elif turn['speaker_id'].isdigit(): run += 1
    if run: member_run_lengths.append(run)
    if len(member_run_lengths) >= 3 and len(set(member_run_lengths[-3:])) == 1:
        warnings.append('REPEATED_HOST_MEMBER_CADENCE_REVIEW_NOT_AUTOMATIC_REJECTION')
    for i, turn in enumerate(scene):
        for earlier in scene[:i]:
            a, b = compact(turn['text']), compact(earlier['text'])
            if min(len(a), len(b)) >= 20 and SequenceMatcher(None, a, b).ratio() > .90:
                warnings.append('SIMILAR_WORDING:'+turn['id'])
    return {'warnings': sorted(set(warnings)), 'semantic_status': 'PENDING_HUMAN_REVIEW',
        'rubric': ['distinct voices', 'reply motivation and target', 'emotion and knowledge continuity',
                   'topic progression', 'name and GIF use without quotas'], 'automatically_approved': False}


def delivery_status(receipt=None):
    if not receipt: return 'NO_RECEIPT'
    if receipt.get('platform') == 'telegram' and receipt.get('message_id'):
        return 'PLATFORM_ACCEPTED_DELIVERY_AND_READ_UNKNOWN'
    return 'UNVERIFIED_RECEIPT'


def run(root, snapshot, cast, now, revision_check=None, decisions=None, scene=None, ledger=None, event_history=None, state_records=None):
    root = Path(root); policy = load(root/POLICY)
    hashes = {POLICY: sha((root/POLICY).read_bytes())}
    roster_path = 'skills/p004-chat-suite/characters/final-identity-65.json'
    raw = (root/roster_path).read_bytes(); hashes[roster_path] = sha(raw)
    roster = {p['id']: p for p in json.loads(raw)['people']}
    lo, hi = policy['active_ids']
    if len(cast) != len(set(cast)) or any(pid not in roster or not lo <= int(pid) <= hi for pid in cast):
        raise ValueError('INVALID_OR_OUTSIDE_ACTIVE_CAST')
    snapshot = normalize_document(snapshot)
    if decisions is None:
        # Reuse reviewed label attribution only for the exact unchanged source.
        candidates = []
        for path in sorted((root/'memory/sources').glob('*-review.json')):
            raw = path.read_bytes(); hashes[path.relative_to(root).as_posix()] = sha(raw)
            candidates.append(json.loads(raw))
        decisions = next((d for d in candidates if d.get('snapshot_sha256') == source_digest(snapshot)), None)
        if decisions is None:
            raw_days, _ = parse_snapshot(snapshot, roster, now.astimezone(ZoneInfo(policy['timezone'])).year)
            by_fingerprint = {}
            for candidate in candidates:
                if not candidate.get('reviewer'): continue
                for old in candidate.get('blocks', {}).values():
                    key = old.get('label_fingerprint')
                    if key: by_fingerprint.setdefault(key, []).append(old)
            rebound = {}
            for row in (r for rows in raw_days.values() for r in rows):
                matches = by_fingerprint.get(row['label_fingerprint'], [])
                targets = {(m.get('speaker_id'), m.get('gender')) for m in matches}
                if len(targets) > 1: raise ValueError('AMBIGUOUS_PRIOR_LABEL_REVIEW')
                if matches: rebound[row['id']] = matches[0]
            decisions = {'snapshot_sha256': source_digest(snapshot),
                'reviewer': 'REUSED_EXACT_UNCHANGED_LABEL_REVIEWS', 'blocks': rebound} if rebound else {}
    errors = validate_snapshot(snapshot, policy, now, revision_check)
    days, digest = parse_snapshot(snapshot, roster, now.astimezone(ZoneInfo(policy['timezone'])).year, decisions)
    if any(date.fromisoformat(day) > now.astimezone(ZoneInfo(policy['timezone'])).date() for day in days):
        errors.append('FUTURE_STORY_CONTENT')
    current = checkpoint(days, snapshot, digest)
    if current['quarantined_blocks']: errors.append('LATEST_DAY_HAS_UNREVIEWED_LABELS')
    members, index, sources = member_context(root, roster, days, cast, hashes)
    if state_records is None:
        state_records = []
        for path in sorted((root/'memory/curated').glob('*-dynamic-state.json')):
            raw = path.read_bytes(); hashes[path.relative_to(root).as_posix()] = sha(raw)
            state_records.extend(json.loads(raw))
    states = reviewed_states(state_records, sources, roster)
    for pid, member in members.items():
        member['reviewed_dynamic_records'] = [r for r in states if r.get('member_id') == pid]
    context = {'schema_version': 'editorial-runtime-2.1', 'members': members, 'source_hashes': hashes,
        'freshness': 'CURRENT_DOCUMENT_LOADED' if not errors else 'REQUIRES_REFRESH_OR_REVIEW',
        'source_conflicts': current['quarantined_blocks'], 'checkpoint': current,
        'snapshot_revision': snapshot['revisionId'], 'snapshot_sha256': digest}
    for role in ('chat-suite', 'director', 'writer', 'teacher', 'assistant', 'members'):
        path = f'skills/p004-{role}/SKILL.md'
        hashes[path] = sha((root/path).read_bytes())
    guide = 'skills/p004-chat-suite/references/runtime-v2.1.md'
    raw = (root/guide).read_bytes(); hashes[guide] = sha(raw)
    context['execution_rules'] = raw.decode('utf-8')
    relation_path = root/'memory/long-term/relationship-seeds.json'
    if relation_path.exists():
        raw = relation_path.read_bytes(); hashes[relation_path.relative_to(root).as_posix()] = sha(raw)
        context['relationship_records'] = json.loads(raw)
        context['relationship_note'] = 'Source IDs must be relinked before treating a candidate or old exchange as a current established relationship.'
    fact = {'status': 'NOT_REQUESTED', 'truth_certified': False}; claims = []
    if ledger is not None:
        from news_release_gate import evaluate
        fact = evaluate(ledger); fact['truth_certified'] = False
        if fact['status'] != 'PASS': errors.append('FACT_GATE_BLOCKED')
        else:
            keys = evidence_keys(ledger)
            if event_history is None: errors.append('NEWS_HISTORY_NOT_LOADED')
            elif not new_evidence_keys(keys, event_history): errors.append('NO_NEW_NEWS_EVIDENCE')
            claims = ledger['publish_claim_ids']
    review = None
    if scene is not None:
        review = review_scene(scene, context, claims)
        errors.extend(review['errors'])
        if not review['errors']: review['quality'] = quality_signals(scene)
        for turn in scene if isinstance(scene, list) and all(isinstance(t, dict) and 'speaker_id' in t and 'text' in t and 'id' in t for t in scene) else []:
            assertion = turn.get('action_assertion')
            if assertion:
                matching = [r for r in states if r.get('member_id') == turn['speaker_id']
                            and r.get('symbol') == assertion.get('symbol')
                            and r.get('action') == assertion.get('action')
                            and set(r['evidence_ids']).issubset(turn.get('memory_refs', []))]
                if not matching: errors.append('UNSUPPORTED_STORY_ACTION:'+turn['id'])
                if assertion.get('quantity') is not None and not any(r.get('quantity') == assertion['quantity'] for r in matching):
                    errors.append('UNSUPPORTED_QUANTITY:'+turn['id'])
            if turn.get('kind') == 'financial_fact' and not turn.get('claim_ids'):
                errors.append('FINANCIAL_FACT_WITHOUT_CLAIM:'+turn['id'])
            if turn.get('kind') == 'quote':
                quote = turn.get('quote', {})
                price = quote.get('price')
                import math
                if (isinstance(price, bool) or not isinstance(price, (int, float)) or not math.isfinite(price)
                        or not quote.get('as_of') or not quote.get('source_url') or not turn.get('claim_ids')):
                    errors.append('INVALID_OR_MISSING_QUOTE:'+turn['id'])
            if turn.get('kind') == 'course_start' and any(r.get('course_id') == turn.get('course_id')
                    and r.get('course_status') == 'COMPLETED_IN_FORMAL_STORY' for r in states):
                errors.append('COMPLETED_COURSE_RESTART_REQUIRES_EXPLICIT_REVIEW')
    return {'version': '2.1', 'status': 'BLOCK' if errors else 'CONTEXT_READY_FOR_HUMAN_REVIEW',
        'errors': sorted(set(errors)), 'context': context, 'member_index': index, 'scene_review': review,
        'states': {'facts': fact, 'story': 'CANDIDATE_NOT_ADOPTED', 'delivery': delivery_status()},
        'effective_history': sources, 'reviewed_dynamic_records': states,
        'runtime': {'online_tasks_updated': False, 'sending_enabled': False}, 'publication_allowed': False}


def save_projection(root, result, source_path):
    """Explicit archival projection only; readiness is never persisted as live."""
    root = Path(root)
    archive_only_errors = {'SNAPSHOT_STALE_OR_FUTURE', 'LATEST_REVISION_NOT_RECHECKED', 'REVISION_CHECK_STALE_OR_FUTURE'}
    if set(result['errors']) - archive_only_errors:
        raise ValueError('UNREVIEWED_OR_INVALID_SOURCE_CANNOT_UPDATE_PROJECTION')
    folder = root/'memory/derived/v2.1'
    write(folder/'member-index.json', {'schema': '65-member-entrypoints-v2.1',
        'source_snapshot': source_path, 'source_sha256': result['context']['snapshot_sha256'],
        'members': result['member_index'], 'freshness': 'ARCHIVE_REQUIRES_LIVE_REFRESH'})
    write(folder/'effective-history.json', result['effective_history'])
    for pid, entry in result['member_index'].items():
        records = [r for rows in result['effective_history'].values() for r in rows if r.get('speaker_id') == pid]
        write(folder/f'members/{pid}.json', {'identity': entry,
            'evidence_store': 'memory/derived/v2.1/effective-history.json',
            'evidence_ids': [r['id'] for r in records], 'recent_examples': records[-12:],
            'dynamic_records': [r for r in result['reviewed_dynamic_records'] if r.get('member_id') == pid],
            'real_trade_verified': False, 'source_snapshot': source_path})
    check = dict(result['context']['checkpoint'], source_snapshot_path=source_path)
    write(root/'memory/runtime/latest-checkpoint.json', check)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--snapshot'); p.add_argument('--fetch-google-docs', action='store_true')
    p.add_argument('--revision-check'); p.add_argument('--decisions'); p.add_argument('--members', default='')
    p.add_argument('--scene'); p.add_argument('--ledger'); p.add_argument('--event-history')
    p.add_argument('--curated-state')
    p.add_argument('--output', required=True)
    p.add_argument('--date', help='Planned story date; does not change retrieval freshness')
    args = p.parse_args()
    if bool(args.snapshot) == args.fetch_google_docs: p.error('Choose exactly one source mode')
    policy = load(ROOT/POLICY)
    native = fetch_document(policy) if args.fetch_google_docs else load(args.snapshot)
    check = fetch_document(policy) if args.fetch_google_docs else load(args.revision_check) if args.revision_check else None
    def optional(path): return load(path) if path else None
    try:
        result = run(ROOT, native, args.members.split(',') if args.members else [], datetime.now(timezone.utc), check,
                     optional(args.decisions), optional(args.scene), optional(args.ledger), optional(args.event_history), optional(args.curated_state))
    except (ValueError, KeyError, TypeError) as error:
        write(args.output, {'version':'2.1', 'status':'BLOCK', 'errors':[str(error)], 'publication_allowed':False})
        print('BLOCK'); return 2
    if args.date:
        planned = date.fromisoformat(args.date)
        result['planned_story_date'] = args.date
        result['planned_activity'] = ('WEEKLY_REVIEW_AND_OUTLOOK' if planned.weekday() == 6 else
            'TECHNICAL_CLASS_AND_US_QUIZ' if planned.weekday() in (0, 2, 4) else
            'PRINCIPLES_CLASS_AND_KNOWLEDGE_QUIZ' if planned.weekday() in (1, 3) else 'NO_FIXED_ACTIVITY')
    result['input_file_receipts'] = {path: sha(Path(path).read_bytes()) for path in
        (args.snapshot, args.revision_check, args.decisions, args.curated_state, args.scene, args.ledger, args.event_history) if path}
    write(args.output, result)
    print(result['status'])
    return 2 if result['errors'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
