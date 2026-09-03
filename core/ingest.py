"""
Ingesta de documentos para el Maestro CRONOS.

Soporta: .txt, .md, .pdf, .docx
Extrae texto, lo trocea en fragmentos útiles y los incorpora
a la gramática (infinitud discreta) y a la biblioteca del maestro.
"""
from __future__ import annotations
import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


def _now():
    return datetime.now(timezone.utc).isoformat()


def extract_text(path: Path) -> str:
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix in {".txt", ".md", ".markdown"}:
        return path.read_text(encoding="utf-8", errors="replace")
    if suffix == ".pdf":
        return _extract_pdf(path)
    if suffix in {".docx", ".doc"}:
        return _extract_docx(path)
    raise ValueError(f"Formato no soportado: {suffix}. Usa txt, md, pdf o docx.")


def _extract_pdf(path: Path) -> str:
    # Intento 1: pypdf
    try:
        from pypdf import PdfReader
        reader = PdfReader(str(path))
        parts = []
        for page in reader.pages:
            t = page.extract_text() or ""
            if t.strip():
                parts.append(t)
        if parts:
            return "\n\n".join(parts)
    except Exception:
        pass
    # Intento 2: pdftotext (poppler)
    import subprocess
    try:
        r = subprocess.run(
            ["pdftotext", "-layout", str(path), "-"],
            capture_output=True, timeout=60,
        )
        if r.returncode == 0 and r.stdout:
            return r.stdout.decode("utf-8", errors="replace")
    except Exception:
        pass
    raise RuntimeError(
        "No se pudo extraer texto del PDF. Instala: pip install pypdf"
    )


def _extract_docx(path: Path) -> str:
    try:
        import zipfile
        from xml.etree import ElementTree as ET
        with zipfile.ZipFile(path) as z:
            xml = z.read("word/document.xml")
        root = ET.fromstring(xml)
        ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
        paras = []
        for p in root.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p"):
            texts = [
                t.text for t in p.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t")
                if t.text
            ]
            if texts:
                paras.append("".join(texts))
        return "\n\n".join(paras)
    except Exception as e:
        raise RuntimeError(f"No se pudo leer el DOCX: {e}") from e


def chunk_text(text: str, max_chars: int = 400) -> list[str]:
    """Trocea en fragmentos semánticos cortos para la infinitud discreta."""
    text = re.sub(r"\r\n?", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Primero por párrafos
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks = []
    buf = ""
    for p in paragraphs:
        if len(p) <= max_chars:
            if buf and len(buf) + len(p) + 1 > max_chars:
                chunks.append(buf.strip())
                buf = p
            else:
                buf = (buf + " " + p).strip() if buf else p
        else:
            if buf:
                chunks.append(buf.strip())
                buf = ""
            # dividir frases largas
            sentences = re.split(r"(?<=[.!?])\s+", p)
            for s in sentences:
                s = s.strip()
                if not s:
                    continue
                if len(s) > max_chars:
                    for i in range(0, len(s), max_chars):
                        chunks.append(s[i : i + max_chars].strip())
                elif buf and len(buf) + len(s) + 1 > max_chars:
                    chunks.append(buf.strip())
                    buf = s
                else:
                    buf = (buf + " " + s).strip() if buf else s
    if buf:
        chunks.append(buf.strip())
    # Filtrar ruido muy corto o muy repetitivo
    clean = []
    seen = set()
    for c in chunks:
        key = c[:80].lower()
        if len(c) < 40:
            continue
        if key in seen:
            continue
        # Evitar bucles de texto generado basura
        if c.count("Cronos representa estabilidad") > 1:
            continue
        seen.add(key)
        clean.append(c)
    return clean


class DocumentLibrary:
    """Biblioteca del Maestro: documentos ingeridos + metadatos."""

    def __init__(self, base_path: str = "data/library"):
        self.base = Path(base_path)
        self.base.mkdir(parents=True, exist_ok=True)
        self.docs_dir = self.base / "docs"
        self.docs_dir.mkdir(exist_ok=True)
        self.index_file = self.base / "index.json"
        if not self.index_file.exists():
            self._save_index([])

    def _load_index(self) -> list:
        return json.loads(self.index_file.read_text(encoding="utf-8"))

    def _save_index(self, data: list):
        self.index_file.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def list_docs(self) -> list:
        return self._load_index()

    def ingest_file(
        self,
        path: Path,
        title: Optional[str] = None,
        tags: Optional[list] = None,
        grammar=None,
    ) -> dict:
        path = Path(path)
        text = extract_text(path)
        chunks = chunk_text(text)
        doc_id = str(uuid.uuid4())
        # Guardar copia del texto extraído
        stored = self.docs_dir / f"{doc_id}.txt"
        stored.write_text(text, encoding="utf-8")

        entry = {
            "id": doc_id,
            "title": title or path.stem,
            "source_name": path.name,
            "tags": tags or [],
            "chars": len(text),
            "chunks": len(chunks),
            "ingested_at": _now(),
            "stored_as": str(stored.name),
        }
        index = self._load_index()
        index.append(entry)
        self._save_index(index)

        fragments_added = 0
        if grammar is not None:
            for ch in chunks:
                if grammar.learn_fragment(ch):
                    fragments_added += 1

        entry["fragments_added"] = fragments_added
        # Guardar chunks para recuperación
        chunks_file = self.docs_dir / f"{doc_id}.chunks.json"
        chunks_file.write_text(
            json.dumps(chunks, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return entry

    def ingest_text(
        self,
        text: str,
        title: str = "Nota",
        tags: Optional[list] = None,
        grammar=None,
    ) -> dict:
        chunks = chunk_text(text)
        doc_id = str(uuid.uuid4())
        stored = self.docs_dir / f"{doc_id}.txt"
        stored.write_text(text, encoding="utf-8")
        entry = {
            "id": doc_id,
            "title": title,
            "source_name": "texto_directo",
            "tags": tags or [],
            "chars": len(text),
            "chunks": len(chunks),
            "ingested_at": _now(),
            "stored_as": str(stored.name),
        }
        index = self._load_index()
        index.append(entry)
        self._save_index(index)
        fragments_added = 0
        if grammar is not None:
            for ch in chunks:
                if grammar.learn_fragment(ch):
                    fragments_added += 1
        entry["fragments_added"] = fragments_added
        chunks_file = self.docs_dir / f"{doc_id}.chunks.json"
        chunks_file.write_text(
            json.dumps(chunks, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return entry

    def get_chunks(self, doc_id: str) -> list[str]:
        f = self.docs_dir / f"{doc_id}.chunks.json"
        if not f.exists():
            return []
        return json.loads(f.read_text(encoding="utf-8"))

    def search(self, query: str, limit: int = 8) -> list[dict]:
        """Búsqueda simple por coincidencia de palabras en chunks."""
        q = set(re.findall(r"\w+", query.lower()))
        if not q:
            return []
        results = []
        for doc in self._load_index():
            chunks = self.get_chunks(doc["id"])
            for i, ch in enumerate(chunks):
                words = set(re.findall(r"\w+", ch.lower()))
                score = len(q & words)
                if score > 0:
                    results.append({
                        "score": score,
                        "doc_id": doc["id"],
                        "title": doc["title"],
                        "chunk": ch,
                        "chunk_index": i,
                    })
        results.sort(key=lambda x: -x["score"])
        return results[:limit]
