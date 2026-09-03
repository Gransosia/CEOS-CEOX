"""
Modo Maestro CRONOS — mentor del protocolo Espiral / Cronos / OCA / CEOS.

Capacidades:
- Diagnosticar al aprendiz
- Diseñar trayectorias de enseñanza
- Generar lecciones a partir de la biblioteca + infinitud discreta
- Evaluar comprensión con preguntas de contraste
- Generar material exportable (guías, resúmenes)
"""
from __future__ import annotations
import json
import random
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .learning import FASES_ESPIRAL, LearningDesigner
from .protocol import ARCHETYPES
from .codex import Codex, ATOMOS
from .llm_bridge import deep_write, build_context, available as llm_available


def _now():
    return datetime.now(timezone.utc).isoformat()


# Núcleo doctrinal mínimo (semilla) — se enriquece con documentos ingeridos
CORE_DOCTRINE = [
    "Todo sistema adaptativo metaboliza incertidumbre transformándola en estructura.",
    "Cronos representa previsibilidad, estabilidad, memoria y continuidad.",
    "El Vórtice representa la atracción de lo ajeno, la novedad y la transformación.",
    "Todo sistema requiere una membrana que distinga lo propio de lo ajeno.",
    "Los cuatro regímenes de existencia son Campo, Protocolo, Posesión y Semilla.",
    "Las operaciones fundamentales son incorporar, conservar, expulsar e ignorar.",
    "La Espiral es un algoritmo adaptativo de exploración, aprendizaje, institucionalización y renovación.",
    "Un sistema es la capacidad organizada de producir, conservar, transformar y transmitir diferencias adaptativas.",
    "Los personajes se describen por su frontera, protocolos, posesiones, semillas, relación con el Vórtice, tensión identitaria y posición en la Espiral.",
    "El criterio de identidad del Motor es funcional: sigue siendo el mismo mientras ejecute el protocolo sobre el corpus versionado.",
    "Toda definición debe ser necesaria, suficiente, independiente, operativa y no circular.",
    "El protocolo solo se considera terminado cuando dos investigadores independientes obtienen esencialmente la misma descripción estructural.",
]


LESSON_TEMPLATES = {
    "concepto": (
        "Lección: {titulo}\n\n"
        "1. Idea central\n{idea}\n\n"
        "2. Por qué importa en CRONOS\n{por_que}\n\n"
        "3. Cómo reconocerlo en un sistema real\n{reconocer}\n\n"
        "4. Operaciones asociadas\n{operaciones}\n\n"
        "5. Pregunta de contraste\n{pregunta}\n\n"
        "6. Ejercicio práctico\n{ejercicio}\n"
    ),
    "fase_espiral": (
        "Lección de fase: {titulo}\n\n"
        "Fase de la Espiral: {fase}\n\n"
        "Propósito de esta fase:\n{proposito}\n\n"
        "Señales de que estás en ella:\n{senales}\n\n"
        "Riesgos típicos:\n{riesgos}\n\n"
        "Cómo avanzar a la siguiente:\n{avance}\n\n"
        "Ejercicio:\n{ejercicio}\n"
    ),
    "aplicacion": (
        "Aplicación práctica: {titulo}\n\n"
        "Sistema de referencia:\n{sistema}\n\n"
        "Diagnóstico sugerido:\n{diagnostico}\n\n"
        "Pasos de intervención (operaciones):\n{pasos}\n\n"
        "Criterio de éxito:\n{exito}\n\n"
        "Pregunta de autoevaluación:\n{pregunta}\n"
    ),
}


