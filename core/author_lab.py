"""Laboratorio de autor de CEOS.

Analiza una obra/corpus literario desde dos capas complementarias:
1) crítica literaria de oficio: voz, ritmo, estructura, personajes, diálogo,
   exposición, poda, precisión y posibilidades de mejora;
2) lectura CRONOS-Espiral-OCa: elementos, condiciones, relaciones, operaciones,
   estados, transiciones, pérdida, encuentro, desafío, transformación,
   sustitución, reaparición transformada, cuello de botella y narrativa.

El módulo funciona sin LLM (heurística reproducible) y gana profundidad cuando
hay un LLM operativo. Nunca presenta la heurística como juicio literario
objetivo ni confunde hipótesis con hechos del texto.
"""
from __future__ import annotations

import json
import re
import statistics
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .ingest import DocumentLibrary, chunk_text
from .llm_bridge import available as llm_available, chat_completion


def _now():
    return datetime.now(timezone.utc).isoformat()


class AuthorLab:
    def __init__(self, library: DocumentLibrary, base_path: str = "data/author_lab"):
        self.library = library
        self.base = Path(base_path)
        self.base.mkdir(parents=True, exist_ok=True)
        self.reports = self.base / "reports"
        self.reports.mkdir(exist_ok=True)
        self.index_file = self.base / "index.json"
        if not self.index_file.exists():
            self.index_file.write_text("[]", encoding="utf-8")

    def list_reports(self, limit: int = 20) -> list[dict]:
        try:
            data = json.loads(self.index_file.read_text(encoding="utf-8"))
            return data[-limit:][::-1]
        except Exception:
            return []

    def _save_report(self, report: dict) -> None:
        rid = report.get("id") or f"author-{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        report["id"] = rid
        p = self.reports / f"{rid}.json"
        p.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        try:
            data = json.loads(self.index_file.read_text(encoding="utf-8"))
        except Exception:
            data = []
        data.append({
            "id": rid,
            "created_at": report.get("created_at"),
            "author": report.get("author"),
            "documents": report.get("documents", []),
            "engine": report.get("engine"),
            "thesis": (report.get("summary") or "")[:220],
        })
        self.index_file.write_text(json.dumps(data[-100:], ensure_ascii=False, indent=2), encoding="utf-8")

    @staticmethod
    def _sentences(text: str) -> list[str]:
        return [s.strip() for s in re.split(r"(?<=[.!?…])\s+(?=[A-ZÁÉÍÓÚÑ¿¡«—\"'])", text) if s.strip()]

    @staticmethod
    def _words(text: str) -> list[str]:
        return re.findall(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+(?:['’-][A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+)?", text.lower())

    def _stats(self, text: str) -> dict:
        text = re.sub(r"\s+", " ", text).strip()
        words = self._words(text)
        sents = self._sentences(text)
        sent_lengths = [len(self._words(s)) for s in sents] or [0]
        uniq = len(set(words))
        dialogue_markers = len(re.findall(r"(^|[\n\r])\s*(?:—|[A-ZÁÉÍÓÚÑ][\wÁÉÍÓÚÑ]{1,22}\s*—)", text))
        speaker_labels = len(re.findall(r"\b(?:Mamá|Abuela|Julia|33 besos|Pez Dorado|Oly|Haydée|Elora|Renatta|Álvar|Doctor Fetiches|Locutor|Enfermera)\s*[:—]", text, re.I))
        explanatory = len(re.findall(r"\b(?:es decir|en otras palabras|esto significa|como ya he|como he dicho|antes de que|os diré|quiero hablaros|aprovechemos|lo que quiero decir|la historia)\b", text, re.I))
        metanarrative = len(re.findall(r"\b(?:autor|lector|lectores|historia de la historia|os quiero contar|os diré|cuento|cuentos|relato|narrador|mientras os cuento|en esta historia)\b", text, re.I))
        invented = len(re.findall(r"\b[A-ZÁÉÍÓÚÑ][a-záéíóúñ]{3,}\b", text))
        question = text.count("?") + text.count("¿")
        exclaim = text.count("!") + text.count("¡")
        return {
            "chars": len(text),
            "words": len(words),
            "sentences": len(sents),
            "type_token_ratio": round(uniq / len(words), 3) if words else 0.0,
            "avg_sentence_words": round(statistics.mean(sent_lengths), 1),
            "median_sentence_words": round(statistics.median(sent_lengths), 1),
            "p90_sentence_words": round(sorted(sent_lengths)[min(len(sent_lengths)-1, int(len(sent_lengths)*0.9))], 1),
            "dialogue_markers": dialogue_markers,
            "speaker_labels": speaker_labels,
            "expository_markers": explanatory,
            "metanarrative_markers": metanarrative,
            "proper_name_signal": invented,
            "questions": question,
            "exclamations": exclaim,
        }

    def _cronos(self, text: str) -> dict:
        t = text.lower()
        patterns = {
            "perdida": r"\b(pérdida|perdió|pierde|ausencia|muerte|abandona|abandono|falta|vacío|sin\s+\w+)\b",
            "encuentro": r"\b(encuentro|encontró|encuentran|aparece|apareció|conoce|conocen|llega|llegan|descubre|descubren)\b",
            "desafio": r"\b(prueba|reto|obstáculo|obstaculo|conflicto|presión|presion|dificultad|prohibición|prohibicion|problema)\b",
            "transformacion": r"\b(cambia|cambio|transforma|transformación|transformacion|despierta|renace|evoluciona|aprende|descubre)\b",
            "sustitucion": r"\b(sustituye|sustitución|sustitucion|reemplaza|ocupa el lugar|en vez de|en lugar de)\b",
            "integracion": r"\b(unidos|juntos|integran|fusiona|mezcla|combina|completo|completan|forma una unidad)\b",
            "retorno": r"\b(regresa|regresar|vuelve|volver|retorno|otra vez|de nuevo|reaparece)\b",
        }
        hits = {k: len(re.findall(p, t)) for k, p in patterns.items()}
        transitions = []
        for k in ("perdida", "encuentro", "desafio", "transformacion", "sustitucion", "integracion", "retorno"):
            if hits[k]:
                transitions.append(k)
        return {
            "hits": hits,
            "dominant_operators": sorted(transitions, key=lambda k: hits[k], reverse=True)[:6],
            "spiral_signal": bool(hits["retorno"] and hits["transformacion"]),
            "substitution_signal": bool(hits["sustitucion"]),
            "integration_signal": bool(hits["integracion"]),
        }

    def _select_evidence(self, chunks: list[str], max_items: int = 18) -> list[str]:
        if not chunks:
            return []
        picks = []
        # Inicio, centro y final: continuidad estructural.
        idxs = [0, len(chunks)//4, len(chunks)//2, (3*len(chunks))//4, len(chunks)-1]
        for i in idxs:
            if 0 <= i < len(chunks):
                picks.append(chunks[i])
        # Marcadores de escenas, diálogo, metanarrativa y transformación.
        needles = [
            "os diré", "como ya", "autor", "lector", "historia", "prueba", "encuentro",
            "perdió", "cambió", "volvió", "de nuevo", "—", "Mamá:", "Julia:", "Haydée—",
            "Oly—", "Pez Dorado:", "Doctor Fetiches",
        ]
        for needle in needles:
            low = needle.lower()
            for c in chunks:
                if low in c.lower():
                    picks.append(c)
                    break
        out = []
        seen = set()
        for p in picks:
            p = re.sub(r"\s+", " ", p).strip()
            if len(p) < 80:
                continue
            key = p[:120].lower()
            if key in seen:
                continue
            seen.add(key)
            out.append(p[:950])
            if len(out) >= max_items:
                break
        return out

    def _docs(self, author: str = "", titles: Optional[list[str]] = None, limit: int = 12) -> list[dict]:
        author_l = (author or "").strip().lower()
        titles = [t.strip().lower() for t in (titles or []) if t.strip()]
        docs = []
        for d in self.library.list_docs() or []:
            blob = " ".join([
                str(d.get("title") or ""),
                str(d.get("source_name") or ""),
                str(d.get("author") or ""),
                " ".join(d.get("tags") or []),
            ]).lower()
            ok = True
            if author_l:
                ok = author_l in str(d.get("author") or "").lower() or author_l in blob
            if ok and titles:
                ok = any(t in blob for t in titles)
            if ok:
                docs.append(d)
        return docs[:limit]

    def _local_report(self, corpora: list[dict], author: str, requested_focus: str) -> dict:
        combined = "\n\n".join(c["text"] for c in corpora)
        st = self._stats(combined)
        cr = self._cronos(combined)
        # Heurísticas explícitas, no puntuaciones estéticas.
        strengths = []
        risks = []
        if st["metanarrative_markers"] > 15:
            strengths.append("Fuerte capacidad metanarrativa: el texto incorpora el acto de contar y jugar con el lector.")
            risks.append("La voz puede explicar o comentar tanto que, en algunos pasajes, reduce la presión de la escena.")
        if st["proper_name_signal"] > 80:
            strengths.append("Alta fecundidad imaginativa y capacidad para poblar mundos con nombres, conceptos y entidades memorables.")
            risks.append("La abundancia de nombres propios puede elevar el coste de orientación del lector y exige jerarquización.")
        if st["speaker_labels"] > 40:
            strengths.append("El diálogo es un motor narrativo importante y permite trabajar oralidad, humor y relación entre personajes.")
            risks.append("Conviene diferenciar aún más las voces: cuando varios personajes cumplen funciones expositivas, pueden acercarse entre sí en timbre.")
        if st["avg_sentence_words"] > 18:
            risks.append("Hay una tendencia a la acumulación sintáctica; la poda de subordinadas puede aumentar el golpe narrativo.")
        else:
            strengths.append("La sintaxis general mantiene una respiración relativamente ágil, con margen para reservar las frases largas para acumulación o pensamiento.")
        if st["exclamations"] > st["questions"] * 1.1:
            strengths.append("La exclamación aporta energía, comicidad y oralidad.")
            risks.append("La exclamación frecuente puede rebajar la intensidad cuando todo está subrayado con la misma energía.")
        if st["type_token_ratio"] > 0.17:
            strengths.append("Diversidad léxica alta en el corpus muestreado.")
        else:
            risks.append("En algunos tramos la reiteración de nombres, acciones o fórmulas puede concentrarse más de lo necesario.")
        strengths += [
            "Ambición de género: mezclas fantasía, ciencia ficción, humor, metaficción, aventura y pensamiento sin miedo a cambiar de registro.",
            "Imaginación convertida en mecanismo: muchos elementos fantásticos no son decorativos, sino que producen acción, reglas o preguntas.",
            "Capacidad para hacer convivir lo tierno y lo absurdo sin convertir el humor en una negación automática de la emoción.",
        ]
        risks += [
            "Tu principal enemigo no parece ser la falta de imaginación sino la falta de poda: a menudo tienes más material interesante del que una escena necesita.",
            "Necesitas proteger mejor los momentos emocionales: cuando una imagen ya comunica, la explicación posterior puede sobrar.",
            "La corrección ortotipográfica y sintáctica debe subir un escalón: los errores pequeños pueden restar autoridad a una voz que por imaginación sí merece atención.",
            "Conviene trabajar más el cierre de escenas: que la transición nazca de la consecuencia y no de una nueva explicación de lo que acaba de suceder.",
        ]
        priorities = [
            {"area":"Poda", "why":"Eliminar reiteraciones y explicaciones redundantes sin perder tu imaginación.", "exercise":"Reescribe una escena reduciéndola un 20–30 % y compara qué información sigue viva."},
            {"area":"Voz de personaje", "why":"Conseguir que cada personaje sea reconocible sin la etiqueta de diálogo.", "exercise":"Quita los nombres de 12 intervenciones y comprueba si todavía puedes identificar a cada hablante."},
            {"area":"Arquitectura de escena", "why":"Aumentar presión causal y evitar que las escenas se conviertan en acumulación de ocurrencias.", "exercise":"Para cada escena escribe: deseo → obstáculo → decisión → consecuencia."},
            {"area":"Subtexto", "why":"Dejar que parte del significado lo complete el lector.", "exercise":"Elimina una explicación emocional de un diálogo y deja que gesto, silencio o acción la sostengan."},
            {"area":"Corrección fina", "why":"La voz tiene personalidad; necesita una superficie técnica a su altura.", "exercise":"Haz una pasada exclusivamente de comas, concordancias, tiempos verbales y rayas de diálogo."},
            {"area":"Finales", "why":"Tus ideas tienden a producir muchas puertas; no todas necesitan abrirse al final de la misma escena.", "exercise":"Escribe tres cierres del mismo episodio: explícito, insinuado y por imagen. Compara cuál resuena más."},
        ]
        report = {
            "ok": True,
            "engine": "local-heuristic",
            "created_at": _now(),
            "author": author,
            "documents": [c["title"] for c in corpora],
            "focus": requested_focus,
            "summary": "El rasgo más poderoso del corpus es la imaginación estructural. El salto de excelencia no exige inventar más: exige seleccionar, jerarquizar y dejar que la escena haga más trabajo que la explicación.",
            "strengths": strengths,
            "risks": risks,
            "priorities": priorities,
            "metrics": st,
            "cronos": cr,
            "evidence": [e for c in corpora for e in c["evidence"]][:24],
            "teaching": {
                "goal": "Convertir intuición estilística en criterio reproducible.",
                "next": priorities[0],
            },
        }
        return report

    def _llm_report(self, corpora: list[dict], author: str, requested_focus: str, local_report: dict) -> dict:
        evidence_lines = []
        for c in corpora:
            evidence_lines.append(f"DOCUMENTO: {c['title']}")
            for e in c["evidence"][:10]:
                # Limitar evidencia mostrada al modelo para evitar deriva y favorecer crítica textual.
                evidence_lines.append(f"EXCERPT: {e[:850]}")
        system = """Eres el crítico literario y maestro de escritura de CEOS. Analizas la obra de un autor con rigor, sin adulación automática y sin destruir su voz por imponer una receta ajena. Tu tarea es localizar el potencial real del autor y convertirlo en un plan de excelencia.

Debes separar tres capas:
1) HECHOS DEL TEXTO: rasgos observables.
2) INTERPRETACIÓN CRÍTICA: lectura razonada.
3) HIPÓTESIS CRONOS-ESPIRAL-OCA: lectura estructural adicional, nunca presentada como hecho literario.

Para el análisis literario evalúa: voz, ritmo, sintaxis, léxico, diálogo, personajes, escenas, tensión, exposición, humor, emoción, imaginación, mundo, simbolismo, metanarrativa, puntos de vista, arquitectura, finales y corrección técnica.

Para CRONOS-ESPIRAL-OCA identifica, solo cuando haya evidencia textual: origen/génesis; pérdida; encuentro; desafío/prueba; transformación; elementos; condiciones; relaciones; estados; operaciones; transiciones; sustitución; integración; refuncionalización; bifurcación; migración del cuello de botella; retorno transformado y diferencia entre ciclo y espiral. También señala los puntos donde el modelo NO explica bien el texto.

No hagas rankings ni puntuaciones numéricas del valor literario. No inventes intenciones del autor. No conviertas un defecto ortotipográfico aislado en un juicio global. No cites largas porciones: usa como máximo frases muy breves y prioriza paráfrasis.

Entrega:
A. diagnóstico global del autor;
B. 8-12 bondades con evidencia;
C. 8-12 puntos débiles/riesgos con evidencia;
D. 6 prioridades de trabajo ordenadas por impacto práctico, sin llamarlas mejores/peores;
E. análisis comparado entre obras/documentos;
F. lectura CRONOS-Espiral-OCA;
G. programa de mejora de 12 semanas;
H. ejercicios concretos de reescritura;
I. qué no conviene cambiar porque forma parte de la identidad de voz;
J. qué debería probar el autor para salir de su zona de confort;
K. una conclusión honesta sobre dónde está el potencial de excelencia.
"""
        user = f"Autor: {author}\nFoco pedido: {requested_focus}\n\nINFORME HEURÍSTICO PREVIO (para contrastar, no para aceptar):\n{json.dumps(local_report, ensure_ascii=False)[:8000]}\n\nCORPUS DE EVIDENCIA:\n" + "\n".join(evidence_lines)
        res = chat_completion([
            {"role":"system","content":system},
            {"role":"user","content":user},
        ], context="laboratorio de autor CEOS + CRONOS-Espiral-OCa", max_tokens=5200)
        if res.get("ok") and res.get("text"):
            local_report["engine"] = res.get("engine") or "llm"
            local_report["llm_report"] = res["text"].strip()
        else:
            local_report["engine"] = "local-heuristic-fallback"
            local_report["llm_error"] = res.get("error") or "llm_fail"
        return local_report

    def analyze(self, author: str = "", titles: Optional[list[str]] = None, focus: str = "obra completa", use_llm: bool = True) -> dict:
        docs = self._docs(author=author, titles=titles, limit=12)
        if not docs:
            return {"ok": False, "error": "No encuentro en el reservorio documentos del autor/corpus indicado."}
        corpora = []
        for d in docs:
            text = self.library.get_doc_text(d["id"])
            if not text or len(text) < 40:
                continue
            chunks = self.library.get_doc_chunks(d["id"]) or chunk_text(text, max_chars=700)
            corpora.append({
                "id": d["id"],
                "title": d.get("title") or d.get("source_name") or "Documento",
                "author": d.get("author"),
                "text": text,
                "evidence": self._select_evidence(chunks, max_items=14),
                "chars": len(text),
                "chunks": len(chunks),
            })
        if not corpora:
            return {"ok": False, "error": "Hay documentos, pero no texto utilizable para el análisis."}
        local = self._local_report(corpora, author or "autor del corpus", focus)
        report = local
        if use_llm and llm_available().get("available"):
            report = self._llm_report(corpora, author or "autor del corpus", focus, local)
        report["documents_detail"] = [{k:v for k,v in c.items() if k != "text"} for c in corpora]
        self._save_report(report)
        return report

    def next_lesson(self, report: dict) -> dict:
        priorities = report.get("priorities") or []
        next_item = priorities[0] if priorities else {
            "area":"Poda",
            "why":"Reducir lo que compite con la escena.",
            "exercise":"Reduce una escena un 20% y explica qué has preservado."
        }
        return {
            "ok": True,
            "title": f"Laboratorio de escritura: {next_item.get('area','siguiente paso')}",
            "objective": next_item.get("why",""),
            "exercise": next_item.get("exercise",""),
            "method": "Escribe → compara con el original → justifica tres decisiones → vuelve a probar una sola variable.",
            "teacher_role": "CEOS debe devolverte una lectura crítica concreta y una segunda prueba, no una nota numérica.",
        }
