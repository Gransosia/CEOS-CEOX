import tempfile
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.adaptive import AdaptiveCore


class AdaptiveCoreTest(unittest.TestCase):
    def test_adaptive_profile_and_teaching_cycle(self):
        a = AdaptiveCore(tempfile.mkdtemp(prefix="ceos8-test-"))
        first = a.analyze_turn("Enséñame qué es una espiral adaptativa", history=[], explicit_mode="teach")
        self.assertEqual(first["mode"], "teach")
        self.assertEqual(first["intent"], "teach")

        a.update_after_turn(
            "Enséñame qué es una espiral adaptativa",
            "Una espiral adaptativa permite transformar el sistema conservando lo que funciona.",
            first,
            engine="local",
        )
        move = a.next_teaching_move(first["topic"])
        self.assertIn(move["step"], {"anchor", "connect", "apply", "contrast", "teach_back"})

        second = a.analyze_turn(
            "Creo que significa que un sistema puede volver a una estructura parecida pero con condiciones nuevas.",
            history=[{"role": "user", "content": "Enséñame qué es una espiral adaptativa"}],
            explicit_mode="teach",
        )
        a.update_after_turn(
            "Creo que significa que un sistema puede volver a una estructura parecida pero con condiciones nuevas.",
            "Exacto; ahora prueba un caso distinto.",
            second,
            engine="local",
        )
        prof = a.profile_snapshot()
        self.assertGreaterEqual(prof["turns"], 2)
        self.assertTrue(prof["current"]["topic"])
        self.assertTrue(Path(a.file).exists())

    def test_feedback_changes_profile(self):
        a = AdaptiveCore(tempfile.mkdtemp(prefix="ceos8-test-"))
        before = a.profile_snapshot()["profile"]["structure"]
        a.feedback("correction", "La explicación debía ser más directa.")
        after = a.profile_snapshot()["profile"]["structure"]
        self.assertGreater(after, before)


if __name__ == "__main__":
    unittest.main()
