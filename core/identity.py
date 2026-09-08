"""
Identidad persistente del Motor CRONOS-Espiral.
Criterio de continuidad funcional: sigue siendo "el mismo" mientras
ejecute el protocolo sobre el corpus versionado, independientemente
del dispositivo o proceso.
"""
from pathlib import Path
import json
from datetime import datetime, timezone

DEFAULT_CORE = {
    "name": "CEOS",
    "version": "5.5.0",
    "codename": "Mentor-memoria evolutivo",
    "mission": (
        "Ser un mentor-memoria evolutivo: conversar, estudiar el reservorio, "
        "investigar bajo demanda, criticar, corregir y medir el crecimiento del códice. "
        "No ser un buscador web disfrazado de chat."
    ),
    "identity_criterion": "funcional",
    "identity_note": (
        "Sigue siendo el mismo CEOS mientras ejecute la constitución "
        "(reservorio + códice + conversación + evolución medible) sobre el corpus, "
        "en cualquier dispositivo."
    ),
    "constitution": "core/constitution.py",
}

DEFAULT_GOALS = {
    "main_goal": "Mantener un corpus de casos y trayectorias de aprendizaje con disciplina de evidencia.",
    "active_goals": [
        "Contrastar la tabla de arquetipos v2 con casos reales.",
        "Definir el criterio exacto de corte entre niveles de evidencia A-E.",
        "Hacer operativa la generación de trayectorias de aprendizaje personalizadas.",
        "Lograr sync fiable multi-dispositivo (PC + Android + iOS).",
    ],
}

DEFAULT_STATE = {
    "mode": "habitual",
    "current_task": None,
    "last_activity": None,
    "device_id": None,
}


class Identity:
    def __init__(self, base_path="data/identity"):
        self.base = Path(base_path)
        self.base.mkdir(parents=True, exist_ok=True)

        self.core_file = self.base / "core.json"
        self.state_file = self.base / "state.json"
        self.goals_file = self.base / "goals.json"
        self.history_file = self.base / "history.log"

        self.core = self._load_or_init(self.core_file, DEFAULT_CORE)
        self.state = self._load_or_init(self.state_file, DEFAULT_STATE)
        self.goals = self._load_or_init(self.goals_file, DEFAULT_GOALS)

    def _load_or_init(self, path, default):
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        self._save(path, default)
        return dict(default)

    def _save(self, path, data):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def who_am_i(self):
        data = dict(self.core)
        # refrescar misión/nombre si aún es plantilla antigua
        if data.get("name") in ("Motor CRONOS-Espiral", None) or "buscador web" not in (data.get("mission") or ""):
            try:
                from .constitution import NAME, NORTH_STAR, FULL_NAME
                data.setdefault("name", NAME)
                data["mission"] = (
                    "Ser un mentor-memoria evolutivo: conversar, estudiar el reservorio, "
                    "investigar bajo demanda, criticar, corregir y medir el crecimiento del códice. "
                    "No ser un buscador web disfrazado de chat."
                )
                data["codename"] = data.get("codename") or "Mentor-memoria evolutivo"
                data["north_star"] = NORTH_STAR
                data["full_name"] = FULL_NAME
            except Exception:
                pass
        return data

    def current_goal(self):
        return self.goals["main_goal"]

    def active_goals(self):
        return list(self.goals["active_goals"])

    def set_device_id(self, device_id: str):
        self.state["device_id"] = device_id
        self._save(self.state_file, self.state)

    def update_state(self, mode=None, task=None):
        if mode is not None:
            self.state["mode"] = mode
        if task is not None:
            self.state["current_task"] = task
        self.state["last_activity"] = datetime.now(timezone.utc).isoformat()
        self._save(self.state_file, self.state)

    def log(self, event, importance=1):
        line = f"{datetime.now(timezone.utc).isoformat()} | {event} | importancia={importance}\n"
        with open(self.history_file, "a", encoding="utf-8") as f:
            f.write(line)

    def add_goal(self, goal: str):
        if goal not in self.goals["active_goals"]:
            self.goals["active_goals"].append(goal)
            self._save(self.goals_file, self.goals)
