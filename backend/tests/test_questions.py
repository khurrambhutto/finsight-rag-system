import io
import json
import unittest
from unittest.mock import patch

from app.generation.llm import answer, INSUFFICIENT


class ModelResponseTests(unittest.TestCase):
    def response(self, result):
        payload = json.dumps({'message': {'content': json.dumps(result)}}).encode()
        return io.BytesIO(payload)

    def test_citation_must_identify_supplied_evidence(self):
        passages = [{'page': 35, 'text': 'Revenue was 245,122 million.'}]
        with patch('urllib.request.urlopen', return_value=self.response({'answer': '245,122 million', 'citations': [1]})):
            result = answer('Revenue?', passages)
        self.assertEqual(result.text, '245,122 million')
        self.assertEqual(result.citations, passages)
        with patch('urllib.request.urlopen', return_value=self.response({'answer': '245,122 million', 'citations': [2]})):
            with self.assertRaises(RuntimeError):
                answer('Revenue?', passages)

    def test_uncited_answer_is_reported_as_a_citation_failure(self):
        with patch('urllib.request.urlopen', return_value=self.response({'answer': 'A guess', 'citations': []})):
            with self.assertRaisesRegex(RuntimeError, 'citation'):
                answer('Revenue?', [{'page': 1, 'text': 'Unrelated'}])

    def test_explicit_insufficient_evidence_response_is_preserved(self):
        with patch('urllib.request.urlopen', return_value=self.response({'answer': INSUFFICIENT, 'citations': []})):
            result = answer('Revenue?', [{'page': 1, 'text': 'Unrelated'}])
        self.assertEqual(result.text, INSUFFICIENT)
        self.assertEqual(result.citations, [])


if __name__ == '__main__':
    unittest.main()
