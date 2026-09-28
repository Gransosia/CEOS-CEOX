import tempfile
from pathlib import Path
from core.fractal_mind import FractalMind

def test_seed_and_query():
    with tempfile.TemporaryDirectory() as td:
        k = Path(td)/"knowledge"
        k.mkdir(); (k/"seed.md").write_text("Béchamp estudió microzymas y el medio interno; esto es una hipótesis histórica de trabajo.", encoding="utf-8")
        m = FractalMind(str(Path(td)/"mind"), str(k))
        s=m.status()
        assert s["nodes"] > 0
        assert m.query("Béchamp microzymas")

def test_learning_and_consolidation():
    with tempfile.TemporaryDirectory() as td:
        k=Path(td)/"knowledge"; k.mkdir(); (k/"seed.md").write_text("CRONOS trata de sucesión y memoria.",encoding="utf-8")
        m=FractalMind(str(Path(td)/"mind"), str(k))
        r=m.learn("Una corrección importante sobre cronos y memoria",topic="cronos",evidence="E4")
        assert r["ok"]
        c=m.consolidate("cronos")
        assert c["ok"]

def test_seal():
    with tempfile.TemporaryDirectory() as td:
        k=Path(td)/"knowledge"; k.mkdir(); (k/"seed.md").write_text("Astroteología: estudio cultural del cielo.",encoding="utf-8")
        m=FractalMind(str(Path(td)/"mind"), str(k))
        s=m.export_seal(); assert s["ok"] and "checksum" in s["seal"]
