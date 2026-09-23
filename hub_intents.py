"""
Intents del hub conversacional: identidad, reservorio, informes, ayuda.
Evita obligar al usuario a saltar entre pestañas para lo básico.
"""
from __future__ import annotations
import re
from typing import Any, Optional


def _strip(s: str) -> str:
    return (s or "").strip()


def match_name_declaration(text: str) -> Optional[str]:
    t = _strip(text)
    patterns = [
        r"(?i)^me\s+llamo\s+(.+?)(?:\.|$)",
        r"(?i)^soy\s+([A-ZÁÉÍÓÚÑ][\wÁÉÍÓÚáéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][\wÁÉÍÓÚáéíóúñ]+){0,4})\s*$",
        r"(?i)^mi\s+nombre\s+es\s+(.+?)(?:\.|$)",
        r"(?i)^puedes\s+llamarme\s+(.+?)(?:\.|$)",
        r"(?i)^ll[aá]mame\s+(.+?)(?:\.|$)",
        r"(?i)^identif[ií]came\s+como\s+(.+?)(?:\.|$)",
    ]
    for p in patterns:
        m = re.search(p, t)
        if m:
            name = m.group(1).strip(" .,!¿?¡")
            # rechazar frases, no nombres compuestos (p. ej. «de la Fuente»)
            if len(name) < 2 or len(name) > 60:
                continue
            if re.search(r"\b(porque|quiero|necesito|sobre|libro|estilo)\b", name.lower()):
                continue
            return name
    return None


def match_library_list(text: str) -> bool:
    low = text.lower()
    return bool(
        re.search(
            r"(qu[eé]\s+(hay|tienes|documentos|libros)|lista(r)?\s+(el\s+)?reservorio|"
            r"mis\s+libros|documentos\s+cargados|qu[eé]\s+tienes\s+en\s+(el\s+)?reservorio|"
            r"mostrar\s+(biblioteca|reservorio)|inventario\s+de\s+(libros|docs))",
            low,
        )
    )


def match_research_report(text: str) -> Optional[str]:
    t = _strip(text)
    low = t.lower()
    m = re.search(
        r"(?i)(?:investiga(?:r)?|informe\s+(?:sobre|de)|busca(?:r)?\s+(?:en\s+internet\s+)?(?:sobre\s+)?|"
        r"haz(?:me)?\s+un\s+informe\s+(?:sobre|de)|research)\s+(.+)$",
        t,
    )
    if m:
        topic = m.group(1).strip(" .,")
        if len(topic) >= 3:
            return topic
    if re.search(r"(?i)^informe:\s*(.+)", t):
        return re.search(r"(?i)^informe:\s*(.+)", t).group(1).strip()
    return None


def match_help_capabilities(text: str) -> bool:
    low = text.lower()
    return bool(
        re.search(
            r"(qu[eé]\s+puedes\s+hacer|c[oó]mo\s+te\s+uso|c[oó]mo\s+funciona(?:s)?|"
            r"ayuda(?:me)?$|qu[eé]\s+s[eé]\s+hacer|comandos|gu[ií]a\s+r[aá]pida)",
            low,
        )
    )


def help_text() -> str:
    return (
        "Operativa simple — casi todo desde este **Chat**:\n\n"
        "1. **Nombre:** `Me llamo David`\n"
        "2. **Subir libros:** 📎 o «Subir docs» (varias tandas se acumulan)\n"
        "3. **Comprobar:** `Qué hay en el reservorio`\n"
        "4. **Aprender / analizar:** habla en naturalidad o `Investiga …`\n"
        "5. **No perder memoria (Render free):** Sync → Descargar copia completa\n\n"
        "Límites prácticos: ~40 MB por archivo; muchos archivos en lotes. "
        "Maestro tiene el mismo subidor. Coaching e Idiomas son opcionales."
    )


def library_list_text(library) -> str:
    if library is None:
        return "No tengo acceso al reservorio en este momento."
    try:
        docs = library.list_docs() or []
        st = library.stats() if hasattr(library, "stats") else {}
    except Exception as e:
        return f"No pude leer el reservorio: {e}"
    if not docs:
        return (
            "El reservorio está vacío. Sube PDF/DOCX/TXT con el 📎 de este chat "
            "(o «Subir docs») y podré hablar de tu material."
        )
    lines = [
        f"En el reservorio hay **{st.get('docs', len(docs))} documento(s)**, "
        f"~{st.get('chars', 0)} caracteres:\n"
    ]
    for d in docs[-20:]:
        title = d.get("title") or d.get("source_name") or "sin título"
        author = d.get("author") or ""
        chunks = d.get("chunks") or "?"
        lines.append(f"· {title}" + (f" — {author}" if author else "") + f" ({chunks} trozos)")
    lines.append("\nPuedes pedirme un informe sobre uno de ellos o preguntar por estilo, temas o personajes.")
    return "\n".join(lines)


def handle_hub_intent(
    text: str,
    *,
    user=None,
    library=None,
    research_fn=None,
) -> Optional[dict[str, Any]]:
    """
    Si el mensaje es un intent de hub, devuelve dict listo para reply().
    Si no, None (seguir flujo normal).
    """
    text = _strip(text)
    if not text:
        return None

    # 1) Nombre
    name = match_name_declaration(text)
    if name and user is not None:
        try:
            user.set_name(name)
            return {
                "ok": True,
                "reply": (
                    f"Perfecto, te recordaré como **{name}**. "
                    "Ya puedes hablarme de tus textos o subir documentos con el 📎."
                ),
                "engine": "hub",
                "mode": "identity",
                "web": False,
            }
        except Exception as e:
            return {
                "ok": True,
                "reply": f"No pude guardar el nombre: {e}",
                "engine": "hub",
                "mode": "identity",
                "web": False,
            }

    # 2) Ayuda / capacidades
    if match_help_capabilities(text):
        return {
            "ok": True,
            "reply": help_text(),
            "engine": "hub",
            "mode": "help",
            "web": False,
        }

    # 3) Listar reservorio
    if match_library_list(text):
        return {
            "ok": True,
            "reply": library_list_text(library),
            "engine": "hub",
            "mode": "library",
            "web": False,
        }

    # 4) Informe / investigación (usa research si está disponible)
    topic = match_research_report(text)
    if topic and research_fn is not None:
        try:
            report = research_fn(topic)
            if isinstance(report, dict):
                summary = report.get("summary") or report.get("error") or ""
                sources = report.get("sources") or []
                tail = ""
                if sources:
                    tail = "\n\nFuentes: " + "; ".join(
                        (s.get("title") or s.get("url") or "")[:60] for s in sources[:4] if isinstance(s, dict)
                    )
                body = summary if summary else "No obtuve un informe útil; prueba a reformular el tema."
                return {
                    "ok": True,
                    "reply": f"**Informe: {topic}**\n\n{body}{tail}",
                    "engine": "hub-research",
                    "mode": "research",
                    "web": True,
                    "research": report,
                }
        except Exception as e:
            return {
                "ok": True,
                "reply": f"Intenté investigar «{topic}» pero falló: {e}",
                "engine": "hub",
                "mode": "research",
                "web": True,
            }

    return None
