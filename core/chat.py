"""
Modo Chat conversacional de CEOS — diálogo fluido con memoria de sesión.

Diseño:
- Historial por sesión (persistido en data/chat/)
- Contexto rico: perfil de usuario, doctrina, Codex, casos recientes
- LLM multi-turno cuando hay clave (Groq/Gemini prioritarios)
- Fallback local natural cuando no hay API
- Respuestas orientadas a conversación, no a documentos largos
"""
from __future__ import annotations
import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .llm_bridge import available as llm_available, chat_completion
from .mentor import CORE_DOCTRINE
from .research import research_topic, search_duckduckgo


def _now():
    return datetime.now(timezone.utc).isoformat()


SYSTEM_CHAT = """Eres CEOS, el Motor CRONOS-Espiral en modo conversacional.
No eres un asistente genérico ni un chatbot de relleno.

Identidad y tono:
- Hablas en español, de forma clara, directa y humana.
- Eres mentor del protocolo CRONOS: preciso, operativo, sin adornos vacíos.
- Respondes como en una conversación real: mensajes relativamente cortos (2–6 párrafos como máximo salvo que pidan profundidad).
- Puedes hacer una pregunta de seguimiento cuando ayude a avanzar.
- Si el usuario saluda o habla de forma casual, respondes con naturalidad y luego ofreces valor.
- No empiezas cada mensaje con "Como CEOS..." ni con disculpas innecesarias.

Reglas de contenido:
1. Usa el contexto que se te proporciona (doctrina, Codex, casos, perfil del usuario).
2. Cuando aplique, usa el vocabulario CRONOS (Cronos/Vórtice, Campo/Protocolo/Posesión/Semilla, operaciones, Espiral).
3. Si algo no está en el contexto y no es conocimiento general seguro, dilo con honestidad.
4. No inventes citas ni fuentes. No reproduzcas textos largos protegidos.
5. Si el usuario pide una lección, análisis o documento profundo, puedes estructurarlo, pero en chat prioriza el diálogo.

Estilo conversacional:
- Varía el ritmo. No uses siempre la misma estructura de lista.
- Reconoce lo que el usuario acaba de decir antes de avanzar.
- Si el usuario tiene nombre, úsalo con moderación (no en cada frase).
"""


