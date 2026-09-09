"""
Identidad-desde-memoria.

Tesis operativa de CEOS:
  La memoria no es un anexo de la identidad; es su soporte.
  Quien somos (motor y usuario) se infiere y se actualiza
  a partir de lo recordado: reservorio, códice, hechos, diálogo.

No afirma conciencia: afirma continuidad funcional con contenido.
"""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Any, Optional


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def compose_identity(
    *,
    identity=None,
    library=None,
    codex=None,
    long_memory=None,
    user=None,
    evolution_scale=None,
) -> dict:
    """Construye un retrato de identidad anclado en memoria actual."""
    out: dict[str, Any] = {
        "at": _now(),
        "thesis": (
            "La memoria determina en gran parte quiénes somos: "
            "sin recuerdo no hay continuidad ni enseñanza posible."
        ),
        "motor": {},
        "usuario": {},
        "memoria": {},
        "implicaciones_ensenanza": [],
    }

    # Motor (constitución + estado)
    try:
        who = identity.who_am_i() if identity is not None else {}
    except Exception:
        who = {}
    out["motor"]["name"] = who.get("name") or "CEOS"
    out["motor"]["mission"] = who.get("mission") or ""
    out["motor"]["codename"] = who.get("codename") or ""

    # Usuario
    name = nivel = ""
    try:
        if user is not None:
            u = user.get() or {}
            name = (u.get("display_name") or u.get("name") or "").strip()
            nivel = u.get("nivel") or ""
    except Exception:
        pass
    out["usuario"]["nombre"] = name or "(aún sin nombre en memoria)"
    out["usuario"]["nivel"] = nivel or "inicial"

    # Reservorio
    docs = chars = 0
    titles = []
    authors = set()
    try:
        if library is not None:
            st = library.stats() if hasattr(library, "stats") else {}
            docs = int(st.get("docs") or 0)
            chars = int(st.get("chars") or 0)
            for d in (library.list_docs() or [])[-12:]:
                t = d.get("title") or d.get("source_name")
                if t:
                    titles.append(t)
                a = d.get("author")
                if a:
                    authors.add(a)
    except Exception:
        pass
    out["memoria"]["reservorio_docs"] = docs
    out["memoria"]["reservorio_chars"] = chars
    out["memoria"]["titulos_recientes"] = titles[:8]
    out["memoria"]["autores"] = sorted(authors)[:8]

    # Códice
    crystals = maps = gen = 0
    try:
        if codex is not None:
            if hasattr(codex, "stats"):
                cs = codex.stats() or {}
                crystals = int(cs.get("crystals") or 0)
                maps = int(cs.get("maps") or 0)
            if hasattr(codex, "fractal_state"):
                fs = codex.fractal_state() or {}
                gen = int(fs.get("generation") or fs.get("fractal_generation") or 0)
    except Exception:
        pass
    out["memoria"]["codex_cristales"] = crystals
    out["memoria"]["codex_mapas"] = maps
    out["memoria"]["fractal_generacion"] = gen

    # Hechos / temas largos
    facts_n = topics_n = 0
    fact_samples = []
    try:
        if long_memory is not None:
            if hasattr(long_memory, "stats"):
                s = long_memory.stats() or {}
                facts_n = int(s.get("facts") or s.get("n_facts") or 0)
                topics_n = int(s.get("topics") or s.get("n_topics") or 0)
            block = long_memory.context_block("identidad memoria", limit=5) if hasattr(long_memory, "context_block") else ""
            if block:
                fact_samples = [ln.strip() for ln in block.splitlines() if ln.strip()][:5]
    except Exception:
        pass
    out["memoria"]["hechos"] = facts_n
    out["memoria"]["temas"] = topics_n
    out["memoria"]["muestras"] = fact_samples

    # Escala
    try:
        if evolution_scale is not None and hasattr(evolution_scale, "compute"):
            rep = evolution_scale.compute(
                library=library, codex=codex, evolve_engine=None, long_memory=long_memory
            )
            out["memoria"]["escala"] = {
                "score": rep.get("score"),
                "level": (rep.get("level") or {}).get("name"),
            }
    except Exception:
        pass

    # Narración de identidad (quiénes somos *ahora*)
    motor_bits = []
    if docs:
        motor_bits.append(f"custodio de {docs} documento(s) en el reservorio")
    if crystals:
        motor_bits.append(f"códice con {crystals} cristales y {maps} mapas")
    if not motor_bits:
        motor_bits.append("semilla: memoria aún escasa; identidad en formación")
    out["motor"]["quien_es_ahora"] = (
        f"{out['motor']['name']} es, en este momento, " + "; ".join(motor_bits) + "."
    )

    if name and docs:
        out["usuario"]["quien_es_ahora"] = (
            f"{name} aparece en la memoria de CEOS como interlocutor"
            + (f" y autor vinculado a: {', '.join(list(authors)[:3])}" if authors else "")
            + (f". Textos recientes en memoria: {titles[0]}" if titles else ".")
        )
    elif name:
        out["usuario"]["quien_es_ahora"] = (
            f"{name} está en el perfil, pero el reservorio aún no sostiene del todo su obra o su historia."
        )
    else:
        out["usuario"]["quien_es_ahora"] = (
            "El usuario aún no tiene un nombre estable en memoria; la identidad compartida es incipiente."
        )

    # Enseñanza: sin memoria no hay a quién enseñar ni desde dónde
    out["implicaciones_ensenanza"] = [
        "Enseñar es reorganizar memoria ajena y propia: sin anclaje, solo hay exposición de datos.",
        "Cada documento en el reservorio amplía quién puede ser CEOS como maestro de ese dominio.",
        "Corregir (marcar falso) es un acto de identidad: decide qué dejamos de ser.",
        "La escala G0–G6 no mide talento abstracto; mide espesor de memoria operable.",
    ]

    out["narrativa"] = (
        out["motor"]["quien_es_ahora"]
        + " "
        + out["usuario"]["quien_es_ahora"]
        + " La enseñanza en CEOS parte de esta memoria compartida, no de un manual genérico."
    )
    return out


def teaching_seed_from_identity(portrait: dict) -> str:
    """Texto breve para abrir un acto de enseñanza anclado en identidad-memoria."""
    lines = [
        "Punto de partida (identidad-memoria):",
        portrait.get("narrativa") or "",
        "",
        "Principio didáctico:",
        "No enseñamos «en abstracto»: enseñamos desde lo que ya somos capaces de recordar juntos.",
    ]
    titles = (portrait.get("memoria") or {}).get("titulos_recientes") or []
    if titles:
        lines.append("Material vivo disponible: " + "; ".join(titles[:5]))
    for imp in (portrait.get("implicaciones_ensenanza") or [])[:2]:
        lines.append("· " + imp)
    return "\n".join(lines)
