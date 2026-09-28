import io
import os
import time
import unittest
from urllib.error import HTTPError
from unittest.mock import patch

from core import llm_bridge as lb


class V83HardeningTest(unittest.TestCase):
    def setUp(self):
        with lb._LOCK:
            for p in lb._CACHE:
                lb._CACHE[p] = {"ts": 0.0, "models": []}
                lb._DISCOVERY[p] = {"ts": 0.0, "ok": False, "error": "", "status": None}
            lb._PROVIDER_COOLDOWN.clear()
            lb._MODEL_COOLDOWN.clear()
            lb._LAST_PROBE.update(ts=0.0, data=None)

    def test_discovery_403_does_not_fallback_to_stale_models(self):
        err = lb.ProviderError("groq", "blocked", status=403, model="", retriable=False)
        with patch.dict(os.environ, {"GROQ_API_KEY": "x"}, clear=False):
            with patch.object(lb, "_http_json", side_effect=err):
                models = lb._candidate_models("groq", force_refresh=True)
        self.assertEqual(models, [])

    def test_discovery_transient_error_allows_controlled_fallback(self):
        err = lb.ProviderError("groq", "temporarily unavailable", status=503, retriable=True)
        with patch.dict(os.environ, {"GROQ_API_KEY": "x"}, clear=False):
            with patch.object(lb, "_http_json", side_effect=err):
                models = lb._candidate_models("groq", force_refresh=True)
        self.assertIn("openai/gpt-oss-120b", models)
        self.assertLessEqual(len(models), lb.MODEL_LIMIT)

    def test_openai_responses_text_extraction(self):
        data = {
            "output": [{
                "type": "message",
                "content": [
                    {"type": "output_text", "text": "Hola"},
                    {"type": "output_text", "text": " mundo"},
                ],
            }]
        }
        self.assertEqual(lb._extract_openai_response_text(data), "Hola mundo")

    def test_gemini_interactions_text_extraction(self):
        data = {"steps": [{"type": "model_output", "content": [{"type": "text", "text": "Hola"}, {"type": "text", "text": " CEOS"}]}]}
        self.assertEqual(lb._extract_gemini_interaction_text(data), "Hola CEOS")

    def test_gemini_key_never_goes_in_url(self):
        captured = {}
        def fake_http(provider, method, url, **kwargs):
            captured["url"] = url
            captured["headers"] = kwargs.get("headers") or {}
            return {"steps": [{"type": "model_output", "content": [{"type": "text", "text": "OK"}]}]}
        with patch.dict(os.environ, {"GEMINI_API_KEY": "secret-gemini"}, clear=False):
            with patch.object(lb, "_candidate_models", return_value=["gemini-3.8-flash"]):
                with patch.object(lb, "_http_json", side_effect=fake_http):
                    text, model, _ = lb._call_gemini([
                        {"role": "system", "content": "test"},
                        {"role": "user", "content": "hola"},
                    ], max_tokens=8)
        self.assertEqual(text, "OK")
        self.assertEqual(model, "gemini-3.8-flash")
        self.assertNotIn("secret-gemini", captured["url"])
        self.assertEqual(captured["headers"].get("x-goog-api-key"), "secret-gemini")

    def test_success_clears_provider_and_model_cooldowns(self):
        with lb._LOCK:
            lb._PROVIDER_COOLDOWN["groq"] = time.time() + 100
            lb._MODEL_COOLDOWN[("groq", "openai/gpt-oss-120b")] = time.time() + 100
        lb._mark_success("groq", "openai/gpt-oss-120b")
        self.assertFalse(lb._cooldown_active("groq"))
        self.assertFalse(lb._model_cooldown_active("groq", "openai/gpt-oss-120b"))

    def test_safe_http_error_redacts_secret_from_file(self):
        body = io.BytesIO(b'{"error":{"message":"bearer super-secret-value"}}')
        err = HTTPError("https://example.com", 403, "Forbidden", {}, body)
        with patch.object(lb, "_load_keys_file", return_value={"GROQ_API_KEY": "super-secret-value"}):
            msg = str(lb._safe_http_error(err))
        self.assertNotIn("super-secret-value", msg)
        self.assertIn("403 prohibido", msg.lower())

    def test_probe_cached_does_not_call_network(self):
        with patch.object(lb, "urlopen", side_effect=AssertionError("network called")):
            r = lb.probe_cached()
        self.assertFalse(r["known"])


    def test_available_without_refresh_never_calls_network(self):
        with patch.dict(os.environ, {"GROQ_API_KEY": "x"}, clear=False):
            with patch.object(lb, "_get_groq_models", side_effect=AssertionError("network called")):
                data = lb.available(refresh=False)
        self.assertTrue(data["available"])
        self.assertFalse(data["ready"])

    def test_chat_completion_falls_back_to_next_provider(self):
        with patch.dict(os.environ, {"GROQ_API_KEY": "x", "GEMINI_API_KEY": "y"}, clear=False):
            with patch.object(lb, "_provider_call", side_effect=[
                lb.ProviderError("groq", "forbidden", status=403, model="openai/gpt-oss-120b"),
                ("Hola", "gemini-3.8-flash", 12),
            ]) as calls:
                result = lb.chat_completion([{"role": "user", "content": "hola"}], max_tokens=10)
        self.assertTrue(result["ok"])
        self.assertEqual(result["provider"], "gemini")
        self.assertEqual(result["model"], "gemini-3.8-flash")
        self.assertEqual(calls.call_count, 2)

    def test_messages_body_skips_temperature_for_reasoning_models(self):
        b = lb._messages_body("openai/gpt-oss-120b", [{"role": "user", "content": "x"}], 10)
        self.assertNotIn("temperature", b)


if __name__ == "__main__":
    unittest.main()
