#!/usr/bin/env python3
"""Check a reviewed evidence ledger. Does not fetch sources or prove truth."""
import argparse
import json
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path


def instant(value):
    if not isinstance(value, str):
        raise ValueError('timestamp required')
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        raise ValueError('timezone required')
    return parsed


def valid_shape(ledger):
    """Reject malformed external ledgers before evaluating any candidate."""
    if not isinstance(ledger, dict):
        return False
    sources, claims, publish = (ledger.get('sources', {}), ledger.get('claims', []),
                                ledger.get('publish_claim_ids', []))
    if not isinstance(sources, dict) or not isinstance(claims, list) or not isinstance(publish, list):
        return False
    if not all(isinstance(cid, str) for cid in publish):
        return False
    for sid, source in sources.items():
        if not isinstance(sid, str) or not isinstance(source, dict):
            return False
        if any(not isinstance(source.get(k, ''), str) for k in
               ('url', 'access_status', 'source_type', 'origin_id')):
            return False
    for claim in claims:
        if not isinstance(claim, dict):
            return False
        if any(not isinstance(claim.get(k, ''), str) for k in ('id', 'text', 'kind')):
            return False
        refs, numbers, premises = (claim.get('evidence', []), claim.get('numbers', []),
                                   claim.get('premise_claim_ids', []))
        if not all(isinstance(v, list) for v in (refs, numbers, premises)):
            return False
        if not all(isinstance(v, str) for v in premises):
            return False
        for ref in refs:
            if not isinstance(ref, dict) or any(not isinstance(ref.get(k, ''), str)
                                               for k in ('source_id', 'excerpt', 'locator')):
                return False
        for number in numbers:
            if not isinstance(number, dict) or not isinstance(number.get('source_id', ''), str):
                return False
            if number.get('percent_inputs') is not None and not isinstance(number['percent_inputs'], dict):
                return False
    return True


