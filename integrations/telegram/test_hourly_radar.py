import os
import sys
import unittest
from datetime import datetime, timezone
sys.path.insert(0, os.path.dirname(__file__))
import hourly_radar as hourly


class HourlyRadarTests(unittest.TestCase):
    def setUp(self):
        self.end = datetime(2026, 10, 16, 9, 37, tzinfo=timezone.utc)
        self.feeds = [{'id': 'test', 'source': 'Official test', 'url': 'https://publisher.example/feed',
                       'article_hosts': ('publisher.example',)}]

    def feed(self, _):
        rows = []
        for i, date in enumerate(('Fri, 16 Oct 2026 09:10:00 GMT', 'Fri, 16 Oct 2026 07:00:00 GMT')):
            rows.append('<item><title>Announcement without scoring keywords</title><link>https://publisher.example/'
                        + str(i) + '</link><pubDate>' + date + '</pubDate></item>')
        return ('<rss><channel>' + ''.join(rows) + '</channel></rss>').encode()

    def inspector(self, row):
        return {**row, 'body_fetch_status': 'FETCHED_FOR_REVIEW', 'source_text_snapshot': 'Official body',
                'source_text_truncated': False}

    def test_all_hourly_candidates_collected_without_keyword_filter(self):
        result = hourly.collect_hour(self.feeds, self.feed, self.inspector, self.end)
        self.assertEqual(result['status'], 'COMPLETE')
        self.assertEqual(len(result['candidates']), 1)
        self.assertEqual(result['candidates'][0]['article_url'], 'https://publisher.example/0')
        self.assertEqual(result['assessments_status'], 'UNREVIEWED')

    def test_missing_feed_cannot_establish_complete_comparison(self):
        def failed(_):
            raise hourly.radar.RadarError('Unavailable')
        result = hourly.collect_hour(self.feeds, failed, self.inspector, self.end)
        self.assertEqual(result['status'], 'INCOMPLETE')

    def test_body_failure_does_not_discard_potential_winner(self):
        result = hourly.collect_hour(self.feeds, self.feed,
            lambda r: {**r, 'body_fetch_status': 'UNAVAILABLE'}, self.end)
        self.assertEqual(len(result['candidates']), 1)
        self.assertEqual(result['candidates'][0]['body_fetch_status'], 'UNAVAILABLE')
        self.assertFalse(result['telegram_publishable'])

    def test_cap_is_reported_not_silently_called_complete(self):
        result = hourly.collect_hour(self.feeds, self.feed, self.inspector, self.end, max_candidates=0)
        self.assertTrue(result['truncated'])
        self.assertEqual(result['status'], 'INCOMPLETE')

    def test_known_old_item_with_missing_title_does_not_corrupt_current_hour(self):
        def fetch(feed):
            return self.feed(feed).replace(b'</channel>',
                b'<item><pubDate>Fri, 16 Oct 2026 06:00:00 GMT</pubDate></item></channel>')
        result = hourly.collect_hour(self.feeds, fetch, self.inspector, self.end)
        self.assertEqual(result['status'], 'COMPLETE')
        self.assertEqual(len(result['candidates']), 1)

    def test_bvb_same_timestamp_pdf_is_not_discarded_without_actual_article_link(self):
        feeds = [{'id': 'bvb_market', 'source': 'Bucharest Stock Exchange',
            'url': 'https://bvb.ro/feed', 'article_hosts': ('bvb.ro',)}]
        page = 'https://bvb.ro/FinancialInstruments/SelectedData/NewsItem/SNG/123'
        linked = 'https://bvb.ro/infocont/report.pdf'
        unrelated = 'https://bvb.ro/infocont/separate-disclosure.pdf'
        def fetch(_):
            return ('<rss><channel>' + ''.join('<item><title>ROMGAZ (SNG)</title><link>' + url
                + '</link><pubDate>Fri, 16 Oct 2026 09:10:00 GMT</pubDate></item>'
                for url in (page, linked, unrelated)) + '</channel></rss>').encode()
        def inspect(row):
            if row['article_url'] == page:
                return {**self.inspector(row), 'linked_document_urls': [linked]}
            return {**row, 'body_fetch_status': 'UNAVAILABLE'}
        result = hourly.collect_hour(feeds, fetch, inspect, self.end)
        self.assertEqual({r['article_url'] for r in result['candidates']}, {page, unrelated})
        self.assertEqual(result['status'], 'INCOMPLETE')


if __name__ == '__main__':
    unittest.main()
