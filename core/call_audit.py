"""
Simulador de auditoría de llamadas + feedback E-C-A-M automático.
Entrada: transcripción (texto). Salida: matriz por dimensiones + feedback accionable.
"""
from __future__ import annotations
import re
from typing import Optional

DIMENSIONS = [
    ("apertura", "Apertura", ["hola", "buenos días", "buenas tardes", "mi nombre", "le atiende", "le llamo de", "soy de"]),
    ("diagnostico", "Diagnóstico", ["qué necesita", "en qué puedo", "cuénteme", "qué le interesa", "qué busca", "cuál es su"]),
    ("argumentacion", "Argumentación", ["porque", "beneficio", "incluye", "le permite", "ventaja", "programa", "titulación"]),
    ("objeciones", "Objeciones", ["entiendo", "comprendo", "respecto al precio", "comparar", "otra universidad", "caro", "descuento"]),
    ("cierre", "Cierre", ["siguiente paso", "agendamos", "le envío", "confirmamos", "matricular", "reserva", "cita"]),
    ("experiencia", "Experiencia", ["gracias", "disculpe", "por supuesto", "claro", "con gusto", "no se preocupe"]),
    ("compliance", "Compliance", ["privacidad", "datos personales", "protección de datos", "grabada", "autoriza", "consentimiento"]),
    ("resultado", "Resultado", ["matrícula", "lead", "cita", "envío de información", "compromiso", "quedamos"]),
]

# Señales de riesgo / mejora
RISKS = [
    (re.compile(r"descuento|rebaja|más barato", re.I), "objeciones",
     "Respuesta rápida a precio/descuento sin explorar la comparación."),
    (re.compile(r"\bno\s+(puedo|sé|tenemos)\b", re.I), "experiencia",
     "Negación directa sin alternativa o derivación."),
    (re.compile(r"\bespere|aguante|no me interrumpa\b", re.I), "experiencia",
     "Tono potencialmente de control excesivo o brusquedad."),
    (re.compile(r"\bgarantizo|100\s*%|siempre funciona\b", re.I), "compliance",
     "Promesa absoluta: revisar política comercial y compliance."),
]

STRENGTHS = [
    (re.compile(r"\b(entiendo|comprendo) (su|la)\b", re.I), "Validación de la preocupación del cliente."),
    (re.compile(r"\b(qué|cuál) (es|sería)\b", re.I), "Uso de preguntas (posible diagnóstico)."),
    (re.compile(r"\bgracias por\b", re.I), "Cortesía y reconocimiento."),
]


def _score_dimension(text: str, keywords: list[str]) -> tuple[int, list[str]]:
    low = text.lower()
    hits = [k for k in keywords if k in low]
    if not hits:
        return 1, []  # ausente / débil
    if len(hits) == 1:
        return 2, hits
    if len(hits) <= 3:
        return 3, hits
    return 4, hits[:5]


def audit_transcript(transcript: str, context: Optional[str] = None) -> dict:
    text = (transcript or "").strip()
    if len(text) < 40:
        return {"ok": False, "error": "Transcripción demasiado corta (mín. ~40 caracteres)."}

    dims = []
    total = 0
    evidence_notes = []
    for key, label, kws in DIMENSIONS:
        score, hits = _score_dimension(text, kws)
        total += score
        dims.append({
            "id": key,
            "label": label,
            "score": score,  # 1-4
            "max": 4,
            "hits": hits,
            "comment": (
                "Sin señales claras en el texto." if score == 1 else
                "Presencia básica." if score == 2 else
                "Aceptable / varias señales." if score == 3 else
                "Fuerte presencia de indicadores."
            ),
        })

    risks = []
    for pat, dim, msg in RISKS:
        if pat.search(text):
            risks.append({"dimension": dim, "message": msg})

    strengths = []
    for pat, msg in STRENGTHS:
        if pat.search(text):
            strengths.append(msg)

    # E-C-A-M automático sobre el riesgo principal o dimensión más baja
    lowest = sorted(dims, key=lambda d: d["score"])[:2]
    primary_risk = risks[0] if risks else None
    if primary_risk:
        ecam = {
            "evidencia": primary_risk["message"] + " (detectado en la transcripción).",
            "consecuencia": (
                "Puede erosionar confianza, reducir exploración de necesidad "
                "o generar riesgo de calidad/compliance según el caso."
            ),
            "alternativa": (
                "Validar → preguntar qué compara o qué teme → conectar valor "
                "y solo entonces hablar de precio/condiciones."
                if "precio" in primary_risk["message"].lower() or primary_risk["dimension"] == "objeciones"
                else "Nombrar el hecho, ofrecer alternativa concreta y comprobar aceptación."
            ),
            "medicion": (
                "En las próximas 10 interacciones, registrar si se explora antes de ofertar "
                "y el resultado (avance / pérdida)."
            ),
        }
    else:
        weak = lowest[0]["label"] if lowest else "Diagnóstico"
        ecam = {
            "evidencia": f"La dimensión «{weak}» muestra pocas señales explícitas en el texto.",
            "consecuencia": "Sin esa conducta, el asesor improvisa y el resultado es menos predecible.",
            "alternativa": f"Entrenar una frase estándar de «{weak}» y practicarla en role play.",
            "medicion": f"Auditar 5 llamadas centradas solo en «{weak}» esta semana.",
        }

    pct = round(100 * total / (len(DIMENSIONS) * 4))
    coaching_focus = [d["label"] for d in lowest]

    summary = (
        f"Puntuación orientativa {total}/{len(DIMENSIONS)*4} ({pct}%). "
        f"Foco de coaching sugerido: {', '.join(coaching_focus)}. "
        "Esta auditoría es un simulador didáctico sobre texto; no sustituye la matriz oficial del contact center."
    )

    return {
        "ok": True,
        "summary": summary,
        "score_total": total,
        "score_max": len(DIMENSIONS) * 4,
        "percent": pct,
        "dimensions": dims,
        "risks": risks,
        "strengths": strengths[:5],
        "ecam": ecam,
        "coaching_focus": coaching_focus,
        "context": context or "",
    }
