import io
import json
import os
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from pydantic import ValidationError

import app.main as main
from app.generation.config import GenerationError, OpenRouterConfig
from app.generation.llm import answer
from app.generation.openrouter import free_models


def response(payload):
    return io.BytesIO(json.dumps(payload).encode())


class OpenRouterTests(unittest.TestCase):
    def test_free_router_uses_key_json_mode_and_returns_actual_model(self):
        passages = [{'page': 35, 'text': 'Revenue was 245,122 million.'}]
        content = json.dumps({'answer': 'Revenue was 245,122 million.', 'citations': [1]})
        raw = {'model': 'example/answer:free', 'choices': [{'message': {'content': content}}]}
        config = OpenRouterConfig(api_key='test-key')
        with patch('urllib.request.urlopen', return_value=response(raw)) as transport:
            result = answer('Revenue?', passages, config)
        request = transport.call_args.args[0]
        self.assertEqual(request.full_url, 'https://openrouter.ai/api/v1/chat/completions')
        self.assertEqual(request.get_header('Authorization'), 'Bearer test-key')
        body = json.loads(request.data)
        self.assertEqual(body['model'], 'openrouter/free')
        self.assertEqual(body['response_format'], {'type': 'json_object'})
        self.assertEqual(result.model, 'example/answer:free')
        self.assertEqual(result.citations, passages)
        self.assertNotIn('test-key', repr(config))

    def test_server_key_is_used_when_request_key_is_empty(self):
        from app.generation.openrouter import api_key
        with patch.dict(os.environ, {'OPENROUTER_API_KEY': 'server-test-key'}):
            self.assertEqual(api_key(OpenRouterConfig(api_key='')), 'server-test-key')
            self.assertEqual(api_key(OpenRouterConfig(api_key='request-test-key')), 'request-test-key')

    def test_paid_models_are_rejected(self):
        for model in ['openrouter/auto', 'vendor/paid-model', 'vendor/model:free:online']:
            with self.subTest(model=model), self.assertRaises(ValidationError):
                OpenRouterConfig(model=model)

    def test_catalog_only_includes_free_models_supporting_json(self):
        models = [
            {'id': 'vendor/paid', 'name': 'Paid', 'supported_parameters': ['response_format']},
            {'id': 'vendor/plain:free', 'name': 'Plain', 'supported_parameters': []},
            {'id': 'vendor/json:free', 'name': 'JSON', 'supported_parameters': ['response_format']},
        ]
        with patch('urllib.request.urlopen', return_value=response({'data': models})):
            self.assertEqual([model['id'] for model in free_models()], ['openrouter/free', 'vendor/json:free'])

    def test_rate_limit_error_is_actionable_and_does_not_echo_provider_body(self):
        error = urllib.error.HTTPError('https://openrouter.ai', 429, 'Limit', {}, io.BytesIO(b'secret provider data'))
        with patch('urllib.request.urlopen', side_effect=error):
            with self.assertRaises(GenerationError) as raised:
                answer('Revenue?', [{'page': 1, 'text': 'Evidence'}], OpenRouterConfig(api_key='test-key'))
        self.assertEqual(raised.exception.status_code, 429)
        self.assertIn('rate limit', str(raised.exception))
        self.assertNotIn('secret', str(raised.exception))

    def test_invalid_provider_and_citation_responses_are_rejected(self):
        for raw in [
            {'model': 'vendor/json:free', 'choices': []},
            {'model': 'vendor/json:free', 'choices': [{'message': {'content': 'not JSON'}}]},
            {'model': 'vendor/json:free', 'choices': [{'message': {'content': '{"answer":"Guess","citations":[99]}'}}]},
            {'error': {'message': 'upstream failure'}},
        ]:
            with self.subTest(raw=raw), patch('urllib.request.urlopen', return_value=response(raw)):
                with self.assertRaises(GenerationError):
                    answer('Revenue?', [{'page': 1, 'text': 'Evidence'}], OpenRouterConfig(api_key='test-key'))


class QuestionProviderApiTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        root = Path(self.directory.name)
        self.database = patch.object(main, 'DATABASE', root / 'test.db')
        self.reports = patch.object(main, 'REPORTS', root / 'reports')
        self.database.start()
        self.addCleanup(self.database.stop)
        self.reports.start()
        self.addCleanup(self.reports.stop)
        self.environment = patch.dict(os.environ, {'OPENROUTER_API_KEY': '', 'GEMINI_API_KEY': ''})
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.client = self.enterContext(TestClient(main.app))
        with main.connect() as db:
            db.execute("INSERT INTO documents VALUES ('report', 'report.pdf', 'Company', 2024, '2026-01-01', 'ready', NULL)")

    def test_api_rejects_paid_models(self):
        result = self.client.post('/questions', json={'question': 'Revenue?', 'document_id': 'report',
            'generation': {'provider': 'openrouter', 'model': 'vendor/paid', 'api_key': 'test-key'}})
        self.assertEqual(result.status_code, 422)

    def test_missing_key_fails_before_retrieval(self):
        result = self.client.post('/questions', json={'question': 'Revenue?', 'document_id': 'report',
            'generation': {'provider': 'openrouter'}})
        self.assertEqual(result.status_code, 400)
        self.assertIn('API key', result.json()['detail'])

    def test_model_endpoint_never_exposes_server_key(self):
        with patch.dict(os.environ, {'OPENROUTER_API_KEY': 'server-test-key'}), patch(
            'app.api.models.free_models', return_value=[{'id': 'openrouter/free', 'name': 'Auto'}]):
            result = self.client.get('/models/openrouter')
        self.assertTrue(result.json()['api_key_configured'])
        self.assertNotIn('server-test-key', result.text)

    def test_question_api_routes_to_openrouter_and_preserves_sources(self):
        passages = [{'document_id': 'report', 'page': 35, 'text': 'Revenue was 245,122 million.',
                     'section': 'Revenue', 'content_type': 'text', 'score': 0.8}]
        raw = {'model': 'vendor/json:free', 'choices': [{'message': {
            'content': json.dumps({'answer': '245,122 million', 'citations': [1]})}}]}
        with patch('app.retrieval.search.search', return_value=passages), patch(
            'urllib.request.urlopen', return_value=response(raw)):
            result = self.client.post('/questions', json={'question': 'Revenue?', 'document_id': 'report',
                'generation': {'provider': 'openrouter', 'api_key': 'test-key'}})
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json()['model'], 'vendor/json:free')
        self.assertEqual(result.json()['citations'], passages)
        self.assertNotIn('test-key', result.text)

    def test_existing_question_request_defaults_to_ollama(self):
        from app.api.questions import QuestionRequest
        self.assertEqual(QuestionRequest(question='Revenue?', document_id='report').generation.provider, 'ollama')

    def test_gemini_missing_key_fails_before_retrieval(self):
        result = self.client.post('/questions', json={'question': 'Revenue?', 'document_id': 'report',
            'generation': {'provider': 'gemini'}})
        self.assertEqual(result.status_code, 400)
        self.assertIn('Gemini API key', result.json()['detail'])

    def test_gemini_model_endpoint_does_not_expose_the_key(self):
        with patch.dict(os.environ, {'GEMINI_API_KEY': 'gemini-server-test-key'}):
            result = self.client.get('/models/gemini')
        self.assertEqual(result.status_code, 200)
        self.assertTrue(result.json()['api_key_configured'])
        self.assertTrue(result.json()['models'])
        self.assertNotIn('gemini-server-test-key', result.text)

    def test_question_api_routes_to_gemini_and_preserves_sources(self):
        from app.generation.config import GEMINI_MODEL
        passages = [{'document_id': 'report', 'page': 35, 'text': 'Revenue was 245,122 million.',
                     'section': 'Revenue', 'content_type': 'text', 'score': 0.8}]
        raw = {'modelVersion': GEMINI_MODEL, 'candidates': [{'finishReason': 'STOP', 'content': {'parts': [
            {'text': '{"answer":"245,122 million","citations":[1]}'}]}}]}
        with patch('app.retrieval.search.search', return_value=passages), patch(
            'urllib.request.urlopen', return_value=response(raw)):
            result = self.client.post('/questions', json={'question': 'Revenue?', 'document_id': 'report',
                'generation': {'provider': 'gemini', 'api_key': 'test-gemini-key'}})
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json()['model'], GEMINI_MODEL)
        self.assertEqual(result.json()['citations'], passages)
        self.assertNotIn('test-gemini-key', result.text)


if __name__ == '__main__':
    unittest.main()
