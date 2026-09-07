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


# Formatos de texto extraíble vs medios (solo metadatos + transcripción si hay)
TEXT_SUFFIXES = {
    ".txt", ".md", ".markdown", ".pdf", ".docx", ".doc",
    ".epub", ".html", ".htm", ".rtf", ".csv", ".json", ".xml",
    ".odt", ".srt", ".vtt",
}
MEDIA_SUFFIXES = {
    ".mp3", ".wav", ".m4a", ".ogg", ".flac",
    ".mp4", ".webm", ".mkv", ".mov", ".avi",
}
ARCHIVE_SUFFIXES = {".zip"}


def extract_text(path: Path) -> str:
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix in {".txt", ".md", ".markdown", ".csv", ".xml"}:
        return path.read_text(encoding="utf-8", errors="replace")
    if suffix == ".json":
        raw = path.read_text(encoding="utf-8", errors="replace")
        try:
            import json as _json
            data = _json.loads(raw)
            return _json.dumps(data, ensure_ascii=False, indent=2)
        except Exception:
            return raw
    if suffix == ".pdf":
        return _extract_pdf(path)
    if suffix in {".docx", ".doc"}:
        return _extract_docx(path)
    if suffix == ".epub":
        return _extract_epub(path)
    if suffix in {".html", ".htm"}:
        return _extract_html(path)
    if suffix == ".rtf":
        return _extract_rtf(path)
    if suffix == ".odt":
        return _extract_odt(path)
    if suffix in {".srt", ".vtt"}:
        return path.read_text(encoding="utf-8", errors="replace")
    raise ValueError(
        f"Formato no soportado para extracción de texto: {suffix}. "
        f"Texto: {', '.join(sorted(TEXT_SUFFIXES))}. "
        f"Medios (se guardan como referencia): {', '.join(sorted(MEDIA_SUFFIXES))}."
    )


def _extract_epub(path: Path) -> str:
    import zipfile
    from html.parser import HTMLParser

    class _H(HTMLParser):
        def __init__(self):
            super().__init__()
            self.parts = []
            self._skip = False
        def handle_starttag(self, tag, attrs):
            if tag in ("script", "style"):
                self._skip = True
        def handle_endtag(self, tag):
            if tag in ("script", "style"):
                self._skip = False
        def handle_data(self, data):
            if not self._skip and data and data.strip():
                self.parts.append(data.strip())

    parts = []
    with zipfile.ZipFile(path) as z:
        names = [n for n in z.namelist() if n.lower().endswith((".xhtml", ".html", ".htm", ".xml"))]
        for n in sorted(names)[:200]:
            try:
                raw = z.read(n).decode("utf-8", errors="replace")
            except Exception:
                continue
            p = _H()
            try:
                p.feed(raw)
            except Exception:
                continue
            if p.parts:
                parts.append(" ".join(p.parts))
    text = "\n\n".join(parts)
    if not text.strip():
        raise RuntimeError("EPUB sin texto extraíble")
    return text


def _extract_html(path: Path) -> str:
    raw = path.read_text(encoding="utf-8", errors="replace")
    raw = re.sub(r"(?is)<script.*?>.*?</script>", " ", raw)
    raw = re.sub(r"(?is)<style.*?>.*?</style>", " ", raw)
    raw = re.sub(r"(?s)<[^>]+>", " ", raw)
    raw = re.sub(r"&nbsp;", " ", raw)
    raw = re.sub(r"&amp;", "&", raw)
    raw = re.sub(r"\s+", " ", raw)
    return raw.strip()


def _extract_rtf(path: Path) -> str:
    raw = path.read_text(encoding="utf-8", errors="replace")
    # quitar control words RTF de forma tosca
    raw = re.sub(r"\\[a-zA-Z]+\d*\s?", " ", raw)
    raw = re.sub(r"[{}]", " ", raw)
    raw = re.sub(r"\s+", " ", raw)
    return raw.strip()


