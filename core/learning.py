"""
Diseñador de Trayectorias de Aprendizaje — basado en la Espiral Cronos-Vórtice.

Genera secuencias de:
  Exploración → Aprendizaje → Institucionalización → Renovación

Usa el diagnóstico de arquetipo + posición en la Espiral + infinitud discreta
para proponer caminos personalizados y guiar al usuario.
"""
from datetime import datetime, timezone
import uuid
from .grammar import Grammar
from .protocol import ARCHETYPES


FASES_ESPIRAL = [
    {
        "id": "exploracion",
        "nombre": "Exploración",
        "descripcion": "Abrirse al Vórtice. Enfrentarse a lo ajeno sin pretender controlarlo aún.",
        "operaciones_prioritarias": ["incorporar", "ignorar"],
    },
    {
        "id": "aprendizaje",
        "nombre": "Aprendizaje",
        "descripcion": "Metabolizar la incertidumbre. Convertir diferencia en estructura usable.",
        "operaciones_prioritarias": ["incorporar", "conservar"],
    },
    {
        "id": "institucionalizacion",
        "nombre": "Institucionalización",
        "descripcion": "Fijar lo aprendido en Protocolos y Posesiones estables.",
        "operaciones_prioritarias": ["conservar"],
    },
    {
        "id": "renovacion",
        "nombre": "Renovación",
        "descripcion": "Permitir que el Vórtice desestabilice parcialmente lo instituido para evitar esclerosis.",
        "operaciones_prioritarias": ["expulsar", "incorporar"],
    },
]


class LearningDesigner:
    def __init__(self, grammar: Grammar = None):
        self.grammar = grammar or Grammar()

    def diagnose_learner(self, descripcion: str, modo="habitual", regla="dependiente",
                         kappa="medio", sigma="medio", rol_declarado=None) -> dict:
        """Diagnóstico rápido del estado del aprendiz / sistema de aprendizaje."""
        from .protocol import build_case
        case = build_case(
            identidad=descripcion,
            modo=modo,
            regla=regla,
            kappa=kappa,
            sigma=sigma,
            rol_declarado=rol_declarado,
        )
        # Heurística simple de fase actual
        fase = "exploracion"
        if kappa == "alto" and modo == "habitual":
            fase = "institucionalizacion"
        elif sigma in ("alto", "medio") and kappa in ("bajo", "medio"):
            fase = "aprendizaje"
        elif modo in ("oculto", "prohibido"):
            fase = "renovacion"

        return {
            "diagnostico": case,
            "fase_estimada": fase,
            "fase_info": next(f for f in FASES_ESPIRAL if f["id"] == fase),
        }

    def design_trajectory(self, learner_desc: str, objetivo: str,
                          diagnostico: dict = None, num_pasos=4) -> dict:
        """
        Diseña una trayectoria de aprendizaje personalizada.
        Devuelve una secuencia de pasos anclados a las fases de la Espiral.
        """
        if diagnostico is None:
            diagnostico = self.diagnose_learner(learner_desc)

        fase_actual = diagnostico["fase_estimada"]
        fases_orden = ["exploracion", "aprendizaje", "institucionalizacion", "renovacion"]
        try:
            start_idx = fases_orden.index(fase_actual)
        except ValueError:
            start_idx = 0

        pasos = []
        for i in range(num_pasos):
            fase_id = fases_orden[(start_idx + i) % len(fases_orden)]
            fase = next(f for f in FASES_ESPIRAL if f["id"] == fase_id)
            generacion = self.grammar.generate_trajectory_step(recursion=1)
            pasos.append({
                "orden": i + 1,
                "fase": fase["nombre"],
                "fase_id": fase_id,
                "descripcion_fase": fase["descripcion"],
                "operaciones": fase["operaciones_prioritarias"],
                "guia": generacion,
                "criterio_avance": (
                    f"El paso se considera avanzado cuando se ha practicado al menos "
                    f"una de las operaciones prioritarias ({', '.join(fase['operaciones_prioritarias'])}) "
                    f"de forma consciente y se puede describir el cambio producido."
                ),
            })

        trajectory = {
            "id": str(uuid.uuid4()),
            "learner": learner_desc,
            "objetivo": objetivo,
            "diagnostico_inicial": diagnostico,
            "pasos": pasos,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "estado": "activa",
            "progreso": 0,
        }
        return trajectory

    def next_guidance(self, trajectory: dict) -> dict:
        """Devuelve la guía del siguiente paso pendiente."""
        progreso = trajectory.get("progreso", 0)
        pasos = trajectory.get("pasos", [])
        if progreso >= len(pasos):
            return {
                "completada": True,
                "mensaje": "Trayectoria completada. Considera iniciar una nueva renovación o un nuevo ciclo de la Espiral.",
            }
        paso = pasos[progreso]
        return {
            "completada": False,
            "paso_actual": paso,
            "mensaje": (
                f"Fase actual: {paso['fase']}.\n\n"
                f"{paso['guia']}\n\n"
                f"Criterio de avance: {paso['criterio_avance']}"
            ),
        }

    def advance(self, trajectory: dict, nota: str = None) -> dict:
        """Marca el paso actual como avanzado y opcionalmente registra una nota."""
        progreso = trajectory.get("progreso", 0)
        if progreso < len(trajectory.get("pasos", [])):
            trajectory["pasos"][progreso]["completado_at"] = datetime.now(timezone.utc).isoformat()
            if nota:
                trajectory["pasos"][progreso]["nota"] = nota
            trajectory["progreso"] = progreso + 1
        if trajectory["progreso"] >= len(trajectory["pasos"]):
            trajectory["estado"] = "completada"
        return trajectory
