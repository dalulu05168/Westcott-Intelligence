"""Real PDF extraction, preserving the separate original-photo requirement."""
import shutil
import unittest
from source_media import pdf_markup, inspect_markup, SourceMediaError


def document(text):
    stream = ('BT /F1 12 Tf 40 700 Td (' + text + ') Tj ET').encode()
    objects = [b'<< /Type /Catalog /Pages 2 0 R >>',
               b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
               b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>',
               b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
               b'<< /Length ' + str(len(stream)).encode() + b' >>\nstream\n' + stream + b'\nendstream']
    result, offsets = b'%PDF-1.4\n', [0]
    for index, body in enumerate(objects, 1):
        offsets.append(len(result))
        result += str(index).encode() + b' 0 obj\n' + body + b'\nendobj\n'
    start = len(result)
    result += b'xref\n0 6\n0000000000 65535 f \n'
    result += b''.join(f'{offset:010d} 00000 n \n'.encode() for offset in offsets[1:])
    return result + b'trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n' + str(start).encode() + b'\n%%EOF'


class OriginalPdfTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('pdftotext'), 'poppler required')
    def test_real_pdf_text_is_reviewable_but_has_no_original_photo(self):
        text = 'Official issuer report confirms a bond listing with a total value of 100 million RON on 16 October 2026.'
        result = inspect_markup('https://bvb.ro/report.pdf', pdf_markup(document(text)))
        self.assertEqual(result['source_text'], text)
        self.assertIsNone(result['image_candidate_url'])
        self.assertEqual(result['article_image_candidates'], [])
        self.assertFalse(result['verified_for_reuse'])

    def test_non_pdf_cannot_be_passed_as_original(self):
        with self.assertRaises(SourceMediaError):
            pdf_markup(b'not a PDF')

    @unittest.skipUnless(shutil.which('pdftotext'), 'poppler required')
    def test_unreadable_empty_document_is_held(self):
        with self.assertRaises(SourceMediaError):
            pdf_markup(document(''))
