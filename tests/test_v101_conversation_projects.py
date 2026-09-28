import tempfile
import unittest
from pathlib import Path

from core.co_evolution import CoEvolutionGraph
from core.chat import ConversationalEngine


class TestV101ConversationAndProjects(unittest.TestCase):
    def test_invention_projects_are_in_graph(self):
        with tempfile.TemporaryDirectory() as td:
            g = CoEvolutionGraph(td, user_label="David")
            self.assertTrue(g.search("FORMA 333 Olla lenta", 5))
            self.assertTrue(g.search("SAD Tubería", 5))
            self.assertTrue(g.search("AND-001", 5))
            p = g.work_profile("SAD / Tubería")
            self.assertTrue(p["ok"])
            labels = {x["node"]["label"] for x in p["neighbors"]}
            self.assertIn("AND-001", labels)

    def test_casual_turn_does_not_create_word_nodes(self):
        with tempfile.TemporaryDirectory() as td:
            g = CoEvolutionGraph(td, user_label="David")
            before = len(g.nodes)
            r = g.record_casual_turn("Buenos días", "Buenos días, David. Aquí estoy.")
            self.assertTrue(r["ok"])
            self.assertEqual(len(g.nodes), before)
            self.assertGreaterEqual(r["casual_turns"], 1)

    def test_conversational_detector_handles_banalities(self):
        obj = object.__new__(ConversationalEngine)
        self.assertTrue(obj._is_casual_turn("Buenos días", []))
        self.assertTrue(obj._is_casual_turn("¿Qué tal?", []))
        self.assertTrue(obj._is_casual_turn("Gracias", []))
        self.assertFalse(obj._is_casual_turn("Analiza CRONOS-Espiral-OCa aplicado a SAD", []))


if __name__ == "__main__":
    unittest.main()
