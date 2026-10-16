#!/usr/bin/env python3
"""Import an explicitly requested Google Docs snapshot into audited story memory.

Does not fetch documents, certify news, send messages or infer learning/trades.
Previous derived views are retained under revisions; original source files stay intact.
"""
import argparse
from collections import Counter
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
from editorial_execution import ADOPTED, FORMAL_DOC_ID, LABEL, ROOT


def parse_tab(day, text, tab_id, roster, old):
    text = text.replace('\x0b', '\n')
    matches = list(LABEL.finditer(text)); rows = []; seen = {}; used = set()
    for index, match in enumerate(matches):
        pid = f'{int(match.group(1)):02}' if match.group(1) else {
            '资讯助理': 'news_assistant', '助理': 'news_assistant', '先生': 'teacher',
            '教授': 'teacher', '投资顾问': 'investment_advisor', '咨询顾问': 'consultant'
        }.get(match.group(3).strip(), 'unknown_staff')
        body = text[match.end():matches[index+1].start() if index+1<len(matches) else len(text)].strip()
        candidates = [m for m in old if m.get('speaker_id')==pid and m.get('text')==body]
        mid = candidates[0]['id'] if len(candidates)==1 else f'{day.replace("-", "")}-DOC-{index+1:03}'
        if mid in used:
            mid = f'{day.replace("-", "")}-DOC-{index+1:03}-repeat'
        used.add(mid)
        status = 'ADOPTED_IN_USER_SUBMITTED_STORY'; warnings = []
        if pid == 'unknown_staff' or (match.group(1) and (pid not in roster or roster[pid]['gender'] != match.group(2))):
            status = 'REVIEW_ROLE_MISMATCH'; warnings.append('UNRESOLVED_ROLE_OR_GENDER')
        if not body:
            status = 'EXCLUDED_EMPTY_LABEL'; warnings.append('EMPTY_LABEL')
        key = (pid, body)
        if key in seen and status == 'ADOPTED_IN_USER_SUBMITTED_STORY':
            status = 'EXCLUDED_EXACT_DUPLICATE'; warnings.append('DUPLICATE_OF:' + seen[key])
        elif status == 'ADOPTED_IN_USER_SUBMITTED_STORY':
            seen[key] = mid
        rows.append({'id': mid, 'speaker_id': pid, 'source_label': match.group(0).strip(),
                     'node': 'UNSPECIFIED_IN_SOURCE', 'kind': 'message', 'text': body,
                     'source_tab_id': tab_id, 'source_block_number': index+1,
                     'source_normalized_character_offset': match.start(),
                     'status': status, 'warnings': warnings, 'fictional_only': True,
                     'market_news_not_independently_verified': True, 'real_trade_not_inferred': True})
    return rows


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


