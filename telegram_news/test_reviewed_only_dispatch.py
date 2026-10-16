"""Automatic drafts must not bypass the existing audited group publisher."""
import unittest

from dual_market import send_photo


class SafeDispatchTests(unittest.TestCase):
    def test_raw_article_photo_sender_is_not_an_alternate_delivery_channel(self):
        with self.assertRaisesRegex(RuntimeError, "REVIEWED_QUEUE_ONLY"):
            send_photo("fake-token", "-1001234567890", b"PNG", "image/png", "draft")

if __name__ == "__main__":
    unittest.main()
