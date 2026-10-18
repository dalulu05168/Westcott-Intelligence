#!/usr/bin/env python3
"""Adoption evidence checks and isolated cross-session acceptance helpers.

No API calls, source mutation, candidate adoption or sending. A user confirmation
alone cannot convert absent candidate text into formal document history.
"""
import hashlib
import json
from editorial_execution import normalized
from editorial_runtime_v21 import evidence_fingerprint


def scene_digest(scene):
    return hashlib.sha256(json.dumps(scene, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def verify_adoption(scene, formal_days, confirmation, revision, *, story_date):
    if (confirmation.get('confirmed_by_user') is not True or not confirmation.get('confirmation_reference')
            or confirmation.get('scene_sha256') != scene_digest(scene)
            or confirmation.get('formal_revision') != revision):
        raise ValueError('ADOPTION_CONFIRMATION_OR_REVISION_MISMATCH')
    messages = [r for r in formal_days.get(story_date, [])
                if r.get('date') == story_date and r.get('status') == 'PRESENT_IN_FORMAL_DOCUMENT']
    proposed = []
    for turn in scene:
        matches = [r for r in messages if r['speaker_id'] == turn['speaker_id']
                   and normalized(r['text']) == normalized(turn['text'])]
        if len(matches) != 1:
            raise ValueError('CANDIDATE_ABSENT_OR_AMBIGUOUS_IN_FORMAL_DOCUMENT:'+turn['id'])
        message = matches[0]
        proposed.append({'event_id': evidence_fingerprint(message['date'], message['speaker_id'], message['text']),
            'candidate_turn_id': turn['id'], 'formal_message_id': message['id'], 'source_revision': revision,
            'speaker_id': message['speaker_id'], 'text': message['text'], 'source_date': message['date'],
            'status': 'VERIFIED_FOR_MEMORY_UPDATE_NOT_DELIVERY', 'real_trade_verified': False})
    if len({r['event_id'] for r in proposed}) != len(proposed):
        raise ValueError('DUPLICATE_ADOPTION_EVENT')
    return proposed


def project_events(existing, proposed):
    """Idempotent proposal view, not a write to production memory."""
    result = {r['event_id']: r for r in existing}
    for row in proposed:
        if row['event_id'] in result and result[row['event_id']]['text'] != row['text']:
            raise ValueError('EVENT_HASH_CONFLICT')
        result[row['event_id']] = row
    return list(result.values())


def next_session_plan(story_date, period, checkpoint, policy, course_plan):
    """Plan only. Never invent a future quote, stock order or completed course."""
    from datetime import date
    planned = date.fromisoformat(story_date)
    return {'date':story_date, 'period':period,
        'previous_confirmed_phase':checkpoint['story_phase'],
        'activity':'WEEKLY_REVIEW_AND_OUTLOOK' if planned.weekday()==6 and period=='EVENING' else
                   'TECHNICAL_CLASS' if period=='EVENING' and planned.weekday() in (0,2,4) else 'MARKET_OBSERVATION',
        'market_data':'REFRESH_AT_ACTUAL_SESSION',
        'research_order':policy['research']['order'],
        'course_material':course_plan.get(story_date,{}).get('title'),
        'course_status':course_plan.get(story_date,{}).get('status','NOT_CONFIRMED'),
        'adopted':False, 'delivered':False}
