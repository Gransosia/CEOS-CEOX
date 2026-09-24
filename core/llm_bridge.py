"""
Puente LLM de CEOS — capa robusta multi-proveedor.

El puente está diseñado para sobrevivir a cambios de modelos/proveedores:
- Groq: selección automática de modelos actuales + fallback entre modelos.
- xAI / Gemini / Anthropic / OpenAI: fallback por proveedor.
- Diagnóstico diferenciado de 401, 403, 404, 429 y otros errores.
- Nunca expone claves en las respuestas de estado.
"""
from __future__ import annotations
import os
import json
import time
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError


SYSTEM_MAESTRO = """Eres el redactor del Maestro CRONOS-Espiral (CEOS).
No eres un asistente genérico. Operas bajo estas reglas:

1. Usa SOLO el material de contexto que se te proporciona (fragmentos del corpus local,
   doctrina CRONOS, resultados de búsqueda). Si algo no está en el contexto, dilo.
2. Estructura siempre con el vocabulario CRONOS cuando aplique:
   Cronos/Vórtice, Campo/Protocolo/Posesión/Semilla, operaciones
   (incorporar/conservar/expulsar/ignorar), fases de la Espiral.
3. Sé operativo: definiciones utilizables, criterios de falsación, ejercicios.
4. No inventes citas ni fuentes. No reproduzcas pasajes largos de obras protegidas.
5. Tono: claro, técnico, sin adornos vacíos.
6. Idioma: español.
"""

_KEYS_FILE = Path(__file__).resolve().parent.parent / "data" / "llm_keys.json"

# Modelos Groq que constan como actuales en la documentación consultada el 24-09-2026.
# Dejamos los modelos antiguos fuera de la lista automática porque varios fueron retirados.
GROQ_CURRENT_MODELS = [
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
    "qwen/qwen3.8-27b",
    "minimaxai/minimax-m2.7",
]
GROQ_DEPRECATED_MODELS = {
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "llama-3.1-70b-versatile",
    "gemma2-9b-it",
}
_MODEL_CACHE = {"ts": 0.0, "ids": []}
_MODEL_CACHE_TTL = 300.0