def _extract_odt(path: Path) -> str:
    import zipfile
    from xml.etree import ElementTree as ET
    with zipfile.ZipFile(path) as z:
        xml = z.read("content.xml")
    root = ET.fromstring(xml)
    texts = []
    for el in root.iter():
        if el.text and el.text.strip():
            texts.append(el.text.strip())
        if el.tail and el.tail.strip():
            texts.append(el.tail.strip())
    return "\n".join(texts)


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
        author: Optional[str] = None,
        kind: Optional[str] = None,
        codex=None,
    ) -> dict:
        path = Path(path)
        suffix = path.suffix.lower()
        tags = list(tags or [])
        if author:
            tags.append(f"author:{author.strip()}")

        # Medios: guardar referencia + sidecar de transcripción si existe
        if suffix in MEDIA_SUFFIXES:
            return self._ingest_media(path, title=title, tags=tags, author=author)

        text = extract_text(path)
        chunks = chunk_text(text, max_chars=480)
        doc_id = str(uuid.uuid4())
        stored = self.docs_dir / f"{doc_id}.txt"
        stored.write_text(text, encoding="utf-8")

        entry = {
            "id": doc_id,
            "title": title or path.stem,
            "source_name": path.name,
            "author": (author or "").strip() or None,
            "kind": kind or "document",
            "format": suffix.lstrip("."),
            "tags": tags,
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
        if codex is not None:
            try:
                topic = (author + " — " if author else "") + (title or path.stem)
                codex.compress_text(text[:12000], topic=topic[:80])
                entry["codex"] = True
            except Exception:
                entry["codex"] = False
        return entry

    def _ingest_media(
        self,
        path: Path,
        title: Optional[str] = None,
        tags: Optional[list] = None,
        author: Optional[str] = None,
    ) -> dict:
        """Guarda audio/vídeo como activo del reservorio + transcripción si hay .srt/.vtt junto al archivo."""
        path = Path(path)
        doc_id = str(uuid.uuid4())
        media_dir = self.base / "media"
        media_dir.mkdir(exist_ok=True)
        dest = media_dir / f"{doc_id}{path.suffix.lower()}"
        dest.write_bytes(path.read_bytes())
        transcript = ""
        # buscar sidecar
        for side in (
            path.with_suffix(".srt"),
            path.with_suffix(".vtt"),
            path.with_suffix(".txt"),
        ):
            if side.exists():
                try:
                    transcript = side.read_text(encoding="utf-8", errors="replace")
                    break
                except Exception:
                    pass
        if transcript:
            stored = self.docs_dir / f"{doc_id}.txt"
            stored.write_text(transcript, encoding="utf-8")
            chunks = chunk_text(transcript)
            (self.docs_dir / f"{doc_id}.chunks.json").write_text(
                json.dumps(chunks, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        else:
            chunks = []
            note = (
                f"[MEDIO] {path.name}\n"
                "Sin transcripción adjunta. CEOS no ve ni oye el medio; "
                "sube un .srt/.vtt/.txt con el mismo nombre para indexar el contenido."
            )
            (self.docs_dir / f"{doc_id}.txt").write_text(note, encoding="utf-8")
        entry = {
            "id": doc_id,
            "title": title or path.stem,
            "source_name": path.name,
            "author": (author or "").strip() or None,
            "kind": "media",
            "format": path.suffix.lower().lstrip("."),
            "tags": list(tags or []) + ["media"],
            "chars": len(transcript),
            "chunks": len(chunks),
            "ingested_at": _now(),
            "stored_as": f"{doc_id}.txt",
            "media_file": dest.name,
            "has_transcript": bool(transcript),
            "honest_limit": (
                None if transcript else
                "Audio/vídeo guardado como referencia; el conocimiento indexable requiere transcripción."
            ),
        }
        index = self._load_index()
        index.append(entry)
        self._save_index(index)
        return entry

    def ingest_archive(
        self,
        path: Path,
        grammar=None,
        codex=None,
        author: Optional[str] = None,
        tags: Optional[list] = None,
        max_files: int = 200,
    ) -> dict:
        """Descomprime un ZIP y ingiere cada documento/medio soportado."""
        import zipfile
        import tempfile
        path = Path(path)
        results = []
        errors = []
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            with zipfile.ZipFile(path) as z:
                z.extractall(td_path)
            files = [p for p in td_path.rglob("*") if p.is_file()]
            count = 0
            for f in files:
                if count >= max_files:
                    errors.append(f"Límite de {max_files} archivos en el ZIP")
                    break
                suf = f.suffix.lower()
                if suf in ARCHIVE_SUFFIXES:
                    continue
                if suf not in TEXT_SUFFIXES and suf not in MEDIA_SUFFIXES:
                    continue
                try:
                    entry = self.ingest_file(
                        f, title=f.stem, tags=tags, grammar=grammar,
                        author=author, codex=codex,
                    )
                    results.append({"name": f.name, "ok": True, "id": entry.get("id"), "chunks": entry.get("chunks")})
                    count += 1
                except Exception as e:
                    errors.append(f"{f.name}: {e}")
        return {
            "ok": True,
            "ingested": len(results),
            "results": results,
            "errors": errors[:30],
        }

    def stats(self) -> dict:
        idx = self._load_index()
        chars = sum(int(d.get("chars") or 0) for d in idx)
        chunks = sum(int(d.get("chunks") or 0) for d in idx)
        media = sum(1 for d in idx if d.get("kind") == "media")
        return {
            "docs": len(idx),
            "media": media,
            "chars": chars,
            "chunks": chunks,
        }

    def search_docs(self, query: str, limit: int = 20) -> list:
        """Busca documentos por título, autor, tags o nombre de archivo."""
        q = (query or "").lower().strip()
        if not q:
            return self.list_docs()[:limit]
        out = []
        for d in self._load_index():
            blob = " ".join([
                str(d.get("title") or ""),
                str(d.get("author") or ""),
                str(d.get("source_name") or ""),
                " ".join(d.get("tags") or []),
            ]).lower()
            # coincidencia de frase o de cualquier palabra >=4
            words = [w for w in q.split() if len(w) >= 3]
            if q in blob or any(w in blob for w in words):
                out.append(d)
        return out[:limit]

    def get_doc_text(self, doc_id: str) -> str:
        path = self.docs_dir / f"{doc_id}.txt"
        if path.exists():
            return path.read_text(encoding="utf-8", errors="replace")
        return ""

    def get_doc_chunks(self, doc_id: str) -> list:
        path = self.docs_dir / f"{doc_id}.chunks.json"
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                return []
        text = self.get_doc_text(doc_id)
        return chunk_text(text) if text else []

    def study(
        self,
        query: str,
        lens: str = "general",
        limit_docs: int = 5,
        sample_chunks: int = 8,
        grammar=None,
        codex=None,
    ) -> dict:
        """
        Relee materiales del reservorio con un 'lente' distinto.
        Cada lectura puede enfatizar estilo, temas, estructura, críticas, etc.
        Integra conclusiones en gramática/códice si se pasan.
        """
        query = (query or "").strip()
        lens = (lens or "general").strip().lower()
        docs = self.search_docs(query, limit=limit_docs) if query else self.list_docs()[:limit_docs]
        if not docs and query:
            # fallback: todos y filtrar por texto
            docs = []
            for d in self.list_docs()[:40]:
                t = self.get_doc_text(d["id"])[:3000].lower()
                if query.lower() in t or any(w in t for w in query.lower().split()[:4]):
                    docs.append(d)
                if len(docs) >= limit_docs:
                    break

        lens_hints = {
            "general": "síntesis general y puntos centrales",
            "estilo": "voz, ritmo, léxico, recursos retóricos, tono",
            "temas": "motivos recurrentes, símbolos, conflictos, tesis",
            "estructura": "organización, partes, progresión, desenlace",
            "critica": "límites, tensiones, contradicciones, debilidades",
            "practico": "aplicaciones, lecciones accionables, ejemplos",
            "comparar": "semejanzas y diferencias entre textos del lote",
            "evolucion": "qué cambia si se relee ahora frente a una lectura previa",
        }
        focus = lens_hints.get(lens, lens_hints["general"])

        readings = []
        conclusions = []
        for d in docs[:limit_docs]:
            chunks = self.get_doc_chunks(d["id"])
            if not chunks:
                text = self.get_doc_text(d["id"])
                chunks = chunk_text(text) if text else []
            # muestreo distinto según lente (desfase) para "otra lectura"
            offset = {
                "general": 0, "estilo": 1, "temas": 2, "estructura": 3,
                "critica": 4, "practico": 5, "comparar": 1, "evolucion": 2,
            }.get(lens, 0)
            picked = []
            if chunks:
                for i in range(sample_chunks):
                    picked.append(chunks[(i * 3 + offset) % len(chunks)])
            excerpt = "\n".join(picked)[:3500]
            # conclusiones heurísticas locales
            words = re.findall(r"[A-Za-záéíóúñÁÉÍÓÚÑ]{5,}", excerpt.lower())
            freq = {}
            for w in words:
                if w in ("donde", "cuando", "porque", "entre", "sobre", "desde", "tiene", "puede", "hacer", "estar"):
                    continue
                freq[w] = freq.get(w, 0) + 1
            top = sorted(freq.items(), key=lambda x: -x[1])[:8]
            motifs = ", ".join(w for w, _ in top) if top else "(pocos motivos léxicos)"
            conclusion = (
                f"Lectura «{lens}» de «{d.get('title')}»"
                + (f" ({d.get('author')})" if d.get("author") else "")
                + f": foco en {focus}. Motivos destacados: {motifs}."
            )
            if lens == "estilo" and excerpt:
                long_sent = max((len(s) for s in re.split(r"[.!?]", excerpt)), default=0)
                conclusion += f" Frases de hasta ~{long_sent} caracteres en el muestreo; tono inferido del léxico recurrente."
            if lens == "critica":
                conclusion += " Buscar lagunas: lo que el texto no define, asume o deja en tensión."
            conclusions.append(conclusion)
            readings.append({
                "doc_id": d.get("id"),
                "title": d.get("title"),
                "author": d.get("author"),
                "lens": lens,
                "chunks_sampled": len(picked),
                "excerpt": excerpt[:1200],
                "conclusion": conclusion,
            })
            if grammar is not None:
                try:
                    grammar.learn_fragment(conclusion)
                    for ch in picked[:3]:
                        grammar.learn_fragment(ch[:220])
                except Exception:
                    pass
            if codex is not None:
                try:
                    blob = conclusion + "\n" + excerpt[:4000]
                    topic = f"lectura:{lens}:{(d.get('title') or query)[:40]}"
                    codex.compress_text(blob, topic=topic)
                except Exception:
                    pass

        # meta-conclusión del lote
        meta = (
            f"Relectura del reservorio con lente «{lens}» sobre «{query or 'corpus local'}»: "
            f"{len(readings)} documento(s). "
            + (" | ".join(c[:120] for c in conclusions[:3]) if conclusions else "Sin material.")
        )
        return {
            "ok": True,
            "query": query,
            "lens": lens,
            "focus": focus,
            "readings": readings,
            "conclusions": conclusions,
            "meta_conclusion": meta,
            "docs_used": len(readings),
        }

    def ingest_text(
        self,
        text: str,
        title: str = "Nota",
        tags: Optional[list] = None,
        grammar=None,
        author: Optional[str] = None,
        codex=None,
    ) -> dict:
        tags = list(tags or [])
        if author:
            tags.append(f"author:{author.strip()}")
        chunks = chunk_text(text, max_chars=480)
        doc_id = str(uuid.uuid4())
        stored = self.docs_dir / f"{doc_id}.txt"
        stored.write_text(text, encoding="utf-8")
        entry = {
            "id": doc_id,
            "title": title,
            "source_name": "texto_directo",
            "author": (author or "").strip() or None,
            "kind": "document",
            "tags": tags,
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
        """Búsqueda en metadatos + chunks del reservorio."""
        q = set(re.findall(r"\w+", (query or "").lower()))
        if not q:
            return []
        results = []
        for doc in self.search_docs(query, limit=limit * 3):
            results.append({
                "score": 2,
                "doc_id": doc["id"],
                "title": doc.get("title"),
                "author": doc.get("author"),
                "chunk": f"[doc] {doc.get('title')} — {doc.get('author') or ''}",
                "chunk_index": -1,
            })
        for doc in self._load_index():
            chunks = self.get_chunks(doc["id"])
            for i, ch in enumerate(chunks):
                words = set(re.findall(r"\w+", ch.lower()))
                score = len(q & words)
                if score > 0:
                    results.append({
                        "score": score,
                        "doc_id": doc["id"],
                        "title": doc.get("title"),
                        "author": doc.get("author"),
                        "chunk": ch,
                        "chunk_index": i,
                    })
        results.sort(key=lambda x: -x["score"])
        return results[:limit]
