"""A reachable webpage must never be mistaken for a verified quote feed."""
import os
import sys
import unittest
sys.path.insert(0, os.path.dirname(__file__))
import market_readiness as market


class MarketReadinessTests(unittest.TestCase):
    def test_publisher_denial_is_distinct_from_temporary_server_failure(self):
        self.assertEqual(market.assess_response(500, 'text/html', b'Web Page Blocked!')['status'], 'PUBLISHER_ACCESS_DENIED')
        self.assertEqual(market.assess_response(500, 'text/plain', b'Permission denied')['status'], 'PUBLISHER_ACCESS_DENIED')
        self.assertEqual(market.assess_response(500, 'text/plain', b'Permissiondenied')['status'], 'PUBLISHER_ACCESS_DENIED')
        self.assertEqual(market.assess_response(503, 'text/html', b'Service unavailable')['status'], 'HTTP_UNAVAILABLE')

    def test_successful_html_shell_does_not_enable_quote_publication(self):
        result = market.assess_response(200, 'text/html', b'<title>CAC 40</title><div id="awl-detailed-quote-container"></div>')
        self.assertEqual(result['status'], 'NO_VERIFIED_QUOTE')
        self.assertFalse(result['publishable'])

    def test_bet_page_numbers_normalize_but_page_time_is_not_quote_time(self):
        text = 'Starea pietei: DESCHISA Indici BET 34.798,93 306,70 0,89% BET-TR 84.075,14 740,94 0,89% Ultima actualizare: 16.10.2026 12:11:16'
        row = market.extract_bet_reference(text)
        self.assertEqual(row['level'], '34798.93')
        self.assertEqual(row['change_points'], '306.70')
        self.assertEqual(row['change_percent'], '0.89')
        self.assertEqual(row['unit'], 'index_points')
        self.assertEqual(row['page_last_update'], '16.10.2026 12:11:16')
        self.assertIsNone(row['quote_as_of'])
        self.assertFalse(row['publishable'])

    def test_wrong_percent_or_different_index_cannot_be_bet_reference(self):
        for text in ('BET 34.798,93 306,70 9,89% Ultima actualizare: 16.10.2026 12:11:16',
                     'BET-TR 84.075,14 740,94 0,89% Ultima actualizare: 16.10.2026 12:11:16'):
            with self.assertRaises(ValueError):
                market.extract_bet_reference(text)

    def test_rendered_cac40_normalizes_source_time_and_previous_close(self):
        from datetime import datetime, timezone
        text = '# **CAC 40**\nFR0003500008\nPX1\n7,945.11\nLast Level\n16/10/2026 - 11:32 CET\nSince Previous Close\n+10.41(+0.13%)\n| Previous Close | 7,934.70 | [15/10/2026] |\nUpdated\n16/10/2026 11:32 CEST'
        row = market.extract_cac40_reference(text, datetime(2026,10,16,9,33,tzinfo=timezone.utc))
        self.assertEqual(row['level'], '7945.11')
        self.assertEqual(row['previous_close'], '7934.70')
        self.assertEqual(row['source_updated_at'], '2026-10-16T11:32:00+02:00')
        self.assertTrue(row['recent_observation'])
        self.assertFalse(row['publishable'])
        self.assertFalse(market.extract_cac40_reference(text, datetime(2026,10,16,9,36,tzinfo=timezone.utc))['recent_observation'])
        for changed, now in ((text.replace('7,934.70','7,900.00'), datetime(2026,10,16,9,33,tzinfo=timezone.utc)),
                (text.replace('11:32 CEST','11:32 CET'), datetime(2026,10,16,9,33,tzinfo=timezone.utc)),
                (text.replace('FR0003500008','WRONG-ISIN'), datetime(2026,10,16,9,33,tzinfo=timezone.utc)),
                (text, datetime(2026,10,16,9,31,tzinfo=timezone.utc))):
            with self.assertRaises(ValueError):
                market.extract_cac40_reference(changed, now)

    def test_encrypted_json_quote_requires_normal_page_rendering(self):
        result = market.assess_response(200, 'application/json', b'{"ct":"ciphertext","iv":"iv","s":"salt"}')
        self.assertEqual(result['status'], 'RENDER_REQUIRED')
        self.assertFalse(result['publishable'])

    def test_credentials_report_never_exposes_values(self):
        report = market.credential_status({'TWELVE_DATA_API_KEY': 'do-not-persist-this-secret'})
        self.assertNotIn('do-not-persist-this-secret', str(report))
        self.assertTrue(report['TWELVE_DATA_API_KEY']['configured'])
        self.assertFalse(report['TWELVE_DATA_API_KEY']['coverage_verified'])


if __name__ == '__main__':
    unittest.main()
