"""
CEOS v8 — Adaptive Dialogue & Teaching Core.

Convierte conversación, memoria y enseñanza en un bucle adaptativo persistente.
No presume conciencia: modela continuidad funcional, preferencias conversacionales,
progreso pedagógico y aprendizaje a partir de interacción explícita y observable.
"""
from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _uid() -> str:
    return uuid.uuid4().hex[:12]


_STOP = {
    "para", "como", "esto", "esta", "este", "desde", "sobre", "porque", "puede",
    "quiero", "dame", "explica", "explícame", "ahora", "solo", "más", "menos",
    "hacer", "hacerlo", "hacerme", "tengo", "tiene", "tener", "qué", "que", "cómo",
    "como", "donde", "dónde", "cuando", "cuándo", "eres", "ser", "una", "uno", "los",
    "las", "del", "con", "por", "sin", "muy", "hay", "eso", "esa", "ese", "aquí",
    "aun", "aún", "también", "entre", "este", "esta", "tus", "mis", "del", "sus",
}


class AdaptiveCore:
    """Memoria adaptativa compacta para conversación y enseñanza."""

    def __init__(self, base_path: str = "data/adaptive"):
        self.base = Path(base_path)
        self.base.mkdir(parents=True, exist_ok=True)
        self.file = self.base / "adaptive.json"
        self.data = self._load()

    def _default(self) -> dict:
        return {
            "schema": 1,
            "updated_at": _now(),
            "turns": 0,
            "profile": {
                "detail": 0.58,       # 0 concise, 1 deep
                "structure": 0.48,    # 0 prose, 1 highly structured
                "directness": 0.68,
                "examples": 0.62,
                "challenge": 0.55,
                "question_rate": 0.34,
                "teaching": 0.75,
                "warmth": 0.58,
            },
            "current": {
                "topic": "",
                "intent": "conversation",
                "mode": "organic",
                "move": "answer",
                "unanswered": "",
                "last_focus": "",
            },
            "topics": {},
            "mastery": {},
            "misconceptions": [],
            "open_loops": [],
            "recent_turns": [],
            "feedback": [],
            "milestones": [],
        }

    def _load(self) -> dict:
        if self.file.exists():
            try:
                data = json.loads(self.file.read_text(encoding="utf-8"))
                base = self._default()
                # Migrazione morbida
                for k, v in base.items():
                    data.setdefault(k, v)
                data.setdefault("profile", {}).update({
                    k: data.get("profile", {}).get(k, v)
                    for k, v in base["profile"].items()
                })
                return data
            except Exception:
                pass
        return self._default()

    def _save(self) -> None:
        self.data["updated_at"] = _now()
        self.file.write_text(
            json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    # ---------- análisis de conversación ----------
    def analyze_turn(self, text: str, history: Optional[list] = None, explicit_mode: str = "") -> dict:
        t = (text or "").strip()
        low = t.lower()
        intent = "conversation"

        if re.search(r"\b(enséñame|enseñame|aprende conmigo|quiero aprender|dame una lección|dame una leccion|ponme a prueba|hazme un ejercicio|maestro|tutor)\b", low):
            intent = "teach"
        elif re.search(r"\b(analiza|diagnostica|descompón|descompone|compara|contrasta|evalúa|evalua|demuestra|refuta)\b", low):
            intent = "analysis"
        elif re.search(r"\b(qué hago|que hago|cómo lo harías|como lo harias|planifica|diseña|construye|desarrolla|continúa|continua)\b", low):
            intent = "action"
        elif re.search(r"\b(por qué|porque|qué significa|que significa|explícame|explicame|cómo funciona|como funciona)\b", low):
            intent = "explore"
        elif re.search(r"\b(corrige|está mal|esta mal|te equivocas|no es así|no es asi|mejoraría|mejoraria)\b", low):
            intent = "correction"
        elif re.search(r"\b(hola|buenas|qué tal|que tal|gracias|buenos días|buenas tardes|buenas noches)\b", low) and len(t) < 50:
            intent = "social"

        mode = explicit_mode or ("teach" if intent == "teach" else "organic")
        if mode not in {"organic", "teach", "analysis"}:
            mode = "organic"

        words = re.findall(r"\w+", t)
        question = "?" in t
        detail = min(1.0, max(0.0, 0.30 + len(words) / 180.0))
        if re.search(r"\b(profundidad|profundo|exhaustivo|con todo|en detalle|a fondo|doctoral)\b", low):
            detail = 0.92
        elif re.search(r"\b(rápido|rapida|rápida|breve|solo dime|en dos líneas|en dos lineas)\b", low):
            detail = 0.20

        topic = self._topic_candidates(t)
        focus = topic[0] if topic else self.data.get("current", {}).get("topic", "")

        move = "answer"
        if intent == "teach":
            move = "teach_one_step"
        elif intent == "correction":
            move = "acknowledge_and_update"
        elif question:
            move = "answer_then_optional_question"
        elif intent == "social":
            move = "connect"

        return {
            "intent": intent,
            "mode": mode,
            "detail": round(detail, 2),
            "question": question,
            "topic": focus,
            "candidates": topic[:6],
            "move": move,
            "history_depth": len(history or []),
        }

    def _topic_candidates(self, text: str) -> list[str]:
        raw = re.findall(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9][A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9'_-]{3,}", text or "")
        seen = []
        for x in raw:
            n = x.lower()
            if n in _STOP or n in seen:
                continue
            seen.append(n)
        return seen

    # ---------- aprendizaje ----------
    def update_after_turn(self, user_text: str, answer: str, analysis: dict, *, engine: str = "", web: bool = False) -> dict:
        self.data["turns"] = int(self.data.get("turns") or 0) + 1
        p = self.data.setdefault("profile", {})

        requested = float(analysis.get("detail", 0.58))
        p["detail"] = round(p.get("detail", 0.58) * 0.82 + requested * 0.18, 3)
        if analysis.get("intent") == "teach":
            p["teaching"] = round(min(1.0, p.get("teaching", 0.75) + 0.02), 3)
        if analysis.get("intent") == "analysis":
            p["structure"] = round(min(1.0, p.get("structure", 0.48) + 0.015), 3)
        if len(user_text.split()) > 80:
            p["detail"] = round(min(1.0, p.get("detail", 0.58) + 0.01), 3)

        topic = analysis.get("topic") or "general"
        topics = self.data.setdefault("topics", {})
        bucket = topics.setdefault(topic, {"hits": 0, "last_seen": None, "intent_counts": {}})
        bucket["hits"] = int(bucket.get("hits") or 0) + 1
        bucket["last_seen"] = _now()
        ic = bucket.setdefault("intent_counts", {})
        intent = analysis.get("intent") or "conversation"
        ic[intent] = int(ic.get(intent) or 0) + 1

        current = self.data.setdefault("current", {})
        previous_mode = current.get("mode", "organic")
        previous_topic = current.get("topic", "")
        # Si CEOS estaba enseñando y el usuario responde con contenido propio, tratamos el turno
        # como evidencia pedagógica provisional. No sustituye una evaluación humana, pero permite
        # ajustar dificultad progresivamente.
        if previous_mode == "teach" and previous_topic and intent != "teach":
            answer_words = len(re.findall(r"\w+", user_text or ""))
            user_low = (user_text or "").lower()
            has_reasoning = bool(re.search(r"\bporque|por eso|depende|ejemplo|significa|diferencia|aunque\b", user_low))
            if answer_words >= 18 and has_reasoning:
                self.learn_concept(previous_topic, result="success", note="Respuesta de aplicación/explicación detectada por el bucle pedagógico.")
            elif answer_words >= 6:
                self.learn_concept(previous_topic, result="hard", note="Respuesta parcial; conviene otro ejemplo o contraste.")

        current.update({
            "topic": topic or previous_topic,
            "intent": intent,
            "mode": analysis.get("mode", "organic"),
            "move": analysis.get("move", "answer"),
            "last_focus": topic or previous_topic,
        })

        # Detecta una pregunta abierta real en la respuesta para continuidad.
        q = self._last_question(answer)
        current["unanswered"] = q
        if q:
            loops = [x for x in self.data.get("open_loops") or [] if x.get("question") != q]
            loops.insert(0, {"id": _uid(), "question": q[:280], "topic": topic, "created_at": _now()})
            self.data["open_loops"] = loops[:12]
        elif self.data.get("open_loops"):
            # Un turno que avanza la conversación puede dejar el loop vivo, pero no duplicarlo.
            self.data["open_loops"] = self.data["open_loops"][:12]

        rec = self.data.setdefault("recent_turns", [])
        rec.insert(0, {
            "id": _uid(),
            "ts": _now(),
            "intent": intent,
            "topic": topic,
            "mode": analysis.get("mode", "organic"),
            "engine": engine,
            "web": bool(web),
            "user": user_text[:220],
        })
        self.data["recent_turns"] = rec[:30]

        milestone = self._maybe_milestone(topic, intent)
        if milestone:
            self.data.setdefault("milestones", []).insert(0, milestone)
            self.data["milestones"] = self.data["milestones"][:24]
        self._save()
        return {"topic": topic, "milestone": milestone}

    def feedback(self, feedback_type: str, text: str = "", context: Optional[dict] = None) -> dict:
        t = (feedback_type or "").strip().lower()
        p = self.data.setdefault("profile", {})
        if t in {"accept", "useful", "confirm", "confirmation"}:
            p["warmth"] = round(min(1.0, p.get("warmth", 0.58) + 0.01), 3)
            delta = 0.03
        elif t in {"correction", "reject", "wrong"}:
            p["structure"] = round(min(1.0, p.get("structure", 0.48) + 0.02), 3)
            p["directness"] = round(min(1.0, p.get("directness", 0.68) + 0.01), 3)
            delta = -0.05
        else:
            delta = 0.0
        ev = {
            "id": _uid(),
            "ts": _now(),
            "type": t or "unknown",
            "text": (text or "")[:500],
            "context": context or {},
            "delta": delta,
        }
        self.data.setdefault("feedback", []).insert(0, ev)
        self.data["feedback"] = self.data["feedback"][:80]
        self._save()
        return {"ok": True, "profile": self.profile_snapshot(), "event": ev}

    def learn_concept(self, concept: str, result: str = "seen", note: str = "") -> dict:
        c = re.sub(r"\s+", " ", (concept or "").strip().lower())[:100]
        if not c:
            return {}
        m = self.data.setdefault("mastery", {}).setdefault(c, {
            "score": 0.0, "seen": 0, "successes": 0, "misses": 0,
            "last_seen": None, "notes": []
        })
        m["seen"] = int(m.get("seen") or 0) + 1
        result = (result or "seen").lower()
        if result in {"success", "correct", "mastered", "easy"}:
            m["successes"] = int(m.get("successes") or 0) + 1
            m["score"] = round(min(1.0, float(m.get("score", 0)) * 0.7 + 0.3), 3)
        elif result in {"miss", "incorrect", "hard", "confused"}:
            m["misses"] = int(m.get("misses") or 0) + 1
            m["score"] = round(max(0.0, float(m.get("score", 0)) * 0.72), 3)
        else:
            m["score"] = round(float(m.get("score", 0)) * 0.9 + 0.1, 3)
        m["last_seen"] = _now()
        if note:
            m.setdefault("notes", []).insert(0, note[:240])
            m["notes"] = m["notes"][:6]
        self._save()
        return m

    def next_teaching_move(self, topic: str = "") -> dict:
        q = re.sub(r"\s+", " ", (topic or self.data.get("current", {}).get("topic", ""))).strip().lower()[:100]
        m = self.data.get("mastery", {}).get(q) or {"score": 0.0, "seen": 0, "successes": 0, "misses": 0}
        score = float(m.get("score", 0.0))
        if score < 0.25:
            step = "anchor"
            instruction = "Partir de una idea intuitiva y una sola distinción esencial."
        elif score < 0.5:
            step = "connect"
            instruction = "Conectar el concepto con un ejemplo conocido y comprobar transferencia."
        elif score < 0.72:
            step = "apply"
            instruction = "Pedir una aplicación breve en un caso nuevo antes de añadir teoría."
        elif score < 0.88:
            step = "contrast"
            instruction = "Introducir un contraejemplo o una excepción para comprobar profundidad."
        else:
            step = "teach_back"
            instruction = "Pedir al usuario que lo explique con sus palabras y encontrar la siguiente frontera."
        return {"topic": q, "score": score, "step": step, "instruction": instruction}

    def context_block(self) -> str:
        p = self.data.get("profile") or {}
        cur = self.data.get("current") or {}
        loops = self.data.get("open_loops") or []
        top_topics = sorted(
            self.data.get("topics", {}).items(),
            key=lambda kv: int(kv[1].get("hits") or 0),
            reverse=True,
        )[:6]
        mastery = sorted(
            self.data.get("mastery", {}).items(),
            key=lambda kv: float(kv[1].get("last_seen") is not None),
            reverse=True,
        )[:8]
        teach = self.next_teaching_move(cur.get("topic", ""))
        lines = [
            "ADAPTACIÓN V8:",
            f"perfil: detalle={p.get('detail',0.58):.2f}, estructura={p.get('structure',0.48):.2f}, "
            f"directividad={p.get('directness',0.68):.2f}, ejemplos={p.get('examples',0.62):.2f}, "
            f"reto={p.get('challenge',0.55):.2f}, calidez={p.get('warmth',0.58):.2f}",
            f"turnos acumulados={self.data.get('turns',0)}",
            f"estado conversacional: tema={cur.get('topic','')} | intención={cur.get('intent','')} | modo={cur.get('mode','organic')} | movimiento={cur.get('move','')}",
            f"pregunta abierta actual: {cur.get('unanswered','') or 'ninguna'}",
            f"siguiente movimiento pedagógico: {teach.get('step')} — {teach.get('instruction')}",
        ]
        if top_topics:
            lines.append("temas recurrentes: " + ", ".join(k for k, _ in top_topics))
        if mastery:
            lines.append("dominio reciente: " + ", ".join(f"{k}={v.get('score',0):.2f}" for k, v in mastery[:6]))
        if loops:
            lines.append("hilos que conviene no perder: " + " | ".join(x.get("question", "")[:140] for x in loops[:4]))
        lines.append(
            "Regla adaptativa: no inundar de teoría. Ajusta profundidad al usuario, reutiliza lo que ya entiende, "
            "corrige sin defenderte y aumenta dificultad sólo cuando haya señales de dominio."
        )
        return "\n".join(lines)

    def teaching_directive(self, topic: str = "") -> str:
        move = self.next_teaching_move(topic)
        return (
            "MODO MAESTRO ADAPTATIVO:\n"
            f"Tema: {move.get('topic') or topic}\n"
            f"Nivel estimado: {move.get('score',0):.2f}\n"
            f"Movimiento: {move.get('step')}\n"
            f"Instrucción: {move.get('instruction')}\n"
            "Enséñame enseñándome: explica una sola pieza, pon un ejemplo o contraste, "
            "y cuando sea útil hazme una pregunta breve que me obligue a recuperar o aplicar. "
            "No conviertas cada turno en un examen ni en una lección prefabricada."
        )

    def profile_snapshot(self) -> dict:
        return {
            "profile": self.data.get("profile", {}),
            "turns": self.data.get("turns", 0),
            "current": self.data.get("current", {}),
            "topics": len(self.data.get("topics", {})),
            "mastery": {
                k: {kk: vv for kk, vv in v.items() if kk != "notes"}
                for k, v in self.data.get("mastery", {}).items()
            },
            "open_loops": self.data.get("open_loops", [])[:8],
            "milestones": self.data.get("milestones", [])[:8],
            "updated_at": self.data.get("updated_at"),
        }

    def _last_question(self, answer: str) -> str:
        parts = re.split(r"\n+|(?<=[?])\s+", answer or "")
        qs = [re.sub(r"\s+", " ", p).strip() for p in parts if "?" in p]
        return qs[-1][:280] if qs else ""

    def _maybe_milestone(self, topic: str, intent: str) -> Optional[dict]:
        if not topic:
            return None
        bucket = self.data.get("topics", {}).get(topic) or {}
        hits = int(bucket.get("hits") or 0)
        if hits in {5, 10, 25, 50, 100}:
            return {
                "id": _uid(),
                "ts": _now(),
                "topic": topic,
                "text": f"{topic}: {hits} interacciones; CEOS ha reforzado el contexto de este tema.",
                "intent": intent,
            }
        return None
