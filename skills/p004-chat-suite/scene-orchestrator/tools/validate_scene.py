#!/usr/bin/env python3
"""Static fiction-scene checks: identities, labels and obvious format errors only."""
from __future__ import annotations
import argparse
from collections import defaultdict
import json
from pathlib import Path
import re
import sys

SPEAKER = re.compile(r'^\s*(?:(?:={3,}\s*(资讯助理|先生)\s*={3,})|(?:(\d{1,2})(男|女)\s*[：:]))\s*(.*)$')
OLD_TEACHER = re.compile(r'(?<![A-Za-z])(Henry(?:\s+Fairchild)?|Jonathan(?:\s+Richard\s+Hayes)?)(?:先生|\s+先生)', re.I)
CURRENT = re.compile(r'(今天(?:的)?活动|今日(?:的)?活动|本期(?:的)?活动|今天(?:的)?(?:题目|判断题|竞猜)|今日(?:的)?(?:题目|判断题|竞猜))')

def analyze(text: str, people: list[dict], *, max_active: int = 42, activity: bool = False, scene: str = 'unspecified', corrections: dict | None = None) -> dict:
    issues = []
    def add(code, severity, detail, line=None):
        issue = {'code':code,'severity':severity,'detail':detail}
        if line is not None: issue['line'] = line
        issues.append(issue)
    if not text.strip(): add('EMPTY','blocker','没有可审核的稿件')
    indexed = {int(x['id']):x for x in people}
    if len(indexed)!=65 or set(indexed)!=set(range(1,66)):
        add('BAD_ROSTER','blocker','65人权威名单缺失或编号重复')
    if not isinstance(max_active,int) or not 1<=max_active<=65:
        add('BAD_ACTIVE_RANGE','blocker','出场范围无效')
    speakers = []
    seen = defaultdict(list)
    for line_no,line in enumerate(text.splitlines(),1):
        if '**' in line or '__' in line: add('MARKDOWN_BOLD','blocker','复制稿出现Markdown加粗',line_no)
        if OLD_TEACHER.search(line): add('OLD_TEACHER','blocker','新稿出现前任先生称谓',line_no)
        m=SPEAKER.match(line)
        if not m:
            if re.match(r'^\s*\d{1,2}[男女]\s*',line):add('INVALID_LABEL','blocker','人物发言需使用冒号',line_no)
            continue
        staff,ident,gender,body=m.groups()
        if staff: label=staff
        else:
            ident_no=int(ident)
            label=f'{ident_no:02d}{gender}'
            target=indexed.get(ident_no)
            if not target: add('UNKNOWN_MEMBER','blocker',f'未知成员{ident_no:02d}',line_no)
            else:
                if ident_no>max_active: add('OUT_OF_RANGE','blocker',f'成员{ident_no:02d}无当前出场权限',line_no)
                if gender!=target['gender']: add('GENDER_MISMATCH','blocker',f'{ident_no:02d}应为{target["gender"]}，稿件为{gender}',line_no)
                if ident!=f'{ident_no:02d}': add('NON_PADDED_LABEL','warning','人物编号应补零',line_no)
        speakers.append({'label':label,'line':line_no})
        normalized=re.sub(r'[\s，。？！,.!?：:、“”‘’\-（）()]+','',body)
        if len(normalized)>=10:
            if seen[normalized]: add('DUPLICATE_TURN','blocker',f'与先前台词完全重复：{label}',line_no)
            seen[normalized].append(label)
    if scene == 'morning':
        active_rules = [r for r in (corrections or {}).get('rules', []) if r.get('status') == 'approved' and r.get('scene') == 'morning']
        if corrections is None:
            add('MISSING_CORRECTIONS','blocker','上午稿缺少Notion已批准纠错快照')
        if not active_rules:
            add('NO_APPROVED_RULES','blocker','上午稿无可用的已批准纠错规则')
        # Only check the opening lead, not incidental later mentions of last night's lesson.
        lines = text.splitlines()
        lead = '\n'.join(lines[:min(14, len(lines))])
        for rule in active_rules:
            if rule.get('status') != 'approved' or rule.get('scene') != 'morning':
                continue
            for term in rule.get('forbidden_lead_terms', []):
                if re.search(term, lead):
                    add('MORNING_LESSON_LEAD','blocker','上午开场不应以昨晚课程复盘为主线：'+term)
                    break
            if not any(re.search(term, lead) for term in rule.get('required_lead_terms', [])):
                add('MORNING_NO_MARKET_LEAD','blocker','上午开场缺少财经资讯主线')
        add('MORNING_SEMANTIC_MANUAL','manual','关键词仅做初筛，仍需导演审核节点、资讯时点和主线')
    if activity:
        # 2026-10-22: no prior-answer/result precondition for new activities.
        today=CURRENT.search(text)
        if not today: add('MISSING_CURRENT_ACTIVITY','blocker','未发现今日活动题')
    add('REAL_FACTS_MANUAL','manual','真实市场数据、活动结果、来源时点需单独核验')
    add('VOICE_MANUAL','manual','人物自然度及剧情连续性需要本人历史对白人工复核')
    return {'pass':not any(x['severity']=='blocker' for x in issues),'speakers':speakers,'issues':issues,
            'not_checked':['live-financial-facts','current-google-doc-revision','voice-similarity','family-facts','delivery-status']}

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('draft',type=Path)
    parser.add_argument('--roster',type=Path,default=Path(__file__).resolve().parents[2]/'characters/final-identity-65.json')
    parser.add_argument('--max-active',type=int,default=42)
    parser.add_argument('--activity',action='store_true')
    parser.add_argument('--scene',choices=['morning','afternoon','evening','general'],required=True,help='Required so morning-specific correction gates cannot be silently bypassed')
    parser.add_argument('--corrections',type=Path,default=Path(__file__).resolve().parents[1]/'references/notion-approved-corrections.json')
    parser.add_argument('--json',action='store_true')
    args=parser.parse_args(argv)
    if not args.roster.is_file():parser.error('缺少65人最终身份表：'+str(args.roster))
    if not args.draft.is_file():parser.error('缺少输入稿：'+str(args.draft))
    people=json.loads(args.roster.read_text(encoding='utf-8-sig'))['people']
    corrections=json.loads(args.corrections.read_text(encoding='utf-8-sig')) if args.corrections.is_file() else None
    result=analyze(args.draft.read_text(encoding='utf-8-sig'),people,max_active=args.max_active,activity=args.activity,scene=args.scene,corrections=corrections)
    if args.json:print(json.dumps(result,ensure_ascii=False,indent=2))
    else:
        print('PASS (static only)' if result['pass'] else 'BLOCKED')
        for i in result['issues']:print(i['severity'],i['code'],i['detail'])
    return 0 if result['pass'] else 2

if __name__=='__main__':sys.exit(main())
