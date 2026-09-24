import tempfile
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.agency import AgencyCore


class AgencyLifecycleTest(unittest.TestCase):
    def test_agency_lifecycle(self):
        a = AgencyCore(tempfile.mkdtemp(prefix="ceos7-test-"))
        goal = a.add_goal("Construir una inteligencia dinámica")
        self.assertEqual(goal["status"], "active")

        r = a.tick({
            "open_threads": [{"id": "t1", "status": "open", "text": "continuar experimento", "weight": 1.0}],
            "relationship": {"corrections": 1},
        })
        self.assertEqual(r["cycle"], 1)
        self.assertTrue(a.initiatives("proposed"))

        exp = a.create_experiment(
            "Predicción T0",
            {"state": "S0"},
            [{"transition": "S0->S1"}],
            ["la transición no ocurre"],
        )
        self.assertEqual(exp["status"], "open")
        self.assertTrue(exp["frozen_at"])
        resolved = a.resolve_experiment(exp["id"], {"state": "S1"}, "none")
        self.assertEqual(resolved["status"], "resolved")

        gap = a.add_model_gap(
            "No representa bifurcaciones",
            "caso X",
            component="transition",
            severity=.9,
        )
        self.assertEqual(gap["status"], "open")

        proposal = a.create_evolution_proposal(
            "Mejorar el detector de bifurcaciones",
            "core/agency.py",
            "Añadir una métrica de transición",
        )
        self.assertEqual(proposal["status"], "proposed")
        self.assertTrue((Path(a.base) / "evolution_proposals" / f"{proposal['id']}.json").exists())


if __name__ == "__main__":
    unittest.main()
