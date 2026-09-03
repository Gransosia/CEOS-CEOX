"""
Curso progresivo e indefinido: Coaching aplicado a Formación y Calidad en Contact Center.
Orientado al perfil Técnico/a de Formación y Calidad (Admisiones Internacionales / call center).
"""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

def _now():
    return datetime.now(timezone.utc).isoformat()

# ----- Contenido curricular (progresivo) -----
MODULES = [
    {
        "id": "m0",
        "order": 0,
        "title": "El puesto híbrido",
        "level": "base",
        "minutes": 15,
        "objectives": [
            "Distinguir coaching personal vs coaching de desempeño",
            "Conectar interacción, conducta observable y resultado operativo",
        ],
        "content": (
            "El puesto no es el de un coach personal clásico. Es un perfil híbrido: "
            "calidad + formación + coaching de desempeño + análisis de datos + conocimiento comercial.\n\n"
            "Tu valor está en conectar lo que ocurre en una interacción con el cliente, "
            "la conducta observable del asesor y el resultado operativo.\n\n"
            "Áreas: Calidad (auditoría, calibración) · Coaching (feedback, acuerdos) · "
            "Formación (diseño y transferencia) · Call center (guion, objeciones) · "
            "Analítica (conversión, AHT, calidad) · Onboarding (ramp-up)."
        ),
        "practice": "Escribe en una frase tu definición del puesto para una entrevista.",
        "model": None,
    },
    {
        "id": "m1",
        "order": 1,
        "title": "Actualización del coaching profesional",
        "level": "base",
        "minutes": 25,
        "objectives": [
            "Aplicar el ciclo OBSERVAR→…→SEGUIR",
            "Separar persona, conducta y resultado",
        ],
        "content": (
            "Pasa del coaching centrado en desarrollo personal al orientado al desempeño.\n"
            "No se trata de 'dar consejos': ayudar a identificar una conducta modificable, "
            "comprender su impacto, practicar una alternativa y comprobar el resultado.\n\n"
            "Modelo operativo:\n"
            "OBSERVAR → ANALIZAR → PREGUNTAR → ACORDAR → PRACTICAR → MEDIR → SEGUIR\n\n"
            "• Separar persona, conducta y resultado.\n"
            "• Preguntas abiertas antes de prescribir.\n"
            "• Evidencias concretas de la llamada.\n"
            "• Una o dos conductas prioritarias por sesión.\n"
            "• Compromiso, plazo y criterio de éxito.\n\n"
            "Preguntas de alto valor: ¿Qué pretendías? ¿Qué escuchaste? ¿Qué otra opción tenías? "
            "¿Qué repetirías? ¿Qué cambiarías? ¿Cómo comprobarás la mejora?"
        ),
        "practice": "Elige una llamada imaginaria y formula 3 preguntas de alto valor.",
        "model": "OBSERVAR → ANALIZAR → PREGUNTAR → ACORDAR → PRACTICAR → MEDIR → SEGUIR",
    },
    {
        "id": "m2",
        "order": 2,
        "title": "Feedback avanzado (E-C-A-M)",
        "level": "base",
        "minutes": 25,
        "objectives": [
            "Aplicar Evidencia → Consecuencia → Alternativa → Medición",
            "Sustituir etiquetas por conductas observables",
        ],
        "content": (
            "Modelo E-C-A-M:\n"
            "1. Evidencia — minuto y hecho (ej. min 04:10 duda de precio → descuento inmediato).\n"
            "2. Consecuencia — impacto en cliente/resultado.\n"
            "3. Alternativa — conducta concreta a probar.\n"
            "4. Medición — cómo se comprobará (ej. próximas 10 llamadas).\n\n"
            "Regla de oro: específico, próximo en el tiempo, equilibrado y accionable.\n"
            "Evita 'te falta empatía'. Prefiere: 'cuando el cliente duda, haces pausa y preguntas "
            "antes de argumentar'."
        ),
        "practice": "Redacta un feedback E-C-A-M sobre una objeción de precio mal tratada.",
        "model": "E-C-A-M",
    },
    {
        "id": "m3",
        "order": 3,
        "title": "Auditoría de llamadas",
        "level": "intermedio",
        "minutes": 30,
        "objectives": [
            "Evaluar de forma reproducible",
            "Usar dimensiones de calidad comerciales",
        ],
        "content": (
            "Escucha buscando evidencia, no confirmación de una impresión previa.\n\n"
            "• Matriz de calidad antes de escuchar.\n"
            "• Separar cumplimiento crítico, calidad comunicativa y eficacia comercial.\n"
            "• Registrar minuto y conducta cuando sea posible.\n"
            "• No penalizar dos veces la misma conducta salvo que el sistema lo indique.\n\n"
            "Dimensiones: Apertura · Diagnóstico · Argumentación · Objeciones · Cierre · "
            "Experiencia · Compliance · Resultado."
        ),
        "practice": "Diseña 3 ítems de tu matriz para 'Objeciones' con criterio de puntuación.",
        "model": "MATRIZ DE AUDITORÍA",
    },
    {
        "id": "m4",
        "order": 4,
        "title": "Coaching sobre llamadas reales",
        "level": "intermedio",
        "minutes": 25,
        "objectives": [
            "Conducir escucha acompañada en 3 fases",
            "Priorizar autoevaluación del asesor",
        ],
        "content": (
            "Antes: foco (una habilidad + hipótesis).\n"
            "Durante: escuchar, pausar, registrar evidencia; no interrumpir el aprendizaje.\n"
            "Después: autoevaluación → contraste → práctica → compromiso.\n\n"
            "Técnica avanzada: pide primero autoevaluación. Si el asesor detecta el problema, "
            "aumenta el aprendizaje y reduce la sensación punitiva."
        ),
        "practice": "Escribe el guion de apertura de una escucha acompañada de 15 minutos.",
        "model": "ANTES · DURANTE · DESPUÉS",
    },
    {
        "id": "m5",
        "order": 5,
        "title": "Role plays profesionales",
        "level": "intermedio",
        "minutes": 25,
        "objectives": [
            "Diseñar role plays con presión real",
            "Aplicar secuencia briefing→repetición",
        ],
        "content": (
            "Clientes a simular: informado que compara universidades; sensible al precio; "
            "quiere hablar con otra persona; internacional con dudas de modalidad/documentación; "
            "indeciso; molesto por interacción anterior; objeción repetitiva.\n\n"
            "Secuencia: briefing → role play → autoevaluación → feedback → repetición inmediata → "
            "segunda evaluación. La repetición convierte conocimiento en conducta."
        ),
        "practice": "Diseña un role play de 'cliente sensible al precio' con briefing de 5 líneas.",
        "model": "BRIEFING → RP → AUTOEVAL → FEEDBACK → REPETIR",
    },
    {
        "id": "m6",
        "order": 6,
        "title": "Tratamiento de objeciones (A-P-E-C)",
        "level": "intermedio",
        "minutes": 25,
        "objectives": [
            "Aplicar Acoger → Preguntar → Explorar → Conectar",
            "No responder demasiado rápido",
        ],
        "content": (
            "A — Acoger: reconocer sin discutir.\n"
            "P — Preguntar: qué significa realmente la objeción.\n"
            "E — Explorar: criterio de decisión, urgencia, alternativa.\n"
            "C — Conectar: propuesta con necesidad y comprobar aceptación.\n\n"
            "Error crítico: responder demasiado rápido. Una objeción de precio puede esconder "
            "falta de valor, comparación, incertidumbre o falta de confianza."
        ),
        "practice": "Aplica A-P-E-C a: 'Es muy caro comparado con otra universidad online'.",
        "model": "A-P-E-C",
    },
    {
        "id": "m7",
        "order": 7,
        "title": "KPIs de contact center para un coach",
        "level": "intermedio",
        "minutes": 20,
        "objectives": [
            "Interpretar conversión, AHT, calidad, adherencia",
            "No coachar un KPI aislado",
        ],
        "content": (
            "Conversión · AHT/TMG · FCR · Calidad · Adherencia al guion · Abandono · CSAT/NPS.\n\n"
            "Principio: nunca coachar un KPI aislado. Busca relaciones. Reducir AHT puede ser "
            "positivo o negativo según efecto en calidad, conversión y satisfacción."
        ),
        "practice": "Propón una hipótesis: 'sube AHT y baja conversión' → qué conductas mirarías.",
        "model": "KPI RELACIONAL",
    },
    {
        "id": "m8",
        "order": 8,
        "title": "Coaching basado en datos",
        "level": "avanzado",
        "minutes": 20,
        "objectives": [
            "Cuadro de mando individual",
            "Matriz IMPACTO × FRECUENCIA × CORREGIBILIDAD",
        ],
        "content": (
            "Cuadro de mando: calidad media, conversión, AHT, principales fallos, fortaleza, "
            "objetivo de la semana.\n\n"
            "Lógica 70/20/10: ~70% práctica en puesto, 20% feedback, 10% conceptual.\n"
            "Prioridad: IMPACTO × FRECUENCIA × CORREGIBILIDAD."
        ),
        "practice": "Prioriza 3 conductas de un asesor ficticio con esa matriz.",
        "model": "70/20/10 · IMPACTO×FRECUENCIA×CORREGIBILIDAD",
    },
    {
        "id": "m9",
        "order": 9,
        "title": "Calibración de calidad",
        "level": "avanzado",
        "minutes": 20,
        "objectives": [
            "Conducir una calibración por criterios",
            "Documentar acuerdos y ejemplos límite",
        ],
        "content": (
            "Muestra común → puntuación independiente → comparar por criterio → evidencia → "
            "interpretación común → actualizar guía → registrar acuerdos."
        ),
        "practice": "Lista 5 pasos de una sesión de calibración de 45 minutos.",
        "model": "CALIBRACIÓN",
    },
    {
        "id": "m10",
        "order": 10,
        "title": "Formación de adultos y transferencia",
        "level": "avanzado",
        "minutes": 15,
        "objectives": [
            "Diseñar microformación práctica",
            "Medir transferencia, no solo satisfacción",
        ],
        "content": (
            "Estructura: objetivo → ejemplo → demostración → práctica → feedback → repetición → compromiso.\n"
            "No confundas satisfacción del alumno con aprendizaje ni aprendizaje con cambio de conducta."
        ),
        "practice": "Diseña una microformación de 20 min sobre objeción de precio.",
        "model": "OBJ → EJ → DEMO → PRÁCTICA → FEEDBACK → REPETIR → COMPROMISO",
    },
    {
        "id": "m11",
        "order": 11,
        "title": "Onboarding de asesores",
        "level": "avanzado",
        "minutes": 15,
        "objectives": [
            "Estándares mínimos antes de autonomía",
            "Certificación por competencias",
        ],
        "content": (
            "Estándares mínimos · teoría + buenos ejemplos + práctica · certificación por competencias · "
            "seguimiento reforzado primeras semanas · coordinar formación, calidad y operación."
        ),
        "practice": "Define 5 competencias mínimas para liberar a un asesor de admisiones.",
        "model": "ONBOARDING POR COMPETENCIAS",
    },
    {
        "id": "m12",
        "order": 12,
        "title": "Admisiones internacionales",
        "level": "avanzado",
        "minutes": 20,
        "objectives": [
            "Adaptar coaching a diversidad cultural y lingüística",
            "Separar objeción comercial de barrera documental",
        ],
        "content": (
            "No confundir estilo comunicativo diferente con mala calidad.\n"
            "Claridad · comprobación de comprensión · evitar jerga · confirmar datos y próximos pasos · "
            "escucha activa ante dudas culturales/académicas."
        ),
        "practice": "Redacta 3 preguntas de comprobación de comprensión para un candidato no nativo.",
        "model": "CLARIDAD + COMPROBACIÓN",
    },
    {
        "id": "m13",
        "order": 13,
        "title": "Influencia sin autoridad jerárquica",
        "level": "avanzado",
        "minutes": 15,
        "objectives": [
            "Influir con criterio, evidencia y ayuda",
        ],
        "content": (
            "Autoridad de: criterio técnico, evidencia y capacidad de ayudar a mejorar.\n"
            "Conducta: 'Te muestro qué ocurre, por qué importa, qué alternativa probamos y cómo medimos'."
        ),
        "practice": "Prepara un mensaje de 4 frases a un responsable operativo sobre una caída de conversión.",
        "model": "EVIDENCIA → IMPACTO → ALTERNATIVA → MEDICIÓN",
    },
    {
        "id": "m14",
        "order": 14,
        "title": "Conversaciones difíciles",
        "level": "avanzado",
        "minutes": 15,
        "objectives": [
            "Mantener el marco profesional ante incumplimiento",
        ],
        "content": (
            "Hecho (no intención) · perspectiva del asesor · estándar y evidencia · obstáculo · "
            "conducta concreta · seguimiento.\n"
            "Incumplimiento reiterado: documentar, escalar, no convertir coaching en terapia."
        ),
        "practice": "Escribe el guion de una conversación por incumplimiento de protocolo de privacidad.",
        "model": "HECHO → ESTÁNDAR → OBSTÁCULO → ACUERDO → SEGUIMIENTO",
    },
    {
        "id": "m15",
        "order": 15,
        "title": "Plan 30 días y mensaje de entrevista",
        "level": "cierre",
        "minutes": 20,
        "objectives": [
            "Plan de actualización de 30 días",
            "Mensaje profesional para la oferta UNIR",
        ],
        "content": (
            "Semana 1: lenguaje de calidad + KPIs + auditoría → matriz propia.\n"
            "Semana 2: feedback + coaching + escucha → guion de sesión.\n"
            "Semana 3: role plays + objeciones + formación → 3 escenarios.\n"
            "Semana 4: datos + calibración + onboarding → mini plan con indicadores.\n\n"
            "Mensaje clave de entrevista:\n"
            "«Entiendo el coaching como herramienta de mejora de desempeño. Parto de evidencias "
            "observables, facilito la autoevaluación del asesor, acordamos una conducta concreta, "
            "la practicamos y comprobamos su impacto en calidad y resultados.»"
        ),
        "practice": "Graba (o escribe) tu respuesta de 60 segundos a: ¿Qué es para ti el coaching en calidad?",
        "model": "PLAN 30 DÍAS",
    },
]

