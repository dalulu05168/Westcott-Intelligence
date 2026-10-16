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

    def test_credentials_report_never_exposes_values(self):
        report = market.credential_status({'TWELVE_DATA_API_KEY': 'do-not-persist-this-secret'})
        self.assertNotIn('do-not-persist-this-secret', str(report))
        self.assertTrue(report['TWELVE_DATA_API_KEY']['configured'])
        self.assertFalse(report['TWELVE_DATA_API_KEY']['coverage_verified'])


if __name__ == '__main__':
    unittest.main()
