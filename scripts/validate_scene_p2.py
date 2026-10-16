#!/usr/bin/env python3
"""P2 read-only, evidence-based heuristic checks; not a semantic approval engine."""
import argparse, json, re, unicodedata
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
LABEL=re.compile(r'^\s*(\d{1,2})([男女])?\s*[：:]\s*$')
STAFF=re.compile(r'^\s*={2,}\s*(.*?)\s*={2,}\s*$')
def norm(s):
    return ''.join(c for c in unicodedata.normalize('NFKC',s) if c.isalnum())
def inspect(snapshot,relationship):
    paragraphs=snapshot.get('paragraphs',[])
    issues=[]
    turns=[]
    speaker=None
    label_index=None
    for p in paragraphs:
        t=p.get('text','')
        idx=p.get('paragraph_index')
        m=LABEL.match(t)
        h=STAFF.match(t)
        if m or h:
            if speaker is not None:
                turns.append({'speaker':speaker,'label_index':label_index,'text':'\n'.join(buf),'paragraph_indexes':ids})
            speaker=f'{int(m.group(1)):02}' if m else h.group(1).strip()
            label_index=idx
            buf=[];ids=[]
            if m and not m.group(2):
                issues.append({'code':'SPEAKER_GENDER_LABEL_MISSING','severity':'REVIEW','paragraph_indexes':[idx],'evidence_id':f'DOC-P{idx}'})
        elif speaker is not None:
            buf.append(t);ids.append(idx)
    if speaker is not None:
        turns.append({'speaker':speaker,'label_index':label_index,'text':'\n'.join(buf),'paragraph_indexes':ids})
    for a,b in zip(turns,turns[1:]):
        na,nb=norm(a['text']),norm(b['text'])
        if a['speaker']==b['speaker'] and na and nb and (na==nb or (min(len(na),len(nb))>=12 and (na in nb or nb in na))):
            issues.append({'code':'ADJACENT_NEAR_DUPLICATE','severity':'REVIEW','paragraph_indexes':[a['label_index'],b['label_index']],'evidence_id':f'DOC-P{a["label_index"]}-P{b["label_index"]}'})
    pending=[]
    for seed in relationship.get('seeds',[]):
        if seed.get('status') in ('FUTURE_DEVELOPMENT_NOT_ADOPTED_HISTORY','ONE_DOCUMENTED_EXCHANGE_NOT_FIXED_RELATIONSHIP'):
            pending.append({'member_ids':seed.get('member_ids'),'status':seed['status'],'review':'RELATIONSHIP_PROMOTION_REQUIRES_ADOPTED_EVIDENCE'})
    return {'schema':'westcott-p2-scene-review-v1','source_document_id':snapshot.get('document_id'),'source_revision':snapshot.get('revision_id'),'story_date_attribution':snapshot.get('date_attribution'),'total_turns':len(turns),'issues':issues,'relationship_guards':pending,'review_status':'PENDING_HUMAN_REVIEW','semantic_pass':False,'note':'Detectable warning flags only; no modification of source or invented evidence. Financial truth and voice quality require human review.'}
def main():
    p=argparse.ArgumentParser();p.add_argument('--snapshot',default='memory/daily/2026-10-16/formal-google-doc-snapshot.json');p.add_argument('--relationships',default='memory/long-term/relationship-seeds.json');p.add_argument('--output',default='audit/P2-SCENE-REVIEW-2026-10-16.json');a=p.parse_args()
    r=inspect(json.loads((ROOT/a.snapshot).read_text()),json.loads((ROOT/a.relationships).read_text()))
    (ROOT/a.output).parent.mkdir(parents=True,exist_ok=True)
    (ROOT/a.output).write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
    print('P2_SCENE_REVIEW='+json.dumps({'turns':r['total_turns'],'issues':r['issues'],'review_status':r['review_status']},ensure_ascii=False))
if __name__=='__main__':main()