# Herramientas rápidas (plantillas)
TOOLS = {
    "ecam": {
        "name": "Plantilla E-C-A-M",
        "fields": ["Evidencia (minuto + hecho)", "Consecuencia", "Alternativa", "Medición"],
    },
    "apec": {
        "name": "Plantilla A-P-E-C (objeciones)",
        "fields": ["Acoger", "Preguntar", "Explorar", "Conectar"],
    },
    "audit": {
        "name": "Checklist auditoría rápida",
        "fields": [
            "Apertura", "Diagnóstico", "Argumentación", "Objeciones",
            "Cierre", "Experiencia", "Compliance", "Resultado",
        ],
    },
    "session": {
        "name": "Guion sesión de coaching",
        "fields": [
            "Apertura (foco)", "Autoevaluación", "Evidencia", "Impacto",
            "Alternativa", "Práctica", "Compromiso", "Seguimiento",
        ],
    },
}


class CoachingProgress:
    def __init__(self, base: Path):
        self.path = Path(base) / "coaching_progress.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> dict:
        if self.path.exists():
            try:
                return json.loads(self.path.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {
            "completed": [],
            "notes": {},
            "current": "m0",
            "streak_days": 0,
            "last_study": None,
            "practice_log": [],
            "updated_at": None,
        }

    def save(self, data: dict):
        data["updated_at"] = _now()
        self.path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def complete(self, module_id: str, note: str = "") -> dict:
        data = self.load()
        if module_id not in data["completed"]:
            data["completed"].append(module_id)
        if note:
            data["notes"][module_id] = note[:2000]
        data["last_study"] = _now()[:10]
        # advance current
        ids = [m["id"] for m in MODULES]
        if module_id in ids:
            i = ids.index(module_id)
            if i + 1 < len(ids):
                data["current"] = ids[i + 1]
        self.save(data)
        return data

    def log_practice(self, kind: str, text: str) -> dict:
        data = self.load()
        data["practice_log"].insert(0, {"ts": _now(), "kind": kind, "text": text[:1500]})
        data["practice_log"] = data["practice_log"][:50]
        self.save(data)
        return data


def list_modules() -> list[dict]:
    return [
        {
            "id": m["id"],
            "order": m["order"],
            "title": m["title"],
            "level": m["level"],
            "minutes": m["minutes"],
            "objectives": m["objectives"],
            "model": m.get("model"),
        }
        for m in MODULES
    ]


def get_module(module_id: str) -> Optional[dict]:
    for m in MODULES:
        if m["id"] == module_id:
            return m
    return None


def course_status(progress: dict) -> dict:
    total = len(MODULES)
    done = len(progress.get("completed") or [])
    return {
        "total_modules": total,
        "completed": done,
        "percent": round(100 * done / max(total, 1)),
        "current": progress.get("current") or "m0",
        "indefinite": True,
        "message": (
            "Curso progresivo e indefinido: puedes repetir módulos, ampliar prácticas "
            "y seguir el plan 30 días en bucle de mejora continua."
        ),
    }
