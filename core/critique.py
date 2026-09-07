"""
Crítica automática de lo investigado y reconciliación con el Codex.

- Compara hallazgos nuevos con cristales/mapas previos del mismo tema.
- Detecta solapamientos, novedades y posibles contradicciones (heurística léxica).
- Reescribe / refuerza el códice: comprime lo sólido y marca conflictos.
"""
from __future__ import annotations
import re
from datetime import datetime, timezone
from typing import Any, Optional


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _tokens(s: str) -> set[str]:
    s = (s or "").lower()
    s = (
        s.replace("á", "a").replace("é", "e").replace("í", "i")
        .replace("ó", "o").replace("ú", "u").replace("ñ", "n")
    )
    return set(re.findall(r"[a-z0-9]{4,}", s))


def _negation_conflict(a: str, b: str) -> bool:
    """Heurística: una frase niega algo que la otra afirma (no / never / neither vs yes-patterns)."""
    al, bl = a.lower(), b.lower()
    neg = (" no ", " not ", " never ", " neither ", " nadie ", " ninguno ", " without ")
    # si una tiene negación fuerte y comparten muchos tokens de contenido
    ta, tb = _tokens(a), _tokens(b)
    stop = {"that", "this", "with", "from", "have", "been", "were", "para", "como", "sobre", "entre"}
    ta -= stop
    tb -= stop
    overlap = ta & tb
    if len(overlap) < 3:
        return False
    a_neg = any(n in f" {al} " for n in neg)
    b_neg = any(n in f" {bl} " for n in neg)
    return a_neg != b_neg and len(overlap) >= 4


def critique_research(report: dict, codex=None) -> dict:
    """
    Analiza un informe de research_topic / learn.
    Devuelve críticas, contradicciones y acciones sugeridas/aplicadas sobre el códice.
    """
    topic = (report.get("topic") or "").strip()
    points = list(report.get("key_points") or [])
    sources = list(report.get("sources") or [])
    summary = report.get("summary") or ""

    issues = []
    strengths = []
    contradictions = []
    novel = []

    if not sources:
        issues.append("Sin fuentes recuperadas: la investigación es débil.")
    elif len(sources) < 2:
        issues.append("Pocas fuentes: conviene contrastar con al menos otra independiente.")
    else:
        strengths.append(f"{len(sources)} fuentes con filtro de relevancia.")

    if len(points) < 3:
        issues.append("Poca profundidad en hallazgos (pocos puntos extraídos).")
    else:
        strengths.append(f"{len(points)} hallazgos textuales extraídos.")

    # Contraste interno entre puntos nuevos
    for i, a in enumerate(points[:8]):
        for b in points[i + 1 : 8]:
            if _negation_conflict(a, b):
                contradictions.append({
                    "type": "internal",
                    "a": a[:220],
                    "b": b[:220],
                    "note": "Posible tensión entre dos hallazgos nuevos (negación vs afirmación).",
                })

    prior_texts = []
    if codex is not None and topic:
        try:
            exp = codex.expand_topic(topic, limit=10)
            if isinstance(exp, dict) and exp.get("ok") is not False:
                for f in (exp.get("fragments") or exp.get("texts") or [])[:12]:
                    if isinstance(f, dict):
                        prior_texts.append(str(f.get("text") or f.get("content") or "")[:400])
                    else:
                        prior_texts.append(str(f)[:400])
            # también cristales recientes por mapa
            m = None
            try:
                m = codex.get_map(topic)
            except Exception:
                m = None
            if isinstance(m, dict):
                for cid in (m.get("crystals") or [])[:8]:
                    try:
                        c = codex.get_crystal(cid)
                        if c and c.get("text"):
                            prior_texts.append(str(c["text"])[:400])
                    except Exception:
                        pass
        except Exception:
            pass

    for p in points[:10]:
        pt = _tokens(p)
        if not prior_texts:
            novel.append(p[:220])
            continue
        best_overlap = 0
        conflict_hit = None
        for prev in prior_texts:
            ov = len(pt & _tokens(prev))
            best_overlap = max(best_overlap, ov)
            if _negation_conflict(p, prev):
                conflict_hit = prev[:220]
        if conflict_hit:
            contradictions.append({
                "type": "vs_codex",
                "new": p[:220],
                "prior": conflict_hit,
                "note": "El hallazgo nuevo tensiona con conocimiento previo del códice.",
            })
        elif best_overlap < 3:
            novel.append(p[:220])

    if novel:
        strengths.append(f"{len(novel)} fragmentos parecen novedosos respecto al códice previo.")
    if contradictions:
        issues.append(f"{len(contradictions)} posible(s) contradicción(es) a revisar.")

    actions = []
    codex_result = {}
    if codex is not None and topic and (points or summary):
        try:
            # 1) Comprimir informe (reescribe/refuerza representación del tema)
            blob = summary or "\n".join(points)
            if contradictions:
                # marca explícita de conflicto en el texto ingerido
                blob += "\n\nCONFLICTOS DETECTADOS:\n"
                for c in contradictions[:5]:
                    blob += f"- {c.get('note')}: {c.get('new') or c.get('a')}\n"
                actions.append("marcado_conflictos_en_códice")
            codex_result = codex.compress_text(blob[:6000], topic=topic[:80]) or {}
            actions.append("compress_text")
            # 2) Guardar cristales de contradicción para no perder la tensión
            for c in contradictions[:4]:
                try:
                    codex.store_crystal(
                        f"CONTRADICCIÓN ({c.get('type')}): {c.get('note')} | NUEVO: {c.get('new') or c.get('a')} | PREVIO: {c.get('prior') or c.get('b')}",
                        kind="critique",
                        meta={"topic": topic[:80], "type": c.get("type")},
                    )
                except Exception:
                    pass
            if contradictions:
                actions.append("store_contradiction_crystals")
            try:
                frac = codex.maybe_fractal_after_ingest(topic[:80])
                if frac:
                    codex_result["fractal"] = frac
                    actions.append("fractal_cycle")
            except Exception:
                pass
        except Exception as e:
            codex_result = {"error": str(e)[:160]}
            actions.append("codex_error")

    verdict = "solido"
    if contradictions and len(sources) >= 2:
        verdict = "revisable"
    if not sources or len(points) < 2:
        verdict = "debil"
    if contradictions and not sources:
        verdict = "debil"

    return {
        "ok": True,
        "topic": topic,
        "verdict": verdict,
        "strengths": strengths,
        "issues": issues,
        "contradictions": contradictions,
        "novel_fragments": novel[:8],
        "actions": actions,
        "codex": codex_result,
        "critiqued_at": _now(),
    }