def evaluate(ledger):
    if not valid_shape(ledger):
        return {'status': 'BLOCK', 'errors': ['INVALID_LEDGER_SHAPE'], 'claims': [],
                'approved_facts': [], 'limitation': 'Malformed ledger; no publication allowed.'}
    errors = []
    try:
        execution = instant(ledger['executed_at'])
    except (KeyError, ValueError, TypeError):
        return {'status': 'BLOCK', 'errors': ['INVALID_EXECUTION_TIME'], 'claims': [],
                'approved_facts': [], 'limitation': 'Evidence attestations require external review.'}
    sources = ledger.get('sources', {})
    results = []
    seen = set()
    for claim in ledger.get('claims', []):
        cid = claim.get('id', '')
        issues = []
        if not cid or cid in seen:
            issues.append('MISSING_OR_DUPLICATE_CLAIM_ID')
        seen.add(cid)
        if not claim.get('text', '').strip():
            issues.append('MISSING_FACT_TEXT')
        if claim.get('kind') not in ('fact', 'causal', 'analysis'):
            issues.append('INVALID_CLAIM_KIND')
        if claim.get('review_status') != 'CONFIRMED' or not claim.get('reviewed_by'):
            issues.append('NOT_REVIEWED')
        if claim.get('unresolved_conflict', False):
            issues.append('UNRESOLVED_CONFLICT')
        families = set()
        refs = claim.get('evidence', [])
        if not refs:
            issues.append('NO_EVIDENCE')
        for evidence in refs:
            source = sources.get(evidence.get('source_id'))
            if not source:
                issues.append('UNKNOWN_SOURCE')
                continue
            if source.get('access_status') != 'BODY_READ':
                issues.append('SOURCE_BODY_NOT_READ')
            if not source.get('url', '').startswith('https://'):
                issues.append('MISSING_SOURCE_URL')
            if not source.get('origin_id') or source.get('source_type') not in ('official', 'reliable_original'):
                issues.append('UNQUALIFIED_SOURCE_OR_ORIGIN')
            try:
                if instant(source['retrieved_at']) > execution:
                    issues.append('SOURCE_RETRIEVED_AFTER_EXECUTION')
                if instant(source['published_at']) > execution:
                    issues.append('SOURCE_PUBLISHED_AFTER_EXECUTION')
            except (KeyError, ValueError, TypeError):
                issues.append('MISSING_SOURCE_TIMES')
            if not evidence.get('excerpt', '').strip() or not evidence.get('locator'):
                issues.append('MISSING_LOCATABLE_EXCERPT')
            if evidence.get('supports_exact_claim') is not True:
                issues.append('EXACT_CLAIM_NOT_SUPPORTED')
            families.add(source.get('origin_id'))
        if claim.get('kind') == 'causal' and len(families - {None, ''}) < 2:
            issues.append('CAUSALITY_NEEDS_TWO_INDEPENDENT_ORIGINS')
        if claim.get('kind') == 'analysis':
            if claim.get('conditional') is not True or not claim.get('boundary_text'):
                issues.append('ANALYSIS_MUST_BE_CONDITIONAL')
        if claim.get('is_numeric') and not claim.get('numbers'):
            issues.append('MISSING_NUMERIC_FIELDS')
        for number in claim.get('numbers', []):
            if number.get('quantity_type') not in ('index_level', 'price', 'percent', 'yield', 'count', 'amount'):
                issues.append('MISSING_OR_INVALID_QUANTITY_TYPE')
            if number.get('quantity_type') in ('price', 'amount') and not number.get('currency'):
                issues.append('MISSING_CURRENCY')
            if number.get('instrument_type') == 'future' and not number.get('contract'):
                issues.append('MISSING_FUTURES_CONTRACT')
            for field in ('instrument', 'unit', 'basis', 'market_state', 'as_of', 'value', 'source_value', 'source_id'):
                if number.get(field) in (None, ''):
                    issues.append('MISSING_NUMBER_' + field.upper())
            if number.get('source_id') not in {e.get('source_id') for e in refs}:
                issues.append('NUMBER_SOURCE_NOT_IN_CLAIM_EVIDENCE')
            if number.get('normalization_reviewed') is not True:
                issues.append('NUMERIC_NORMALIZATION_NOT_REVIEWED')
            try:
                a, b = Decimal(str(number['value'])), Decimal(str(number['source_value']))
                if not a.is_finite() or not b.is_finite() or a != b:
                    issues.append('NUMBER_MISMATCH')
                if instant(number['as_of']) > execution:
                    issues.append('FUTURE_MARKET_DATA')
                number_source = sources.get(number.get('source_id'))
                if number_source and instant(number['as_of']) > instant(number_source['retrieved_at']):
                    issues.append('QUOTE_AFTER_SOURCE_RETRIEVAL')
                calc = number.get('percent_inputs')
                if calc:
                    current, previous = Decimal(str(calc['current'])), Decimal(str(calc['previous']))
                    if previous <= 0 or not current.is_finite() or not previous.is_finite():
                        raise ValueError('invalid percent inputs')
                    expected = ((current / previous - 1) * 100).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                    if a != expected:
                        issues.append('PERCENT_BASELINE_MISMATCH')
            except (KeyError, ValueError, TypeError, InvalidOperation, ZeroDivisionError):
                issues.append('INVALID_NUMBER_OR_TIME')
        results.append({'id': cid, 'status': 'HOLD' if issues else 'PASS',
                        'issues': sorted(set(issues)), 'text': claim.get('text', '')})
    by_id = {r['id']: r for r in results}
    claims_by_id = {c['id']: c for c in ledger.get('claims', [])}
    memo = {}
    def supported(cid, visiting):
        if cid in visiting or cid not in by_id or by_id[cid]['status'] != 'PASS':
            return False
        if cid in memo:
            return memo[cid]
        claim = claims_by_id[cid]
        if claim.get('kind') != 'analysis':
            memo[cid] = True
        else:
            dependencies = claim.get('premise_claim_ids', [])
            memo[cid] = bool(dependencies) and all(supported(d, visiting | {cid}) for d in dependencies)
        return memo[cid]
    # Resolve the full premise graph before approving publication, independent of input order.
    support = {cid: supported(cid, set()) for cid in by_id}
    for claim in ledger.get('claims', []):
        if claim.get('kind') == 'analysis' and not support.get(claim['id']):
            by_id[claim['id']]['status'] = 'HOLD'
            by_id[claim['id']]['issues'].append('UNVERIFIED_ANALYSIS_PREMISE')
    publish_ids = ledger.get('publish_claim_ids', [])
    if len(set(publish_ids)) != len(publish_ids):
        errors.append('DUPLICATE_PUBLISHED_CLAIM')
    for cid in publish_ids:
        if cid not in by_id or by_id[cid]['status'] != 'PASS':
            errors.append('UNAPPROVED_PUBLISHED_CLAIM:' + cid)
    # No free-form publication text is accepted: render only reviewed claim text.
    status = 'BLOCK' if errors else ('PASS' if publish_ids else 'NO_PUBLISHABLE_FACTS')
    approved = [by_id[c]['text'] for c in publish_ids] if status == 'PASS' else []
    return {'status': status, 'errors': errors, 'claims': results, 'approved_facts': approved,
            'limitation': 'Checks ledger consistency, not source authenticity, semantic truth, source independence, or completeness. External review is required; this script is not connected to ChatGPT Scheduled.'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('ledger')
    parser.add_argument('--output')
    args = parser.parse_args()
    result = evaluate(json.loads(Path(args.ledger).read_text(encoding='utf-8')))
    encoded = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(encoded + '\n', encoding='utf-8')
    print(encoded)
    return 0 if result['status'] == 'PASS' else 2


if __name__ == '__main__':
    raise SystemExit(main())
