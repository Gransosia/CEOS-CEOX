"""
Memoria generativa — infinitud discreta (Chomsky).

Conjunto FINITO de reglas de producción + fragmentos aprendidos de casos reales.
Aplicadas de forma recursiva generan variedad prácticamente ilimitada.
No es machine learning. No hay pesos ni GPU.
"Aprender" = añadir piezas al vocabulario; cada pieza multiplica el espacio de combinaciones.
"""
import json
import random
from pathlib import Path
from datetime import datetime, timezone

from .protocol import ARCHETYPES, VALID_MODOS, VALID_REGLA, VALID_NIVEL

CONECTORES_CAUSA = [
    "porque su Configuración quedó desalineada",
    "aunque su Regla declarada seguía intacta",
    "tras un cambio no reconocido en su sustrato",
    "sin que ningún agente lo corrigiera a tiempo",
    "coincidiendo con una subida de ruido no explicada",
    "porque la frontera entre lo propio y lo ajeno se volvió porosa",
    "mientras el Vórtice atraía elementos no metabolizados",
]

PLANTILLAS_CASO = [
    "Un sistema que declara ser {rol_declarado} pero cuyo modo real es {modo}, "
    "con Regla {regla} {conector}.",
    "Sistema en modo {modo}, Regla {regla}, con κ {kappa} y σ {sigma} — "
    "{conector}.",
    "Caso hipotético: {rol_declarado} que empieza a mostrar señales de {arquetipo_generado} "
    "{conector}.",
    "Un {arquetipo_generado} cuya Configuración depende de un {rol_declarado} "
    "que {conector}.",
    "Sistema cuya posición en la Espiral se ha estancado en institucionalización "
    "mientras su modo es {modo} y {conector}.",
]

PLANTILLAS_PREGUNTA = [
    "¿Qué pasaría con un {rol_declarado} si su Regla pasara de {regla} a "
    "{regla_alt}?",
    "¿Cómo se distingue un {arquetipo_generado} real de uno que solo lo aparenta "
    "{conector}?",
    "Si κ sube de {kappa} a alto pero σ se mantiene {sigma}, ¿deja de ser "
    "{arquetipo_generado}?",
    "¿Qué operación (incorporar / conservar / expulsar / ignorar) sería prioritaria "
    "para un sistema en modo {modo} con σ {sigma}?",
]

PLANTILLAS_TRAYECTORIA = [
    "Fase de exploración: enfrentar el Vórtice desde un {rol_declarado} en modo {modo}.",
    "Fase de aprendizaje: metabolizar la incertidumbre generada por σ {sigma} "
    "manteniendo la Regla {regla}.",
    "Fase de institucionalización: convertir lo aprendido en Protocolo estable "
    "para un sistema que opera como {arquetipo_generado}.",
    "Fase de renovación: permitir que el Vórtice desestabilice parcialmente "
    "la Posesión actual sin destruir la identidad.",
]


class Grammar:
    def __init__(self, base_path="data/grammar"):
        self.base = Path(base_path)
        self.base.mkdir(parents=True, exist_ok=True)
        self.rules_file = self.base / "learned_rules.json"
        self.learned = self._load()

    def _load(self):
        if self.rules_file.exists():
            with open(self.rules_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"fragmentos": [], "casos_aprendidos": 0, "updated_at": None}

    def _save(self):
        self.learned["updated_at"] = datetime.now(timezone.utc).isoformat()
        with open(self.rules_file, "w", encoding="utf-8") as f:
            json.dump(self.learned, f, ensure_ascii=False, indent=2)

    def learn_from_case(self, case: dict) -> bool:
        """Extrae un fragmento reutilizable de un caso real confirmado."""
        frag = (case.get("identidad") or "").strip()
        if frag and frag not in self.learned["fragmentos"]:
            self.learned["fragmentos"].append(frag)
            self.learned["casos_aprendidos"] += 1
            self._save()
            return True
        return False

    def learn_fragment(self, text: str) -> bool:
        text = text.strip()
        if text and text not in self.learned["fragmentos"]:
            self.learned["fragmentos"].append(text)
            self.learned["casos_aprendidos"] += 1
            self._save()
            return True
        return False

    def _rol(self):
        return random.choice(list(ARCHETYPES.keys()))

    def _conector(self, recursion=1):
        base = random.choice(CONECTORES_CAUSA)
        if recursion > 0 and self.learned["fragmentos"]:
            eco = random.choice(self.learned["fragmentos"])
            base += f", en un patrón parecido al ya visto en: «{eco[:70]}»"
        return base

    def generate_case(self, recursion=1) -> str:
        plantilla = random.choice(PLANTILLAS_CASO)
        return plantilla.format(
            rol_declarado=self._rol(),
            arquetipo_generado=self._rol(),
            modo=random.choice(sorted(VALID_MODOS)),
            regla=random.choice(sorted(VALID_REGLA)),
            kappa=random.choice(sorted(VALID_NIVEL)),
            sigma=random.choice(sorted(VALID_NIVEL)),
            conector=self._conector(recursion),
        )

    def generate_question(self, recursion=1) -> str:
        plantilla = random.choice(PLANTILLAS_PREGUNTA)
        return plantilla.format(
            rol_declarado=self._rol(),
            arquetipo_generado=self._rol(),
            modo=random.choice(sorted(VALID_MODOS)),
            regla=random.choice(sorted(VALID_REGLA)),
            regla_alt=random.choice(sorted(VALID_REGLA)),
            kappa=random.choice(sorted(VALID_NIVEL)),
            sigma=random.choice(sorted(VALID_NIVEL)),
            conector=self._conector(recursion),
        )

    def generate_trajectory_step(self, recursion=1) -> str:
        plantilla = random.choice(PLANTILLAS_TRAYECTORIA)
        return plantilla.format(
            rol_declarado=self._rol(),
            arquetipo_generado=self._rol(),
            modo=random.choice(sorted(VALID_MODOS)),
            regla=random.choice(sorted(VALID_REGLA)),
            sigma=random.choice(sorted(VALID_NIVEL)),
            conector=self._conector(recursion),
        )

    def export_learned(self) -> dict:
        return dict(self.learned)

    def merge_learned(self, foreign: dict) -> int:
        """Incorpora fragmentos de otro dispositivo. Devuelve cuántos nuevos se añadieron."""
        added = 0
        for frag in foreign.get("fragmentos", []):
            if frag and frag not in self.learned["fragmentos"]:
                self.learned["fragmentos"].append(frag)
                added += 1
        if added:
            self.learned["casos_aprendidos"] = len(self.learned["fragmentos"])
            self._save()
        return added

    def stats(self) -> dict:
        return {
            "fragmentos": len(self.learned["fragmentos"]),
            "casos_aprendidos": self.learned["casos_aprendidos"],
            "updated_at": self.learned.get("updated_at"),
        }