def import_snapshot(root, snapshot, selected_dates):
    root = Path(root)
    if snapshot.get('documentId') != FORMAL_DOC_ID or not snapshot.get('revisionId'):
        raise ValueError('Expected formal document ID and revision')
    stamp = datetime.fromisoformat(snapshot['retrieved_at'].replace('Z', '+00:00'))
    if stamp.tzinfo is None:
        raise ValueError('Snapshot retrieval timezone required')
    key = stamp.strftime('%Y%m%dT%H%M%S%z')
    roster = {p['id']:p for p in json.loads((root/'skills/p004-chat-suite/characters/final-identity-65.json').read_text())['people']}
    tabs = {f"{stamp.year}-{int(t['title'].split('/')[0]):02}-{int(t['title'].split('/')[1]):02}":t
            for t in snapshot['tabs'] if re.fullmatch(r'\d{1,2}/\d{1,2}', t.get('title', ''))}
    report = []
    for day in selected_dates:
        tab = tabs[day]; folder = root/'memory/daily'/day
        paragraphs = [p for p in snapshot['paragraphs'] if p.get('tabId')==tab['tabId']]
        if not paragraphs:
            raise ValueError('Selected date has no text: '+day)
        raw = '\n'.join(p['text'] for p in paragraphs)
        old = json.loads((folder/'day-memory.json').read_text()) if (folder/'day-memory.json').exists() else {'messages':[]}
        rows = parse_tab(day, raw, tab['tabId'], roster, old['messages'])
        if not rows:
            raise ValueError('No recognized role blocks: '+day)
        revision = folder/'revisions'/key
        for name in ('day-memory.json', 'adopted-normalized.md'):
            p = folder/name
            if p.exists():
                revision.mkdir(parents=True,exist_ok=True)
                previous=revision/('previous-'+name)
                if not previous.exists():previous.write_bytes(p.read_bytes())
        source = {'documentId':snapshot['documentId'], 'revisionId':snapshot['revisionId'],
                  'retrieved_at':snapshot['retrieved_at'], 'tab':tab, 'paragraphs':paragraphs}
        write_json(revision/'source-paragraphs.json', source)
        (revision/'source-text.txt').write_text(raw, encoding='utf-8')
        for row in rows:
            row.update(source_google_doc_id=snapshot['documentId'], source_google_doc_url=snapshot.get('document_url'),
                       source_doc_revision=snapshot['revisionId'])
        approved = [r for r in rows if r['status'] in ADOPTED]
        current = {'schema_version':'formal-snapshot-1.0', 'date':day, 'story_date':day,
                   'source':'用户指定正式Google Docs当前修订文本', 'source_document_id':snapshot['documentId'],
                   'source_document_url':snapshot.get('document_url'), 'source_document_revision':snapshot['revisionId'],
                   'retrieved_at':snapshot['retrieved_at'], 'source_tab_id':tab['tabId'],
                   'source_snapshot':(revision/'source-paragraphs.json').relative_to(root).as_posix(),
                   'source_text_sha256':hashlib.sha256(raw.encode()).hexdigest(),
                   'normalization':'Only U+000B to LF and boundary whitespace for message extraction; raw paragraphs preserved.',
                   'story_only':True, 'not_verified_delivery':True, 'messages':rows}
        write_json(folder/'day-memory.json',current)
        (folder/'adopted-normalized.md').write_text('\n\n'.join(r['source_label']+'\n'+r['text'] for r in approved)+'\n')
        oldids={r['id'] for r in old['messages'] if r.get('status') in ADOPTED}
        newids={r['id'] for r in approved}
        summary={'date':day, 'source_revision':snapshot['revisionId'], 'role_blocks':len(rows),
                 'approved_role_blocks':len(approved), 'member_text_messages':sum(r['speaker_id'] in roster for r in approved),
                 'members':sorted({r['speaker_id'] for r in approved if r['speaker_id'] in roster}),
                 'quarantined_blocks':[r['id'] for r in rows if r['status'] not in ADOPTED],
                 'previous_adopted_ids_no_longer_effective':sorted(oldids-newids)}
        write_json(revision/'revision-change-log.json',summary);report.append(summary)
    # Re-project all effective adopted daily evidence; quarantine remains in source files.
    observed = {pid:[] for pid in roster}
    for p in sorted((root/'memory/daily').glob('*/day-memory.json')):
        data=json.loads(p.read_text());day=data.get('story_date') or data.get('date') or p.parent.name
        for r in data['messages']:
            pid=r.get('speaker_id')
            if pid not in roster or r.get('status') not in ADOPTED:
                continue
            entry={'message_id':r['id'],'source_date':day,'node':r['node'],'kind':r.get('kind','message'),'text':r['text']}
            for k in ('source_google_doc_id','source_google_doc_url','source_doc_revision','source_block_number','source_tab_id'):
                if k in r:entry[k]=r[k]
            observed[pid].append(entry)
    for pid, entries in observed.items():
        p=root/f'memory/long-term/members/{pid}.json'
        if not entries and not p.exists():continue
        old=json.loads(p.read_text()) if p.exists() else {}
        old.update(id=pid,name=roster[pid]['name'],identity_source='skills/p004-chat-suite/characters/final-identity-65.json',
                   status='USER_SUBMITTED_ADOPTED_WITH_AUDIT_FLAGS',observed_in_submitted_story=entries,
                   message_count=sum(e['kind']=='message' for e in entries),reaction_count=sum(e['kind']=='reaction' for e in entries),
                   no_unrecorded_history=True,no_real_trading_inferred=True,
                   latest_source_date=max((e['source_date'] for e in entries),default=None))
        write_json(p,old)
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('snapshot');parser.add_argument('--dates',required=True)
    args=parser.parse_args()
    print(json.dumps(import_snapshot(ROOT,json.loads(Path(args.snapshot).read_text()),args.dates.split(',')),ensure_ascii=False,indent=2))
