#!/usr/bin/env python3
import json,sys,csv,re
from pathlib import Path
root=Path(__file__).resolve().parents[1]
ch=root/'skills/p004-chat-suite/characters'
roster=json.loads((ch/'final-identity-65.json').read_text(encoding='utf-8'))
people=roster['people']
assert len(people)==65 and len({p['id'] for p in people})==65
fields=['name','nick','gender','age','occupation','investment_years','capital_scale','student_seniority','location','background_note']
assert [p['id'] for p in people]==[f'{i:02}' for i in range(1,66)]
for p in people:
 q=json.loads((ch/'profiles'/f"{p['id']}.json").read_text(encoding='utf-8'))
 for field in ['id']+fields: assert p[field]==q[field],(p['id'],field,p[field],q[field])
 assert p['gender'] in ('男','女') and q.get('identity_approved_by_user') is True
 assert q.get('voice',{}).get('voice_status')=='CREATIVE_DRAFT_NOT_USER_APPROVED'
with (ch/'final-identity-65.csv').open(encoding='utf-8-sig',newline='') as f:
 rows=list(csv.DictReader(f))
assert len(rows)==65
for p,row in zip(people,rows):
 assert row['id']==p['id']
 assert row['name']==p['name']
 assert row['gender']==p['gender']
 assert int(row['age'])==p['age']
assert [(people[int(i)-1]['gender'],people[int(i)-1]['capital_scale']) for i in ['06','16','26','36','46','56']]==[('男','大额投资'),('女','大额投资'),('女','大额投资'),('男','大额投资'),('男','大额投资'),('男','大额投资')]
assert people[9]['name']=='Mirela Pană' and people[9]['gender']=='女'
req=[root/f'skills/p004-{n}/SKILL.md' for n in ['director','writer','teacher','assistant','members']]
req += [root/'skills/p004-chat-suite/SKILL.md',root/'skills/p004-chat-suite/references/staff-and-role-identity-20261012.md']
for p in req:
 s=p.read_text(encoding='utf-8')
 assert 'Jonathan' in s and (p.name=='staff-and-role-identity-20261012.md' or 'Nicolae' not in s),(p,'wrong teacher')
for p in (root/'skills').rglob('*.md'):
 s=p.read_text(encoding='utf-8')
 if p.name!='staff-and-role-identity-20261012.md':
  assert 'Nicolae Petrescu' not in s,(p,'stale teacher')
assert not (root/'skills/p004-professor').exists()
assert not (root/'skills/p004-fiction-director').exists()
assert not (ch/'name-update.json').exists()
assert not list(root.rglob('roster-v2.json'))
assert not list(root.rglob('approved-roster.json'))
assert not list(root.rglob('*.secret'))
mem=json.loads((root/'memory/daily/2026-10-12/day-memory.json').read_text(encoding='utf-8'))
assert mem['canonical_text_message_count']==63 and mem['reactions_count']==1
assert mem['review_required_count']>=1 and mem['teacher_current_identity'].startswith('Jonathan')
assert (root/'memory/daily/2026-10-12/final-transcript-submitted.md').exists()
assert (root/'memory/daily/2026-10-12/TEACHER-NAME-REVISION.md').exists()
assert len(list((root/'memory/long-term/members').glob('*.json')))==16
print('PASS: 65 canonical identities + 65 profiles + CSV + six large-investment personas + teacher Jonathan + five Skills + daily memory audit; editorial exceptions remain flagged')
