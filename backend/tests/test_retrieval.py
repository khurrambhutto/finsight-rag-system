import unittest
from unittest.mock import patch

import numpy as np
from qdrant_client import QdrantClient

from app.retrieval.search import search


class TestEncoder:
    def get_sentence_embedding_dimension(self):
        return 2

    def encode(self, inputs, **kwargs):
        if isinstance(inputs, str):
            return np.array([1.0, 0.0])
        return np.array([[1.0, 0.0] if 'Cost of revenue:' in text else [0.8, 0.2] for text in inputs])


class RetrievalContextTests(unittest.TestCase):
    def setUp(self):
        store = QdrantClient(':memory:')
        self.addCleanup(store.close)
        self.enterContext(patch('app.retrieval.search.client', return_value=store))
        self.enterContext(patch('app.retrieval.search.embedder', return_value=TestEncoder()))
        self.document = {'id': 'report', 'company': 'Microsoft', 'year': 2024}

    def test_matching_table_keeps_revenue_row_with_years(self):
        table = '| Year ended June 30 | 2024 | 2023 | 2022 |\n|---|---|---|---|\n| Cost of revenue: | | | |\n| Total revenue | 245,122 | 211,915 | 198,270 |'
        chunks = [{'id': 'income', 'page': 48, 'section': 'Income statements', 'content_type': 'table', 'text': table}]
        passages = search(self.document, chunks, 'what was the revenue in 2022')
        self.assertTrue(any('198,270' in passage['text'] and '2022' in passage['text'] for passage in passages))

    def test_overview_includes_the_cover_and_report_title(self):
        chunks = [
            {'id': 'company', 'page': 1, 'section': None, 'content_type': 'text', 'text': 'Microsoft'},
            {'id': 'title', 'page': 1, 'section': 'Annual Report 2024', 'content_type': 'heading', 'text': 'Annual Report 2024'},
            {'id': 'segments', 'page': 20, 'section': 'Operating segments', 'content_type': 'text', 'text': 'Our reportable segments are described below.'},
        ]
        passages = search(self.document, chunks, 'what is the report about')
        self.assertTrue(any('Microsoft' in passage['text'] and 'Annual Report 2024' in passage['text'] and passage['page'] == 1 for passage in passages))

    def test_table_context_keeps_units_from_the_same_page(self):
        chunks = [
            {'id': 'units', 'page': 48, 'section': 'Income statements', 'content_type': 'text', 'text': '(In millions, except per share amounts)'},
            {'id': 'income', 'page': 48, 'section': 'Income statements', 'content_type': 'table',
             'text': '| Year | 2022 |\n|---|---|\n| Total revenue | 198,270 |'},
        ]
        passages = search(self.document, chunks, 'revenue in 2022')
        table = next(passage for passage in passages if passage['content_type'] == 'table')
        self.assertIn('In millions', table['text'])

    def test_text_context_never_borrows_from_another_page(self):
        chunks = [
            {'id': 'before', 'page': 2, 'section': 'Business', 'content_type': 'text', 'text': 'Other-page figure'},
            {'id': 'body', 'page': 3, 'section': 'Business', 'content_type': 'text', 'text': 'Microsoft business overview'},
            {'id': 'after', 'page': 4, 'section': 'Business', 'content_type': 'text', 'text': 'Another-page figure'},
        ]
        passages = search(self.document, chunks, 'business overview')
        passage = next(passage for passage in passages if passage['page'] == 3)
        self.assertNotIn('Other-page', passage['text'])
        self.assertNotIn('Another-page', passage['text'])


if __name__ == '__main__':
    unittest.main()
