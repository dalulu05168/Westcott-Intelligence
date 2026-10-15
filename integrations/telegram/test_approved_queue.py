import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, os.path.dirname(__file__))
import approved_queue as queue
import test_reviewed_publish as fixtures
import reviewed_publish as pub


class ApprovedQueueTests(unittest.TestCase):
    def test_delivered_identical_ledger_stays_skipped_after_freshness_expires(self):
        from datetime import datetime, timezone, timedelta
        import hashlib
        with tempfile.TemporaryDirectory() as directory, patch.object(pub, 'publish') as send:
            root = Path(directory)
            ledger = fixtures.OriginalArticleTests().ledger()
            ledger['executed_at'] = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()
            relative = 'news/approved/test.json'
            path = root / relative
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps(ledger))
            digest = hashlib.sha256(json.dumps(ledger, ensure_ascii=False, sort_keys=True).encode('utf-8')).hexdigest()
            audit=root/'audit/telegram-delivery/previous.json'
            audit.parent.mkdir(parents=True)
            audit.write_text(json.dumps({'ledger': relative, 'ledger_digest': digest, 'state': 'DELIVERED'}))
            self.assertEqual(queue.drain(root, {})[0]['status'], 'ALREADY_RESERVED')
            send.assert_not_called()

    def test_empty_queue_is_silent(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(pub, 'publish') as send:
            self.assertEqual(queue.drain(Path(directory), {}), [])
            send.assert_not_called()

    def test_unreviewed_ledger_never_reaches_sender(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(pub, 'publish') as send:
            root=Path(directory)
            (root/'news/approved').mkdir(parents=True)
            ledger=fixtures.OriginalArticleTests().ledger()
            ledger['claims'][0]['review_status']='UNREVIEWED'
            (root/'news/approved/test.json').write_text(json.dumps(ledger))
            result=queue.drain(root, {})
            self.assertEqual(result[0]['status'], 'HELD')
            send.assert_not_called()

    def test_pending_or_delivered_audit_blocks_automatic_retry(self):
        for state in ('PENDING_DO_NOT_RETRY', 'DELIVERED'):
            with self.subTest(state=state), tempfile.TemporaryDirectory() as directory, patch.object(pub, 'publish') as send:
                root=Path(directory)
                (root/'news/approved').mkdir(parents=True)
                ledger=fixtures.OriginalArticleTests().ledger()
                prepared=pub.prepare(ledger, 'news/approved/test.json')
                (root/'news/approved/test.json').write_text(json.dumps(ledger))
                audit=root/'audit/telegram-delivery'/str(prepared['fingerprint'][:40]+'.json')
                audit.parent.mkdir(parents=True)
                audit.write_text(json.dumps({'state':state}))
                self.assertEqual(queue.drain(root, {})[0]['status'], 'ALREADY_RESERVED')
                send.assert_not_called()


if __name__ == '__main__':
    unittest.main()
