"""
Módulo de Investigación y Aprendizaje de Temas.

- Busca información en internet (cuando hay conexión y herramienta disponible).
- Resume y genera fragmentos útiles.
- Los incorpora a la memoria y a la gramática (infinitud discreta).
- Límite honesto sobre YouTube: no puede ver ni escuchar el vídeo;
  solo puede usar texto ya publicado (transcripciones, reseñas, resúmenes).
"""
from __future__ import annotations
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from urllib.parse import quote_plus
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

USER_AGENT = "CEOS-CRONOS/5.0 (research; local-first; educational)"


def _now():
    return datetime.now(timezone.utc).isoformat()


def _fetch_text(url: str, timeout: int = 12) -> Optional[str]:
    try:
        req = Request(url, headers={"User-Agent": USER_AGENT})
        with urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            charset = "utf-8"
            ctype = resp.headers.get_content_charset()
            if ctype:
                charset = ctype
            return raw.decode(charset, errors="replace")
    except (URLError, HTTPError, TimeoutError, Exception):
        return None


def _strip_html(html: str) -> str:
    # Muy simple: quitar tags y compactar espacios
    text = re.sub(r"(?is)<script.*?>.*?</script>", " ", html)
    text = re.sub(r"(?is)<style.*?>.*?</style>", " ", text)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = re.sub(r"&\w+;", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def search_duckduckgo(query: str, max_results: int = 5) -> list[dict]:
    """
    Búsqueda ligera vía DuckDuckGo HTML (sin API key).
    Devuelve lista de {title, url, snippet}.
    """
    url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
    html = _fetch_text(url)
    if not html:
        return []

    results = []
    # Patrón aproximado de resultados DDG HTML
    blocks = re.findall(
        r'class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>.*?class="result__snippet"[^>]*>(.*?)</',
        html,
        flags=re.I | re.S,
    )
    for href, title, snippet in blocks[:max_results]:
        title_clean = _strip_html(title)[:120]
        snippet_clean = _strip_html(snippet)[:280]
        # DuckDuckGo a veces envuelve el enlace
        if "uddg=" in href:
            m = re.search(r"uddg=([^&]+)", href)
            if m:
                from urllib.parse import unquote
                href = unquote(m.group(1))
        results.append({
            "title": title_clean,
            "url": href,
            "snippet": snippet_clean,
        })
    return results


def is_youtube_url(text: str) -> bool:
    return bool(re.search(r"(youtube\.com|youtu\.be)/", text, re.I))


def research_topic(topic: str, focus: str = None) -> dict:
    """
    Investiga un tema.
    - Si el tema parece un vídeo de YouTube: deja claro el límite.
    - Busca texto publicado y construye un informe + fragmentos aprendibles.
    """
    topic = (topic or "").strip()
    if not topic:
        return {"ok": False, "error": "Tema vacío"}

    youtube = is_youtube_url(topic) or "youtube" in topic.lower()
    queries = []
    if youtube:
        queries.append(f"{topic} transcripción OR transcript OR resumen OR reseña")
        queries.append(f"{topic} resumen comentarios análisis")
    else:
        q = topic if not focus else f"{topic} {focus}"
        queries.append(q)
        queries.append(f"{topic} explicación conceptos clave")

    all_results = []
    seen_urls = set()
    for q in queries:
        for r in search_duckduckgo(q, max_results=4):
            if r["url"] not in seen_urls:
                seen_urls.add(r["url"])
                all_results.append(r)

    # Construir resumen a partir de snippets (sin LLM externo obligatorio)
    snippets = [r["snippet"] for r in all_results if r.get("snippet")]
    key_points = []
    for s in snippets[:8]:
        s = s.strip()
        if len(s) > 40:
            key_points.append(s)

    fragments = []
    for kp in key_points[:5]:
        # Fragmentos cortos utilizables por la gramática / memoria
        frag = re.sub(r"\s+", " ", kp)[:180]
        if frag:
            fragments.append(frag)

    report = {
        "ok": True,
        "topic": topic,
        "focus": focus,
        "youtube_limit_applied": youtube,
        "disclaimer": (
            "Límite honesto: no puedo ver ni escuchar vídeos de YouTube. "
            "Solo uso texto ya publicado (transcripciones, resúmenes, reseñas, artículos)."
            if youtube else
            "Información obtenida de fuentes de texto públicas. Verifica siempre datos críticos."
        ),
        "sources": all_results[:8],
        "key_points": key_points[:8],
        "fragments_for_learning": fragments,
        "researched_at": _now(),
    }

    if not all_results:
        report["ok"] = False
        report["error"] = (
            "No se pudieron obtener resultados (sin conexión o bloqueo temporal). "
            "Inténtalo más tarde o reformula el tema."
        )

    return report


class TopicLearner:
    """
    Orquesta investigación + incorporación a Memory y Grammar.
    """
    def __init__(self, memory, grammar, identity=None):
        self.memory = memory
        self.grammar = grammar
        self.identity = identity
        self.base = Path("data/research")
        self.base.mkdir(parents=True, exist_ok=True)
        self.log_file = self.base / "topics.json"
        if not self.log_file.exists():
            self.log_file.write_text("[]", encoding="utf-8")

    def _load_log(self):
        return json.loads(self.log_file.read_text(encoding="utf-8"))

    def _save_log(self, data):
        self.log_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def learn(self, topic: str, focus: str = None, device: str = None) -> dict:
        report = research_topic(topic, focus=focus)
        if not report.get("ok"):
            return report

        # Incorporar fragmentos a la gramática (infinitud discreta)
        added = 0
        for frag in report.get("fragments_for_learning", []):
            if self.grammar.learn_fragment(frag):
                added += 1

        # Registrar hito
        hito_text = f"Investigado: «{topic[:80]}» — {added} fragmentos incorporados."
        self.memory.add_hito(hito_text, device=device)

        # Guardar informe local
        entry = {
            "id": report.get("researched_at"),
            "topic": topic,
            "focus": focus,
            "fragments_added": added,
            "sources_count": len(report.get("sources", [])),
            "youtube_limit_applied": report.get("youtube_limit_applied", False),
            "device": device,
        }
        log = self._load_log()
        log.append(entry)
        self._save_log(log)

        if self.identity:
            self.identity.log(hito_text, importance=2)

        report["fragments_added"] = added
        report["learned"] = True
        return report

    def history(self, limit: int = 20) -> list:
        log = self._load_log()
        return log[-limit:]
