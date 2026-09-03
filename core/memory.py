"""
Órgano Memoria — persiste casos, hitos y fragmentos de aprendizaje.
Soporta marcado de origen (device) y timestamps para sync posterior.
"""
from pathlib import Path
import json
import uuid
from datetime import datetime, timezone


def _now():
    return datetime.now(timezone.utc).isoformat()


class Memory:
    def __init__(self, base_path="data/memory"):
        self.base = Path(base_path)
        self.base.mkdir(parents=True, exist_ok=True)
        self.cases_file = self.base / "cases.json"
        self.hitos_file = self.base / "hitos.json"
        self.trajectories_file = self.base / "trajectories.json"
        self._ensure(self.cases_file)
        self._ensure(self.hitos_file)
        self._ensure(self.trajectories_file)

    def _ensure(self, path):
        if not path.exists():
            with open(path, "w", encoding="utf-8") as f:
                json.dump([], f)

    def _read(self, path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _write(self, path, data):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    # ---------- Casos ----------
    def add_case(self, case: dict) -> dict:
        cases = self._read(self.cases_file)
        entry = {
            "id": str(uuid.uuid4()),
            "saved_at": _now(),
            **case,
        }
        cases.append(entry)
        self._write(self.cases_file, cases)
        return entry

    def cases(self, limit=None):
        data = self._read(self.cases_file)
        if limit:
            return data[-limit:]
        return data

    def case_by_id(self, case_id):
        for c in self._read(self.cases_file):
            if c.get("id") == case_id:
                return c
        return None

    # ---------- Hitos ----------
    def add_hito(self, text: str, device=None) -> dict:
        hitos = self._read(self.hitos_file)
        entry = {
            "id": str(uuid.uuid4()),
            "text": text,
            "ts": _now(),
            "device": device,
        }
        hitos.append(entry)
        self._write(self.hitos_file, hitos)
        return entry

    def hitos(self, limit=None):
        data = self._read(self.hitos_file)
        if limit:
            return data[-limit:]
        return data

    # ---------- Trayectorias de aprendizaje ----------
    def add_trajectory(self, trajectory: dict) -> dict:
        trajs = self._read(self.trajectories_file)
        entry = {
            "id": str(uuid.uuid4()),
            "created_at": _now(),
            **trajectory,
        }
        trajs.append(entry)
        self._write(self.trajectories_file, trajs)
        return entry

    def trajectories(self):
        return self._read(self.trajectories_file)

    # ---------- Export / Import para sync ----------
    def export_all(self) -> dict:
        return {
            "exported_at": _now(),
            "cases": self._read(self.cases_file),
            "hitos": self._read(self.hitos_file),
            "trajectories": self._read(self.trajectories_file),
        }

    def merge_from(self, foreign: dict) -> dict:
        """
        Fusión simple por ID (last-write-wins por timestamp).
        Devuelve resumen de lo incorporado.
        """
        stats = {"cases_added": 0, "hitos_added": 0, "trajectories_added": 0}

        def merge_list(local_path, foreign_list, key="id"):
            local = self._read(local_path)
            existing = {item[key]: item for item in local if key in item}
            added = 0
            for item in foreign_list:
                iid = item.get(key)
                if not iid:
                    continue
                if iid not in existing:
                    local.append(item)
                    added += 1
                else:
                    # last-write-wins
                    local_ts = existing[iid].get("saved_at") or existing[iid].get("ts") or existing[iid].get("created_at") or ""
                    foreign_ts = item.get("saved_at") or item.get("ts") or item.get("created_at") or ""
                    if foreign_ts > local_ts:
                        # reemplazar
                        for i, old in enumerate(local):
                            if old.get(key) == iid:
                                local[i] = item
                                break
            self._write(local_path, local)
            return added

        stats["cases_added"] = merge_list(self.cases_file, foreign.get("cases", []))
        stats["hitos_added"] = merge_list(self.hitos_file, foreign.get("hitos", []))
        stats["trajectories_added"] = merge_list(self.trajectories_file, foreign.get("trajectories", []))
        return stats
