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

# En CEOS, "pt" significa portugués europeo (Portugal), no portugués brasileño.
# Se priorizan formas útiles para viajes y entorno profesional internacional.

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

# Correcciones orientadas a hispanohablantes para portugués europeo.
# No se tratan como "errores absolutos" las formas brasileñas válidas: cuando la
# diferencia es de variedad, la explicación lo deja explícito y se propone la
# forma preferida en Portugal por utilidad laboral.
CORRECTIONS_PT = [
    (re.compile(r"\b(formação|formacao)\s+t[eé]cnica\b", re.I), "formação técnica", "Esta forma es correcta en Portugal; evita la grafía española 'formación'."),
    (re.compile(r"\bformaci[oó]n\b", re.I), "formação", "En portugués: 'formação'."),
    (re.compile(r"\bgesti[oó]n\b", re.I), "gestão", "En portugués: 'gestão'."),
    (re.compile(r"\baplicaci[oó]n\b", re.I), "aplicação", "En portugués: 'aplicação'."),
    (re.compile(r"\binformaci[oó]n\b", re.I), "informação", "En portugués: 'informação'."),
    (re.compile(r"\borganizaci[oó]n\b", re.I), "organização", "En portugués: 'organização'."),
    (re.compile(r"\boperaci[oó]n\b", re.I), "operação", "En portugués: 'operação'."),
    (re.compile(r"\bequipo\b", re.I), "equipa", "En Portugal, 'equipa' es la forma habitual en este contexto profesional."),
    (re.compile(r"\busuario\b", re.I), "utilizador", "En Portugal, 'utilizador' es la forma preferida para 'user' en tecnología/procesos."),
    (re.compile(r"\b(actualmente)\b", re.I), "atualmente", "En portugués europeo: 'atualmente' (no 'actualmente')."),
    (re.compile(r"\bestoy\s+(\w+ando|\w+iendo)\b", re.I), "estou a + infinitivo", "En portugués europeo se prefiere 'estar a + infinitivo': 'estou a trabalhar'."),
    (re.compile(r"\btenho\s+experiencia\b", re.I), "tenho experiência", "La forma natural en Portugal lleva 'ê': experiência."),
    (re.compile(r"\btrabalho\s+em\s+equipe\b", re.I), "trabalho em equipa", "Para Portugal, usa 'equipa'."),
    (re.compile(r"\bdisponibilidade\s+para\s+viajar\b", re.I), "tenho disponibilidade para viajar", "En una entrevista suena más completo con el verbo: 'tenho disponibilidade para viajar'."),
    (re.compile(r"\bcom\s+voc[eê]\b", re.I), "consigo", "En portugués europeo formal, 'consigo' suele sonar más natural que 'com você'."),
]


def _corrections(text: str, target: str) -> list[dict]:
    out = []
    if target == "en":
        for pat, corr, exp in CORRECTIONS_EN:
            if pat.search(text):
                out.append({"original": pat.pattern, "corrected": corr, "explanation": exp})
    elif target == "pt":
        for pat, corr, exp in CORRECTIONS_PT:
            if pat.search(text):
                out.append({"original": pat.pattern, "corrected": corr, "explanation": exp})
    return out[:4]


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



def _to_castellano(text: str, context: str = "") -> str:
    """Traduce al castellano el mensaje del compañero (LLM si hay clave; si no, nota honesta)."""
    text = (text or "").strip()
    if not text:
        return ""
    status = llm_available()
    if status.get("available"):
        try:
            r = chat_completion(
                [
                    {
                        "role": "system",
                        "content": (
                            "Traduce al castellano de España el siguiente texto. "
                            "Solo la traducción, sin comillas ni comentarios. "
                            "Mantén el tono conversacional."
                        ),
                    },
                    {"role": "user", "content": text[:1500]},
                ],
                max_tokens=400,
            )
            out = (r or "").strip()
            if out:
                return out
        except Exception:
            pass
    # Sin API: glosa mínima honesta (no inventar traducción palabra a palabra falsa)
    return (
        "(Traducción automática no disponible sin API gratuita configurada. "
        "Texto original arriba. Activa Groq/Gemini en Maestro para traducir al castellano.)"
    )


def reply_turn(
    *,
    role_id: str,
    target_lang: str,
    user_text: str,
    history: list[dict],
    native_lang: str = "es",
    long: bool = False,
    translate_es: bool = True,
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
        if tl == "pt":
            sys += (
                " Use European Portuguese (Portugal), not Brazilian Portuguese. "
                "Prefer natural spoken Portugal forms such as 'equipa', 'utilizador', "
                "'ficheiro', 'ecrã', 'telemóvel', and 'estar a + infinitivo'. "
                "Keep the language practical and contemporary; do not sound like a textbook."
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

    partner_es = ""
    if translate_es and tl != "es" and partner:
        partner_es = _to_castellano(partner)
    elif translate_es and tl == "es":
        partner_es = partner

    pt_focus = []
    if tl == "pt":
        pt_focus = [
            "Português europeu (Portugal)",
            "Vocabulário profissional: formação, gestão, melhoria contínua, aplicação, utilizador, equipa",
            "Entorno Prosegur: UAT, manuais/guias, implementação, suporte, processos e deslocações Espanha-Portugal",
        ]
    return {
        "ok": True,
        "partner_message": partner,
        "partner_message_es": partner_es,
        "corrections": corrections,
        "pt_focus": pt_focus,
        "chunks": chunks,
        "suggestions": (role.get("suggestions") or {}).get(tl) or [],
        "engine": engine,
        "role_id": role_id,
        "target_lang": tl,
        "translate_es": bool(translate_es),
    }


def roles_payload() -> dict:
    return {"ok": True, "roles": list_roles()}
