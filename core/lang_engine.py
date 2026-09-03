"""
Motor de práctica de idiomas (CEOX) integrado en CEOS.
Usa memoria larga, códice fractal y opcionalmente LLM (Groq/Gemini).
"""
from __future__ import annotations
import re
from typing import Optional
from .lang_scenarios import get_role, list_roles
from .llm_bridge import available as llm_available, chat_completion

TARGET = ("en", "es", "fr", "it", "pt")

# Correcciones frecuentes EN (aprendices hispanohablantes)
CORRECTIONS_EN = [
    (re.compile(r"\bi am been\b", re.I), "I have been", "Se usa 'have been', no 'am been'."),
    (re.compile(r"\bi have \d+ years?\b", re.I), "I am … years old", "La edad: 'I am 30 years old', no 'I have 30 years'."),
    (re.compile(r"\bfor to\b", re.I), "to", "No se dice 'for to'; solo 'to' + verbo."),
    (re.compile(r"\bthe people is\b", re.I), "the people are", "'People' va en plural: are."),
    (re.compile(r"\bi am agree\b", re.I), "I agree", "Se dice 'I agree', no 'I am agree'."),
    (re.compile(r"\bdepend of\b", re.I), "depend on", "Es 'depend on', no 'depend of'."),
    (re.compile(r"\bhe go\b", re.I), "he goes", "3ª persona: goes, not go."),
    (re.compile(r"\bshe go\b", re.I), "she goes", "3ª persona: goes, not go."),
]


def _corrections(text: str, target: str) -> list[dict]:
    out = []
    if target == "en":
        for pat, corr, exp in CORRECTIONS_EN:
            if pat.search(text):
                out.append({"original": pat.pattern, "corrected": corr, "explanation": exp})
    return out[:3]


def start_session(role_id: str, target_lang: str = "en") -> dict:
    role = get_role(role_id)
    if not role:
        return {"ok": False, "error": "rol desconocido"}
    tl = target_lang if target_lang in TARGET else "en"
    opener = role["opener"].get(tl) or role["opener"].get("en", "")
    suggestions = role["suggestions"].get(tl) or role["suggestions"].get("en", [])
    return {
        "ok": True,
        "role": {"id": role["id"], "name_es": role["name_es"], "persona": role["persona"], "setting": role["setting"], "goal": role["goal"]},
        "target_lang": tl,
        "partner_message": opener,
        "suggestions": suggestions,
    }


def reply_turn(
    *,
    role_id: str,
    target_lang: str,
    user_text: str,
    history: list[dict],
    native_lang: str = "es",
    long: bool = False,
    codex=None,
    long_memory=None,
) -> dict:
    user_text = (user_text or "").strip()
    if not user_text:
        return {"ok": False, "error": "mensaje vacío"}
    role = get_role(role_id) or get_role("friends")
    tl = target_lang if target_lang in TARGET else "en"
    corrections = _corrections(user_text, tl)

    # Memoria + códice
    if long_memory is not None:
        try:
            long_memory.absorb_turn(user_text, "", do_facts=True, do_topics=True)
        except Exception:
            pass
    chunks = []
    if codex is not None:
        try:
            for s in (role.get("suggestions") or {}).get(tl) or []:
                codex.store_crystal(s, kind="lang_chunk", meta={"topic": f"lang:{role_id}", "lang": tl})
            if corrections:
                for c in corrections:
                    codex.store_crystal(
                        f"{c['corrected']} — {c['explanation']}",
                        kind="lang_fix",
                        meta={"topic": f"lang:{role_id}", "lang": tl},
                    )
            try:
                codex.maybe_fractal_after_ingest(f"lang:{role_id}")
            except Exception:
                pass
            chunks = [{"phrase": s, "meaning": "Sugerencia del escenario"} for s in ((role.get("suggestions") or {}).get(tl) or [])[:2]]
        except Exception:
            pass

    partner = None
    engine = "local"
    # LLM si hay clave
    status = llm_available()
    if status.get("available"):
        sys = (
            f"You are a conversation partner for language practice. "
            f"Role: {role['persona']}. Setting: {role['setting']}. Goal: {role['goal']}. "
            f"Speak ONLY in {tl}. Short turns (under 40 words). One question max. "
            f"Learner native language for corrections: {native_lang}."
        )
        if long:
            sys += " Slightly longer, richer reply still under 80 words."
        msgs = [{"role": "system", "content": sys}]
        for h in history[-10:]:
            role_h = h.get("role")
            content = (h.get("content") or "").strip()
            if role_h == "user" and content:
                msgs.append({"role": "user", "content": content})
            elif role_h in ("partner", "assistant") and content:
                msgs.append({"role": "assistant", "content": content})
        msgs.append({"role": "user", "content": user_text})
        result = chat_completion(
            [{"role": m["role"], "content": m["content"]} for m in msgs if m["role"] != "system"],
            context=sys,
            max_tokens=400 if not long else 700,
        )
        if result.get("ok") and result.get("text"):
            partner = result["text"].strip()
            engine = result.get("engine", "llm")

    if not partner:
        # Local scripted continuation
        suggestions = (role.get("suggestions") or {}).get(tl) or []
        if "yes" in user_text.lower() or "sí" in user_text.lower() or "ok" in user_text.lower():
            partner = suggestions[0] if suggestions else ("Okay. Tell me more." if tl == "en" else "Vale. Cuéntame más.")
        else:
            partner = {
                "en": "I see. What would you like to do next?",
                "es": "Entiendo. ¿Qué te gustaría hacer ahora?",
                "fr": "Je vois. Tu veux faire quoi ensuite ?",
                "it": "Capisco. Cosa vuoi fare adesso?",
                "pt": "Entendi. O que você quer fazer agora?",
            }.get(tl, "Okay. Go on.")
        # If user wrote in native by mistake, nudge
        if tl == "en" and re.search(r"[áéíóúñ¿¡]", user_text):
            partner = "Try saying that in English — I can help. " + partner

    return {
        "ok": True,
        "partner_message": partner,
        "corrections": corrections,
        "chunks": chunks,
        "suggestions": (role.get("suggestions") or {}).get(tl) or [],
        "engine": engine,
        "role_id": role_id,
        "target_lang": tl,
    }


def roles_payload() -> dict:
    return {"ok": True, "roles": list_roles()}
