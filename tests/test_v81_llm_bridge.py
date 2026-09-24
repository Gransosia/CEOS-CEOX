import os
import unittest
from unittest.mock import patch

from core import llm_bridge as lb


class LLMBridgeV81Test(unittest.TestCase):
    def test_deprecated_groq_model_is_not_selected(self):
        old = os.environ.get('CEOS_GROQ_MODEL')
        try:
            os.environ['CEOS_GROQ_MODEL'] = 'llama-3.3-70b-versatile'
            with patch.object(lb, '_get_groq_models', return_value=[]):
                c = lb._groq_candidates()
            self.assertNotIn('llama-3.3-70b-versatile', c)
            self.assertIn('openai/gpt-oss-120b', c)
        finally:
            if old is None:
                os.environ.pop('CEOS_GROQ_MODEL', None)
            else:
                os.environ['CEOS_GROQ_MODEL'] = old

    def test_current_preferred_model_is_first(self):
        old = os.environ.get('CEOS_GROQ_MODEL')
        try:
            os.environ['CEOS_GROQ_MODEL'] = 'openai/gpt-oss-20b'
            with patch.object(lb, '_get_groq_models', return_value=[]):
                c = lb._groq_candidates()
            self.assertEqual(c[0], 'openai/gpt-oss-20b')
        finally:
            if old is None:
                os.environ.pop('CEOS_GROQ_MODEL', None)
            else:
                os.environ['CEOS_GROQ_MODEL'] = old

    def test_403_has_model_or_permission_diagnosis(self):
        from urllib.error import HTTPError
        import io
        body = io.BytesIO(b'{"error":{"message":"model not allowed for project"}}')
        e = HTTPError('https://api.groq.com/openai/v1/chat/completions', 403, 'Forbidden', {}, body)
        msg = str(lb._safe_http_error(e))
        self.assertIn('403 prohibido', msg.lower())
        self.assertIn('modelo', msg.lower())


if __name__ == '__main__':
    unittest.main()
