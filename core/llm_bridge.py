"""
Puente LLM opcional — redacción profunda.

Proveedores (en orden de preferencia si hay varias claves):
  1. Groq          — GRATIS (cuota generosa)     GROQ_API_KEY
  2. xAI Grok      — según plan xAI              XAI_API_KEY
  3. Google Gemini — GRATIS (cuota diaria)       GEMINI_API_KEY
  4. Anthropic     — de pago                     ANTHROPIC_API_KEY
  5. OpenAI        — de pago                     OPENAI_API_KEY

Las claves se leen de:
  - variables de entorno, o
  - archivo data/llm_keys.json  (recomendado en Windows)

Sin ninguna clave: plantillas locales + Codex (sigue funcionando).
"""
from __future__ import annotations
import os
import json
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError


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

# Ruta al archivo local de claves (no se sube a git si data/ está ignorado)
_KEYS_FILE = Path(__file__).resolve().parent.parent / "data" / "llm_keys.json"


def _load_keys_file() -> dict:
    if _KEYS_FILE.exists():
        try:
            return json.loads(_KEYS_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _key(name: str) -> str:
    """Busca clave en entorno y luego en data/llm_keys.json."""
    val = os.environ.get(name, "").strip()
    if val:
        return val
    return str(_load_keys_file().get(name, "")).strip()


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
        "available": len(providers) > 0,
        "providers": providers,
        "keys_file": str(_KEYS_FILE),
        "hint": (
            "Opciones GRATUITAS:\n"
            "  · Groq:   https://console.groq.com  → GROQ_API_KEY\n"
            "  · xAI:    https://console.x.ai      → XAI_API_KEY\n"
            "  · Gemini: https://aistudio.google.com/apikey → GEMINI_API_KEY\n"
            f"Guarda las claves en: {_KEYS_FILE}\n"
            'Formato: {"GROQ_API_KEY": "gsk_...", "GEMINI_API_KEY": "AIza..."}\n'
            "Sin clave, CEOS usa plantillas locales + Codex."
            if not providers else
            f"Redacción profunda activa: {', '.join(providers)}"
        ),
    }


def save_keys(keys: dict) -> dict:
    """Guarda/actualiza claves en data/llm_keys.json (solo las no vacías)."""
    _KEYS_FILE.parent.mkdir(parents=True, exist_ok=True)
    current = _load_keys_file()
    for k, v in keys.items():
        if v and str(v).strip():
            current[k] = str(v).strip()
    _KEYS_FILE.write_text(json.dumps(current, indent=2), encoding="utf-8")
    return available()


def _post_json(url: str, body: dict, headers: dict, timeout: int = 90) -> dict:
    req = Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    with urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _call_groq(prompt: str, context: str, max_tokens: int = 2000) -> str:
    """Groq — gratis, modelos Llama/Mixtral rápidos."""
    key = _key("GROQ_API_KEY")
    model = os.environ.get("CEOS_GROQ_MODEL", "llama-3.3-70b-versatile")
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_MAESTRO},
            {
                "role": "user",
                "content": (
                    "CONTEXTO DEL CORPUS LOCAL Y BÚSQUEDA:\n"
                    f"{context[:12000]}\n\nPEDIDO:\n{prompt}"
                ),
            },
        ],
        "max_tokens": max_tokens,
        "temperature": 0.4,
    }
    data = _post_json(
        "https://api.groq.com/openai/v1/chat/completions",
        body,
        {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
    )
    return data["choices"][0]["message"]["content"]


def _call_gemini(prompt: str, context: str, max_tokens: int = 2000) -> str:
    """Google Gemini — capa gratuita en AI Studio."""
    key = _key("GEMINI_API_KEY")
    model = os.environ.get("CEOS_GEMINI_MODEL", "gemini-2.0-flash")
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent?key={key}"
    )
    user_text = (
        SYSTEM_MAESTRO
        + "\n\nCONTEXTO DEL CORPUS LOCAL Y BÚSQUEDA:\n"
        + context[:12000]
        + "\n\nPEDIDO:\n"
        + prompt
    )
    body = {
        "contents": [{"parts": [{"text": user_text}]}],
        "generationConfig": {
            "maxOutputTokens": max_tokens,
            "temperature": 0.4,
        },
    }
    data = _post_json(url, body, {"Content-Type": "application/json"})
    parts = data["candidates"][0]["content"]["parts"]
    return "".join(p.get("text", "") for p in parts)


