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
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
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

    def __init__(self, mentor, codex, memory, user_profile, identity, base_path: str, long_memory=None, library=None):
        self.mentor = mentor
        self.codex = codex
        self.memory = memory
        self.user = user_profile
        self.identity = identity
        self.long_memory = long_memory
        self.library = library
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
        try:
            from .constitution import as_context_block
            parts.append(as_context_block())
        except Exception:
            pass
        _low_ctx = (user_text or "").lower()
        if re.search(r"\b(cronos|protocolo|espiral|membrana|arquetipo|régimen|regimen)\b", _low_ctx):
            parts.append("DOCTRINA CRONOS (núcleo):" + chr(10) + chr(10).join(f"- {d}" for d in CORE_DOCTRINE[:8]))

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
                parts.append("FRAGMENTOS BIBLIOTECA:" + chr(10) + (chr(10) + "---" + chr(10)).join(str(f)[:300] for f in frags[:4]))
        except Exception:
            pass

        # RESERVORIO: lectura anclada (núcleo del bucle cerrado)
        if self.library is not None and len((user_text or "").strip()) >= 8:
            try:
                low = user_text.lower()
                lens = "general"
                if any(k in low for k in ("estilo", "voz", "narrat", "prosa", "literar")):
                    lens = "estilo"
                elif any(k in low for k in ("tema", "motivo", "amor", "memoria")):
                    lens = "temas"
                elif any(k in low for k in ("crític", "critic", "debil", "valor")):
                    lens = "critica"
                study = self.library.study(
                    query=user_text[:120],
                    lens=lens,
                    limit_docs=4,
                    sample_chunks=6,
                    grammar=None,
                    codex=None,
                )
                if study.get("docs_used"):
                    block = ["RESERVORIO LOCAL (fuente prioritaria):"]
                    # no meter doctrina en el bloque literario
                    meta = study.get("meta_conclusion") or ""
                    if not re.search(r"cronos|doctrina", meta, re.I):
                        block.append(meta)
                    for r in (study.get("readings") or [])[:3]:
                        title = r.get("title") or ""
                        if re.search(r"cronos|doctrina", title, re.I):
                            continue
                        author = r.get("author") or ""
                        ex = (r.get("excerpt") or "")[:500]
                        if re.search(r"cronos representa|espiral es un algoritmo", (ex or "").lower()):
                            continue
                        block.append("— " + title + ((" (" + author + ")") if author else ""))
                        if ex:
                            block.append(ex)
                    if len(block) > 1:
                        parts.append(chr(10).join(block))
            except Exception:
                pass

        return (chr(10) + chr(10)).join(parts)


    def _is_literature_query(self, t: str) -> bool:
        return bool(re.search(
            r"\b(libro|libros|autor|novela|cuento|estilo|literar|prosa|narrat|personaje|"
            r"capítulo|capitulo|obra|virtud|defect|crítica|critica|voz narrativa|david de la fuente)\b",
            t,
            re.I,
        ))

    def _clean_literary_excerpt(self, text: str, limit: int = 900) -> str:
        if not text:
            return ""
        lines = []
        for ln in text.splitlines():
            s = ln.strip()
            if not s:
                continue
            low = s.lower()
            if re.search(
                r"\bisbn\b|\bindice\b|\bíndice\b|editado por|www\.|http|"
                r"doctrina núcleo|cronos representa|la espiral es un algoritmo|"
                r"todo sistema adaptativo|los cuatro regímenes",
                low,
            ):
                continue
            if re.match(r"^[\d.\-–—\s]+$", s):
                continue
            if re.match(r"^\d+\.\s*[-–—]", s):
                continue
            if re.search(r"\.{4,}|_{3,}", s):
                continue
            if "membrana que distinga" in low or "vórtice representa" in low:
                continue
            if len(s) < 30 and not re.search(r"[.!?…]$", s):
                continue
            lines.append(s)
        body = re.sub(r"\s+", " ", " ".join(lines)).strip()
        return body[:limit]

    def _organic_from_reservoir(self, user_text: str, context: str) -> str:
        t = (user_text or "").lower()
        name = ""
        try:
            u = self.user.get() or {}
            name = (u.get("display_name") or u.get("name") or "").strip()
        except Exception:
            name = ""
        hello = (name + ", ") if name and name.lower() not in ("ceos", "cronos") else ""

        readings = []
        if self.library is not None:
            try:
                lens = "estilo" if re.search(r"estilo|voz|prosa|narrat|literar", t) else "temas"
                if re.search(r"defect|virtud|crític|critic|limit|debil|fuerte", t):
                    lens = "critica"
                study = self.library.study(
                    query=user_text[:140],
                    lens=lens,
                    limit_docs=5,
                    sample_chunks=10,
                    grammar=None,
                    codex=None,
                )
                for r in (study.get("readings") or []):
                    title = r.get("title") or "Documento"
                    if re.search(r"cronos|doctrina", title, re.I):
                        continue
                    author = r.get("author") or ""
                    raw = ((r.get("excerpt") or "") + "\n" + (r.get("conclusion") or ""))
                    ex = self._clean_literary_excerpt(raw, 750)
                    if not ex:
                        continue
                    readings.append({"title": title, "author": author, "excerpt": ex})
            except Exception:
                readings = []

        if not readings and context and "RESERVORIO LOCAL" in context:
            chunk = self._clean_literary_excerpt(context.split("RESERVORIO LOCAL", 1)[-1], 900)
            if chunk:
                readings = [{"title": "Reservorio", "author": "", "excerpt": chunk}]

        if not readings:
            return (
                hello
                + "No encuentro aún prosa literaria usable de ese autor en el reservorio "
                "(solo metadatos, índices o textos de protocolo). "
                "Restaura el snapshot o vuelve a cargar los libros y lo leemos en serio."
            )

        wants_style = bool(re.search(r"estilo|voz|prosa|narrat|literar|características|caracteristicas", t))
        wants_critique = bool(re.search(r"defect|virtud|crític|critic|limit|debil|fuerza|mejor", t))

        parts = [
            hello
            + "Te respondo solo con lo literario del reservorio, sin mezclar el manual CRONOS."
        ]
        for r in readings[:4]:
            head = r["title"]
            if r.get("author"):
                head += " (" + r["author"] + ")"
            parts.append("")
            parts.append(head)
            ex = r["excerpt"]
            if wants_style and wants_critique:
                parts.append(
                    "Rasgos que se perciben en el fragmento disponible: cercanía afectiva y mundo íntimo; "
                    "ritmo de cuento hablado más que de ensayo. "
                    "Virtud: calor humano y dedicación al lector concreto. "
                    "Límite: con trozos sueltos no cierro una crítica estructural del libro entero."
                )
                parts.append("Pasaje de apoyo: " + ex[:380])
            elif wants_style:
                parts.append(
                    "El estilo que se deja ver es íntimo y dedicativo: la voz se dirige a personas reales "
                    "y convierte lo cotidiano en materia de cuento. Prioriza calor y cercanía."
                )
                parts.append("Pasaje: " + ex[:400])
            elif wants_critique:
                parts.append(
                    "Virtudes probables: cercanía, claridad emocional, voluntad de regalo al lector. "
                    "Límites honestos: sin el arco completo solo veo piezas; la emoción a veces puede "
                    "adelantarse a la tensión narrativa."
                )
                parts.append("Base textual: " + ex[:360])
            else:
                parts.append(ex[:450])

        parts.append("")
        parts.append(
            "Si quieres, el siguiente turno lo centramos en un solo libro "
            "y lo miramos con más calma, sin índice ni metadatos."
        )
        return "\n".join(parts)


    def _local_reply(self, user_text: str, history: list, context: str) -> str:
        """
        Conversación fluida local (sin LLM).
        Prioriza: continuidad del diálogo → reservorio → códice → protocolo.
        Evita tonos de informe o búsqueda web.
        """
        raw = (user_text or "").strip()
        t = raw.lower()

        # Literatura / autor / estilo → respuesta orgánica (sin doctrina, sin volcado crudo)
        if self._is_literature_query(t) or (
            context and "RESERVORIO LOCAL" in context and not re.search(
                r"\b(cronos|protocolo|espiral|membrana)\b", t
            )
        ):
            return self._organic_from_reservoir(raw, context or "")

        # --- historial reciente (continuidad) ---
        prev_user = ""
        prev_bot = ""
        turns = []
        for m in history[-8:]:
            role = m.get("role")
            content = (m.get("content") or "").strip()
            if not content:
                continue
            if role == "user":
                turns.append(("user", content))
                prev_user = content
            elif role in ("assistant", "ceos", "bot"):
                turns.append(("assistant", content))
                prev_bot = content

        name = ""
        try:
            u = self.user.get() or {}
            name = (u.get("display_name") or u.get("name") or "").strip()
        except Exception:
            name = ""
        hello = (name + ", ") if name and name.lower() not in ("ceos", "cronos") else ""

        def follow_up(options):
            return " " + options

        # --- saludos ---
        if re.match(
            r"^(hola|buenas|hey|qué tal|que tal|buenos días|buenas tardes|buenas noches|hi)([!?.\s]*)$",
            t,
        ) or (
            len(t) < 24
            and re.search(r"\b(hola|buenas|qué tal|que tal)\b", t)
            and not re.search(r"\b(libro|estilo|autor|protocolo|aprend)\b", t)
        ):
            tail = ""
            if self.long_memory is not None:
                try:
                    lt = (self.long_memory.data.get("last_topics") or [])[:2]
                    names = []
                    for x in lt:
                        top = (x.get("topic") or "").strip()
                        if top and not re.match(r"^(hola|buenas)\b", top.lower()):
                            names.append(top)
                    if names:
                        tail = " La última vez tocamos: " + "; ".join(names[:2]) + "."
                except Exception:
                    pass
            return (
                f"Hola{', ' + name if name else ''}. Aquí estoy, en conversación contigo."
                + tail
                + follow_up(
                    "¿Seguimos con tus textos, con el protocolo CRONOS, o con algo que te ronda ahora?"
                )
            )

        if re.search(r"\b(gracias|thank you|thanks)\b", t) and len(t) < 40:
            return "De nada. Cuando quieras, seguimos el hilo."

        # --- continuidad: "y eso?", "cuéntame más", "por qué?" ---
        if re.match(
            r"^(y eso|sigue|continúa|continua|cuéntame más|cuentame mas|más|mas|por qué|porque|y\?|vale y|ok y|explícate|explicate)([!?.\s]*)$",
            t,
        ) or (
            len(t) < 36
            and re.search(r"\b(más|mas|sigue|profundiza|amplía|amplia|detalle)\b", t)
            and prev_bot
        ):
            if prev_bot:
                # ampliar el último tema sin reiniciar
                base = prev_bot[:500]
                extra = ""
                if "RESERVORIO LOCAL" in (context or ""):
                    extra = context.split("RESERVORIO LOCAL", 1)[-1].strip()[:600]
                if extra:
                    return (
                        "Sigo sobre lo anterior.\n\n"
                        + extra
                        + follow_up("¿Quieres que lo enlace con otro capítulo o con tu estilo en general?")
                    )
                return (
                    "Sigo el hilo. Antes decía, en esencia: "
                    + base[:320]
                    + follow_up("¿Qué parte quieres apretar: estilo, temas o un pasaje concreto?")
                )

        # --- identidad ---
        if re.search(r"\b(quién eres|quien eres|qué eres|que eres)\b", t):
            return (
                f"{hello}Soy CEOS: un mentor-memoria. Converso, estudio lo que cargues en el reservorio, "
                "investigo si me lo pides, y voy actualizando un códice de cristales y mapas. "
                "No soy un buscador ni un modelo genérico sin memoria."
                + follow_up("¿Quieres que te diga qué tengo aprendido ahora mismo de ti o de tus textos?")
            )

        # --- anclaje conversacional al reservorio (no volcar informe) ---
        if context and "RESERVORIO LOCAL" in context:
            chunk = context.split("RESERVORIO LOCAL", 1)[-1].strip()
            # limpiar metadatos ruidosos
            lines = []
            for ln in chunk.splitlines():
                ln = ln.strip()
                if not ln or ln.startswith("(fuente"):
                    continue
                if ln.startswith("Relectura del reservorio"):
                    continue
                lines.append(ln)
            body = "\n".join(lines).strip()[:900]
            if body:
                opener = f"{hello}Mirando lo que tengo en el reservorio"
                if re.search(r"estilo|voz|prosa|narrat", t):
                    opener += " sobre el estilo"
                elif re.search(r"tema|motivo|amor|memoria", t):
                    opener += " sobre los temas"
                opener += ":\n\n"
                return (
                    opener
                    + body
                    + follow_up(
                        "¿Seguimos con un libro concreto, comparando obras, o con cómo suena tu voz en un párrafo?"
                    )
                )

        # --- códice, si hay mapa del tema ---
        topic = raw
        try:
            if hasattr(self.codex, "expand_topic"):
                exp = self.codex.expand_topic(topic[:80])
                if isinstance(exp, dict) and exp.get("ok"):
                    bits = []
                    for f in (exp.get("fragments") or [])[:4]:
                        bits.append(str(f)[:200])
                    for m in (exp.get("molecules") or [])[:2]:
                        if isinstance(m, dict):
                            bits.append(f"{m.get('formula','')}: {m.get('meaning','')[:140]}")
                    body = "\n\n".join(bits)
                    if body:
                        return (
                            f"{hello}Desde el códice, enlazado con lo que me dices:\n\n"
                            + body[:800]
                            + follow_up("¿Lo aplicamos a un caso tuyo o lo dejamos en concepto?")
                        )
        except Exception:
            pass

        try:
            frags = self.mentor._pick_knowledge(raw, n=2) if hasattr(self.mentor, "_pick_knowledge") else []
            if frags:
                joined = "\n\n".join(str(f)[:220] for f in frags)
                return (
                    f"{hello}Con el corpus que manejo:\n\n"
                    + joined
                    + follow_up("¿Te encaja o lo contrastamos con un ejemplo real?")
                )
        except Exception:
            pass

        # --- análisis / protocolo ---
        if re.search(r"\b(analiza|análisis|diagnostica|evalúa|evalua)\b", t):
            return (
                f"{hello}Para analizar con el protocolo necesito el sistema en juego: "
                "quiénes intervienen, qué se intercambia, y qué te preocupa del resultado."
                + follow_up("¿Me lo cuentas en 4–5 frases o pegas un fragmento?")
            )

        if re.search(r"\b(protocolo|cronos|espiral|membrana|arquetipo)\b", t):
            return (
                f"{hello}El núcleo CRONOS mira sistemas con membrana, regímenes e intercambios, "
                "y la Espiral ordena explorar → aprender → instituir → renovar. "
                "No es adorno: es una forma de leer complejidad sin aplastarla."
                + follow_up("¿Lo quieres sobre un equipo, un texto tuyo, o una decisión que tienes encima?")
            )

        # --- fallback conversacional (nunca informe vacío) ---
        if prev_bot and len(raw) < 80:
            return (
                f"{hello}Te sigo. Sobre lo que veníamos hablando, ¿puedes precisar un poco más "
                f"qué te interesa de «{raw[:60]}»?"
                + follow_up("Con una frase de más suele bastar para aterrizar.")
            )

        return (
            f"{hello}Te escucho. Puedo trabajar con tus textos del reservorio, con el códice, "
            "con coaching/idiomas, o pensar contigo en voz alta."
            + follow_up(
                "¿Sobre qué quieres tirar del hilo ahora: un libro, un aprendizaje, o una pregunta suelta?"
            )
        )


    def _call_llm_chat(self, messages: list, context: str, max_tokens: int = 1200) -> dict:
        """Llama al LLM en modo chat multi-turno nativo."""
        status = llm_available()
        if not status["available"]:
            return {"ok": False, "error": "sin_api"}

        api_msgs = []
        system = (
            "Eres CEOS, mentor-memoria en castellano. Conversas con naturalidad: "
            "turnos claros, continuidad con el hilo, sin tono de informe ni de buscador. "
            "Prioriza el RESERVORIO LOCAL del contexto si existe. "
            "Si no sabes, dilo. Termina a menudo con una pregunta breve de seguimiento. "
            "No inventes libros o hechos que no estén en el contexto."
        )
        api_msgs.append({"role": "system", "content": system})
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
        """
        Busca en internet solo si tiene sentido.
        NO busca en saludos, meta-preguntas sobre el propio aprendizaje, ni charla cotidiana.
        """
        text = (user_text or "").strip()
        low = text.lower()
        if web_flag is False:
            return False
        if any(x in low for x in ("sin internet", "no busques", "no buscar", "solo corpus", "solo local", "offline")):
            return False
        # Meta / conversación sobre el propio sistema → local
        if self._is_self_reflection(low):
            return False
        if re.match(
            r"^(hola|hi|hey|buenas|buenos d[ií]as|buenas tardes|buenas noches|ok|vale|gracias|adi[oó]s|hasta luego)[!?.\s]*$",
            low,
        ):
            return False
        # Pedido explícito de búsqueda
        if re.search(
            r"\b(busca en internet|investiga|navega|busca informaci[oó]n|qu[eé] dice la web|en internet)\b",
            low,
        ):
            return True
        # Pregunta de conocimiento general (no sobre "tú/CEOS")
        if re.search(r"\b(qu[eé] es|qui[eé]n es|c[oó]mo funciona|historia de|definici[oó]n)\b", low):
            if not re.search(r"\b(has aprendido|aprendiste|tu memoria|tu c[oó]dice|reservorio)\b", low):
                return True
        # Por defecto: conversar en local (corpus + reservorio + memoria)
        return False

    def _is_self_reflection(self, low: str) -> bool:
        keys = (
            "qué has aprendido", "que has aprendido", "qué aprendiste", "que aprendiste",
            "qué sabes de mí", "que sabes de mi", "qué sabes sobre", "que sabes sobre",
            "tu memoria", "tu códice", "tu codex", "el reservorio", "qué tienes en",
            "cómo has evolucionado", "como has evolucionado", "qué has investigado",
            "que has investigado", "qué recuerdas", "que recuerdas", "quién eres",
            "quien eres", "cómo estás", "como estas", "qué tal", "que tal",
            "háblame de ti", "hablame de ti", "qué puedes hacer", "que puedes hacer",
            "aprendido hoy", "aprendido esta semana", "en el reservorio",
            "quién soy", "quien soy", "quién eres tú", "quien eres tu",
            "quiénes somos", "quienes somos", "nuestra identidad", "tu identidad",
            "la memoria", "quiénes somos", "determina quién",
        )
        return any(k in low for k in keys)

    def _self_status_reply(self, user_text: str) -> str:
        """Respuesta conversacional sobre lo aprendido / estado interno (sin web)."""
        lines = []
        try:
            from .identity_memory import compose_identity, teaching_seed_from_identity
            portrait = compose_identity(
                identity=self.identity,
                library=self.library,
                codex=self.codex,
                long_memory=self.long_memory,
                user=self.user,
            )
            lines.append(portrait.get("narrativa") or "")
            lines.append("")
            lines.append(portrait.get("thesis") or "")
            lines.append("")
            seed = teaching_seed_from_identity(portrait)
            if seed:
                lines.append(seed)
                lines.append("")
        except Exception:
            pass
        lines.append("Te respondo desde lo que tengo en memoria local (no desde una búsqueda web vacía).")
        # Biblioteca
        docs = nchars = 0
        titles = []
        if self.library is not None:
            try:
                st = self.library.stats() if hasattr(self.library, "stats") else {}
                docs = int(st.get("docs") or 0)
                nchars = int(st.get("chars") or 0)
                for d in (self.library.list_docs() or [])[-8:]:
                    t = d.get("title") or d.get("source_name") or ""
                    a = d.get("author") or ""
                    if t:
                        titles.append(f"· {t}" + (f" ({a})" if a else ""))
            except Exception:
                pass
        # Codex
        crystals = maps = 0
        try:
            if hasattr(self.codex, "stats"):
                cs = self.codex.stats() or {}
                crystals = int(cs.get("crystals") or 0)
                maps = int(cs.get("maps") or 0)
            else:
                crystals = len(self.codex._load(self.codex.crystals_file))
                maps = len(self.codex._load(self.codex.maps_file))
        except Exception:
            pass
        # Long memory
        lm = ""
        if self.long_memory is not None:
            try:
                lm = self.long_memory.context_block(user_text, limit=5) or ""
            except Exception:
                lm = ""
        lines.append("")
        lines.append(f"**Reservorio:** {docs} documento(s), ~{nchars} caracteres.")
        if titles:
            lines.append("Últimos materiales:")
            lines.extend(titles[:6])
        else:
            lines.append("Aún no veo documentos en el reservorio de esta instancia (o el disco se reinició).")
        lines.append(f"**Códice:** {crystals} cristales, {maps} mapas temáticos.")
        if lm:
            lines.append("")
            lines.append("**Memoria reciente / hechos:**")
            lines.append(lm[:800])
        lines.append("")
        lines.append(
            "Si me preguntas por un autor o libro que hayas cargado, puedo hablar desde ese texto "
            "(pestaña Investigar o «relee el reservorio»). "
            "Si quieres que busque en internet algo concreto, dímelo: «investiga …» o «busca en internet …»."
        )
        return chr(10).join(lines)


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
            report = research_topic(topic, focus=None, library=getattr(self, "library", None))
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
        low_early = user_text.lower()

        # Meta-conversación: qué has aprendido / estado → respuesta local directa
        if self._is_self_reflection(low_early):
            answer = self._self_status_reply(user_text)
            history.append({"role": "user", "content": user_text, "ts": _now(), "device": device_id})
            history.append({"role": "assistant", "content": answer, "ts": _now()})
            session["messages"] = history[-40:]
            try:
                self.store.save(session_id, session)
            except Exception:
                pass
            if self.long_memory is not None:
                try:
                    self.long_memory.absorb_turn(user_text, answer, do_facts=True, do_topics=True)
                except Exception:
                    pass
            return {
                "ok": True,
                "reply": answer,
                "engine": "local-reflection",
                "mode": "self",
                "web": False,
            }

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
            web_block, web_meta = "", {"ok": False, "topic": user_text[:80], "results": 0}
            try:
                with ThreadPoolExecutor(max_workers=1) as pool:
                    fut = pool.submit(self._web_research_pack, user_text)
                    web_block, web_meta = fut.result(timeout=12)
            except Exception as e:
                web_block = f"BÚSQUEDA WEB: (tiempo agotado o error: {type(e).__name__})"
                web_meta = {"ok": False, "topic": user_text[:80], "results": 0, "error": str(e)[:120]}
            context = context + "\n\n" + web_block
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
