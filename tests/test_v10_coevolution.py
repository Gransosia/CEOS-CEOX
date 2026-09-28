import json
import tempfile
import unittest
from pathlib import Path

from core.co_evolution import CoEvolutionGraph


class CoEvolutionTests(unittest.TestCase):
    def test_seed_contains_user_work_domains_and_thinkers(self):
        with tempfile.TemporaryDirectory() as td:
            g = CoEvolutionGraph(td, user_label="David")
            self.assertGreaterEqual(len(g.nodes), 30)
            self.assertTrue(g.search("Cuentos para Julia y 33 besos", 3))
            self.assertTrue(g.search("Béchamp", 3))
            self.assertTrue(g.search("CRONOS-Espiral-OCa", 3))

    def test_feedback_changes_mastery_and_marks_uncertainty(self):
        with tempfile.TemporaryDirectory() as td:
            g = CoEvolutionGraph(td, user_label="David")
            node = g.search("Astroteología", 1)[0]
            before = node["mastery"]
            g.learn_from_feedback("Astroteología", accepted=True, note="Útil")
            self.assertGreater(g.nodes[node["id"]]["mastery"], before)
            g.learn_from_feedback("Astroteología", accepted=False, note="Revisar")
            self.assertEqual(g.nodes[node["id"]]["stance"], "uncertain")

    def test_next_moves_respects_context(self):
        with tempfile.TemporaryDirectory() as td:
            g = CoEvolutionGraph(td, user_label="David")
            move = g.teacher_next("Béchamp")
            self.assertIn(move["next"]["title"], {"Pierre Jacques Antoine Béchamp", "CRONOS-Espiral-OCa", "Grafo Vivo"})
            research = g.research_next("Béchamp")
            self.assertEqual(research["target"]["title"], "Pierre Jacques Antoine Béchamp")

    def test_autopilot_has_both_sides(self):
        with tempfile.TemporaryDirectory() as td:
            g = CoEvolutionGraph(td, user_label="David")
            auto = g.autopilot("CRONOS")
            self.assertIn("teach_user", auto["cycle"])
            self.assertIn("learn_ceos", auto["cycle"])
            self.assertIn("practice_author", auto["cycle"])
            self.assertIn("research_world", auto["cycle"])

    def test_persistence_and_graph(self):
        with tempfile.TemporaryDirectory() as td:
            g = CoEvolutionGraph(td, user_label="David")
            a = g.add_node("Nodo A", kind="concept")
            b = g.add_node("Nodo B", kind="concept")
            g.connect(a["id"], b["id"], "depende_de")
            snap1 = g.snapshot()
            g2 = CoEvolutionGraph(td, user_label="David")
            snap2 = g2.snapshot()
            self.assertEqual(snap1["nodes"], snap2["nodes"])
            self.assertEqual(snap1["edges"], snap2["edges"])
            graph = g2.graph(a["id"])
            self.assertEqual(len(graph["edges"]), 1)


if __name__ == "__main__":
    unittest.main()
