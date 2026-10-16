"""Fail-closed editorial acceptance: original photo and country-specific top one.

Scores are reviewed judgements grounded in the captured original bodies, not
keyword counts or a claim to know every event in the world.
"""
import hashlib
import json
import re
from datetime import datetime, timedelta, timezone

WEIGHTS = {'market_scope': 30, 'local_exposure': 25, 'magnitude': 20,
           'unexpectedness': 15, 'urgency': 10}
COUNTRIES = {'RO': ('🔵', '罗马尼亚'), 'FR': ('🔴', '法国')}
EDITION_PATH = re.compile(r'^news/editions/[a-z0-9_-]{8,80}\.json$')
MIN_SCORE = 70


class PolicyError(ValueError):
    pass


def instant(value):
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        raise PolicyError('Timezone required for hourly comparison.')
    return parsed.astimezone(timezone.utc)


def digest(record):
    return hashlib.sha256(json.dumps(record, ensure_ascii=False, sort_keys=True).encode('utf-8')).hexdigest()


def validate_release(prepared, root, now=None, expected_feed_ids=None):
    try:
        return _validate(prepared, root, now or datetime.now(timezone.utc), expected_feed_ids)
    except PolicyError:
        raise
    except (KeyError, TypeError, ValueError, OSError, AttributeError) as exc:
        raise PolicyError('Invalid/missing hourly comparison: ' + type(exc).__name__) from None


def _validate(prepared, root, now, expected_feed_ids):
    country = prepared.get('target_country')
    if country not in COUNTRIES:
        raise PolicyError('Explicit RO or FR target country required.')
    media = prepared['media']
    # User explicitly approved original article links when no approved original photo exists.
    if media.get('image_url'):
        if media.get('image_decision') != 'verified_original_publisher_photo':
            raise PolicyError('Uploaded photo must be matched and approved by the original publisher review.')
    elif (media.get('image_decision') not in ('original_article_link_preview',
            'original_article_link_preview_rights_unverified')
            or not media.get('article_url') or media['article_url'] not in prepared.get('sources', [])):
        raise PolicyError('Missing photo requires the selected original evidence article link.')
    for field in ('local_impact_claim_id', 'watch_next_claim_id'):
        cid = prepared.get(field)
        if cid not in prepared['claim_ids'] or prepared.get('claim_kinds', {}).get(cid) != 'analysis':
            raise PolicyError('Reviewed country-specific impact and watch-next analysis required.')
        if prepared.get('claim_countries', {}).get(cid) != country:
            raise PolicyError('Impact/watch analysis must explicitly concern the selected target country.')
    selection = prepared.get('hourly_selection', {})
    path = selection.get('edition_path', '')
    if not isinstance(path, str) or not EDITION_PATH.fullmatch(path):
        raise PolicyError('Committed hourly edition path is required.')
    edition = json.loads((root / path).read_text(encoding='utf-8'))
    if digest(edition) != selection.get('edition_sha256'):
        raise PolicyError('Hourly edition digest differs from reviewed snapshot.')
    start, end = instant(edition['window_start']), instant(edition['window_end'])
    if end - start != timedelta(hours=1) or not timedelta(0) <= now - end <= timedelta(minutes=20):
        raise PolicyError('Comparison must cover one recent complete 60-minute window.')
    if edition.get('status') != 'COMPLETE' or edition.get('truncated') is not False:
        raise PolicyError('Incomplete or truncated coverage cannot establish a highest-impact event.')
    if expected_feed_ids is None:
        from news_radar import FEEDS
        expected_feed_ids = {f['id'] for f in FEEDS}
    expected_feed_ids = set(expected_feed_ids)
    coverage = edition['coverage']
    if (set(edition['required_feed_ids']) != expected_feed_ids
            or len(coverage) != len(expected_feed_ids)
            or {row['feed_id'] for row in coverage} != expected_feed_ids
            or any(row['status'] != 'OK' for row in coverage)):
        raise PolicyError('Every configured official source must have a successful coverage check.')
    candidates = edition['candidates']
    by_id = {row['id']: row for row in candidates}
    if len(by_id) != len(candidates) or not by_id:
        raise PolicyError('No complete unique candidate set to compare.')
    reviews = selection['assessments']
    if len(reviews) != len(by_id) or {r['candidate_id'] for r in reviews} != set(by_id):
        raise PolicyError('All hourly candidates need exactly one country-specific assessment.')
    ranking = []
    for review in reviews:
        row = by_id[review['candidate_id']]
        stamp = instant(row['published_at'])
        body = row.get('source_text_snapshot', '')
        body_hash = hashlib.sha256(body.encode('utf-8')).hexdigest()
        if (not start <= stamp < end or row.get('body_fetch_status') != 'FETCHED_FOR_REVIEW'
                or row.get('source_text_truncated') is not False or not body.strip()
                or row.get('source_text_sha256') != body_hash
                or review.get('body_sha256') != body_hash):
            raise PolicyError('Candidate outside hourly window or original body not fully captured/reviewed.')
        excerpt = review.get('support_excerpt', '')
        if (not isinstance(excerpt, str) or not excerpt.strip()
                or ' '.join(excerpt.split()) not in ' '.join(body.split())
                or not isinstance(review.get('reviewed_by'), str) or not review['reviewed_by'].strip()
                or not isinstance(review.get('rationale'), str) or not review['rationale'].strip()
                or type(review.get('relevant')) is not bool):
            raise PolicyError('Impact judgement requires a reviewer, rationale and locatable original evidence.')
        scores = review['scores']
        if set(scores) != set(WEIGHTS) or any(type(v) is not int or not 0 <= v <= 5 for v in scores.values()):
            raise PolicyError('Impact dimensions must be reviewed integers from zero to five.')
        if not review['relevant']:
            if any(scores.values()):
                raise PolicyError('Irrelevant candidate must have zero impact scores.')
            continue
        weighted = sum(scores[k] * WEIGHTS[k] for k in WEIGHTS) / 5
        ranking.append((weighted, stamp, row['id']))
    ranking.sort(reverse=True)
    if not ranking or ranking[0][0] < MIN_SCORE:
        raise PolicyError('No sufficiently important new event; stay silent.')
    winner_score, _, winner_id = ranking[0]
    if selection.get('selected_candidate_id') != winner_id:
        raise PolicyError('Selected story is not the highest reviewed impact in this country/hour.')
    if by_id[winner_id]['article_url'] != media['article_url']:
        raise PolicyError('Photo/article source is not the ranked winning story.')
    return {'target_country': country, 'winner_id': winner_id, 'winner_score': winner_score,
            'slot_key': country + '-' + end.strftime('%Y%m%dT%H'),
            'edition_path': path, 'edition_sha256': digest(edition),
            'window_start': start.isoformat(), 'window_end': end.isoformat(),
            'ranked_candidate_count': len(candidates),
            'ranking': [{'candidate_id': ident, 'score': score} for score, _, ident in ranking]}
