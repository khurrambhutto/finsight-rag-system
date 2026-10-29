import io
import json
import os
import unittest
import urllib.error
from unittest.mock import patch

from pydantic import ValidationError

from app.generation.config import GEMINI_MODEL, GeminiConfig, GenerationError
from app.generation.gemini import api_key
from app.generation.llm import answer


def response(payload):
    return io.BytesIO(json.dumps(payload).encode())


def completion(parts, finish='STOP'):
    return {'modelVersion': GEMINI_MODEL, 'candidates': [{'finishReason': finish, 'content': {'parts': parts}}]}


class GeminiTests(unittest.TestCase):
    def test_native_request_uses_header_key_and_structured_answer(self):
        passages = [{'page': 35, 'text': 'Revenue was 245,122 million.'}]
        raw = completion([{'text': '{"answer":"245,122 million","citations":[1]}'}])
        config = GeminiConfig(api_key='test-gemini-key')
        with patch('urllib.request.urlopen', return_value=response(raw)) as transport:
            result = answer('Revenue?', passages, config)
        request = transport.call_args.args[0]
        self.assertEqual(request.full_url, f'https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent')
        self.assertEqual(request.get_header('X-goog-api-key'), 'test-gemini-key')
        self.assertNotIn('test-gemini-key', request.full_url)
        self.assertNotIn('test-gemini-key', repr(config))
        body = json.loads(request.data)
        self.assertEqual(body['generationConfig']['responseFormat']['text']['mimeType'], 'APPLICATION_JSON')
        self.assertIn('Revenue?', body['contents'][0]['parts'][0]['text'])
        self.assertEqual(result.text, '245,122 million')
        self.assertEqual(result.citations, passages)
        self.assertEqual(result.model, GEMINI_MODEL)

    def test_request_key_overrides_server_key_and_missing_key_is_actionable(self):
        with patch.dict(os.environ, {'GEMINI_API_KEY': 'server-test-key'}):
            self.assertEqual(api_key(GeminiConfig()), 'server-test-key')
            self.assertEqual(api_key(GeminiConfig(api_key='request-test-key')), 'request-test-key')
        with patch.dict(os.environ, {'GEMINI_API_KEY': ''}), self.assertRaises(GenerationError) as raised:
            api_key(GeminiConfig())
        self.assertEqual(raised.exception.status_code, 400)

    def test_model_id_cannot_inject_a_url_path_or_query(self):
        for model in ['../models/other', 'gemini-model?key=value', 'gemini-model:other']:
            with self.subTest(model=model), self.assertRaises(ValidationError):
                GeminiConfig(model=model)

    def test_thought_parts_are_excluded_and_answer_parts_are_joined(self):
        raw = completion([{'thought': True, 'text': 'private reasoning'},
                          {'text': '{"answer":"Revenue","citations":'}, {'text': '[1]}'}])
        with patch('urllib.request.urlopen', return_value=response(raw)):
            result = answer('Revenue?', [{'page': 1, 'text': 'Revenue'}], GeminiConfig(api_key='test-key'))
        self.assertEqual(result.text, 'Revenue')

    def test_blocked_truncated_and_malformed_responses_are_rejected(self):
        for raw in [{}, {'candidates': None}, completion([], 'SAFETY'), completion([], 'MAX_TOKENS'),
                    completion([]), completion([{'text': 'not JSON'}]),
                    completion([{'text': '{"answer":"Guess","citations":[99]}'}])]:
            with self.subTest(raw=raw), patch('urllib.request.urlopen', return_value=response(raw)):
                with self.assertRaises(GenerationError):
                    answer('Revenue?', [{'page': 1, 'text': 'Evidence'}], GeminiConfig(api_key='test-key'))

    def test_auth_and_quota_errors_are_sanitized(self):
        for status in [400, 403, 429]:
            error = urllib.error.HTTPError('https://generativelanguage.googleapis.com', status, 'Failure', {},
                                          io.BytesIO(b'sensitive provider content'))
            with self.subTest(status=status), patch('urllib.request.urlopen', side_effect=error):
                with self.assertRaises(GenerationError) as raised:
                    answer('Revenue?', [{'page': 1, 'text': 'Evidence'}], GeminiConfig(api_key='test-key'))
            self.assertNotIn('sensitive', str(raised.exception))
            self.assertEqual(raised.exception.status_code, 429 if status == 429 else 502)


if __name__ == '__main__':
    unittest.main()
