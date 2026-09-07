"""
Escala de evolución del aprendizaje de CEOS.

Métricas observables y persistentes (no "conciencia"):
- volumen de corpus (docs, chars, chunks)
- códice (cristales, mapas, generación fractal)
- actividad de aprendizaje (estudios, evoluciones, investigaciones)
- correcciones (retractaciones)
- política interna de evolución

Cada snapshot se guarda con timestamp para comparar periodos.
"""
from __future__ import annotations
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Optional


def _now():
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _parse_iso(s: str) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None


# Niveles legibles (escala 0–100 → nombre)
LEVELS = [
    (0, 10, "G0 · Semilla", "Poco corpus; respuestas casi solo de plantilla o web puntual."),
    (10, 25, "G1 · Germinal", "Primeros documentos y fragmentos; memoria mínima."),
    (25, 40, "G2 · Aprendiz", "Reservorio usable; relecturas y algo de códice."),
    (40, 55, "G3 · Operativo", "Uso regular de biblioteca + investigación + críticas."),
    (55, 70, "G4 · Integrado", "Códice denso, varias lecturas y correcciones humanas."),
    (70, 85, "G5 · Maduro", "Historial rico; políticas de evolución activas; re-cifrados."),
    (85, 100, "G6 · Expansivo", "Alto volumen y diversidad; evolución continua documentada."),
]


def level_for(score: float) -> dict:
    score = max(0, min(100, float(score)))
    for a, b, name, desc in LEVELS:
        if a <= score < b or (b == 100 and score <= 100 and score >= a):
            return {"score": round(score, 1), "code": name.split("·")[0].strip(), "name": name, "description": desc}
    return {"score": round(score, 1), "code": "G0", "name": LEVELS[0][2], "description": LEVELS[0][3]}