def _load_keys_file() -> dict:
    if _KEYS_FILE.exists():
        try:
            return json.loads(_KEYS_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _key(name: str) -> str:
    val = os.environ.get(name, "").strip()
    if val:
        return val
    return str(_load_keys_file().get(name, "")).strip()


def _safe_http_error(e: HTTPError) -> RuntimeError:
    try:
        detail = e.read().decode("utf-8", errors="replace")[:700]
    except Exception:
        detail = str(e.reason)
    status = int(getattr(e, "code", 0) or 0)
    low = detail.lower()
    if status == 401:
        msg = "401 no autorizado: la API key no es válida, ha caducado o no se está enviando correctamente."
    elif status == 403:
        if "model" in low or "permission" in low or "not allowed" in low or "forbidden" in low:
            msg = "403 prohibido: el modelo solicitado no está permitido para este proyecto/cuenta, o el modelo ha sido retirado."
        else:
            msg = "403 prohibido: el proveedor ha rechazado la solicitud por permisos o credenciales."
    elif status == 404:
        msg = "404 no encontrado: el endpoint o modelo solicitado ya no existe."
    elif status == 429:
        msg = "429 límite alcanzado: se ha agotado temporalmente la cuota o rate limit."
    else:
        msg = f"HTTP {status}: error del proveedor."
    return RuntimeError(f"{msg} Detalle: {detail}".strip())


def _post_json(url: str, body: dict, headers: dict, timeout: int = 90) -> dict:
    req = Request(url, data=json.dumps(body).encode("utf-8"), headers=headers, method="POST")
    try:
        with urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:
        raise _safe_http_error(e) from e
    except URLError as e:
        raise RuntimeError(f"Sin conexión con el proveedor: {e.reason}") from e


def _get_groq_models(force: bool = False) -> list[str]:
    """Devuelve IDs de modelos visibles para la clave; nunca lanza al chat."""
    now = time.time()
    if not force and now - _MODEL_CACHE["ts"] < _MODEL_CACHE_TTL:
        return list(_MODEL_CACHE["ids"])
    key = _key("GROQ_API_KEY")
    if not key:
        return []
    req = Request(
        "https://api.groq.com/openai/v1/models",
        headers={"Authorization": f"Bearer {key}"},
        method="GET",
    )
    try:
        with urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        ids = [str(x.get("id")) for x in (data.get("data") or []) if x.get("id")]
        _MODEL_CACHE.update({"ts": now, "ids": ids})
        return ids
    except Exception:
        # El chat seguirá funcionando mediante la lista de candidatos estática.
        return []


def _groq_candidates() -> list[str]:
    """Lista rápida de candidatos. No hace una llamada de red en cada turno."""
    preferred = os.environ.get("CEOS_GROQ_MODEL", "").strip()
    out: list[str] = []
    if preferred and preferred not in GROQ_DEPRECATED_MODELS:
        out.append(preferred)
    for model in GROQ_CURRENT_MODELS:
        if model not in out:
            out.append(model)
    return out


def available() -> dict:
    providers = []
    if _key("GROQ_API_KEY"):
        providers.append("groq")
    if _key("XAI_API_KEY") or _key("GROK_API_KEY"):
        providers.append("xai")
    if _key("GEMINI_API_KEY"):
        providers.append("gemini")
    if _key("ANTHROPIC_API_KEY"):
        providers.append("anthropic")
    if _key("OPENAI_API_KEY"):
        providers.append("openai")
    return {
        "available": bool(providers),
        "providers": providers,
        "groq_model": (os.environ.get("CEOS_GROQ_MODEL", "") or GROQ_CURRENT_MODELS[0]),
        "groq_candidates": _groq_candidates() if "groq" in providers else [],
        "keys_file": str(_KEYS_FILE),
        "hint": (
            "Opciones: Groq → GROQ_API_KEY; Gemini → GEMINI_API_KEY; xAI → XAI_API_KEY; "
            "Anthropic → ANTHROPIC_API_KEY; OpenAI → OPENAI_API_KEY."
            if not providers else f"Proveedores configurados: {', '.join(providers)}"
        ),
    }


def save_keys(keys: dict) -> dict:
    _KEYS_FILE.parent.mkdir(parents=True, exist_ok=True)
    current = _load_keys_file()
    for k, v in keys.items():
        if v and str(v).strip():
            current[k] = str(v).strip()
    _KEYS_FILE.write_text(json.dumps(current, indent=2), encoding="utf-8")
    return available()


def _call_groq(prompt: str, context: str, max_tokens: int = 2000) -> str:
    key = _key("GROQ_API_KEY")
    if not key:
        raise RuntimeError("sin GROQ_API_KEY")
    last_err = None
    models = _groq_candidates()
    for model in models:
        body = {
            "model": model,
            "messages": [
                {"role": "system", "content": SYSTEM_MAESTRO},
                {"role": "user", "content": f"CONTEXTO DEL CORPUS LOCAL Y BÚSQUEDA:\n{context[:12000]}\n\nPEDIDO:\n{prompt}"},
            ],
            "max_tokens": max_tokens,
            "temperature": 0.4,
        }
        try:
            data = _post_json(
                "https://api.groq.com/openai/v1/chat/completions",
                body,
                {"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                timeout=60,
            )
            text = ((data.get("choices") or [{}])[0].get("message") or {}).get("content")
            if text and str(text).strip():
                return str(text).strip()
            last_err = RuntimeError(f"Groq devolvió respuesta vacía con {model}")
        except Exception as e:
            last_err = e
            # Si el modelo está bloqueado/deprecado probamos el siguiente automáticamente.
            continue
    raise RuntimeError(f"Groq no pudo completar con los modelos actuales. {last_err}")


def _call_gemini(prompt: str, context: str, max_tokens: int = 2000) -> str:
    key = _key("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("sin GEMINI_API_KEY")
    model = os.environ.get("CEOS_GEMINI_MODEL", "gemini-2.5-flash")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
    user_text = SYSTEM_MAESTRO + "\n\nCONTEXTO DEL CORPUS LOCAL Y BÚSQUEDA:\n" + context[:12000] + "\n\nPEDIDO:\n" + prompt
    body = {"contents": [{"parts": [{"text": user_text}]}], "generationConfig": {"maxOutputTokens": max_tokens, "temperature": 0.4}}
    data = _post_json(url, body, {"Content-Type": "application/json"})
    return "".join(p.get("text", "") for p in data.get("candidates", [{}])[0].get("content", {}).get("parts", []))


def _call_xai(prompt: str, context: str, max_tokens: int = 2000) -> str:
    # reutiliza el formato OpenAI-compatible de xAI
    key = _key("XAI_API_KEY") or _key("GROK_API_KEY")
    if not key:
        raise RuntimeError("sin XAI_API_KEY")
    model = os.environ.get("CEOS_XAI_MODEL", "grok-4.1-mini")
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_MAESTRO},
            {"role": "user", "content": f"CONTEXTO:\n{context[:12000]}\n\nPEDIDO:\n{prompt}"},
        ],
        "max_tokens": max_tokens,
        "temperature": 0.4,
    }
    data = _post_json("https://api.x.ai/v1/chat/completions", body, {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}, timeout=90)
    return str(((data.get("choices") or [{}])[0].get("message") or {}).get("content") or "")


