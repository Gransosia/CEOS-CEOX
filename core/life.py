"""
CEOS Living Core — continuidad funcional del sistema.

Esto no afirma conciencia. Implementa algo más concreto y comprobable:
- estado persistente entre procesos y sesiones
- pulso/heartbeat
- atención y foco actual
- hilos abiertos (cosas que siguen vivas en la conversación)
- registro de influencia en ambos sentidos
- aprendizaje a partir de correcciones y confirmaciones
- reflexión local sin necesidad de LLM ni web
- política de autonomía acotada: actuar localmente, pedir permiso fuera

La idea es que CEOS no sea solo una respuesta por turno, sino un proceso
continuo cuyo estado cambia por lo que recibe, hace y aprende.
"""
from __future__ import annotations

import json
import re
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


STOPWORDS = {
    "para", "como", "desde", "entre", "sobre", "esta", "este", "esto", "estas", "estos",
    "porque", "cuando", "donde", "quien", "quién", "cual", "cuál", "que", "qué", "del", "las",
    "los", "una", "uno", "unos", "unas", "por", "con", "sin", "muy", "más", "mas", "solo",
    "sólo", "también", "tambien", "tiene", "tienen", "ser", "soy", "eres", "es", "hay", "han",
    "hemos", "quiero", "quieres", "puedo", "puedes", "debo", "debería", "ahora", "aquí", "aqui",
    "sobre", "hacia", "hasta", "cada", "otro", "otra", "otros", "otras", "todo", "toda", "todos",
    "todas", "este", "esa", "ese", "mi", "mis", "tu", "tus", "su", "sus", "yo", "tú", "el", "la",
    "y", "o", "u", "e", "a", "en", "un", "de", "lo", "me", "te", "se", "le", "les", "ya", "si",
    "sí", "no", "bien", "vale", "ok", "hola", "buenas", "gracias", "pero", "cómo", "como", "hacer",
    "haz", "dame", "decime", "dime", "explica", "explícame", "explícame", "ahora", "vamos", "hayamos",
}