class EvolutionScale:
    def __init__(self, base_path: str = "data/evolve"):
        self.base = Path(base_path)
        self.base.mkdir(parents=True, exist_ok=True)
        self.snap_file = self.base / "scale_snapshots.json"
        if not self.snap_file.exists():
            self.snap_file.write_text("[]", encoding="utf-8")

    def _load(self) -> list:
        try:
            return json.loads(self.snap_file.read_text(encoding="utf-8"))
        except Exception:
            return []

    def _save(self, data: list):
        self.snap_file.write_text(json.dumps(data[-500:], ensure_ascii=False, indent=2), encoding="utf-8")

    def compute(
        self,
        *,
        library=None,
        codex=None,
        evolve_engine=None,
        long_memory=None,
    ) -> dict:
        docs = chars = chunks = media = 0
        if library is not None:
            try:
                st = library.stats()
                docs = int(st.get("docs") or 0)
                chars = int(st.get("chars") or 0)
                chunks = int(st.get("chunks") or 0)
                media = int(st.get("media") or 0)
            except Exception:
                pass

        crystals = maps = gen = 0
        if codex is not None:
            try:
                if hasattr(codex, "stats"):
                    cs = codex.stats() or {}
                    crystals = int(cs.get("crystals") or 0)
                    maps = int(cs.get("maps") or 0)
                else:
                    crystals = len(codex._load(codex.crystals_file))
                    maps = len(codex._load(codex.maps_file))
                if hasattr(codex, "fractal_state"):
                    fs = codex.fractal_state() or {}
                    gen = int(fs.get("generation") or fs.get("fractal_generation") or 0)
            except Exception:
                pass

        runs = total_frags = 0
        policy = {}
        history = []
        if evolve_engine is not None:
            try:
                st = evolve_engine.state() or {}
                runs = int(st.get("runs") or 0)
                total_frags = int(st.get("total_fragments") or 0)
                policy = st.get("policy") or {}
                history = evolve_engine.history(50) or []
            except Exception:
                pass

        retracts = 0
        if codex is not None:
            try:
                crystals_data = codex._load(codex.crystals_file)
                for c in crystals_data.values():
                    if (c.get("kind") in ("retracted", "falsehood")) or (c.get("meta") or {}).get("retracted"):
                        retracts += 1
            except Exception:
                pass

        topics_mem = 0
        if long_memory is not None:
            try:
                s = long_memory.stats() if hasattr(long_memory, "stats") else {}
                topics_mem = int(s.get("topics") or s.get("facts") or 0)
            except Exception:
                pass

        # Score compuesto 0–100 (ponderado, acotado)
        score = 0.0
        score += min(20.0, docs * 1.5)             # hasta 20: documentos
        score += min(15.0, chars / 20000.0 * 15)  # hasta 15: volumen texto
        score += min(15.0, chunks / 100.0 * 15)   # hasta 15: trozos
        score += min(15.0, crystals / 50.0 * 15)  # hasta 15: códice
        score += min(10.0, maps * 1.2)              # hasta 10: mapas temáticos
        score += min(10.0, runs * 1.5)              # hasta 10: ciclos evolución
        score += min(5.0, gen * 1.5)                # hasta 5: generación fractal
        score += min(5.0, retracts * 0.8)           # hasta 5: correcciones humanas
        score += min(5.0, topics_mem * 0.3)         # hasta 5: memoria larga
        score = max(0.0, min(100.0, score))

        level = level_for(score)
        # Poliedro de memoria: cada faceta es un modo de recibir/reflejar
        faces = [
            {"face": "reservorio", "value": docs, "role": "recibe textos y medios"},
            {"face": "cristales", "value": crystals, "role": "refleja fragmentos comprimidos"},
            {"face": "mapas", "value": maps, "role": "orienta acceso por tema"},
            {"face": "fractal", "value": gen, "role": "re-cifra y reorganiza con el tiempo"},
            {"face": "ciclos", "value": runs, "role": "tareas autónomas acumuladas"},
            {"face": "correcciones", "value": retracts, "role": "recibe juicio humano y se ajusta"},
        ]
        polyhedron = {
            "metaphor": (
                "La memoria actúa como un poliedro: cada interacción ilumina o desgasta una faceta. "
                "Los cristales son caras locales de contenido; los mapas son aristas que las conectan; "
                "el re-cifrado fractal es el giro del sólido en el tiempo."
            ),
            "faces": faces,
            "dominant_face": max(faces, key=lambda f: f["value"])["face"] if any(f["value"] for f in faces) else "reservorio",
        }
        return {
            "ok": True,
            "at": _iso(_now()),
            "score": level["score"],
            "level": level,
            "polyhedron": polyhedron,
            "metrics": {
                "library_docs": docs,
                "library_chars": chars,
                "library_chunks": chunks,
                "library_media": media,
                "codex_crystals": crystals,
                "codex_maps": maps,
                "fractal_generation": gen,
                "evolve_runs": runs,
                "evolve_fragments": total_frags,
                "retracts_falsehoods": retracts,
                "long_memory_signals": topics_mem,
                "policy": policy,
            },
            "recent_evolve_tasks": [
                {"task": h.get("task"), "at": h.get("id"), "frags": h.get("fragments_integrated")}
                for h in history[-8:]
            ],
        }

    def snapshot(self, report: dict) -> dict:
        snaps = self._load()
        entry = {
            "at": report.get("at") or _iso(_now()),
            "score": report.get("score"),
            "level": (report.get("level") or {}).get("name"),
            "metrics": report.get("metrics") or {},
        }
        snaps.append(entry)
        self._save(snaps)
        return entry

    def history(
        self,
        *,
        since: Optional[str] = None,
        until: Optional[str] = None,
        limit: int = 100,
    ) -> dict:
        snaps = self._load()
        since_dt = _parse_iso(since) if since else None
        until_dt = _parse_iso(until) if until else None
        out = []
        for s in snaps:
            dt = _parse_iso(s.get("at") or "")
            if since_dt and dt and dt < since_dt:
                continue
            if until_dt and dt and dt > until_dt:
                continue
            out.append(s)
        out = out[-limit:]
        # delta
        delta = None
        if len(out) >= 2:
            a, b = out[0], out[-1]
            delta = {
                "score_from": a.get("score"),
                "score_to": b.get("score"),
                "score_delta": round(float(b.get("score") or 0) - float(a.get("score") or 0), 1),
                "level_from": a.get("level"),
                "level_to": b.get("level"),
            }
        all_snaps = self._load()
        origin = all_snaps[0] if all_snaps else None
        current = all_snaps[-1] if all_snaps else None
        origin_to_now = None
        if origin and current:
            origin_to_now = {
                "score_from": origin.get("score"),
                "score_to": current.get("score"),
                "score_delta": round(float(current.get("score") or 0) - float(origin.get("score") or 0), 1),
                "level_from": origin.get("level"),
                "level_to": current.get("level"),
                "from_at": origin.get("at"),
                "to_at": current.get("at"),
            }
        return {
            "ok": True,
            "count": len(out),
            "snapshots": out,
            "delta": delta,
            "origin": origin,
            "current": current,
            "origin_to_now": origin_to_now,
            "levels_legend": [
                {"range": f"{a}-{b}", "name": n, "description": d}
                for a, b, n, d in LEVELS
            ],
        }

    def measure_and_record(self, **deps) -> dict:
        report = self.compute(**deps)
        self.snapshot(report)
        hist = self.history()
        report["origin"] = hist.get("origin")
        report["origin_to_now"] = hist.get("origin_to_now")
        return report