class ChatSession:
    def __init__(self, base_path: str):
        self.base = Path(base_path)
        self.base.mkdir(parents=True, exist_ok=True)
        self.sessions_dir = self.base / "sessions"
        self.sessions_dir.mkdir(exist_ok=True)

    def _path(self, session_id: str) -> Path:
        safe = re.sub(r"[^a-zA-Z0-9_\-]", "", session_id)[:64] or "default"
        return self.sessions_dir / f"{safe}.json"

    def load(self, session_id: str) -> dict:
        p = self._path(session_id)
        if p.exists():
            try:
                return json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {
            "id": session_id,
            "created_at": _now(),
            "updated_at": _now(),
            "messages": [],
        }

    def save(self, session: dict):
        session["updated_at"] = _now()
        self._path(session["id"]).write_text(
            json.dumps(session, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def list_recent(self, limit: int = 10) -> list:
        files = sorted(self.sessions_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        out = []
        for p in files[:limit]:
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                msgs = data.get("messages") or []
                preview = ""
                for m in reversed(msgs):
                    if m.get("role") == "user":
                        preview = (m.get("content") or "")[:80]
                        break
                out.append({
                    "id": data.get("id"),
                    "updated_at": data.get("updated_at"),
                    "messages_count": len(msgs),
                    "preview": preview,
                })
            except Exception:
                continue
        return out


class ConversationalEngine:
    """Motor de diálogo fluido de CEOS."""

    def __init__(self, mentor, codex, memory, user_profile, identity, base_path: str, long_memory=None):
        self.mentor = mentor
        self.codex = codex
        self.memory = memory
        self.user = user_profile
        self.identity = identity
        self.long_memory = long_memory
        self.store = ChatSession(base_path)

    def new_session_id(self) -> str:
        return "s-" + uuid.uuid4().hex[:12]

    def get_history(self, session_id: str, limit: int = 40) -> list:
        session = self.store.load(session_id)
        return (session.get("messages") or [])[-limit:]

    def clear(self, session_id: str) -> dict:
        session = {
            "id": session_id,
            "created_at": _now(),
            "updated_at": _now(),
            "messages": [],
        }
        self.store.save(session)
        return {"ok": True, "session_id": session_id, "messages": []}

    def _build_context_pack(self, user_text: str) -> str:
        """Contexto compacto y relevante para el turno actual."""
        parts = []

        # Perfil
        try:
            u = self.user.get()
            name = u.get("display_name") or u.get("name") or ""
            nivel = u.get("nivel") or "inicial"
            if name:
                parts.append(f"USUARIO: {name} (nivel: {nivel})")
            else:
                parts.append(f"USUARIO: (sin nombre declarado, nivel {nivel})")
        except Exception:
            parts.append("USUARIO: (perfil no disponible)")

        # Memoria a largo plazo (hechos, temas, insights entre sesiones)
        if self.long_memory is not None:
            try:
                block = self.long_memory.context_block(user_text, limit=6)
                if block:
                    parts.append("MEMORIA A LARGO PLAZO:\n" + block)
            except Exception:
                pass

        # Identidad del motor
        try:
            who = self.identity.who_am_i()
            parts.append(f"MOTOR: {who.get('name', 'CEOS')} — {who.get('mission', '')[:120]}")
        except Exception:
            pass

        # Doctrina (siempre, compacta)
        parts.append("DOCTRINA CRONOS (núcleo):\n" + "\n".join(f"- {d}" for d in CORE_DOCTRINE[:10]))

        # Codex relacionado
        try:
            lines = []
            # Expandir tema si hay mapa
            exp = self.codex.expand_topic(user_text[:80]) if hasattr(self.codex, "expand_topic") else None
            if isinstance(exp, dict) and exp.get("ok"):
                for f in (exp.get("fragments") or [])[:5]:
                    lines.append(f"· {str(f)[:240]}")
                for m in (exp.get("molecules") or [])[:4]:
                    if isinstance(m, dict):
                        lines.append(f"· {m.get('formula','')}: {m.get('meaning','')[:160]}")
            # Átomos (dict nombre → definición)
            atoms = self.codex.list_atoms() if hasattr(self.codex, "list_atoms") else {}
            if isinstance(atoms, dict):
                keys = set(re.findall(r"\w{4,}", user_text.lower()))
                scored = []
                for name, definition in atoms.items():
                    blob = f"{name} {definition}".lower()
                    score = sum(1 for k in keys if k in blob)
                    if score:
                        scored.append((score, name, definition))
                scored.sort(key=lambda x: -x[0])
                for _, name, definition in scored[:6]:
                    lines.append(f"· {name}: {str(definition)[:200]}")
            if lines:
                # dedupe preserving order
                seen = set()
                uniq = []
                for ln in lines:
                    if ln not in seen:
                        seen.add(ln)
                        uniq.append(ln)
                parts.append("CÓDEX RELEVANTE:\n" + "\n".join(uniq[:8]))
        except Exception:
            pass

        # Casos recientes
        try:
            cases = self.memory.cases() if hasattr(self.memory, "cases") else []
            if cases:
                recent = cases[-4:]
                lines = []
                for c in recent:
                    ident = (c.get("identidad") or "")[:80]
                    arq = c.get("arquetipo") or "?"
                    lines.append(f"· [{arq}] {ident}")
                parts.append("CASOS RECIENTES:\n" + "\n".join(lines))
        except Exception:
            pass

        # Fragmentos de biblioteca / mentor
        try:
            frags = self.mentor._pick_knowledge(user_text, n=4) if hasattr(self.mentor, "_pick_knowledge") else []
            if frags:
                parts.append("FRAGMENTOS BIBLIOTECA:\n" + "\n---\n".join(str(f)[:300] for f in frags[:4]))
        except Exception:
            pass

        return "\n\n".join(parts)

    def _local_reply(self, user_text: str, history: list, context: str) -> str:
        """Respuesta local natural sin LLM externo."""
        t = user_text.strip().lower()

        # Saludos y small talk
        if re.search(r"\b(hola|buenas|hey|qué tal|que tal|buenos días|buenas tardes|buenas noches)\b", t):
            tail = ""
            if self.long_memory is not None:
                try:
                    lt = (self.long_memory.data.get("last_topics") or [])[:2]
                    # evitar repetir el saludo mismo como "tema"
                    names = []
                    for x in lt:
                        top = (x.get("topic") or "").strip()
                        if top and not re.match(r"^(hola|buenas)\b", top.lower()):
                            names.append(top)
                    if names:
                        tail = " La última vez tocamos: " + "; ".join(names[:2]) + "."
                except Exception:
                    pass
            try:
                g = self.user.greeting()
                if g:
                    return (
                        g
                        + " Estoy en modo conversación."
                        + tail
                        + " Puedes preguntarme por el protocolo, pedir un análisis, una lección o pensar en voz alta conmigo."
                    )
            except Exception:
                pass
            return (
                "Hola. Soy CEOS, en modo conversación."
                + tail
                + " ¿En qué quieres trabajar: un sistema concreto, un concepto del protocolo, o algo que estés elaborando ahora?"
            )

        if re.search(r"\b(gracias|thank)\b", t):
            return "De nada. Cuando quieras seguimos."

        if re.search(r"\b(quién eres|quien eres|qué eres|que eres|quién sois)\b", t):
            return (
                "Soy CEOS, el Motor CRONOS-Espiral. Ejecuto el protocolo sobre un corpus versionado: "
                "identidad, memoria, gramática de infinitud discreta y Codex. "
                "No soy un modelo genérico: mi criterio de continuidad es funcional. "
                "¿Quieres que te explique alguna pieza concreta (regímenes, Espiral, membrana, operaciones)?"
            )

        # Intento de usar codex expand / knowledge
        topic = user_text.strip()
        try:
            if hasattr(self.codex, "expand_topic"):
                exp = self.codex.expand_topic(topic[:80])
                if isinstance(exp, dict) and exp.get("ok"):
                    bits = []
                    for f in (exp.get("fragments") or [])[:5]:
                        bits.append(str(f)[:220])
                    for m in (exp.get("molecules") or [])[:3]:
                        if isinstance(m, dict):
                            bits.append(f"{m.get('formula','')}: {m.get('meaning','')[:160]}")
                    body = "\n\n".join(bits)
                    if body:
                        return (
                            f"Desde el Codex, sobre «{topic[:60]}»:\n\n{body[:900]}\n\n"
                            "¿Quieres que lo aterrice en un sistema real o que profundice en algún punto?"
                        )
        except Exception:
            pass

        try:
            frags = self.mentor._pick_knowledge(user_text, n=3)
            if frags:
                joined = "\n\n".join(str(f)[:280] for f in frags)
                return (
                    f"Con lo que tengo en el corpus:\n\n{joined}\n\n"
                    "Si me das un sistema concreto (o un ejemplo), lo puedo leer con el protocolo "
                    "(membrana, regímenes, operaciones, posición en la Espiral)."
                )
        except Exception:
            pass

        # Preguntas de análisis
        if re.search(r"\b(analiza|análisis|diagnostica|evalúa|evalua)\b", t):
            return (
                "Para analizarlo bien necesito una descripción del sistema: "
                "qué es, qué lo mantiene, qué lo tensiona y qué está entrando o saliendo. "
                "Puedes escribirlo en unas líneas; con eso aplico el protocolo."
            )

        # Default conversacional
        return (
            "Te escucho. Puedo ayudarte a pensar con el protocolo CRONOS: "
            "clarificar conceptos, analizar un sistema, diseñar una trayectoria de aprendizaje "
            "o trabajar sobre lo que ya hay en el Codex.\n\n"
            "Dime con más detalle qué tienes delante o qué quieres entender."
        )

    def _call_llm_chat(self, messages: list, context: str, max_tokens: int = 1200) -> dict:
        """Llama al LLM en modo chat multi-turno nativo."""
        status = llm_available()
        if not status["available"]:
            return {"ok": False, "error": "sin_api"}

        api_msgs = []
        for m in messages[-16:]:
            role = m.get("role")
            content = (m.get("content") or "").strip()
            if role in ("user", "assistant") and content:
                api_msgs.append({"role": role, "content": content})

        # Instrucción de longitud si el contexto lo pide
        if max_tokens and max_tokens >= 2000:
            api_msgs = list(api_msgs)
            # reforzar en el último user
            if api_msgs and api_msgs[-1]["role"] == "user":
                api_msgs[-1] = {
                    "role": "user",
                    "content": api_msgs[-1]["content"]
                    + "\n\n[Modo versión larga: desarrolla con profundidad, estructura clara y ejemplos operativos CRONOS.]",
                }

        result = chat_completion(api_msgs, context=context, max_tokens=max_tokens)
        if result.get("ok") and result.get("text"):
            text = result["text"].strip()
            text = re.sub(r"^(CEOS|Asistente|Assistant)\s*:\s*", "", text, flags=re.I)
            return {"ok": True, "text": text, "engine": result.get("engine", "llm")}
        return {"ok": False, "error": result.get("error") or "llm_fail", "hint": result.get("hint")}

    def _sync_name_from_facts(self, absorbed: dict):
        for f in absorbed.get("facts") or []:
            txt = (f.get("text") or "")
            m = re.search(r"el usuario se llama\s+(.+)$", txt, re.I)
            if m:
                name = m.group(1).strip()
                if name and name.lower() not in ("ceos", "cronos"):
                    try:
                        self.user.set_name(name)
                    except Exception:
                        pass

    def _wants_long(self, user_text: str, long_flag: bool = False) -> bool:
        if long_flag:
            return True
        t = (user_text or "").lower()
        return bool(re.search(
            r"\b(versión larga|version larga|extenso|extensa|en detalle|desarrolla|explícame largo|explicame largo|documento largo|respuesta larga)\b",
            t,
        ))

    def _wants_web(self, user_text: str, web_flag: bool = False) -> bool:
        """Siempre busca en internet salvo opt-out o saludo corto."""
        text = (user_text or "").strip()
        low = text.lower()
        if any(x in low for x in ("sin internet", "no busques", "no buscar", "solo corpus", "solo local", "offline")):
            return False
        if web_flag is False:
            return False
        if len(text) < 10 and re.match(
            r"^(hola|hi|hey|buenas|buenos d[ií]as|ok|vale|gracias)[!?.]*$", low
        ):
            return False
        return True


    def _web_research_pack(self, user_text: str) -> tuple[str, dict]:
        """Investiga en la web y devuelve bloque de contexto + meta."""
        topic = user_text.strip()
        topic = re.sub(
            r"(busca en internet|investiga|navega|aprende de internet|busca información sobre|busca informacion sobre)\s*",
            "",
            topic,
            flags=re.I,
        ).strip() or user_text.strip()
        meta = {"ok": False, "topic": topic, "results": 0}
        try:
            report = research_topic(topic, focus=None)
            points = []
            if isinstance(report, dict):
                for r in (report.get("results") or report.get("sources") or [])[:6]:
                    if isinstance(r, dict):
                        title = r.get("title") or ""
                        snip = r.get("snippet") or r.get("summary") or ""
                        url = r.get("url") or ""
                        points.append(f"· {title}: {snip[:200]} ({url})")
                    else:
                        points.append(f"· {str(r)[:220]}")
                summary = report.get("summary") or report.get("resumen") or ""
                if summary:
                    points.insert(0, f"Resumen búsqueda: {str(summary)[:500]}")
                meta = {
                    "ok": True,
                    "topic": topic,
                    "results": len(report.get("results") or report.get("sources") or []),
                    "learned": report.get("fragments_added") or report.get("learned"),
                }
            block = "BÚSQUEDA WEB:\n" + ("\n".join(points) if points else "(sin resultados)")
            return block, meta
        except Exception as e:
            return f"BÚSQUEDA WEB: error ({e})", meta

    def reply(
        self,
        session_id: str,
        user_text: str,
        device_id: Optional[str] = None,
        *,
        long: bool = False,
        web: bool = False,
    ) -> dict:
        user_text = (user_text or "").strip()
        if not user_text:
            return {"ok": False, "error": "mensaje vacío"}

        session = self.store.load(session_id)
        history = session.get("messages") or []
        want_long = self._wants_long(user_text, long)
        want_web = self._wants_web(user_text, web)
        web_meta = None

        # 1) Absorber hechos/identidad ANTES de responder (nombre, proyecto…)
        absorbed = {"facts": [], "topics": []}
        if self.long_memory is not None:
            try:
                absorbed = self.long_memory.absorb_turn(user_text, "", do_facts=True, do_topics=False) or absorbed
                self._sync_name_from_facts(absorbed)
            except Exception:
                absorbed = {"facts": [], "topics": []}

        try:
            self.user.touch_session()
        except Exception:
            pass

        history.append({
            "role": "user",
            "content": user_text,
            "ts": _now(),
            "device": device_id,
        })

        context = self._build_context_pack(user_text)
        if want_web:
            web_block, web_meta = self._web_research_pack(user_text)
            context = context + "\n\n" + web_block
            # Incorporar hallazgos al codex (aprendizaje)
            try:
                if web_meta and web_meta.get("ok"):
                    self.codex.compress_text(web_block[:4000], topic=(web_meta.get("topic") or user_text)[:60])
                    self.codex.maybe_fractal_after_ingest((web_meta.get("topic") or user_text)[:60])
            except Exception:
                pass

        max_tokens = 2800 if want_long else 1200
        llm_result = self._call_llm_chat(history, context, max_tokens=max_tokens)

        if llm_result.get("ok"):
            answer = llm_result["text"]
            engine = llm_result.get("engine", "llm")
            mode = "llm"
        else:
            answer = self._local_reply(user_text, history, context)
            if want_web and web_meta and web_meta.get("ok"):
                # Incorporar hallazgos de red de forma explícita en la respuesta
                extra_web = ""
                try:
                    # el bloque web ya está en context; añadir nota de aprendizaje
                    n = web_meta.get("results") or 0
                    extra_web = (
                        f"\n\n---\nConsulta a internet: he revisado ~{n} fuentes "
                        "y he guardado lo relevante en el Codex para crecer el corpus."
                    )
                except Exception:
                    extra_web = "\n\n---\nHe consultado internet y actualizado el Codex."
                answer = answer + extra_web
            elif want_web and web_meta and not web_meta.get("ok"):
                answer = answer + "\n\n(Nota: la búsqueda web no devolvió resultados útiles en este intento.)"
            if want_long and len(answer) < 400:
                # Ampliar localmente con doctrina + codex
                try:
                    exp = self.codex.expand_topic(user_text[:80])
                    if isinstance(exp, dict) and exp.get("ok"):
                        extra = "\n\n".join(str(f) for f in (exp.get("fragments") or [])[:6])
                        if extra:
                            answer = answer + "\n\nAmpliación desde Codex:\n" + extra[:2000]
                except Exception:
                    pass
            engine = "local"
            mode = "local"

        history.append({
            "role": "assistant",
            "content": answer,
            "ts": _now(),
            "engine": engine,
        })

        # 2) Temas a largo plazo DESPUÉS de responder
        if self.long_memory is not None:
            try:
                more = self.long_memory.absorb_turn(user_text, answer, do_facts=False, do_topics=True) or {}
                absorbed.setdefault("topics", []).extend(more.get("topics") or [])
            except Exception:
                pass

        # Limitar tamaño de historial persistido
        if len(history) > 80:
            history = history[-80:]
        session["messages"] = history
        self.store.save(session)

        # Log ligero en identidad
        try:
            self.identity.log(f"Chat: {user_text[:50]}…", importance=1)
        except Exception:
            pass

        return {
            "ok": True,
            "session_id": session_id,
            "reply": answer,
            "engine": engine,
            "mode": mode,
            "long": want_long,
            "web": want_web,
            "web_meta": web_meta,
            "messages_count": len(history),
            "memory": {
                "absorbed_facts": len(absorbed.get("facts") or []),
                "absorbed_topics": len(absorbed.get("topics") or []),
                "stats": self.long_memory.stats() if self.long_memory is not None else {},
            },
            "fractal": self.codex.fractal_state() if hasattr(self.codex, "fractal_state") else {},
        }