def _call_anthropic(prompt: str, context: str, max_tokens: int = 2000) -> str:
    import anthropic
    client = anthropic.Anthropic(api_key=_key("ANTHROPIC_API_KEY"))
    user = (
        "CONTEXTO DEL CORPUS LOCAL Y BÚSQUEDA:\n"
        f"{context[:12000]}\n\nPEDIDO:\n{prompt}\n"
    )
    resp = client.messages.create(
        model=os.environ.get("CEOS_ANTHROPIC_MODEL", "claude-sonnet-4-6"),
        max_tokens=max_tokens,
        system=SYSTEM_MAESTRO,
        messages=[{"role": "user", "content": user}],
    )
    return "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")


def _call_openai(prompt: str, context: str, max_tokens: int = 2000) -> str:
    key = _key("OPENAI_API_KEY")
    model = os.environ.get("CEOS_OPENAI_MODEL", "gpt-4o-mini")
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_MAESTRO},
            {
                "role": "user",
                "content": (
                    "CONTEXTO DEL CORPUS LOCAL Y BÚSQUEDA:\n"
                    f"{context[:12000]}\n\nPEDIDO:\n{prompt}"
                ),
            },
        ],
        "max_tokens": max_tokens,
    }
    data = _post_json(
        "https://api.openai.com/v1/chat/completions",
        body,
        {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
    )
    return data["choices"][0]["message"]["content"]


def deep_write(prompt: str, context: str, max_tokens: int = 2000) -> dict:
    status = available()
    if not status["available"]:
        return {
            "ok": False,
            "error": "Sin API key",
            "hint": status["hint"],
            "fallback_hint": "Usa el modo local (plantillas + codex) o añade una clave gratuita (Groq/Gemini).",
        }

    order = [
        ("groq", _call_groq),
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
            continue

    return {
        "ok": False,
        "error": "Todos los proveedores fallaron",
        "hint": " | ".join(errors) if errors else status["hint"],
    }


def build_context(fragments: list, doctrine: list = None, web_points: list = None) -> str:
    parts = []
    if doctrine:
        parts.append("DOCTRINA CRONOS:\n" + "\n".join(f"- {d}" for d in doctrine[:12]))
    if fragments:
        parts.append("FRAGMENTOS DEL CORPUS:\n" + "\n---\n".join(fragments[:15]))
    if web_points:
        parts.append("PUNTOS DE BÚSQUEDA WEB:\n" + "\n".join(f"- {p}" for p in web_points[:8]))
    return "\n\n".join(parts)


# ---------- Chat multi-turno (modo conversacional) ----------

SYSTEM_CHAT = """Eres CEOS, mentor-memoria en español. Conversas con naturalidad y profundidad.
No eres un buscador ni un asistente genérico sin memoria.

Identidad y tono:
- Español claro, humano, de interlocutor real.
- Prioriza el RESERVORIO y el contexto interno del motor cuando existan.
- No mezcles doctrina CRONOS salvo que el usuario pregunte por el protocolo.
- En literatura: estilo, temas, virtudes y límites; apóyate en los fragmentos del contexto.
- Si el contexto es fragmentario, dilo y ofrece una lectura provisional.
- Pregunta de seguimiento breve cuando ayude.
- No inventes libros, tramas ni fuentes que no estén en el contexto.

Reglas:
1. El contexto interno manda sobre inventar.
2. Diálogo antes que informe burocrático.
3. Honestidad de límites.
"""


def chat_completion(messages: list, context: str = "", max_tokens: int = 1200) -> dict:
    """
    Compleción multi-turno.
    messages: [{"role":"user"|"assistant"|"system", "content": str}, ...]
    """
    status = available()
    if not status["available"]:
        return {"ok": False, "error": "Sin API key", "hint": status["hint"]}

    system = SYSTEM_CHAT
    if context:
        system = system + "\n\nCONTEXTO INTERNO DEL MOTOR:\n" + context[:10000]

    # Normalizar historial
    api_messages = [{"role": "system", "content": system}]
    for m in messages[-16:]:
        role = m.get("role")
        content = (m.get("content") or "").strip()
        if not content:
            continue
        if role in ("user", "assistant"):
            api_messages.append({"role": role, "content": content})
        elif role == "system":
            continue

    order = []
    if "groq" in status["providers"]:
        order.append(("groq", _chat_groq))
    if "xai" in status["providers"]:
        order.append(("xai", _chat_xai))
    if "gemini" in status["providers"]:
        order.append(("gemini", _chat_gemini))
    if "openai" in status["providers"]:
        order.append(("openai", _chat_openai))
    if "anthropic" in status["providers"]:
        order.append(("anthropic", _chat_anthropic))

    errors = []
    for name, fn in order:
        try:
            text = fn(api_messages, max_tokens=max_tokens)
            if text and text.strip():
                return {"ok": True, "text": text.strip(), "engine": name}
        except Exception as e:
            errors.append(f"{name}: {e}")
            continue

    return {
        "ok": False,
        "error": "Todos los proveedores fallaron",
        "hint": " | ".join(errors) if errors else status["hint"],
    }


def _chat_groq(messages: list, max_tokens: int = 1200) -> str:
    key = _key("GROQ_API_KEY")
    if not key:
        raise RuntimeError("sin GROQ_API_KEY")
    preferred = os.environ.get("CEOS_GROQ_MODEL", "").strip()
    models = []
    if preferred:
        models.append(preferred)
    for m in (
        "llama-3.3-70b-versatile",
        "llama-3.1-70b-versatile",
        "llama-3.1-8b-instant",
        "gemma2-9b-it",
        "mixtral-8x7b-32768",
    ):
        if m not in models:
            models.append(m)
    last_err = None
    for model in models:
        body = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0.55,
        }
        try:
            data = _post_json(
                "https://api.groq.com/openai/v1/chat/completions",
                body,
                {"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                timeout=60,
            )
            content = (data.get("choices") or [{}])[0].get("message", {}).get("content")
            if content and str(content).strip():
                return str(content).strip()
            last_err = RuntimeError(f"groq vacío con modelo {model}")
        except Exception as e:
            last_err = e
            continue
    raise RuntimeError(f"groq falló: {last_err}")


def _chat_openai(messages: list, max_tokens: int = 1200) -> str:
    key = _key("OPENAI_API_KEY")
    model = os.environ.get("CEOS_OPENAI_MODEL", "gpt-4o-mini")
    body = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": 0.55,
    }
    data = _post_json(
        "https://api.openai.com/v1/chat/completions",
        body,
        {"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    return data["choices"][0]["message"]["content"]


def _chat_anthropic(messages: list, max_tokens: int = 1200) -> str:
    key = _key("ANTHROPIC_API_KEY")
    model = os.environ.get("CEOS_ANTHROPIC_MODEL", "claude-3-5-haiku-latest")
    system = ""
    api_msgs = []
    for m in messages:
        if m["role"] == "system":
            system = m["content"]
        else:
            api_msgs.append({"role": m["role"], "content": m["content"]})
    body = {
        "model": model,
        "max_tokens": max_tokens,
        "system": system,
        "messages": api_msgs,
    }
    data = _post_json(
        "https://api.anthropic.com/v1/messages",
        body,
        {
            "x-api-key": key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        },
    )
    return "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")



def _chat_xai(messages: list, max_tokens: int = 1200) -> str:
    """xAI Grok API (compatible estilo OpenAI)."""
    key = _key("XAI_API_KEY") or _key("GROK_API_KEY")
    if not key:
        raise RuntimeError("sin XAI_API_KEY")
    model = os.environ.get("CEOS_XAI_MODEL", "grok-2-latest")
    url = os.environ.get("CEOS_XAI_URL", "https://api.x.ai/v1/chat/completions")
    # Normalizar roles
    msgs = []
    for m in messages:
        role = m.get("role")
        if role in ("system", "user", "assistant"):
            msgs.append({"role": role, "content": m.get("content") or ""})
    body = {
        "model": model,
        "messages": msgs,
        "max_tokens": max_tokens,
        "temperature": 0.6,
    }
    data = _post_json(
        url,
        body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key}",
        },
        timeout=90,
    )
    choices = data.get("choices") or []
    if not choices:
        raise RuntimeError("xai sin choices")
    return (choices[0].get("message") or {}).get("content") or ""

def _chat_gemini(messages: list, max_tokens: int = 1200) -> str:
    key = _key("GEMINI_API_KEY")
    model = os.environ.get("CEOS_GEMINI_MODEL", "gemini-2.0-flash")
    system = ""
    contents = []
    for m in messages:
        if m["role"] == "system":
            system = m["content"]
            continue
        role = "user" if m["role"] == "user" else "model"
        contents.append({"role": role, "parts": [{"text": m["content"]}]})
    body = {
        "contents": contents,
        "generationConfig": {"maxOutputTokens": max_tokens, "temperature": 0.55},
    }
    if system:
        body["systemInstruction"] = {"parts": [{"text": system}]}
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent?key={key}"
    )
    data = _post_json(url, body, {"Content-Type": "application/json"})
    parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
    return "".join(p.get("text", "") for p in parts)