class Mentor:
    def __init__(self, library, grammar, memory, designer: Optional[LearningDesigner] = None, base_path: str = None, codex: Optional[Codex] = None):
        self.library = library
        self.grammar = grammar
        self.memory = memory
        self.designer = designer or LearningDesigner(grammar)
        if base_path is None:
            base_path = str(Path(__file__).resolve().parent.parent / "data" / "mentor")
        self.base = Path(base_path)
        self.base.mkdir(parents=True, exist_ok=True)
        self.lessons_file = self.base / "lessons.json"
        self.progress_file = self.base / "progress.json"
        if not self.lessons_file.exists():
            self.lessons_file.write_text("[]", encoding="utf-8")
        if not self.progress_file.exists():
            self.progress_file.write_text("{}", encoding="utf-8")
        if codex is None:
            codex_path = str(Path(base_path).parent / "codex")
            self.codex = Codex(base_path=codex_path)
        else:
            self.codex = codex

    def _load_lessons(self):
        return json.loads(self.lessons_file.read_text(encoding="utf-8"))

    def _save_lessons(self, data):
        self.lessons_file.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def _load_progress(self):
        return json.loads(self.progress_file.read_text(encoding="utf-8"))

    def _save_progress(self, data):
        self.progress_file.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def seed_core_doctrine(self) -> int:
        """Incorpora la doctrina mínima si la biblioteca está vacía de fragmentos core."""
        added = 0
        for frag in CORE_DOCTRINE:
            if self.grammar.learn_fragment(frag):
                added += 1
        # También como documento virtual
        if not any(d.get("title") == "Doctrina núcleo CRONOS" for d in self.library.list_docs()):
            self.library.ingest_text(
                "\n\n".join(CORE_DOCTRINE),
                title="Doctrina núcleo CRONOS",
                tags=["core", "cronos", "espiral"],
                grammar=None,  # ya aprendido arriba
            )
        return added

    def knowledge_stats(self) -> dict:
        docs = self.library.list_docs()
        return {
            "documentos": len(docs),
            "fragmentos_grammar": self.grammar.stats().get("fragmentos", 0),
            "lecciones_generadas": len(self._load_lessons()),
            "docs": [
                {"id": d["id"], "title": d["title"], "chunks": d.get("chunks", 0), "tags": d.get("tags", [])}
                for d in docs
            ],
        }

    def diagnose_student(self, perfil: str, nivel_declarado: str = "inicial") -> dict:
        """Diagnóstico del aprendiz para personalizar la enseñanza."""
        diag = self.designer.diagnose_learner(
            descripcion=perfil,
            modo="habitual",
            regla="dependiente",
            kappa="medio" if nivel_declarado != "avanzado" else "alto",
            sigma="medio",
            rol_declarado=None,
        )
        # Recomendación de foco
        fase = diag["fase_estimada"]
        focos = {
            "exploracion": ["Qué es Cronos y el Vórtice", "La membrana y lo ajeno", "Operaciones fundamentales"],
            "aprendizaje": ["Los cuatro regímenes", "Cadena de emergencia", "Cómo diagnosticar un sistema"],
            "institucionalizacion": ["Protocolo reproducible", "Criterios de evidencia", "Aplicación interdisciplinar"],
            "renovacion": ["Límites del modelo", "Falsación activa", "Enseñar a otros"],
        }
        return {
            "perfil": perfil,
            "nivel_declarado": nivel_declarado,
            "diagnostico": diag,
            "focos_recomendados": focos.get(fase, focos["exploracion"]),
            "mensaje": (
                f"Fase estimada en la Espiral: {diag['fase_info']['nombre']}. "
                f"Conviene trabajar: {', '.join(focos.get(fase, focos['exploracion'])[:2])}."
            ),
        }

    def _pick_knowledge(self, topic: str, n: int = 4) -> list[str]:
        hits = self.library.search(topic, limit=n)
        frags = [h["chunk"] for h in hits]
        if len(frags) < n:
            # Completar con doctrina / grammar
            pool = list(CORE_DOCTRINE)
            learned = self.grammar.export_learned().get("fragmentos", [])
            pool.extend(learned[:20])
            random.shuffle(pool)
            for p in pool:
                if p not in frags and topic.lower().split()[0] in p.lower() or len(frags) < n:
                    if p not in frags:
                        frags.append(p)
                if len(frags) >= n:
                    break
        return frags[:n]

    def generate_lesson(self, topic: str, estilo: str = "concepto", student_level: str = "inicial") -> dict:
        """Genera una lección completa sobre un tema."""
        knowledge = self._pick_knowledge(topic, n=5)
        idea = knowledge[0] if knowledge else CORE_DOCTRINE[0]
        extra = " | ".join(knowledge[1:3]) if len(knowledge) > 1 else ""

        if estilo == "fase_espiral":
            fase = next((f for f in FASES_ESPIRAL if f["id"] in topic.lower() or f["nombre"].lower() in topic.lower()), FASES_ESPIRAL[0])
            body = LESSON_TEMPLATES["fase_espiral"].format(
                titulo=topic,
                fase=fase["nombre"],
                proposito=fase["descripcion"],
                senales=f"Operaciones prioritarias visibles: {', '.join(fase['operaciones_prioritarias'])}.",
                riesgos="Quedarse atrapado en la fase o saltarla sin metabolizar.",
                avance="Practicar al menos una operación prioritaria de forma consciente y documentar el cambio.",
                ejercicio=f"Elige un sistema real y describe evidencias de que está en fase de {fase['nombre']}.",
            )
        elif estilo == "aplicacion":
            body = LESSON_TEMPLATES["aplicacion"].format(
                titulo=topic,
                sistema=topic,
                diagnostico=idea,
                pasos="1) Observar frontera\n2) Identificar operaciones dominantes\n3) Situar en la Espiral\n4) Proponer una intervención mínima",
                exito="Dos observadores independientes convergen en la misma descripción estructural.",
                pregunta="¿Qué operación cambiarías primero y por qué?",
            )
        else:
            body = LESSON_TEMPLATES["concepto"].format(
                titulo=topic,
                idea=idea,
                por_que=extra or "Porque permite distinguir estructura de ruido y actuar con criterio.",
                reconocer="Busca conductas repetidas, límites identitarios, gestión de recursos y relación con lo ajeno.",
                operaciones="incorporar · conservar · expulsar · ignorar",
                pregunta=f"¿Cómo se distinguiría «{topic}» de un concepto cercano que solo lo aparenta?",
                ejercicio=f"Aplica «{topic}» a un sistema concreto (una empresa, un organismo o un hábito personal) en 5-8 líneas.",
            )

        lesson = {
            "id": str(uuid.uuid4()),
            "topic": topic,
            "estilo": estilo,
            "student_level": student_level,
            "body": body,
            "sources_used": len(knowledge),
            "created_at": _now(),
        }
        lessons = self._load_lessons()
        lessons.append(lesson)
        self._save_lessons(lessons)
        self.memory.add_hito(f"Lección generada: {topic}", device="mentor")
        return lesson

    def create_teaching_path(self, student_profile: str, objetivo: str, nivel: str = "inicial") -> dict:
        """Crea una trayectoria de enseñanza completa (mentor → alumno)."""
        diag = self.diagnose_student(student_profile, nivel_declarado=nivel)
        focos = diag["focos_recomendados"]
        # Trayectoria base de la Espiral
        traj = self.designer.design_trajectory(
            learner_desc=student_profile,
            objetivo=objetivo,
            diagnostico=diag["diagnostico"],
            num_pasos=4,
        )
        # Enriquecer cada paso con una mini-lección
        for i, paso in enumerate(traj["pasos"]):
            tema = focos[i % len(focos)]
            leccion = self.generate_lesson(tema, estilo="concepto", student_level=nivel)
            paso["leccion_id"] = leccion["id"]
            paso["leccion_tema"] = tema
            paso["leccion_preview"] = leccion["body"][:280] + "…"
        traj["tipo"] = "ensenanza"
        traj["diagnostico_mentor"] = diag
        saved = self.memory.add_trajectory(traj)
        return saved

    def generate_study_guide(self, topic: str) -> dict:
        """Genera una guía de estudio exportable (markdown)."""
        lesson = self.generate_lesson(topic, estilo="concepto")
        hits = self.library.search(topic, limit=6)
        md = [
            f"# Guía de estudio: {topic}",
            "",
            f"_Generada por CEOS Maestro CRONOS — {lesson['created_at'][:10]}_",
            "",
            "## Lección",
            "",
            lesson["body"],
            "",
            "## Fragmentos de la biblioteca",
            "",
        ]
        if hits:
            for h in hits:
                md.append(f"- ({h['title']}) {h['chunk'][:200]}")
        else:
            md.append("_No hay documentos ingeridos aún sobre este tema. Usa la doctrina núcleo._")
        md.extend([
            "",
            "## Criterio de dominio",
            "",
            "Eres capaz de:",
            "1. Definir el concepto de forma operativa (no solo metafórica).",
            "2. Aplicarlo a al menos dos dominios distintos.",
            "3. Proponer un contraejemplo o límite del concepto.",
            "4. Explicárselo a otra persona en menos de 3 minutos.",
            "",
        ])
        guide = {
            "id": str(uuid.uuid4()),
            "topic": topic,
            "markdown": "\n".join(md),
            "lesson_id": lesson["id"],
            "created_at": _now(),
        }
        # Guardar en disco
        out = self.base / f"guia_{guide['id'][:8]}.md"
        out.write_text(guide["markdown"], encoding="utf-8")
        guide["file"] = str(out.name)
        return guide


    def generate_deep_document(self, topic: str, pedido: str = None, use_web: bool = False) -> dict:
        """
        Documento de alta calidad.
        1) Reúne contexto del codex + biblioteca + doctrina
        2) Si hay API: redacción profunda
        3) Si no: guía local enriquecida con codex
        """
        pedido = pedido or (
            f"Redacta un documento didáctico claro sobre «{topic}» para un aprendiz de CRONOS. "
            "Incluye: definición operativa, relación con Cronos/Vórtice, operaciones, "
            "ejemplo aplicado, límites/falsación y ejercicio."
        )
        # Contexto local
        expanded = self.codex.expand_topic(topic, limit=10)
        fragments = []
        if expanded.get("ok"):
            fragments.extend(expanded.get("fragments") or [])
        hits = self.library.search(topic, limit=8)
        fragments.extend([h["chunk"] for h in hits])
        # grammar fragments relacionados
        for frag in self.grammar.export_learned().get("fragmentos", [])[:30]:
            if any(w in frag.lower() for w in topic.lower().split()[:3]):
                fragments.append(frag)
        doctrine = list(__import__("core.mentor", fromlist=["CORE_DOCTRINE"]).CORE_DOCTRINE) if False else None
        from .mentor import CORE_DOCTRINE
        doctrine = CORE_DOCTRINE

        web_points = []
        if use_web:
            try:
                from .research import research_topic
                rep = research_topic(topic)
                web_points = rep.get("key_points") or []
                for f in rep.get("fragments_for_learning") or []:
                    fragments.append(f)
            except Exception:
                pass

        ctx = build_context(fragments, doctrine=doctrine, web_points=web_points)
        llm = deep_write(pedido, ctx)

        if llm.get("ok"):
            doc = {
                "id": str(uuid.uuid4()),
                "topic": topic,
                "mode": "deep",
                "engine": llm.get("engine"),
                "markdown": llm["text"],
                "created_at": _now(),
                "context_fragments": len(fragments),
            }
        else:
            # Fallback local enriquecido
            guide = self.generate_study_guide(topic)
            extra = ""
            if expanded.get("ok") and expanded.get("molecules"):
                extra = "\n\n## Fórmula Codex\n\n" + "\n".join(
                    f"- `{m['formula']}` — {m['meaning']}" for m in expanded["molecules"]
                )
            doc = {
                "id": guide["id"],
                "topic": topic,
                "mode": "local",
                "engine": "plantillas+codex",
                "markdown": guide["markdown"] + extra,
                "created_at": _now(),
                "context_fragments": len(fragments),
                "llm_hint": llm.get("hint") or llm.get("error"),
            }

        out = self.base / f"doc_{doc['id'][:8]}.md"
        out.write_text(doc["markdown"], encoding="utf-8")
        doc["file"] = out.name
        # Comprimir también al codex
        self.codex.compress_text(doc["markdown"], topic=f"doc:{topic}", max_chunks=20)
        self.memory.add_hito(f"Documento ({doc['mode']}): {topic}", device="mentor")
        return doc

    def ingest_to_codex(self, text: str, topic: str) -> dict:
        """Comprime texto largo en el codex (pocos elementos reutilizables)."""
        result = self.codex.compress_text(text, topic=topic)
        # También fragmentos a grammar
        from .ingest import chunk_text
        added = 0
        for ch in chunk_text(text)[:50]:
            if self.grammar.learn_fragment(ch):
                added += 1
        result["grammar_fragments_added"] = added
        return result



    def refine_with_interactions(self, pedido: str, n: int = 3, use_web: bool = False) -> dict:
        """
        n interacciones de refinamiento sobre un pedido.
        Cada paso acumula en memoria, grammar y codex — inteligencia por estructura, no por pesos.
        """
        n = max(1, min(int(n), 8))
        steps = []
        current_focus = pedido.strip()
        accumulated = []

        for i in range(n):
            # Cada interacción acota o profundiza
            if i == 0:
                topic = current_focus[:120]
                step_pedido = (
                    f"Interacción {i+1}/{n}. Interpreta este pedido del aprendiz y responde "
                    f"con estructura CRONOS (definiciones operativas, operaciones, fase de la Espiral, "
                    f"ejercicio). Pedido: {current_focus}"
                )
            else:
                topic = f"refino-{i+1}:{current_focus[:80]}"
                prev = accumulated[-1][:800] if accumulated else ""
                step_pedido = (
                    f"Interacción {i+1}/{n}. Mejora y profundiza la respuesta anterior. "
                    f"Corrige lagunas, añade un contraejemplo, una aplicación y un criterio de falsación. "
                    f"Pedido original: {current_focus}\n\nRespuesta anterior:\n{prev}"
                )

            doc = self.generate_deep_document(
                topic=topic if i > 0 else current_focus[:100],
                pedido=step_pedido,
                use_web=(use_web and i == 0),
            )
            body = doc.get("markdown") or ""
            accumulated.append(body)
            # Persistir cada paso como hito + cristal
            self.memory.add_hito(f"Interacción {i+1}/{n}: {current_focus[:60]}", device="mentor")
            self.codex.store_crystal(body[:2000], kind="interaction", meta={"step": i + 1, "pedido": current_focus[:100]})
            steps.append({
                "step": i + 1,
                "mode": doc.get("mode"),
                "engine": doc.get("engine"),
                "chars": len(body),
                "preview": body[:400],
                "file": doc.get("file"),
            })

        # Síntesis final de los n pasos
        synthesis_pedido = (
            f"Síntesis final tras {n} interacciones sobre: {current_focus}\n\n"
            "Une lo esencial en un documento único, sin repetir, con: "
            "1) tesis CRONOS 2) mapa de operaciones 3) aplicación 4) límites 5) próximo paso de aprendizaje."
        )
        final = self.generate_deep_document(
            topic=f"sintesis:{current_focus[:80]}",
            pedido=synthesis_pedido + "\n\nMaterial:\n" + "\n---\n".join(a[:1000] for a in accumulated),
            use_web=False,
        )

        return {
            "pedido": current_focus,
            "n": n,
            "steps": steps,
            "final": final,
            "note": (
                "La inteligencia crece por acumulación estructurada (casos, cristales, moléculas, hitos), "
                "no por reentrenar una red. Cada interacción deja rastro reutilizable en el Codex y la memoria."
            ),
        }


    def list_lessons(self, limit: int = 30) -> list:
        lessons = self._load_lessons()
        return lessons[-limit:]
