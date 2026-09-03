"""
Puente LLM opcional — redacción profunda.

Proveedores (en orden de preferencia si hay varias claves):
  1. Groq          — GRATIS (cuota generosa)     GROQ_API_KEY
  2. Google Gemini — GRATIS (cuota diaria)       GEMINI_API_KEY
  3. Anthropic     — de pago                     ANTHROPIC_API_KEY
  4. OpenAI        — de pago                     OPENAI_API_KEY

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

SYSTEM_CHAT = """Eres CEOS, el Motor CRONOS-Espiral en modo conversacional.
No eres un asistente genérico.

Identidad y tono:
- Español claro, directo y humano.
- Mentor del protocolo CRONOS: preciso, operativo, sin adornos vacíos.
- Mensajes de conversación real: relativamente cortos salvo que pidan profundidad.
- Puedes hacer una pregunta de seguimiento cuando ayude.
- Si el usuario saluda o habla en casual, respondes con naturalidad y luego ofreces valor.
- No empieces con "Como CEOS..." ni con disculpas innecesarias.

Reglas:
1. Usa el contexto interno que se te da (doctrina, Codex, casos, perfil).
2. Vocabulario CRONOS cuando aplique (Cronos/Vórtice, regímenes, operaciones, Espiral).
3. Si algo no está en el contexto y no es conocimiento general seguro, dilo.
4. No inventes citas ni fuentes.
5. Prioriza el diálogo frente a documentos largos.
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
    model = os.environ.get("CEOS_GROQ_MODEL", "llama-3.3-70b-versatile")
    body = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": 0.55,
    }
    data = _post_json(
        "https://api.groq.com/openai/v1/chat/completions",
        body,
        {"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    return data["choices"][0]["message"]["content"]


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
