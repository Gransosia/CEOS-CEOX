import os
import unittest
from unittest.mock import patch

from core import llm_bridge as lb


class V82ResilienceTest(unittest.TestCase):
    def test_groq_uses_visible_current_model_only(self):
        with patch.object(lb, '_get_groq_models', return_value=['openai/gpt-oss-20b', 'whisper-large-v3']):
            with patch.dict(os.environ, {'GROQ_API_KEY': 'x'}, clear=False):
                models = lb._groq_candidates(force_refresh=True)
        self.assertEqual(models[0], 'openai/gpt-oss-20b')
        self.assertNotIn('whisper-large-v3', models)

    def test_chat_falls_back_to_second_model_after_first_403(self):
        calls = []
        def fake_http(provider, method, url, **kwargs):
            calls.append(kwargs.get('model'))
            if kwargs.get('model') == 'openai/gpt-oss-120b':
                raise lb.ProviderError(provider, 'HTTP 403: model blocked', status=403, code='model_permission_blocked_project', model=kwargs.get('model'))
            return {'choices': [{'message': {'content': 'OK'}}]}
        with patch.dict(os.environ, {'GROQ_API_KEY': 'x'}, clear=False):
            with patch.object(lb, '_get_groq_models', return_value=['openai/gpt-oss-120b', 'openai/gpt-oss-20b']):
                with patch.object(lb, '_http_json', side_effect=fake_http):
                    text, model, _ = lb._provider_call('groq', [{'role':'user','content':'hola'}], 10)
        self.assertEqual(text, 'OK')
        self.assertEqual(model, 'openai/gpt-oss-20b')
        self.assertEqual(calls, ['openai/gpt-oss-120b', 'openai/gpt-oss-20b'])

    def test_probe_reports_real_generation(self):
        with patch.dict(os.environ, {'GROQ_API_KEY': 'x'}, clear=False):
            with patch.object(lb, '_provider_models', return_value=['openai/gpt-oss-20b']):
                with patch.object(lb, '_provider_call', return_value=('OK', 'openai/gpt-oss-20b', 31)):
                    r = lb.probe_provider('groq', real_generation=True)
        self.assertTrue(r['ok'])
        self.assertEqual(r['model'], 'openai/gpt-oss-20b')
        self.assertEqual(r['latency_ms'], 31)


if __name__ == '__main__':
    unittest.main()
