"""
Memoria a largo plazo de CEOS — hechos, temas y preferencias que cruzan sesiones.

No es el historial completo del chat (eso vive en data/chat/sessions).
Aquí se guardan:
- hechos sobre el usuario (nombre, proyectos, preferencias declaradas)
- temas recurrentes / intereses
- insights o conclusiones que el usuario confirma
- recordatorios ligeros ("la última vez hablamos de X")

Diseño: pocos elementos, alta señal, TTL opcional, relevancia por keywords.
"""
from __future__ import annotations
import json
import re
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional


def _now():
    return datetime.now(timezone.utc).isoformat()


def _uid():
    return uuid.uuid4().hex[:12]


class LongMemory:
    def __init__(self, base_path: str = "data/long_memory"):
        self.base = Path(base_path)
        self.base.mkdir(parents=True, exist_ok=True)
        self.file = self.base / "memory.json"
        self.data = self._load()

    def _load(self) -> dict:
        if self.file.exists():
            try:
                return json.loads(self.file.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {
            "facts": [],          # hechos estables sobre el usuario / mundo
            "topics": [],         # temas recurrentes
            "insights": [],       # conclusiones destacadas
            "last_topics": [],    # cola de últimos temas tocados
            "updated_at": None,
        }

    def _save(self):
        self.data["updated_at"] = _now()
        self.file.write_text(
            json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    # ----- escritura -----
    def add_fact(self, text: str, source: str = "chat", tags: Optional[list] = None) -> dict:
        text = (text or "").strip()
        if not text:
            return {}
        # dedupe simple
        for f in self.data.get("facts") or []:
            if f.get("text", "").lower() == text.lower():
                f["last_seen"] = _now()
                f["hits"] = int(f.get("hits") or 1) + 1
                self._save()
                return f
        entry = {
            "id": _uid(),
            "text": text[:400],
            "source": source,
            "tags": tags or [],
            "created_at": _now(),
            "last_seen": _now(),
            "hits": 1,
        }
        self.data.setdefault("facts", []).append(entry)
        # cap
        if len(self.data["facts"]) > 120:
            self.data["facts"] = sorted(
                self.data["facts"], key=lambda x: x.get("last_seen") or "", reverse=True
            )[:120]
        self._save()
        return entry

    def touch_topic(self, topic: str, weight: float = 1.0) -> dict:
        topic = (topic or "").strip()
        if not topic or len(topic) < 3:
            return {}
        topic_norm = re.sub(r"\s+", " ", topic)[:80]
        topics = self.data.setdefault("topics", [])
        found = None
        for t in topics:
            if t.get("topic", "").lower() == topic_norm.lower():
                found = t
                break
        if found:
            found["hits"] = int(found.get("hits") or 0) + 1
            found["weight"] = float(found.get("weight") or 1) + weight
            found["last_seen"] = _now()
        else:
            found = {
                "id": _uid(),
                "topic": topic_norm,
                "hits": 1,
                "weight": weight,
                "first_seen": _now(),
                "last_seen": _now(),
            }
            topics.append(found)
        if len(topics) > 80:
            self.data["topics"] = sorted(
                topics, key=lambda x: (x.get("weight") or 0, x.get("last_seen") or ""), reverse=True
            )[:80]
        # cola reciente
        lt = self.data.setdefault("last_topics", [])
        lt = [x for x in lt if x.get("topic", "").lower() != topic_norm.lower()]
        lt.insert(0, {"topic": topic_norm, "ts": _now()})
        self.data["last_topics"] = lt[:15]
        self._save()
        return found

    def add_insight(self, text: str, topic: Optional[str] = None) -> dict:
        text = (text or "").strip()
        if not text:
            return {}
        entry = {
            "id": _uid(),
            "text": text[:500],
            "topic": (topic or "")[:80] or None,
            "created_at": _now(),
        }
        insights = self.data.setdefault("insights", [])
        insights.append(entry)
        if len(insights) > 60:
            self.data["insights"] = insights[-60:]
        self._save()
        return entry

    # ----- lectura / ranking -----
    def relevant(self, query: str, limit: int = 8) -> dict:
        """Devuelve hechos/temas/insights relevantes al texto actual."""
        keys = set(re.findall(r"\w{3,}", (query or "").lower()))
        scored_facts = []
        for f in self.data.get("facts") or []:
            blob = (f.get("text") or "").lower()
            score = sum(1 for k in keys if k in blob) + min(int(f.get("hits") or 1), 5) * 0.1
            # hechos recientes pesan un poco más
            if score > 0 or not keys:
                scored_facts.append((score, f))
        scored_facts.sort(key=lambda x: (-x[0], x[1].get("last_seen") or ""), reverse=False)
        scored_facts.sort(key=lambda x: -x[0])

        scored_topics = []
        for t in self.data.get("topics") or []:
            blob = (t.get("topic") or "").lower()
            score = sum(1 for k in keys if k in blob) + float(t.get("weight") or 0) * 0.05
            if score > 0 or not keys:
                scored_topics.append((score, t))
        scored_topics.sort(key=lambda x: -x[0])

        insights = list(self.data.get("insights") or [])[-5:]
        last_topics = list(self.data.get("last_topics") or [])[:5]

        return {
            "facts": [f for _, f in scored_facts[:limit]],
            "topics": [t for _, t in scored_topics[:limit]],
            "insights": insights,
            "last_topics": last_topics,
        }

    def context_block(self, query: str, limit: int = 6) -> str:
        rel = self.relevant(query, limit=limit)
        parts = []
        if rel["last_topics"]:
            names = ", ".join(t["topic"] for t in rel["last_topics"][:4] if t.get("topic"))
            if names:
                parts.append(f"ÚLTIMOS TEMAS HABLANDOS: {names}")
        if rel["facts"]:
            lines = [f"· {f['text']}" for f in rel["facts"][:5]]
            parts.append("HECHOS RECORDADOS:\n" + "\n".join(lines))
        if rel["topics"]:
            lines = [f"· {t['topic']} (x{t.get('hits',1)})" for t in rel["topics"][:5]]
            parts.append("TEMAS RECURRENTES:\n" + "\n".join(lines))
        if rel["insights"]:
            lines = [f"· {i['text']}" for i in rel["insights"][:3]]
            parts.append("INSIGHTS PREVIOS:\n" + "\n".join(lines))
        return "\n\n".join(parts)

    def stats(self) -> dict:
        return {
            "facts": len(self.data.get("facts") or []),
            "topics": len(self.data.get("topics") or []),
            "insights": len(self.data.get("insights") or []),
            "last_topics": len(self.data.get("last_topics") or []),
            "updated_at": self.data.get("updated_at"),
        }

    # ----- extracción automática ligera desde un turno de chat -----
    def absorb_turn(self, user_text: str, assistant_text: str = "", *, do_facts: bool = True, do_topics: bool = True) -> dict:
        """
        Extrae señales débiles del turno sin LLM:
        - "me llamo X" / "soy X"
        - "estoy trabajando en X"
        - "recuerda que X"
        - tema principal (sustantivos largos / frases cortas)

        do_facts / do_topics permiten absorber identidad antes de responder
        y temas después (para no contaminar el saludo del mismo turno).
        """
        absorbed = {"facts": [], "topics": []}
        t = (user_text or "").strip()
        if not t:
            return absorbed

        if do_facts:
            # Nombre
            m = re.search(
                r"(?:me llamo|soy|mi nombre es)\s+([A-ZÁÉÍÓÚÜÑa-záéíóúüñ][\wáéíóúüñ\-]{1,30})",
                t,
                re.I,
            )
            if m:
                name = m.group(1).strip()
                if name.lower() not in ("ceos", "cronos", "un", "el", "la", "de"):
                    f = self.add_fact(f"El usuario se llama {name}", source="chat", tags=["identidad"])
                    if f:
                        absorbed["facts"].append(f)

            # Recuerda que...
            m = re.search(r"(?:recuerda que|no olvides que|ten en cuenta que)\s+(.+)", t, re.I)
            if m:
                fact = m.group(1).strip().rstrip(".")
                if 8 <= len(fact) <= 220:
                    f = self.add_fact(fact, source="explicit", tags=["recordatorio"])
                    if f:
                        absorbed["facts"].append(f)

            # Trabajando en / proyecto
            m = re.search(
                r"(?:estoy trabajando en|mi proyecto(?: es| actual)?|trabajo en)\s+(.+)",
                t,
                re.I,
            )
            if m:
                proj = m.group(1).strip().rstrip(".")[:120]
                if len(proj) >= 3:
                    f = self.add_fact(f"Proyecto / foco actual: {proj}", source="chat", tags=["proyecto"])
                    if f:
                        absorbed["facts"].append(f)
                    if do_topics:
                        top = self.touch_topic(proj[:60], weight=1.5)
                        if top:
                            absorbed["topics"].append(top)

        if do_topics:
            # Tema: evitar saludos / intros cortas; conservar frases con contenido
            topic_candidate = t
            topic_candidate = re.sub(r"[¿?¡!.,;:]+", " ", topic_candidate)
            topic_candidate = re.sub(r"\s+", " ", topic_candidate).strip()
            low = topic_candidate.lower()
            pure_short = bool(re.match(
                r"^(hola|buenas|hey|gracias|ok|vale|sí|si|no)(\s+.*)?$",
                low,
            )) and len(topic_candidate) < 24
            only_intro = bool(re.match(
                r"^(hola|buenas|hey)?[,\s]*(me llamo|soy|mi nombre es)\s+\w{1,30}\s*$",
                low,
            ))
            if not pure_short and not only_intro and len(topic_candidate) >= 8:
                # Preferir núcleo temático si empieza por saludo
                core = re.sub(
                    r"^(hola|buenas|hey)[,\s]+(me llamo|soy)\s+\w+[\s,]+(y\s+)?",
                    "",
                    low,
                    flags=re.I,
                ).strip()
                core = re.sub(r"^(estoy trabajando en|trabajo en|mi proyecto(?: es| actual)?)\s+", "", core)
                label = core[:60] if len(core) >= 4 else topic_candidate[:60]
                if len(label) > 60:
                    label = label[:60].rsplit(" ", 1)[0]
                top = self.touch_topic(label, weight=1.0)
                if top:
                    absorbed["topics"].append(top)

        return absorbed
