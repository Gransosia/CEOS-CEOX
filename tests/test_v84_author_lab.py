import tempfile
import unittest
from pathlib import Path

from core.ingest import DocumentLibrary
from core.author_lab import AuthorLab


class TestAuthorLab(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.lib = DocumentLibrary(str(Path(self.tmp.name) / "library"))
        self.lib.ingest_text(
            "Julia entra en un jardín imposible. Encuentra un espejo, pierde el miedo y vuelve transformada.",
            title="Cuentos para Julia y 33 besos",
            author="David de la Fuente Alonso",
        )
        self.lib.ingest_text(
            "Dos amigas hablan con humor sobre un musical. Una ha perdido a su pareja; la otra la empuja a crear.",
            title="Pruebas de amor furtivo",
            author="David de la Fuente Alonso",
        )
        self.lab = AuthorLab(self.lib, str(Path(self.tmp.name) / "author_lab"))

    def tearDown(self):
        self.tmp.cleanup()

    def test_local_analysis(self):
        r = self.lab.analyze(author="David de la Fuente Alonso", use_llm=False)
        self.assertTrue(r["ok"])
        self.assertGreaterEqual(len(r["documents"]), 2)
        self.assertIn("strengths", r)
        self.assertIn("risks", r)
        self.assertIn("cronos", r)
        self.assertTrue((Path(self.tmp.name) / "author_lab").exists())

    def test_lesson(self):
        r = self.lab.analyze(author="David de la Fuente Alonso", use_llm=False)
        l = self.lab.next_lesson(r)
        self.assertTrue(l["ok"])
        self.assertTrue(l["exercise"])


if __name__ == "__main__":
    unittest.main()
