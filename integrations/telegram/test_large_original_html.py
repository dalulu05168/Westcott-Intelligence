"""Bounded original HTML reads must retain late article evidence, never truncate."""
import io
import unittest
from email.message import Message
from unittest.mock import patch
import source_media as media

class Response(io.BytesIO):
    def __init__(self, body):
        super().__init__(body)
        self.headers = Message()
        self.headers['Content-Type'] = 'text/html; charset=utf-8'

class Opener:
    def __init__(self, body): self.body = body
    def open(self, request, timeout): return Response(self.body)

class LargeArticleTests(unittest.TestCase):
    def test_article_after_large_site_wrapper_is_fully_read(self):
        body = b'<html><head><script>' + b' ' * 600000 + b'</script></head><body><article>Official late article evidence.</article></body></html>'
        with patch.object(media, 'public_dns'):
            markup = media.fetch_original_article('https://bvb.ro/example', Opener(body))
        page = media.inspect_markup('https://bvb.ro/example', markup)
        self.assertIn('Official late article evidence.', page['source_text'])

    def test_oversized_document_is_held_not_silently_cut(self):
        with patch.object(media, 'public_dns'), self.assertRaises(media.SourceMediaError):
            media.fetch_original_article('https://bvb.ro/example', Opener(b'x' * (media.MAX_HTML + 1)))

    def test_pdf_text_budget_remains_bounded(self):
        self.assertEqual(media.MAX_PDF_TEXT, 262144)
