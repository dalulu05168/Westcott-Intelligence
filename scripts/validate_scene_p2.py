#!/usr/bin/env python3
"""P2 read-only, evidence-based heuristic checks; not a semantic approval engine."""
import argparse, json, re, unicodedata
from difflib import SequenceMatcher
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
LABEL=re.compile(r'^\s*(\d{1,2})([男女])?\s*[：:]\s*$')
INLINE_LABEL=re.compile(r'^\s*(\d{1,2})([男女])?\s*[：:]\s*')
STAFF=re.compile(r'^\s*={2,}\s*(.*?)\s*={2,}\s*$')
def norm(s):
    return ''.join(c for c in unicodedata.normalize('NFKC',s) if c.isalnum())

def quality_review(turns, snapshot):
    """Evidence candidates only. Never decides whether a character or financial claim is true."""
    members=[t for t in turns if t['speaker'].isdigit()]
    from collections import Counter
    counts=Counter(t['speaker'] for t in members)
    voice=[]
    for pid in sorted(counts):
        samples=[t for t in members if t['speaker']==pid]
        texts=[t['text'] for t in samples]
        voice.append({'speaker':pid,'sample_count':len(samples),
                      'average_chars':round(sum(len(t) for t in texts)/len(texts),1),
                      'questions':sum(('?' in t or '？' in t) for t in texts),
                      'emoji_tendency_samples':sum(bool(re.search(r'[\U0001F300-\U0001FAFF]',t)) for t in texts),
                      'review':'INSUFFICIENT_SAMPLES' if len(samples)<2 else 'HEURISTIC_ONLY_NOT_APPROVED_VOICE'})
    adjacency=[]
    for before,after in zip(turns,turns[1:]):
        if before['speaker'].isdigit() and after['speaker'].isdigit() and before['speaker']!=after['speaker']:
            adjacency.append({'from_speaker':before['speaker'],'to_speaker':after['speaker'],
                              'from_paragraph':before['label_index'],'to_paragraph':after['label_index'],
                              'status':'ADJACENT_ONLY_NOT_PROVEN_REPLY'})
    explicit=[]
    for t in members:
        for m in re.finditer(r'(?<!\d)(\d{1,2})号',t['text']):
            pid=f'{int(m.group(1)):02}'
            if pid!=t['speaker'] and 1<=int(pid)<=40:
                explicit.append({'from_speaker':t['speaker'],'mentioned_speaker':pid,
                                 'evidence_id':f'DOC-P{t["label_index"]}',
                                 'status':'EXPLICIT_REFERENCE_NOT_PROVEN_RELATIONSHIP'})
    shared=[]
    for i,a in enumerate(members):
        for b in members[i+1:]:
            if a['speaker']==b['speaker']:
                continue
            na,nb=norm(a['text']),norm(b['text'])
            if min(len(na),len(nb))>=18 and SequenceMatcher(None,na,nb).ratio()>=0.90:
                shared.append({'speaker_ids':[a['speaker'],b['speaker']],
                               'evidence_ids':[f'DOC-P{a["label_index"]}',f'DOC-P{b["label_index"]}'],
                               'status':'CROSS_SPEAKER_SIMILARITY_REVIEW'})
    trade=[]
    trade_marker=re.compile(r'持有|买过|买入|买进|卖出|卖掉|加仓|赚到|盈利|获利|买入价|成本|卖早')
    for i,t in enumerate(turns):
        if t['speaker'].isdigit() and trade_marker.search(t['text']):
            earlier=[x for x in turns[:i] if x['speaker']==t['speaker'] and trade_marker.search(x['text'])]
            trade.append({'speaker':t['speaker'],'evidence_id':f'DOC-P{t["label_index"]}',
                          'prior_in_scene_evidence_ids':[f'DOC-P{x["label_index"]}' for x in earlier],
                          'status':'STORY_CHARACTER_CLAIM_NOT_VERIFIED_REAL_TRADE',
                          'historical_evidence':'IN_SCENE_ONLY' if earlier else 'OLDER_ARCHIVES_NOT_EVALUATED'})
    facts=[]
    market_regex=re.compile(r'(?:\b(?:BET|BRD|TLV|SNP|NASDAQ|道琼斯|标普|纳斯达克)\b|指数|市场).*?(?:\d[\d,.]*\s*(?:点|RON|%)|[+-]\d+(?:\.\d+)?%)',re.I|re.S)
    for t in turns:
        if not t['speaker'].isdigit() and market_regex.search(t['text']):
            facts.append({'speaker':t['speaker'],'evidence_id':f'DOC-P{t["label_index"]}',
                          'status':'MARKET_FACT_EXTERNAL_SOURCE_NOT_VERIFIED',
                          'truth':'UNDETERMINED','review_required':'INDEPENDENT_TIMESTAMPED_SOURCE'})
    return {'voice_samples':voice,'cross_speaker_similarity':shared,
            'interaction':{'member_to_member_adjacencies':adjacency,
                           'explicit_member_mentions':explicit,
                           'member_turn_count':len(members),
                           'staff_turn_count':len(turns)-len(members),
                           'status':'DESCRIPTIVE_NOT_PROOF_OF_NATURAL_CONVERSATION'},
            'character_trade_claims':trade,'market_fact_candidates':facts,
            'semantic_status':'PENDING_HUMAN_REVIEW',
            'note':'Counts and similarity are only review aids. No voice, relationship, trade or market datum is independently approved.'}

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
        embedded=INLINE_LABEL.match(t) if not m else None
        h=STAFF.match(t)
        if m or embedded or h:
            if speaker is not None:
                turns.append({'speaker':speaker,'label_index':label_index,'text':'\n'.join(buf),'paragraph_indexes':ids})
            member=m or embedded
            speaker=f'{int(member.group(1)):02}' if member else h.group(1).strip()
            label_index=idx
            buf=[];ids=[]
            if member and not member.group(2):
                issues.append({'code':'SPEAKER_GENDER_LABEL_MISSING','severity':'REVIEW','paragraph_indexes':[idx],'evidence_id':f'DOC-P{idx}'})
            if embedded:
                remainder=t[embedded.end():].strip()
                if remainder:
                    buf.append(remainder);ids.append(idx)
                    issues.append({'code':'EMBEDDED_MEMBER_LABEL','severity':'REVIEW','paragraph_indexes':[idx],'evidence_id':f'DOC-P{idx}'})
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
    return {'schema':'westcott-p2-scene-review-v2','quality_review':quality_review(turns,snapshot),'source_document_id':snapshot.get('document_id'),'source_revision':snapshot.get('revision_id'),'story_date_attribution':snapshot.get('date_attribution'),'total_turns':len(turns),'issues':issues,'relationship_guards':pending,'review_status':'PENDING_HUMAN_REVIEW','semantic_pass':False,'note':'Detectable warning flags only; no modification of source or invented evidence. Financial truth and voice quality require human review.'}
def main():
    p=argparse.ArgumentParser();p.add_argument('--snapshot',default='memory/daily/2026-10-16/formal-google-doc-snapshot.json');p.add_argument('--relationships',default='memory/long-term/relationship-seeds.json');p.add_argument('--output',default='audit/P2-SCENE-REVIEW-2026-10-16.json');a=p.parse_args()
    r=inspect(json.loads((ROOT/a.snapshot).read_text()),json.loads((ROOT/a.relationships).read_text()))
    (ROOT/a.output).parent.mkdir(parents=True,exist_ok=True)
    (ROOT/a.output).write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
    print('P2_SCENE_REVIEW='+json.dumps({'turns':r['total_turns'],'issues':r['issues'],'interaction':{'member_adjacencies':len(r['quality_review']['interaction']['member_to_member_adjacencies']),'explicit_mentions':len(r['quality_review']['interaction']['explicit_member_mentions'])},'trade_claims':len(r['quality_review']['character_trade_claims']),'market_fact_candidates':len(r['quality_review']['market_fact_candidates']),'review_status':r['review_status']},ensure_ascii=False))
if __name__=='__main__':main()
