"""Validate embedded persona snapshots against canonical files, not online loading."""
import csv
import io
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BEGIN = '【WESTCOTT_RUNTIME_CONTEXT_V1.5.2_BEGIN】'
END = '【WESTCOTT_RUNTIME_CONTEXT_V1.5.2_END】'

def section(text, tag):
    if text.count('[' + tag + ']') != 1 or text.count('[/' + tag + ']') != 1:
        raise ValueError('Missing or duplicated section: ' + tag)
    return text.split('[' + tag + ']', 1)[1].split('[/' + tag + ']', 1)[0].strip()

def validate(text, root=ROOT):
    if text.count(BEGIN) != 1 or text.count(END) != 1:
        raise ValueError('Missing or duplicated runtime capsule')
    if text.index(END) < text.index(BEGIN):
        raise ValueError('Invalid capsule order')
    context = text.split(BEGIN, 1)[1].split(END, 1)[0]
    suite = root / 'skills/p004-chat-suite'
    roster = json.loads((suite / 'characters/final-identity-65.json').read_text(encoding='utf-8'))['people']
    rows = list(csv.DictReader(io.StringIO(section(context, 'IDENTITY_CSV'))))
    fields = ['id','name','nick','gender','age','occupation','investment_years','capital_scale','student_seniority','location','background_note']
    if len(rows) != 65 or len({r.get('id') for r in rows}) != 65:
        raise ValueError('Expected exactly 65 unique identities')
    for row, person in zip(rows, roster):
        if set(row) != set(fields) or any(row[k] != str(person[k]) for k in fields):
            raise ValueError('Identity mismatch: ' + str(row.get('id')))
    voices = section(context, 'VOICE_REFERENCE').splitlines()
    if len(voices) != 65:
        raise ValueError('Voice row count mismatch')
    for line, person in zip(voices, roster):
        profile = json.loads((suite / f"characters/profiles/{person['id']}.json").read_text(encoding='utf-8'))
        voice = profile['voice']
        expected = '|'.join([person['id'],voice['sentence_length'],voice['register'],voice['emoji_style'],'；'.join(profile['interest_triggers'])])
        if line != expected:
            raise ValueError('Voice projection mismatch: ' + person['id'])
    actual_history = [json.loads(line) for line in section(context, 'ADOPTED_MEMORY_CONFIRMED').splitlines()]
    expected_history = []
    for path in sorted((root / 'memory/long-term/members').glob('*.json')):
        data = json.loads(path.read_text(encoding='utf-8'))
        for entry in data.get('observed_in_submitted_story', []):
            expected_history.append({'id':path.stem, **{k:entry[k] for k in ('message_id','node','kind','text')}})
    # Cross-check every projected member event against adopted daily source messages.
    allowed={'ADOPTED_IN_SUBMITTED_TRANSCRIPT','ADOPTED_IN_USER_SUBMITTED_STORY'}
    source={}
    for day in sorted((root/'memory/daily').glob('*/day-memory.json')):
        data=json.loads(day.read_text(encoding='utf-8'))
        for entry in data['messages']:
            if entry['status'] not in allowed or not (len(str(entry.get('speaker_id',''))) == 2 and str(entry.get('speaker_id','')).isdigit()):
                continue
            key=entry['id']
            if key in source:
                raise ValueError('Duplicate adopted source id: '+key)
            source[key]={'id':entry['speaker_id'],'message_id':key,'node':entry['node'],
                         'kind':entry.get('kind','message'),'text':entry['text']}
    if actual_history != expected_history:
        raise ValueError('Adopted memory projection mismatch')
    if len({x['message_id'] for x in expected_history}) != len(expected_history):
        raise ValueError('Duplicate long-term memory event')
    if {x['message_id']:x for x in expected_history} != source:
        raise ValueError('Long-term memory differs from adopted daily source')
    return {'identities':65,'voice_references':65,'adopted_memory_entries':len(expected_history),'members_with_adopted_history':len({x['id'] for x in expected_history}),
            'result':'SOURCE_PROJECTION_MATCH_ONLY_NOT_ONLINE_LOADING_PROOF'}

if __name__ == '__main__':
    for path in sorted((ROOT / 'integrations/chatgpt-scheduled').glob('*.txt')):
        print(path.name, json.dumps(validate(path.read_text(encoding='utf-8')), ensure_ascii=False))
