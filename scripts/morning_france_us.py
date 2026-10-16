#!/usr/bin/env python3
"""France + prior US close: a separate, evidence-gated Chinese morning draft.

Never invent CAC 40 data, market changes or official source claims.
This module NEVER sends to Telegram or marks material editorially approved.
"""
import argparse
from datetime import datetime, timedelta
import json
from pathlib import Path
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

from morning_opening import BUCHAREST, build as us_build, is_https, parse_iso

ALLOWED_OFFICIAL_DOMAINS = (
    'insee.fr', 'banque-france.fr', 'amf-france.org', 'euronext.com',
    'economie.gouv.fr', 'ecb.europa.eu', 'ec.europa.eu', 'eurostat.ec.europa.eu',
    'gouvernement.fr', 'bpifrance.fr', 'bourse-france.fr'
)

FR_OPENING = (
    "===== 资讯助理 =====\n"
    "🌤️ 大家上午好，欢迎回到 ELLERY WESTCOTT 社群！\n"
    "今天的早间分享重点关注法国市场与上一美股交易日，"
    "先梳理经过核实的市场信息，再看法国经济和相关行业的最新变化。"
)


def official_url(url):
    if not is_https(url):
        return False
    host = urlsplit(url).hostname.lower()
    return any(host == d or host.endswith('.' + d) for d in ALLOWED_OFFICIAL_DOMAINS)


def validate_france(evidence, now):
    """Structural and provenance checks only; substantive truth still requires editorial review."""
    if not isinstance(evidence, dict) or evidence.get('target_country') != 'FR':
        raise ValueError('Missing FR-targeted official source evidence')
    if evidence.get('review_status') != 'REVIEWED' or not evidence.get('reviewed_by'):
        raise ValueError('French sources not fact reviewed')
    checked = parse_iso(evidence.get('source_checked_at'))
    if checked > now or now - checked > timedelta(hours=12):
        raise ValueError('French source check is stale or future')
    events = evidence.get('events')
    if not isinstance(events, list) or not 1 <= len(events) <= 3:
        raise ValueError('Require one to three significant reviewed French events')
    keys = set()
    result = []
    for row in events:
        if not isinstance(row, dict):
            raise ValueError('Invalid French event')
        if row.get('target_country') != 'FR' or row.get('material_new_fact') is not True:
            raise ValueError('Event is not independently material for France')
        url = row.get('source_url', '')
        if not official_url(url):
            raise ValueError('French event must have official source URL')
        published = parse_iso(row.get('published_at'))
        if published > now or now - published > timedelta(days=5):
            raise ValueError('French event is stale/future')
        key = row.get('event_key')
        if not isinstance(key, str) or not (8 <= len(key) <= 160) or key in keys:
            raise ValueError('Invalid/duplicate event key')
        keys.add(key)
        sha = row.get('source_body_sha256')
        if not isinstance(sha, str) or len(sha) != 64 or any(c not in '0123456789abcdef' for c in sha):
            raise ValueError('Missing original body SHA256')
        for field in ('title_cn','fact_cn','source_excerpt','impact_cn','watch_cn'):
            if not isinstance(row.get(field), str) or not row[field].strip():
                raise ValueError('French event missing ' + field)
        if not any(word in row['impact_cn'] for word in ('可能', '如果', '若', '取决于', '需观察', '需要观察')):
            raise ValueError('French impact must be conditional')
        result.append(row)
    return result


def build(now, us_market=None, france_evidence=None):
    if now.tzinfo is None:
        raise ValueError('Timezone required')
    local = now.astimezone(BUCHAREST)
    output = {
        'task': 'westcott-france-us-morning', 'target_country': 'FR',
        'us_market': 'US', 'local_date': local.date().isoformat(),
        'scheduled_time': '07:30', 'timezone': 'Europe/Bucharest',
        'prepared_at': local.isoformat(), 'status': 'HELD_SOURCE_REQUIRED',
        'opening_draft': FR_OPENING, 'us_recap_draft': None,
        'france_draft': None, 'telegram_sent': False, 'delivery_allowed': False,
        'formal_google_docs_loaded': False,
        'reason': '缺少当日已审核法国重大事件及上一美股交易日的实际收盘凭据；没有生成可发布内容。'
    }
    us = us_build(local, us_market)
    if us['status'] != 'READY_FOR_EDITORIAL_REVIEW':
        return output
    output['us_recap_draft'] = us['us_recap_draft'].removeprefix('===== 资讯助理 =====\n')
    try:
        events = validate_france(france_evidence, local)
    except (ValueError, TypeError, KeyError):
        output['status'] = 'HELD_FRANCE_EVIDENCE_REQUIRED'
        output['reason'] = '缺少经核验的法国官方新闻、发布时间、影响分析或事件证据。'
        return output
    sections = ["🔴 法国｜已核实的重要进展"]
    for row in events:
        sections += [
            "📰 " + row['title_cn'].strip(),
            row['fact_cn'].strip(),
            "对法国市场的影响：" + row['impact_cn'].strip(),
            "后续关注：" + row['watch_cn'].strip(),
            "原始来源：" + row['source_url'].strip()
        ]
    output['france_draft'] = '\n\n'.join(sections)
    output['status'] = 'READY_FOR_EDITORIAL_REVIEW'
    output['reason'] = '法国及美国资料通过结构审查；仍须人工确认原文、正式剧情和跨任务去重。'
    return output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--us-source', default='news/verified-market/us-close-latest.json')
    parser.add_argument('--fr-source', default='news/verified-market/france-morning-latest.json')
    parser.add_argument('--output', default='morning-france-review.json')
    parser.add_argument('--text-output', default='morning-france-review.txt')
    args = parser.parse_args()
    def get(path):
        try:
            return json.loads(Path(path).read_text(encoding='utf-8'))
        except (OSError, ValueError):
            return None
    result = build(datetime.now(BUCHAREST), get(args.us_source), get(args.fr_source))
    Path(args.output).write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    sections = [result['opening_draft']]
    if result['us_recap_draft']:
        sections.append(result['us_recap_draft'])
    if result['france_draft']:
        sections.append(result['france_draft'])
    sections.append('内部状态：' + result['status'] + '\n' + result['reason'] +
                    '\n未发送 Telegram；未更新正式剧情。')
    Path(args.text_output).write_text('\n\n'.join(sections) + '\n', encoding='utf-8')
    print('france-us-morning-prep:', result['status'])


if __name__ == '__main__':
    main()