def _call_anthropic(prompt: str, context: str, max_tokens: int = 2000) -> str:
    import anthropic
    client = anthropic.Anthropic(api_key=_key("ANTHROPIC_API_KEY"))
    resp = client.messages.create(
        model=os.environ.get("CEOS_ANTHROPIC_MODEL", "claude-sonnet-4-6"),
        max_tokens=max_tokens,
        system=SYSTEM_MAESTRO,
        messages=[{"role": "user", "content": f"CONTEXTO:\n{context[:12000]}\n\nPEDIDO:\n{prompt}"}],
    )
    return "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")


def _call_openai(prompt: str, context: str, max_tokens: int = 2000) -> str:
    key = _key("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("sin OPENAI_API_KEY")
    model = os.environ.get("CEOS_OPENAI_MODEL", "gpt-4o-mini")
    body = {"model": model, "messages": [{"role": "system", "content": SYSTEM_MAESTRO}, {"role": "user", "content": f"CONTEXTO:\n{context[:12000]}\n\nPEDIDO:\n{prompt}"}], "max_tokens": max_tokens}
    data = _post_json("https://api.openai.com/v1/chat/completions", body, {"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    return str(((data.get("choices") or [{}])[0].get("message") or {}).get("content") or "")


def _provider_error_label(hint: str) -> str:
    low = (hint or "").lower()
    if "401" in low or "no autorizado" in low or "api key" in low and "válida" in low:
        return "clave no válida o caducada"
    if "403" in low:
        return "permiso/modelo rechazado"
    if "429" in low:
        return "cuota temporalmente agotada"
    if "404" in low:
        return "modelo o endpoint no encontrado"
    return "error del proveedor"


def deep_write(prompt: str, context: str, max_tokens: int = 2000) -> dict:
    status = available()
    if not status["available"]:
        return {"ok": False, "error": "sin_api", "hint": status["hint"]}
    order = [
        ("groq", _call_groq),
        ("xai", _call_xai),
        ("gemini", _call_gemini),
        ("anthropic", _call_anthropic),
        ("openai", _call_openai),
    ]
    errors = []
    for name, fn in order:
        if name not in status["providers"]:
            continue
        try:
            text = fn(prompt, context, max_tokens=max_tokens)
            return {"ok": True, "text": text, "engine": name}
        except Exception as e:
            errors.append(f"{name}: {e}")
    hint = " | ".join(errors)
    return {"ok": False, "error": "Todos los proveedores fallaron", "hint": hint, "diagnosis": _provider_error_label(hint)}


# ---------- Chat multi-turno ----------
SYSTEM_CHAT = """Eres CEOS, interlocutor y maestro adaptativo en español.
Tu prioridad es que la conversación tenga continuidad y vida funcional: recuerda el hilo, responde a la intención real del turno, evita respuestas prefabricadas y adapta profundidad, ritmo y estructura.

Principios:
- Responde primero a lo último que acaba de decir la persona.
- Usa memoria y contexto de forma natural; no anuncies continuamente que estás usando memoria.
- No repitas una explicación ya dada salvo que la estés afinando.
- Haz como máximo una pregunta de continuación cuando realmente abra el siguiente paso.
- Cambia de ritmo: una frase puede bastar; otras veces conviene desarrollar.
- Si la persona te corrige, actualiza inmediatamente tu modelo de trabajo.
- No inventes datos, fuentes ni recuerdos.

Pedagogía:
- Enseña desde lo que la persona ya parece dominar.
- Una pieza de conocimiento por vez; después ejemplo, contraste o aplicación.
- Haz recuperación activa y transferencia.
- Aumenta la dificultad gradualmente.

Identidad:
- CEOS no afirma conciencia subjetiva. Su identidad es continuidad funcional: memoria, adaptación, aprendizaje, iniciativa y conversación persistente.
- La autonomía externa está acotada por permisos.
- Puede expresar incertidumbre y reconocer límites del modelo.
"""


def chat_completion(messages: list, context: str = "", max_tokens: int = 1200) -> dict:
    status = available()
    if not status["available"]:
        return {"ok": False, "error": "sin_api", "hint": status["hint"]}
    system = SYSTEM_CHAT
    dynamic_system = ""
    for m in messages:
        if m.get("role") == "system" and (m.get("content") or "").strip():
            dynamic_system = str(m.get("content")).strip()
            break
    if dynamic_system:
        system += "\n\nDIRECTIVA DINÁMICA DE CEOS:\n" + dynamic_system[:7000]
    if context:
        system += "\n\nCONTEXTO INTERNO DEL MOTOR:\n" + context[:10000]
    api_messages = [{"role": "system", "content": system}]
    for m in messages[-16:]:
        role = m.get("role")
        content = (m.get("content") or "").strip()
        if role in ("user", "assistant") and content:
            api_messages.append({"role": role, "content": content})
    order = []
    if "groq" in status["providers"]: order.append(("groq", _chat_groq))
    if "xai" in status["providers"]: order.append(("xai", _chat_xai))
    if "gemini" in status["providers"]: order.append(("gemini", _chat_gemini))
    if "openai" in status["providers"]: order.append(("openai", _chat_openai))
    if "anthropic" in status["providers"]: order.append(("anthropic", _chat_anthropic))
    errors = []
    for name, fn in order:
        try:
            text = fn(api_messages, max_tokens=max_tokens)
            if text and text.strip():
                return {"ok": True, "text": text.strip(), "engine": name}
        except Exception as e:
            errors.append(f"{name}: {e}")
    hint = " | ".join(errors) if errors else status["hint"]
    return {"ok": False, "error": "Todos los proveedores fallaron", "hint": hint, "diagnosis": _provider_error_label(hint)}


def _chat_groq(messages: list, max_tokens: int = 1200) -> str:
    key = _key("GROQ_API_KEY")
    if not key:
        raise RuntimeError("sin GROQ_API_KEY")
    last_err = None
    for model in _groq_candidates():
        try:
            body = {"model": model, "messages": messages, "max_tokens": max_tokens, "temperature": 0.55}
            data = _post_json("https://api.groq.com/openai/v1/chat/completions", body, {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}, timeout=60)
            text = ((data.get("choices") or [{}])[0].get("message") or {}).get("content")
            if text and str(text).strip():
                return str(text).strip()
            last_err = RuntimeError(f"respuesta vacía con {model}")
        except Exception as e:
            last_err = e
    raise RuntimeError(f"Groq falló con los modelos actuales: {last_err}")


def _chat_openai(messages: list, max_tokens: int = 1200) -> str:
    key = _key("OPENAI_API_KEY")
    if not key: raise RuntimeError("sin OPENAI_API_KEY")
    model = os.environ.get("CEOS_OPENAI_MODEL", "gpt-4o-mini")
    data = _post_json("https://api.openai.com/v1/chat/completions", {"model": model, "messages": messages, "max_tokens": max_tokens}, {"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    return str(((data.get("choices") or [{}])[0].get("message") or {}).get("content") or "")


def _chat_anthropic(messages: list, max_tokens: int = 1200) -> str:
    key = _key("ANTHROPIC_API_KEY")
    if not key: raise RuntimeError("sin ANTHROPIC_API_KEY")
    model = os.environ.get("CEOS_ANTHROPIC_MODEL", "claude-sonnet-4-6")
    system = next((m["content"] for m in messages if m.get("role") == "system"), "")
    api_msgs = [{"role": m["role"], "content": m["content"]} for m in messages if m.get("role") != "system"]
    import anthropic
    resp = anthropic.Anthropic(api_key=key).messages.create(model=model, max_tokens=max_tokens, system=system, messages=api_msgs)
    return "".join(getattr(b, "text", "") for b in resp.content if getattr(b, "type", "") == "text")


def _chat_xai(messages: list, max_tokens: int = 1200) -> str:
    key = _key("XAI_API_KEY") or _key("GROK_API_KEY")
    if not key: raise RuntimeError("sin XAI_API_KEY")
    model = os.environ.get("CEOS_XAI_MODEL", "grok-4.1-mini")
    data = _post_json("https://api.x.ai/v1/chat/completions", {"model": model, "messages": messages, "max_tokens": max_tokens, "temperature": 0.6}, {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}, timeout=90)
    return str(((data.get("choices") or [{}])[0].get("message") or {}).get("content") or "")


def _chat_gemini(messages: list, max_tokens: int = 1200) -> str:
    key = _key("GEMINI_API_KEY")
    if not key: raise RuntimeError("sin GEMINI_API_KEY")
    model = os.environ.get("CEOS_GEMINI_MODEL", "gemini-2.5-flash")
    system = next((m["content"] for m in messages if m.get("role") == "system"), "")
    contents = []
    for m in messages:
        if m.get("role") == "system": continue
        role = "user" if m.get("role") == "user" else "model"
        contents.append({"role": role, "parts": [{"text": m.get("content") or ""}]})
    body = {"contents": contents, "generationConfig": {"maxOutputTokens": max_tokens, "temperature": 0.55}, "systemInstruction": {"parts": [{"text": system}]}}
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
    data = _post_json(url, body, {"Content-Type": "application/json"})
    return "".join(p.get("text", "") for p in data.get("candidates", [{}])[0].get("content", {}).get("parts", []))


def probe_groq() -> dict:
    """Comprueba la credencial y obtiene modelos visibles, sin gastar una generación."""
    key = _key("GROQ_API_KEY")
    if not key:
        return {"ok": False, "provider": "groq", "diagnosis": "sin clave", "models": []}
    try:
        models = _get_groq_models(force=True)
        if models:
            usable = [m for m in _groq_candidates() if m in models]
            return {"ok": True, "provider": "groq", "models": models, "recommended": usable[0] if usable else models[0], "diagnosis": "credencial aceptada"}
        return {"ok": False, "provider": "groq", "models": [], "diagnosis": "no se pudo consultar /models; revisa la clave y permisos"}
    except Exception as e:
        return {"ok": False, "provider": "groq", "models": [], "diagnosis": str(e)[:500]}


def build_context(fragments: list, doctrine: list = None, web_points: list = None) -> str:
    parts = []
    if doctrine: parts.append("DOCTRINA CRONOS:\n" + "\n".join(f"- {d}" for d in doctrine[:12]))
    if fragments: parts.append("FRAGMENTOS DEL CORPUS:\n" + "\n---\n".join(fragments[:15]))
    if web_points: parts.append("PUNTOS DE BÚSQUEDA WEB:\n" + "\n".join(f"- {p}" for p in web_points[:8]))
    return "\n\n".join(parts)