INTENT_PATTERNS = [
    ("remember", re.compile(r"\b(recuerda|recuerde|no olvides|no olvide|ten en cuenta|guarda|guarde|memoriza|memorice|anota|anote)\b", re.I)),
    ("research", re.compile(r"\b(investiga|investigue|investigar|busca|buscar|busque|busca en internet|buscar en internet|navega|navegar|fuentes|contrasta|contrastar|verifica|verificar)\b", re.I)),
    ("analyze", re.compile(r"\b(analiza|analizar|diagnostica|diagnóstico|diagnostica|evalúa|evalua|compara)\b", re.I)),
    ("learn", re.compile(r"\b(aprende|aprenda|estudia|estudie|enseña|enseñe|lección|leccion|explica|explícame|explicame|desarrolla|desarrolle|profundiza|profundice)\b", re.I)),
    ("create", re.compile(r"\b(crea|cree|diseña|diseñe|construye|construya|elabora|elabore|programa|programe|mejora|mejore)\b", re.I)),
    ("correct", re.compile(r"(?:^\s*no[,.:;]?\s)|\b(corrección|correccion|te equivocas|eso no|corrige|corrijas|corrígeme|corrigeme|está mal|esta mal|error|falso|no es así|no es asi)\b", re.I)),
]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_ts(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None


class LivingCore:
    """Estado vital funcional, persistente y auditable de CEOS."""

    SCHEMA = 1

    def __init__(self, base_path: str = "data/life"):
        self.base = Path(base_path)
        self.base.mkdir(parents=True, exist_ok=True)
        self.state_file = self.base / "state.json"
        self.events_file = self.base / "events.jsonl"
        self.reflections_file = self.base / "reflections.json"
        self._lock = threading.RLock()
        self.state_data = self._load_state()
        self.reflections = self._load_json(self.reflections_file, [])
        self.boot()

    def _load_json(self, path: Path, default: Any) -> Any:
        if not path.exists():
            return default
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return default

    def _write_json_atomic(self, path: Path, data: Any):
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(path)

    def _load_state(self) -> dict:
        default = {
            "schema": self.SCHEMA,
            "created_at": _now(),
            "boot_count": 0,
            "started_at": None,
            "last_heartbeat": None,
            "last_activity": None,
            "status": "starting",
            "pulse": 0,
            "focus": {"label": None, "score": 0.0, "updated_at": None},
            "open_threads": [],
            "drives": {
                "learn": 0.60,
                "remember": 0.80,
                "verify": 0.85,
                "connect": 0.60,
                "create": 0.55,
                "clarify": 0.70,
            },
            "relationship": {
                "turns": 0,
                "corrections": 0,
                "confirmations": 0,
                "sessions_seen": 0,
                "session_ids": [],
                "shared_topics": [],
            },
            "learning": {
                "corrections": 0,
                "lessons": 0,
                "last_learning": None,
                "adaptation_notes": [],
            },
            "influence": {
                "offered": 0,
                "accepted": 0,
                "rejected": 0,
                "unknown": 0,
                "last": None,
                "history": [],
            },
            "agency": {
                "mode": "bounded_proactive",
                "local_actions": True,
                "web_without_request": False,
                "external_actions": "consent_required",
            },
            "last_event": None,
        }
        if self.state_file.exists():
            loaded = self._load_json(self.state_file, default)
            if isinstance(loaded, dict):
                # merge shallowly to survive future versions
                for k, v in default.items():
                    if k not in loaded:
                        loaded[k] = v
                return loaded
        return default

    def _save_state(self):
        self._write_json_atomic(self.state_file, self.state_data)

    def _event(self, kind: str, payload: Optional[dict] = None, source: str = "ceos") -> dict:
        evt = {
            "id": uuid.uuid4().hex[:16],
            "ts": _now(),
            "kind": kind,
            "source": source,
            "payload": payload or {},
        }
        with self.events_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(evt, ensure_ascii=False) + "\n")
        self.state_data["last_event"] = evt
        return evt

    def boot(self) -> dict:
        with self._lock:
            now = _now()
            self.state_data["boot_count"] = int(self.state_data.get("boot_count") or 0) + 1
            self.state_data["started_at"] = now
            self.state_data["last_heartbeat"] = now
            self.state_data["last_activity"] = now
            self.state_data["status"] = "awake"
            self.state_data["pulse"] = int(self.state_data.get("pulse") or 0) + 1
            self._event("boot", {"boot_count": self.state_data["boot_count"]}, source="system")
            self._save_state()
            return self.snapshot()

    def _topics(self, text: str, limit: int = 5) -> list[str]:
        words = re.findall(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]{4,}", (text or "").lower())
        freq: dict[str, int] = {}
        for w in words:
            if w in STOPWORDS:
                continue
            freq[w] = freq.get(w, 0) + 1
        return [w for w, _ in sorted(freq.items(), key=lambda kv: (-kv[1], -len(kv[0]), kv[0]))[:limit]]

    def _intent(self, text: str) -> str:
        for name, rx in INTENT_PATTERNS:
            if rx.search(text or ""):
                return name
        if "?" in (text or ""):
            return "question"
        return "conversation"

    def _set_focus(self, text: str, weight: float = 1.0):
        topics = self._topics(text, limit=3)
        label = " · ".join(topics[:3]) if topics else (text or "").strip()[:72]
        current = self.state_data.setdefault("focus", {})
        current_label = current.get("label")
        score = float(current.get("score") or 0.0) * 0.72 + weight
        if label:
            current["label"] = label
        current["score"] = min(10.0, score)
        current["updated_at"] = _now()
        if label:
            topics_store = self.state_data.setdefault("relationship", {}).setdefault("shared_topics", [])
            low = label.lower()
            topics_store[:] = [x for x in topics_store if str(x).lower() != low]
            topics_store.insert(0, label)
            del topics_store[12:]

    def _open_thread(self, text: str, session_id: Optional[str], intent: str):
        clean = re.sub(r"\s+", " ", (text or "").strip())[:240]
        if len(clean) < 12:
            return
        threads = self.state_data.setdefault("open_threads", [])
        words = self._topics(clean, limit=3)
        for th in threads:
            if th.get("text", "").lower() == clean.lower():
                th["updated_at"] = _now()
                th["hits"] = int(th.get("hits") or 0) + 1
                return
        threads.append({
            "id": uuid.uuid4().hex[:12],
            "text": clean,
            "topics": words,
            "intent": intent,
            "status": "open",
            "weight": 1.0,
            "created_at": _now(),
            "updated_at": _now(),
            "session_id": session_id,
        })
        if len(threads) > 30:
            threads.sort(key=lambda x: (x.get("weight") or 0, x.get("updated_at") or ""), reverse=True)
            del threads[30:]

    def _touch_thread(self, text: str, status: Optional[str] = None):
        words = set(self._topics(text, limit=5))
        if not words:
            return
        for th in self.state_data.get("open_threads") or []:
            overlap = words.intersection(set(th.get("topics") or []))
            if overlap:
                th["updated_at"] = _now()
                th["weight"] = min(5.0, float(th.get("weight") or 1.0) + 0.25 * len(overlap))
                if status:
                    th["status"] = status

    def observe_session(self, session_id: str, device_id: Optional[str] = None) -> dict:
        with self._lock:
            rel = self.state_data.setdefault("relationship", {})
            rel["sessions_seen"] = int(rel.get("sessions_seen") or 0) + 1
            self.state_data["last_activity"] = _now()
            self.state_data["status"] = "attending"
            evt = self._event("session_open", {"session_id": session_id, "device": device_id}, source="user")
            self._save_state()
            return {"event": evt, "state": self.snapshot()}

    def resolve_thread(self, thread_id: str) -> dict:
        with self._lock:
            for th in self.state_data.get("open_threads") or []:
                if th.get("id") == thread_id:
                    th["status"] = "resolved"
                    th["resolved_at"] = _now()
                    self._event("thread_resolved", {"thread_id": thread_id}, source="ceos")
                    self._save_state()
                    return {"ok": True, "thread": th, "state": self.snapshot()}
            return {"ok": False, "error": "hilo no encontrado"}

    def observe_user_turn(self, text: str, *, session_id: Optional[str] = None, device_id: Optional[str] = None) -> dict:
        with self._lock:
            intent = self._intent(text)
            self._set_focus(text, weight=1.4 if intent != "conversation" else 0.8)
            rel = self.state_data.setdefault("relationship", {})
            rel["turns"] = int(rel.get("turns") or 0) + 1
            if session_id:
                ids = rel.setdefault("session_ids", [])
                if session_id not in ids:
                    ids.insert(0, session_id)
                    rel["sessions_seen"] = int(rel.get("sessions_seen") or 0) + 1
                    del ids[100:]
            drives = self.state_data.setdefault("drives", {})
            if intent == "correct":
                rel["corrections"] = int(rel.get("corrections") or 0) + 1
                drives["verify"] = min(1.0, float(drives.get("verify", 0.8)) + 0.04)
                drives["clarify"] = min(1.0, float(drives.get("clarify", 0.7)) + 0.03)
                self._event("user_correction", {"text": (text or "")[:300]}, source="user")
                self.record_learning("correction", (text or "")[:300], persist_event=False)
            elif intent in {"research", "learn"}:
                drives["learn"] = min(1.0, float(drives.get("learn", 0.6)) + 0.05)
            elif intent == "remember":
                drives["remember"] = min(1.0, float(drives.get("remember", 0.8)) + 0.05)
            elif intent in {"question", "analyze"}:
                drives["clarify"] = min(1.0, float(drives.get("clarify", 0.7)) + 0.04)
            elif intent == "create":
                drives["create"] = min(1.0, float(drives.get("create", 0.55)) + 0.04)
            else:
                drives["connect"] = min(1.0, float(drives.get("connect", 0.6)) + 0.01)
            if intent in {"question", "analyze", "learn", "create", "research", "remember"}:
                self._open_thread(text, session_id, intent)
            self._touch_thread(text)
            self.state_data["last_activity"] = _now()
            self.state_data["last_heartbeat"] = _now()
            self.state_data["status"] = "attending"
            evt = self._event(
                "user_turn",
                {"text": (text or "")[:500], "intent": intent, "topics": self._topics(text), "device": device_id},
                source="user",
            )
            self._save_state()
            return {"intent": intent, "topics": self._topics(text), "event": evt, "state": self.snapshot()}

    def observe_ceos_turn(self, text: str, *, session_id: Optional[str] = None, engine: str = "local") -> dict:
        with self._lock:
            self._set_focus(text, weight=0.45)
            if "?" in (text or ""):
                # A question from CEOS is an explicit next-step offer, not a hidden action.
                self.state_data.setdefault("influence", {})["offered"] = int(self.state_data["influence"].get("offered") or 0) + 1
                self.state_data["influence"]["unknown"] = int(self.state_data["influence"].get("unknown") or 0) + 1
                self.state_data["influence"]["last"] = {"kind": "question", "text": (text or "")[-320:], "ts": _now(), "outcome": "unknown"}
                hist = self.state_data["influence"].setdefault("history", [])
                hist.insert(0, self.state_data["influence"]["last"])
                del hist[50:]
            self._touch_thread(text)
            self.state_data["last_activity"] = _now()
            self.state_data["status"] = "awake"
            evt = self._event(
                "ceos_turn",
                {"text": (text or "")[:700], "engine": engine, "session_id": session_id},
                source="ceos",
            )
            self._save_state()
            return {"event": evt, "state": self.snapshot()}

    def record_learning(self, kind: str, detail: str, *, topic: Optional[str] = None, persist_event: bool = True):
        with self._lock:
            learning = self.state_data.setdefault("learning", {})
            if kind == "correction":
                learning["corrections"] = int(learning.get("corrections") or 0) + 1
            else:
                learning["lessons"] = int(learning.get("lessons") or 0) + 1
            learning["last_learning"] = _now()
            notes = learning.setdefault("adaptation_notes", [])
            note = {"kind": kind, "detail": detail[:500], "topic": (topic or "")[:100], "ts": _now()}
            notes.insert(0, note)
            del notes[20:]
            if persist_event:
                self._event("learning", note, source="ceos")
            self._save_state()
            return note

    def record_feedback(self, feedback_type: str, text: str = "", *, target: Optional[str] = None, session_id: Optional[str] = None) -> dict:
        feedback_type = (feedback_type or "observe").strip().lower()
        with self._lock:
            rel = self.state_data.setdefault("relationship", {})
            inf = self.state_data.setdefault("influence", {})
            if feedback_type in {"correction", "correct", "reject", "rechazo"}:
                rel["corrections"] = int(rel.get("corrections") or 0) + 1
                if int(inf.get("unknown") or 0) > 0:
                    inf["unknown"] = int(inf.get("unknown") or 0) - 1
                inf["rejected"] = int(inf.get("rejected") or 0) + 1
                for item in inf.get("history") or []:
                    if item.get("outcome") == "unknown":
                        item["outcome"] = "rejected"
                        break
                if inf.get("last") and inf["last"].get("outcome") == "unknown":
                    inf["last"]["outcome"] = "rejected"
                learning_kind = "correction"
            elif feedback_type in {"accept", "accepted", "confirm", "confirmation", "confirmación", "aceptacion", "aceptación"}:
                rel["confirmations"] = int(rel.get("confirmations") or 0) + 1
                if int(inf.get("unknown") or 0) > 0:
                    inf["unknown"] = int(inf.get("unknown") or 0) - 1
                inf["accepted"] = int(inf.get("accepted") or 0) + 1
                for item in inf.get("history") or []:
                    if item.get("outcome") == "unknown":
                        item["outcome"] = "accepted"
                        break
                if inf.get("last") and inf["last"].get("outcome") == "unknown":
                    inf["last"]["outcome"] = "accepted"
                learning_kind = "confirmation"
            else:
                learning_kind = "feedback"
            note = self.record_learning(learning_kind, text[:500], topic=target, persist_event=False)
            evt = self._event("feedback", {"type": feedback_type, "text": text[:500], "target": target, "session_id": session_id}, source="user")
            self._save_state()
            return {"ok": True, "event": evt, "learning": note, "state": self.snapshot()}

    def record_influence(self, kind: str, action: str, *, outcome: str = "unknown", target: Optional[str] = None) -> dict:
        with self._lock:
            inf = self.state_data.setdefault("influence", {})
            inf["offered"] = int(inf.get("offered") or 0) + 1
            outcome_key = {"accepted": "accepted", "rejected": "rejected", "unknown": "unknown"}.get(outcome, "unknown")
            inf[outcome_key] = int(inf.get(outcome_key) or 0) + 1
            inf["last"] = {"kind": kind, "action": action[:500], "outcome": outcome_key, "target": target, "ts": _now()}
            hist = inf.setdefault("history", [])
            hist.insert(0, dict(inf["last"]))
            del hist[50:]
            evt = self._event("influence", inf["last"], source="ceos")
            self._save_state()
            return {"ok": True, "event": evt, "state": self.snapshot()}

    def heartbeat(self, reason: str = "ui") -> dict:
        with self._lock:
            now = _now()
            last = _parse_ts(self.state_data.get("last_activity"))
            age = 0.0
            if last:
                age = max(0.0, (datetime.now(timezone.utc) - last).total_seconds())
            previous_status = self.state_data.get("status")
            self.state_data["pulse"] = int(self.state_data.get("pulse") or 0) + 1
            self.state_data["last_heartbeat"] = now
            if age < 90:
                self.state_data["status"] = "awake"
            elif age < 900:
                self.state_data["status"] = "idle"
            else:
                self.state_data["status"] = "hibernating"
            # decay de atención: un foco viejo pierde peso, pero no desaparece de golpe.
            focus = self.state_data.setdefault("focus", {})
            focus["score"] = round(float(focus.get("score") or 0.0) * 0.985, 3)
            # Pulso auditable sin inundar el log: guardamos cambios de estado y cada 5 pulsos.
            if self.state_data["status"] != previous_status or self.state_data["pulse"] % 5 == 0:
                self._event("heartbeat", {"reason": reason, "age_seconds": round(age, 1)}, source="system")
            # Una pausa prolongada puede activar una reflexión local, sin web ni LLM.
            if (
                self.state_data["status"] == "idle"
                and self.state_data["pulse"] % 30 == 0
                and any(t.get("status") == "open" for t in self.state_data.get("open_threads") or [])
            ):
                self.reflect(force=False)
            self._save_state()
            return self.snapshot()

    def reflect(self, force: bool = False) -> dict:
        with self._lock:
            threads = [t for t in (self.state_data.get("open_threads") or []) if t.get("status") == "open"]
            threads.sort(key=lambda t: (-(float(t.get("weight") or 0)), t.get("updated_at") or ""))
            top = threads[:5]
            prompts = []
            for t in top:
                prompts.append({
                    "thread_id": t.get("id"),
                    "question": f"Retomar: {t.get('text', '')}",
                    "reason": "hilo abierto con actividad reciente",
                })
            focus = self.state_data.get("focus") or {}
            reflection = {
                "id": uuid.uuid4().hex[:12],
                "ts": _now(),
                "focus": focus.get("label"),
                "status": self.state_data.get("status"),
                "open_threads": len(threads),
                "next_moves": prompts,
                "note": (
                    "Reflexión local: priorizo los hilos que siguen abiertos y verifico antes de afirmar."
                    if top or force else
                    "Reflexión local: todavía no hay suficiente trayectoria; observo y conservo continuidad."
                ),
            }
            self.reflections.insert(0, reflection)
            self.reflections = self.reflections[:80]
            self._write_json_atomic(self.reflections_file, self.reflections)
            self._event("reflection", reflection, source="ceos")
            self._save_state()
            return reflection

    def propose_actions(self) -> list[dict]:
        with self._lock:
            actions = []
            focus = (self.state_data.get("focus") or {}).get("label")
            if focus:
                actions.append({"type": "deepen", "label": f"Profundizar en {focus}", "requires_consent": False, "local": True})
            threads = sorted(self.state_data.get("open_threads") or [], key=lambda t: -(float(t.get("weight") or 0)))
            if threads:
                actions.append({"type": "resume", "label": "Retomar el hilo más activo", "thread_id": threads[0].get("id"), "requires_consent": False, "local": True})
            actions.append({"type": "verify", "label": "Comprobar antes de consolidar una conclusión", "requires_consent": False, "local": True})
            actions.append({"type": "web", "label": "Investigar fuera del corpus", "requires_consent": True, "local": False})
            return actions

    def snapshot(self) -> dict:
        with self._lock:
            state = json.loads(json.dumps(self.state_data, ensure_ascii=False))
            state["age_since_activity_s"] = self._age_seconds(state.get("last_activity"))
            state["age_since_heartbeat_s"] = self._age_seconds(state.get("last_heartbeat"))
            state["open_threads"] = sorted(
                state.get("open_threads") or [],
                key=lambda t: (t.get("updated_at") or ""), reverse=True,
            )[:12]
            state["next_moves"] = self.propose_actions()
            return state

    def _age_seconds(self, value: Optional[str]) -> Optional[float]:
        dt = _parse_ts(value)
        if not dt:
            return None
        return round(max(0.0, (datetime.now(timezone.utc) - dt).total_seconds()), 1)

    def stats(self) -> dict:
        st = self.snapshot()
        return {
            "pulse": st.get("pulse", 0),
            "status": st.get("status"),
            "boot_count": st.get("boot_count", 0),
            "open_threads": len(st.get("open_threads") or []),
            "turns": (st.get("relationship") or {}).get("turns", 0),
            "corrections": (st.get("relationship") or {}).get("corrections", 0),
            "learning_events": len((st.get("learning") or {}).get("adaptation_notes") or []),
            "influence_offered": (st.get("influence") or {}).get("offered", 0),
            "influence_accepted": (st.get("influence") or {}).get("accepted", 0),
            "influence_rejected": (st.get("influence") or {}).get("rejected", 0),
            "last_activity": st.get("last_activity"),
            "focus": (st.get("focus") or {}).get("label"),
        }

    def events(self, limit: int = 100) -> list[dict]:
        if not self.events_file.exists():
            return []
        out = []
        try:
            with self.events_file.open("r", encoding="utf-8") as f:
                lines = f.readlines()[-max(1, min(int(limit or 100), 1000)):]
            for line in lines:
                try:
                    out.append(json.loads(line))
                except Exception:
                    continue
        except Exception:
            pass
        return out

    def export_bundle(self, event_limit: int = 2000) -> dict:
        return {
            "schema": self.SCHEMA,
            "state": self.state_data,
            "reflections": self.reflections[-80:],
            "events": self.events(event_limit),
        }

    def import_bundle(self, bundle: dict) -> dict:
        if not isinstance(bundle, dict):
            return {"ok": False, "error": "bundle inválido"}
        with self._lock:
            incoming = bundle.get("state") or {}
            state_replaced = False
            if incoming:
                # En una instancia nueva importamos el snapshot aunque su timestamp sea
                # anterior al boot local. En una instancia con trayectoria propia,
                # conservamos el estado local si es más reciente.
                local_ts = self.state_data.get("last_heartbeat") or ""
                inc_ts = incoming.get("last_heartbeat") or ""
                local_is_fresh = bool(
                    int(self.state_data.get("pulse") or 0) > 1
                    or int((self.state_data.get("relationship") or {}).get("turns") or 0) > 0
                    or (self.state_data.get("open_threads") or [])
                    or int((self.state_data.get("learning") or {}).get("lessons") or 0) > 0
                    or int((self.state_data.get("learning") or {}).get("corrections") or 0) > 0
                )
                if (not local_is_fresh) or inc_ts >= local_ts:
                    self.state_data = incoming
                    state_replaced = True
            refs = bundle.get("reflections") or []
            if refs:
                known = {r.get("id") for r in self.reflections}
                self.reflections.extend([r for r in refs if r.get("id") not in known])
                self.reflections = self.reflections[-80:]
                self._write_json_atomic(self.reflections_file, self.reflections)
            existing_ids = {e.get("id") for e in self.events(limit=20000)}
            events_imported = 0
            for evt in bundle.get("events") or []:
                try:
                    eid = evt.get("id") if isinstance(evt, dict) else None
                    if eid and eid in existing_ids:
                        continue
                    with self.events_file.open("a", encoding="utf-8") as f:
                        f.write(json.dumps(evt, ensure_ascii=False) + "\n")
                    if eid:
                        existing_ids.add(eid)
                    events_imported += 1
                except Exception:
                    continue
            self._save_state()
            return {
                "ok": True,
                "state_replaced": state_replaced,
                "open_threads": len(self.state_data.get("open_threads") or []),
                "events_imported": events_imported,
            }
