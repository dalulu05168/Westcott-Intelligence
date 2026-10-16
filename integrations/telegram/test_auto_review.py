import hashlib
import unittest
from datetime import datetime, timezone
from unittest.mock import patch
import auto_review as ar

class ReviewTests(unittest.TestCase):
    def test_wrong_numeric_value_and_empty_excerpt_block(self):
        number = dict(quantity_type='index_level', instrument='BET', unit='points', basis='close', market_state='official release', as_of='2026-10-15T15:00:00Z', value='99999', source_value='99999', source_number='18250', source_scale='1')
        for literal in ('', '18,250 points'):
            with self.subTest(literal=literal), self.assertRaises(ValueError):
                ar.check_numbers([dict(number, source_literal=literal)], 'BET at 18,250 points', datetime(2026,10,15,16,tzinfo=timezone.utc))
        number.update(value='18250', source_value='18250', source_literal='18,250 points')
        ar.check_numbers([number], 'BET at 18,250 points', datetime(2026,10,15,16,tzinfo=timezone.utc))

    def test_other_country_source_is_actually_assessed(self):
        body='Official source event body'
        row=dict(id='test',feed_id='bvb_market',title='Event',source_text_snapshot=body,source_text_sha256=hashlib.sha256(body.encode()).hexdigest(),article_url='https://example.com/news')
        calls=[]
        def model(prompt):
            calls.append(prompt)
            return dict(relevant=False, scores={k:0 for k in ar.WEIGHTS},support_excerpt=body,rationale='No evidenced French exposure')
        with patch('source_media.inspect_article',return_value={'source_text':body}):
            result=ar.assess_all({'candidates':[row]},'FR',model)
        with patch('source_media.inspect_article',return_value={'source_text':'changed'}), self.assertRaises(RuntimeError):
            ar.assess_all({'candidates':[row]},'FR',model)
        self.assertEqual(len(calls),1)
        self.assertTrue(result[0]['reviewed_by'].startswith('auto-llm:'))

    def test_snapshot_timestamp_beats_file_mtime_and_stale_is_rejected(self):
        import json, tempfile
        from pathlib import Path
        from datetime import timedelta
        from news_radar import FEEDS
        now=datetime(2026,10,16,14,0,tzinfo=timezone.utc)
        def edition(end):
            return dict(window_start=(end-timedelta(hours=1)).isoformat(),window_end=end.isoformat(),status='COMPLETE',truncated=False,required_feed_ids=[f['id'] for f in FEEDS],coverage=[dict(feed_id=f['id'],status='OK') for f in FEEDS],candidates=[])
        with tempfile.TemporaryDirectory() as d, patch.object(ar,'ROOT',Path(d)):
            folder=Path(d)/'news/editions';folder.mkdir(parents=True)
            (folder/'new.json').write_text(json.dumps(edition(now-timedelta(minutes=5))))
            (folder/'old.json').write_text(json.dumps(edition(now-timedelta(hours=2))))
            self.assertEqual(ar.latest_edition(now)[0],'news/editions/new.json')
            with self.assertRaises(RuntimeError): ar.latest_edition(now+timedelta(hours=1))

    def test_self_confirmation_and_automatic_release_disabled(self):
        with self.assertRaises(RuntimeError): ar.attest({},'robot')
        with self.assertRaises(RuntimeError): ar.promote('draft','robot')
        with patch.object(ar,'MODE','approved'), self.assertRaises(RuntimeError): ar.main()

if __name__ == '__main__': unittest.main()
