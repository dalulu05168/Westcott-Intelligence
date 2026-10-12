import copy
import unittest
from news_release_gate import evaluate


def valid():
    return {'executed_at': '2026-10-13T01:20:00+03:00',
            'sources': {'bvb': {'url': 'https://bvb.ro/example', 'access_status': 'BODY_READ',
                               'source_type': 'official', 'origin_id': 'BVB',
                               'published_at': '2026-10-12T17:50:02+03:00',
                               'retrieved_at': '2026-10-13T01:19:00+03:00'}},
            'claims': [{'id': 'BET', 'text': '测试数据：BET为33,253.02点。', 'kind': 'fact',
                        'review_status': 'CONFIRMED', 'reviewed_by': 'test-fixture', 'is_numeric': True,
                        'evidence': [{'source_id': 'bvb', 'excerpt': '33.253,02', 'locator': 'index-header',
                                      'supports_exact_claim': True}],
                        'numbers': [{'instrument': 'BET', 'quantity_type': 'index_level', 'unit': 'index_points', 'basis': 'index_level',
                                     'market_state': 'last_observation', 'as_of': '2026-10-12T17:50:02+03:00',
                                     'value': '33253.02', 'source_value': '33253.02', 'source_id': 'bvb',
                                     'normalization_reviewed': True}]}], 'publish_claim_ids': ['BET']}


class GateTest(unittest.TestCase):
    def test_single_official_fact_allowed(self):
        self.assertEqual(evaluate(valid())['status'], 'PASS')

    def rejected(self, mutate):
        data = valid()
        mutate(data)
        self.assertEqual(evaluate(data)['status'], 'BLOCK')

    def test_no_source(self):
        self.rejected(lambda d: d['claims'][0].update(evidence=[]))

    def test_indexed_only_not_body(self):
        self.rejected(lambda d: d['sources']['bvb'].update(access_status='SEARCH_SNIPPET_ONLY'))

    def test_conflict(self):
        self.rejected(lambda d: d['claims'][0].update(unresolved_conflict=True))

    def test_future_quote(self):
        self.rejected(lambda d: d['claims'][0]['numbers'][0].update(as_of='2026-10-13T02:00:00+03:00'))

    def test_missing_timezone(self):
        self.rejected(lambda d: d['claims'][0]['numbers'][0].update(as_of='2026-10-12T17:50:02'))

    def test_number_mismatch(self):
        self.rejected(lambda d: d['claims'][0]['numbers'][0].update(value='33353.02'))

    def test_number_missing_basis(self):
        self.rejected(lambda d: d['claims'][0]['numbers'][0].update(basis=''))

    def test_source_after_execution(self):
        self.rejected(lambda d: d['sources']['bvb'].update(retrieved_at='2026-10-13T01:30:00+03:00'))

    def test_missing_source_time(self):
        self.rejected(lambda d: d['sources']['bvb'].update(published_at=None))

    def test_price_requires_currency(self):
        self.rejected(lambda d: d['claims'][0]['numbers'][0].update(quantity_type='price'))

    def test_future_requires_contract(self):
        self.rejected(lambda d: d['claims'][0]['numbers'][0].update(instrument_type='future'))

    def test_source_not_locatable(self):
        self.rejected(lambda d: d['claims'][0]['evidence'][0].update(locator=''))

    def test_unreviewed_fact(self):
        self.rejected(lambda d: d['claims'][0].update(review_status='PENDING'))

    def test_one_source_causality(self):
        self.rejected(lambda d: d['claims'][0].update(kind='causal'))

    def test_reposts_do_not_count_as_independent(self):
        data = valid()
        data['claims'][0]['kind'] = 'causal'
        data['sources']['reprint'] = copy.deepcopy(data['sources']['bvb'])
        data['sources']['reprint']['url'] = 'https://example.org/reprint'
        ref = copy.deepcopy(data['claims'][0]['evidence'][0])
        ref['source_id'] = 'reprint'
        data['claims'][0]['evidence'].append(ref)
        self.assertEqual(evaluate(data)['status'], 'BLOCK')

    def test_two_independent_reviewed_sources(self):
        data = valid()
        data['claims'][0]['kind'] = 'causal'
        data['sources']['independent'] = copy.deepcopy(data['sources']['bvb'])
        data['sources']['independent'].update(url='https://example.org/original', origin_id='independent-original')
        ref = copy.deepcopy(data['claims'][0]['evidence'][0])
        ref['source_id'] = 'independent'
        data['claims'][0]['evidence'].append(ref)
        self.assertEqual(evaluate(data)['status'], 'PASS')

    def test_unknown_published_fact(self):
        self.rejected(lambda d: d.update(publish_claim_ids=['not-in-ledger']))

    def test_omit_bad_candidate_keep_verified_fact(self):
        data = valid()
        bad = copy.deepcopy(data['claims'][0])
        bad.update(id='airport-date', text='待核实关闭期限', review_status='PENDING')
        data['claims'].append(bad)
        result = evaluate(data)
        self.assertEqual(result['status'], 'PASS')
        self.assertEqual(result['approved_facts'], ['测试数据：BET为33,253.02点。'])
        self.assertEqual(result['claims'][1]['status'], 'HOLD')

    def test_no_publishable_facts(self):
        data = valid()
        data['publish_claim_ids'] = []
        self.assertEqual(evaluate(data)['status'], 'NO_PUBLISHABLE_FACTS')

    def test_percent_baseline(self):
        data = valid()
        data['claims'][0]['numbers'][0].update(value='10.00', source_value='10.00', unit='percent',
                                              percent_inputs={'current': '110', 'previous': '100'})
        self.assertEqual(evaluate(data)['status'], 'PASS')
        data['claims'][0]['numbers'][0]['percent_inputs']['previous'] = '90'
        self.assertEqual(evaluate(data)['status'], 'BLOCK')

    def test_nan_rejected(self):
        self.rejected(lambda d: d['claims'][0]['numbers'][0].update(value='NaN'))

    def test_unconditional_analysis(self):
        self.rejected(lambda d: d['claims'][0].update(kind='analysis', premise_claim_ids=['BET']))


if __name__ == '__main__':
    unittest.main()
