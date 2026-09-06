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


def _fetch_text(url: str, timeout: int = 6) -> Optional[str]:
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



def _stem_token(tok: str) -> str:
    """Aproxima ES/EN para que teologia ~ theology, biologia ~ biology."""
    t = tok
    pairs = [
        ("teologia", "theolog"),
        ("theology", "theolog"),
        ("theological", "theolog"),
        ("theologi", "theolog"),
        ("biologia", "biolog"),
        ("biology", "biolog"),
        ("geologia", "geolog"),
        ("geology", "geolog"),
        ("astroteologia", "astrotheolog"),
        ("astrotheology", "astrotheolog"),
        ("astrotheological", "astrotheolog"),
        ("exoteologia", "exotheolog"),
        ("exotheology", "exotheolog"),
        ("religion", "relig"),
        ("religion", "relig"),
        ("religión", "relig"),
    ]
    for a, b in pairs:
        if t == a or t.startswith(a):
            return b
    # sufijos comunes
    for suf in ("ical", "ics", "ies", "cion", "ción", "ogy", "ia", "y"):
        if len(t) > 6 and t.endswith(suf):
            t = t[: -len(suf)]
            break
    return t


def _normalize_tokens(s: str) -> list:
    s = (s or "").lower()
    s = (
        s.replace("á", "a")
        .replace("é", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ú", "u")
        .replace("ñ", "n")
    )
    parts = re.findall(r"[a-z0-9]{3,}", s)
    return [_stem_token(p) for p in parts]


# Falsos amigos: no confundir teología/religión con biología/geología por el prefijo "astro"
_FALSE_FRIENDS = {
    "teologia": {"biologia", "geologia", "fisica", "nomia", "nautica"},
    "theology": {"biology", "geology", "physics", "nomy"},
}


def _query_variants(query: str) -> list:
    """Variantes fieles al término (no sustitutos semánticos lejanos)."""
    q = (query or "").strip()
    low = q.lower()
    variants = [q]
    pairs = [
        ("astroteología", "astrotheology"),
        ("astroteologia", "astrotheology"),
        ("teología", "theology"),
        ("teologia", "theology"),
        ("exoteología", "exotheology"),
        ("exoteologia", "exotheology"),
    ]
    for a, b in pairs:
        if a in low and b not in variants:
            variants.append(b)
        if b in low and a not in variants:
            variants.append(a)
    # quitar signos de pregunta tipo "qué es X"
    m = re.search(r"(?:qu[eé]\s+es|what\s+is)\s+(.+)", low)
    if m:
        core = m.group(1).strip(" ?¡!.")
        if core and core not in variants:
            variants.append(core)
    # dedupe
    out = []
    seen = set()
    for v in variants:
        k = v.lower()
        if k not in seen:
            seen.add(k)
            out.append(v)
    return out


def _relevance_score(query: str, title: str, snippet: str) -> float:
    """Puntuación 0–1 de pertinencia; penaliza falsos amigos (astrobiología vs astroteología)."""
    q_tokens = _normalize_tokens(query)
    if not q_tokens:
        return 0.0
    blob = _normalize_tokens((title or "") + " " + (snippet or ""))
    if not blob:
        return 0.0
    # tokens significativos del query (ignorar qué/es/the)
    stop = {"que", "es", "the", "what", "is", "una", "un", "sobre", "about", "define", "definir"}
    qt = [t for t in q_tokens if t not in stop]
    if not qt:
        qt = q_tokens
    hits = sum(1 for t in qt if t in blob)
    score = hits / max(len(qt), 1)
    # bonus si el título contiene el término compuesto o gran parte
    title_n = " ".join(_normalize_tokens(title))
    qn = " ".join(qt)
    if qn and qn in title_n.replace(" ", ""):
        score += 0.35
    if any(t in title_n for t in qt):
        score += 0.15
    # penalización falsos amigos
    for key, enemies in _FALSE_FRIENDS.items():
        if any(key in t or t.startswith(key[:5]) for t in qt):
            for e in enemies:
                if e in title_n or e in " ".join(blob):
                    # si no aparece el núcleo teolog/theology, penalizar fuerte
                    if not any(x in title_n for x in ("teolog", "theolog", "relig", "worship", "sagrado")):
                        score -= 0.55
    return max(0.0, min(1.0, score))


def _filter_rank_results(query: str, results: list, min_score: float = 0.2) -> list:
    scored = []
    for r in results:
        sc = _relevance_score(query, r.get("title") or "", r.get("snippet") or "")
        r = dict(r)
        r["relevance"] = round(sc, 3)
        scored.append(r)
    scored.sort(key=lambda x: x.get("relevance", 0), reverse=True)
    good = [r for r in scored if r.get("relevance", 0) >= min_score]
    # si todo filtrado, devolver top 2 con score>0 en vez de basura total
    if not good:
        good = [r for r in scored if r.get("relevance", 0) > 0][:2]
    return good


def search_duckduckgo_api(query: str) -> list[dict]:
    """DuckDuckGo Instant Answer API (JSON, sin clave). Más fiable desde servidores."""
    url = (
        "https://api.duckduckgo.com/?q="
        + quote_plus(query)
        + "&format=json&no_html=1&skip_disambig=1"
    )
    raw = _fetch_text(url, timeout=8)
    results = []
    if not raw:
        return results
    try:
        data = json.loads(raw)
    except Exception:
        return results
    abstract = (data.get("AbstractText") or "").strip()
    abs_url = data.get("AbstractURL") or data.get("AbstractSource") or ""
    heading = data.get("Heading") or query
    if abstract:
        results.append({
            "title": heading,
            "url": abs_url or "https://duckduckgo.com/?q=" + quote_plus(query),
            "snippet": abstract[:500],
            "source": "ddg-abstract",
        })
    for t in (data.get("RelatedTopics") or [])[:5]:
        if not isinstance(t, dict):
            continue
        if "Topics" in t:  # grupo
            for t2 in (t.get("Topics") or [])[:3]:
                if isinstance(t2, dict) and t2.get("Text"):
                    results.append({
                        "title": (t2.get("Text") or "")[:80],
                        "url": t2.get("FirstURL") or "",
                        "snippet": (t2.get("Text") or "")[:280],
                        "source": "ddg-related",
                    })
        elif t.get("Text"):
            results.append({
                "title": (t.get("Text") or "")[:80],
                "url": t.get("FirstURL") or "",
                "snippet": (t.get("Text") or "")[:280],
                "source": "ddg-related",
            })
    return results


def search_wikipedia(query: str, lang: str = "es") -> list[dict]:
    """Wikipedia API opensearch + extract (sin clave)."""
    results = []
    try:
        opensearch = (
            f"https://{lang}.wikipedia.org/w/api.php?action=opensearch&search="
            + quote_plus(query)
            + "&limit=3&namespace=0&format=json"
        )
        raw = _fetch_text(opensearch, timeout=8)
        if not raw:
            # fallback inglés
            if lang != "en":
                return search_wikipedia(query, lang="en")
            return results
        data = json.loads(raw)
        # [query, [titles], [descs], [urls]]
        titles = data[1] if len(data) > 1 else []
        descs = data[2] if len(data) > 2 else []
        urls = data[3] if len(data) > 3 else []
        for i, title in enumerate(titles[:3]):
            results.append({
                "title": title,
                "url": urls[i] if i < len(urls) else "",
                "snippet": (descs[i] if i < len(descs) else title)[:300],
                "source": f"wikipedia-{lang}",
            })
        # extract del primero
        if titles:
            ext_url = (
                f"https://{lang}.wikipedia.org/w/api.php?action=query&prop=extracts"
                f"&explaintext=1&exsectionformat=plain&titles={quote_plus(titles[0])}&format=json"
            )
            raw2 = _fetch_text(ext_url, timeout=8)
            if raw2:
                d2 = json.loads(raw2)
                pages = (d2.get("query") or {}).get("pages") or {}
                for pg in pages.values():
                    extract = (pg.get("extract") or "")[:2500]
                    if extract and results:
                        results[0]["snippet"] = extract
                        break
        if not results and lang != "en":
            return search_wikipedia(query, lang="en")
    except Exception:
        pass
    return results


def search_duckduckgo(query: str, max_results: int = 8) -> list[dict]:
    """Multi-fuente con filtro de relevancia (evita astrobiología cuando pides astroteología)."""
    results = []
    seen = set()

    def _add(items):
        for r in items:
            key = (r.get("url") or "") + "|" + (r.get("title") or "")
            if key in seen:
                continue
            if not (r.get("snippet") or r.get("title")):
                continue
            seen.add(key)
            results.append(r)

    variants = _query_variants(query)
    for v in variants:
        _add(search_duckduckgo_api(v))
        _add(search_wikipedia(v, "es"))
        _add(search_wikipedia(v, "en"))

    # HTML DDG como refuerzo
    if len(_filter_rank_results(query, results, 0.2)) < 2:
        for v in variants[:2]:
            url = f"https://html.duckduckgo.com/html/?q={quote_plus(v)}"
            html = _fetch_text(url, timeout=8)
            if not html:
                continue
            blocks = re.findall(
                r'class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>.*?class="result__snippet"[^>]*>(.*?)</',
                html,
                flags=re.I | re.S,
            )
            from urllib.parse import unquote
            for href, title, snippet in blocks[:max_results]:
                if "uddg=" in href:
                    m = re.search(r"uddg=([^&]+)", href)
                    if m:
                        href = unquote(m.group(1))
                _add([{
                    "title": _strip_html(title)[:120],
                    "url": href,
                    "snippet": _strip_html(snippet)[:280],
                    "source": "ddg-html",
                }])

    ranked = _filter_rank_results(query, results, min_score=0.2)
    return ranked[:max_results]


def is_youtube_url(text: str) -> bool:
    return bool(re.search(r"(youtube\.com|youtu\.be)/", text, re.I))


def research_topic(topic: str, focus: str = None) -> dict:
    """
    Investigación estructurada (no solo reseña):
    pregunta → fuentes relevantes → contraste → síntesis por secciones → límites → aprendizaje.
    El informe se redacta en el idioma de la consulta (castellano si preguntas en castellano).
    """
    topic = (topic or "").strip()
    if not topic:
        return {"ok": False, "error": "Tema vacío"}

    youtube = is_youtube_url(topic) or "youtube" in topic.lower()
    lang_es = bool(re.search(
        r"[áéíóúñ¿¡]|(\b(qué|que|cómo|como|cuál|cual|dónde|donde|definición|definir|explica|investig|sobre|historia|origen)\b)",
        topic,
        re.I,
    ))
    if re.search(r"\b(what|is|the|how|define|research|about)\b", topic, re.I) and not re.search(r"[áéíóúñ¿¡]", topic):
        lang_es = False
    if not re.search(r"[a-zA-ZáéíóúñÁÉÍÓÚÑ]{3,}", topic):
        lang_es = True
    # Por defecto castellano si hay caracteres españoles o el usuario usa CEOS en ES
    if re.search(r"[áéíóúñ¿¡]", topic):
        lang_es = True

    query = topic if not focus else f"{topic} {focus}"
    all_results = []
    seen_urls = set()
    for r in search_duckduckgo(query, max_results=10):
        u = (r.get("url") or "") + "|" + (r.get("title") or "")
        if u not in seen_urls:
            seen_urls.add(u)
            all_results.append(r)
    all_results = _filter_rank_results(topic, all_results, min_score=0.2)

    for r in all_results[:3]:
        url = r.get("url") or ""
        if "wikipedia.org" in url and len(r.get("snippet") or "") < 500:
            title = r.get("title") or ""
            wlang = "es" if "es.wikipedia" in url else "en"
            try:
                ext_url = (
                    f"https://{wlang}.wikipedia.org/w/api.php?action=query&prop=extracts"
                    f"&explaintext=1&titles={quote_plus(title)}&format=json"
                )
                raw2 = _fetch_text(ext_url, timeout=10)
                if raw2:
                    d2 = json.loads(raw2)
                    pages = (d2.get("query") or {}).get("pages") or {}
                    for pg in pages.values():
                        extract = (pg.get("extract") or "")[:3000]
                        if extract:
                            r["snippet"] = extract
                            r["long_extract"] = True
            except Exception:
                pass

    snippets = [r.get("snippet") or "" for r in all_results if r.get("snippet")]
    key_points = []
    for s in snippets:
        s = re.sub(r"\s+", " ", s).strip()
        if len(s) < 40:
            continue
        parts = re.split(r"(?<=\.)\s+", s)
        for part in parts:
            part = part.strip()
            if len(part) > 60:
                key_points.append(part[:420])
            if len(key_points) >= 14:
                break
        if len(key_points) >= 14:
            break

    deduped = []
    for kp in key_points:
        if not any(kp[:50] == d[:50] for d in deduped):
            deduped.append(kp)
    key_points = deduped[:12]

    def _report_es():
        definicion = key_points[0] if key_points else "No hay una definición única consolidada en las fuentes recuperadas."
        contexto = key_points[1] if len(key_points) > 1 else "El contexto aparece de forma fragmentaria en las fuentes."
        dimensiones = key_points[2:7] if len(key_points) > 2 else key_points
        contrastes = key_points[7:11] if len(key_points) > 7 else []
        lines = [
            f"## Investigación: {topic}",
        ]
        if focus:
            lines.append(f"**Enfoque:** {focus}")
        lines += [
            "",
            "### 1. Pregunta y objeto",
            f"Se investiga «{topic}» con fuentes públicas de texto, filtrando por relevancia real al término (no vecinos léxicos engañosos).",
            "",
            "### 2. Definición operativa",
            definicion,
            "",
            "### 3. Contexto y marco",
            contexto,
            "",
            "### 4. Hallazgos principales",
        ]
        if dimensiones:
            for i, d in enumerate(dimensiones, 1):
                lines.append(f"{i}. {d}")
        else:
            lines.append("No se han podido estructurar hallazgos suficientes.")
        lines += ["", "### 5. Matices, límites y contrastes"]
        if contrastes:
            for c in contrastes:
                lines.append(f"- {c}")
        else:
            lines.append("- Las fuentes son heterogéneas; parte del material puede estar en inglés.")
            lines.append("- No sustituye una revisión académica sistemática ni literatura de pago.")
        lines += ["", "### 6. Fuentes consultadas"]
        for s in all_results[:8]:
            title = s.get("title") or "Sin título"
            url = s.get("url") or ""
            rel = s.get("relevance", "")
            extra = f" (relevancia {rel})" if rel != "" else ""
            lines.append(f"- {title}" + (f" — {url}" if url else "") + extra)
        lines += [
            "",
            "### 7. Conclusión provisional",
            f"Sobre «{topic}», la evidencia textual permite una aproximación informada y revisable. "
            "El motor conserva fragmentos para memoria y códice si el aprendizaje está activo.",
        ]
        return "\n".join(lines)

    def _report_en():
        lines = [
            f"## Research report: {topic}",
            "",
            "### 1. Question",
            f"Inquiry into “{topic}” using public text sources with relevance filtering.",
            "",
            "### 2. Working definition",
            key_points[0] if key_points else "No consolidated definition in retrieved sources.",
            "",
            "### 3. Context",
            key_points[1] if len(key_points) > 1 else "Context remains fragmentary.",
            "",
            "### 4. Main findings",
        ]
        for i, d in enumerate((key_points[2:8] or key_points), 1):
            lines.append(f"{i}. {d}")
        lines += ["", "### 5. Limits", "- Public-web synthesis only; not a peer-reviewed systematic review.", "", "### 6. Sources"]
        for s in all_results[:8]:
            lines.append(f"- {s.get('title') or ''} — {s.get('url') or ''}")
        return "\n".join(lines)

    report_text = _report_es() if lang_es else _report_en()

    # Si el contenido fuente está en inglés pero el usuario preguntó en ES, enmarcar en castellano
    # (las citas pueden quedar en inglés; la estructura y el metalenguaje van en ES)

    fragments = []
    for kp in key_points[:8]:
        frag = re.sub(r"\s+", " ", kp)[:220]
        if frag:
            fragments.append(frag)

    report = {
        "ok": True,
        "topic": topic,
        "focus": focus,
        "lang": "es" if lang_es else "en",
        "youtube_limit_applied": youtube,
        "disclaimer": (
            "Investigación con fuentes públicas. Informe estructurado con filtro de relevancia; "
            "no es una revisión sistemática académica. Verifica datos críticos."
            if lang_es else
            "Public-source structured research with relevance filtering; not a systematic academic review."
        ),
        "summary": report_text,
        "sources": all_results[:10],
        "key_points": key_points[:12],
        "fragments_for_learning": fragments,
        "researched_at": _now(),
        "depth": "structured_report",
    }

    if not all_results:
        report["ok"] = False
        report["error"] = (
            "No se pudieron obtener resultados relevantes. Reformula el tema o inténtalo más tarde."
            if lang_es else
            "No relevant results retrieved. Reformulate or try later."
        )

    return report



class TopicLearner:
    """
    Orquesta investigación + Memory + Grammar + Codex fractal + memoria larga.
    """
    def __init__(self, memory, grammar, identity=None, codex=None, long_memory=None):
        self.memory = memory
        self.grammar = grammar
        self.identity = identity
        self.codex = codex
        self.long_memory = long_memory
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

        added = 0
        for frag in report.get("fragments_for_learning", []):
            try:
                if self.grammar.learn_fragment(frag):
                    added += 1
            except Exception:
                pass

        # Codex: comprimir conocimiento y ciclo fractal (re-cifrado / generación)
        codex_info = {}
        if self.codex is not None:
            try:
                blob = "\n".join(
                    [f"{s.get('title','')}: {s.get('snippet','')}" for s in (report.get("sources") or [])[:6]]
                    + (report.get("key_points") or [])[:6]
                )
                codex_info = self.codex.compress_text(blob[:5000], topic=topic[:80]) or {}
                frac = self.codex.maybe_fractal_after_ingest(topic[:80])
                if frac:
                    codex_info["fractal"] = frac
            except Exception as e:
                codex_info = {"error": str(e)[:120]}

        # Memoria larga: hechos / temas
        mem_info = {}
        if self.long_memory is not None:
            try:
                summary = " ".join((report.get("key_points") or [])[:3])[:500]
                mem_info = self.long_memory.absorb_turn(
                    f"Investigación: {topic}",
                    summary or topic,
                    do_facts=True,
                    do_topics=True,
                ) or {}
            except Exception as e:
                mem_info = {"error": str(e)[:120]}

        hito_text = f"Investigado: «{topic[:80]}» — {added} fragmentos + códice."
        try:
            self.memory.add_hito(hito_text, device=device)
        except Exception:
            pass

        entry = {
            "id": report.get("researched_at"),
            "topic": topic,
            "focus": focus,
            "fragments_added": added,
            "sources_count": len(report.get("sources", [])),
            "youtube_limit_applied": report.get("youtube_limit_applied", False),
            "device": device,
            "codex": bool(codex_info) and not codex_info.get("error"),
        }
        log = self._load_log()
        log.append(entry)
        self._save_log(log[-200:])  # limitar tamaño

        if self.identity:
            try:
                self.identity.log(hito_text, importance=2)
            except Exception:
                pass

        report["fragments_added"] = added
        report["learned"] = True
        report["codex"] = codex_info
        report["long_memory"] = mem_info
        return report

    def history(self, limit: int = 20) -> list:
        log = self._load_log()
        return log[-limit:]
