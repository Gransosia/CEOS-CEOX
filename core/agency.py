"""
CEOS v7 — Agency Core.

This module turns the previous Living Core into a bounded, persistent agency loop.
It does not claim consciousness. It implements concrete mechanisms for:
- persistent goals and commitments;
- proactive but bounded initiatives;
- frozen ex-ante experiments/predictions;
- model-gap detection;
- self-evolution proposals that can be reviewed and optionally sent to GitHub;
- an auditable agency journal.

The core rule is simple:
    CEOS may observe, remember, propose and learn;
    external or source-changing actions require explicit consent.
"""
from __future__ import annotations

import json
import re
import threading
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Optional


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe(text: Any, limit: int = 900) -> str:
    return str(text or "").strip()[:limit]


def _parse_ts(value: Optional[str]):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception:
        return None


class AgencyCore:
    SCHEMA = 2
    VERSION = "7.0.0-agency"

    def __init__(self, base_path: str = "data/agency"):
        self.base = Path(base_path)
        self.base.mkdir(parents=True, exist_ok=True)
        self.state_file = self.base / "state.json"
        self.events_file = self.base / "events.jsonl"
        self.proposals_dir = self.base / "evolution_proposals"
        self.proposals_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self.state = self._load_state()

    def _default(self) -> dict:
        now = _now()
        return {
            "schema": self.SCHEMA,
            "version": self.VERSION,
            "organism_id": "ceos-" + uuid.uuid4().hex[:12],
            "born_at": now,
            "cycle": 0,
            "last_cycle": None,
            "active_goal_id": None,
            "goals": [],
            "commitments": [],
            "initiatives": [],
            "experiments": [],
            "model": {
                "version": "7.0",
                "gaps": [],
                "assumptions": [
                    "Una iniciativa no equivale a una acción externa ejecutada.",
                    "Una predicción debe congelarse antes del desenlace.",
                    "La incertidumbre forma parte del estado.",
                ],
                "last_review": now,
            },
            "metrics": {
                "cycles": 0,
                "initiatives_proposed": 0,
                "initiatives_accepted": 0,
                "initiatives_rejected": 0,
                "initiatives_completed": 0,
                "experiments_created": 0,
                "experiments_resolved": 0,
                "model_gaps": 0,
                "evolution_proposals": 0,
            },
            "last_intent": None,
        }

    def _load_state(self) -> dict:
        default = self._default()
        if not self.state_file.exists():
            self._save(default)
            return default
        try:
            current = json.loads(self.state_file.read_text(encoding="utf-8"))
            if not isinstance(current, dict):
                raise ValueError("estado inválido")
        except Exception:
            self._save(default)
            return default
        # Conservative migration.
        for k, v in default.items():
            if k not in current:
                current[k] = v
        current["version"] = self.VERSION
        current["schema"] = self.SCHEMA
        return current

    def _save(self, data: Optional[dict] = None):
        payload = data if data is not None else self.state
        tmp = self.state_file.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self.state_file)

    def _event(self, kind: str, payload: Optional[dict] = None, source: str = "ceos") -> dict:
        event = {
            "id": uuid.uuid4().hex[:16],
            "ts": _now(),
            "kind": kind,
            "source": source,
            "payload": payload or {},
        }
        with self.events_file.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(event, ensure_ascii=False) + "\n")
        self.state["last_intent"] = event
        return event

    def snapshot(self) -> dict:
        with self._lock:
            return json.loads(json.dumps(self.state, ensure_ascii=False))

    def context_block(self, limit: int = 4) -> str:
        with self._lock:
            goals = [g for g in self.state.get("goals", []) if g.get("status") == "active"]
            initiatives = [i for i in self.state.get("initiatives", []) if i.get("status") == "proposed"]
            gaps = (self.state.get("model") or {}).get("gaps") or []
            lines = [
                f"estado_agencia={self.VERSION} | ciclos={self.state.get('cycle', 0)} | organismo={self.state.get('organism_id')}",
                f"objetivo_activo={(goals[0].get('title') if goals else 'ninguno')}",
            ]
            if initiatives:
                lines.append("iniciativas pendientes: " + " | ".join(_safe(i.get("title"), 140) for i in initiatives[:limit]))
            if gaps:
                lines.append("lagunas de modelo: " + " | ".join(_safe(g.get("description"), 160) for g in gaps[:limit]))
            lines.append("regla de agencia: proponer ≠ ejecutar; acciones externas requieren consentimiento.")
            return "AGENCIA CEOS v7:\n" + "\n".join("· " + x for x in lines)

    def _duplicate_recent(self, key: str, within_hours: float = 24) -> bool:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=within_hours)
        for item in self.state.get("initiatives", []):
            if item.get("dedupe_key") != key:
                continue
            dt = _parse_ts(item.get("created_at"))
            if dt and dt >= cutoff and item.get("status") in {"proposed", "accepted"}:
                return True
        return False

    def add_goal(self, title: str, priority: float = 0.7, source: str = "user") -> dict:
        title = _safe(title, 240)
        if not title:
            raise ValueError("objetivo vacío")
        with self._lock:
            for goal in self.state["goals"]:
                if goal.get("status") == "active" and goal.get("title", "").casefold() == title.casefold():
                    return goal
            goal = {
                "id": "g-" + uuid.uuid4().hex[:12],
                "title": title,
                "priority": round(max(0.0, min(float(priority), 1.0)), 3),
                "progress": 0.0,
                "status": "active",
                "created_at": _now(),
                "updated_at": _now(),
                "source": source,
            }
            self.state["goals"].insert(0, goal)
            self.state["active_goal_id"] = goal["id"]
            self._event("goal_created", goal, source=source)
            self._save()
            return goal

    def update_goal(self, goal_id: str, *, progress: Optional[float] = None, status: Optional[str] = None, note: str = "") -> dict:
        with self._lock:
            for goal in self.state["goals"]:
                if goal.get("id") == goal_id:
                    if progress is not None:
                        goal["progress"] = round(max(0.0, min(float(progress), 1.0)), 3)
                    if status in {"active", "paused", "completed", "cancelled"}:
                        goal["status"] = status
                    goal["updated_at"] = _now()
                    if note:
                        goal["last_note"] = _safe(note, 500)
                    self._event("goal_updated", goal, source="ceos")
                    self._save()
                    return goal
            raise ValueError("objetivo no encontrado")

    def goals(self, status: Optional[str] = None) -> list[dict]:
        with self._lock:
            out = self.state.get("goals", [])
            if status:
                out = [g for g in out if g.get("status") == status]
            return json.loads(json.dumps(out, ensure_ascii=False))

    def propose_initiative(self, title: str, action: str, reason: str, *, requires_consent: bool = False, dedupe_key: str = "", source: str = "ceos", metadata: Optional[dict] = None) -> dict:
        title = _safe(title, 240)
        action = _safe(action, 500)
        reason = _safe(reason, 500)
        with self._lock:
            if dedupe_key and self._duplicate_recent(dedupe_key):
                existing = next((i for i in self.state["initiatives"] if i.get("dedupe_key") == dedupe_key and i.get("status") in {"proposed", "accepted"}), None)
                return existing
            item = {
                "id": "i-" + uuid.uuid4().hex[:12],
                "title": title,
                "action": action,
                "reason": reason,
                "requires_consent": bool(requires_consent),
                "status": "proposed",
                "created_at": _now(),
                "updated_at": _now(),
                "source": source,
                "dedupe_key": dedupe_key,
                "metadata": metadata or {},
            }
            self.state["initiatives"].insert(0, item)
            self.state["initiatives"] = self.state["initiatives"][:100]
            self.state["metrics"]["initiatives_proposed"] += 1
            self._event("initiative_proposed", item, source=source)
            self._save()
            return item

    def initiatives(self, status: Optional[str] = None, limit: int = 50) -> list[dict]:
        with self._lock:
            items = self.state.get("initiatives", [])
            if status:
                items = [i for i in items if i.get("status") == status]
            return json.loads(json.dumps(items[: max(1, min(int(limit), 200))], ensure_ascii=False))

    def decide_initiative(self, initiative_id: str, decision: str, note: str = "") -> dict:
        decision = str(decision or "").lower()
        mapping = {"accept": "accepted", "accepted": "accepted", "reject": "rejected", "rejected": "rejected", "complete": "completed", "completed": "completed"}
        if decision not in mapping:
            raise ValueError("decisión inválida")
        status = mapping[decision]
        with self._lock:
            for item in self.state["initiatives"]:
                if item.get("id") == initiative_id:
                    item["status"] = status
                    item["updated_at"] = _now()
                    if note:
                        item["decision_note"] = _safe(note, 500)
                    key = {"accepted": "initiatives_accepted", "rejected": "initiatives_rejected", "completed": "initiatives_completed"}.get(status)
                    if key:
                        self.state["metrics"][key] += 1
                    self._event("initiative_decided", item, source="user" if status in {"accepted", "rejected"} else "ceos")
                    self._save()
                    return item
            raise ValueError("iniciativa no encontrada")

    def create_experiment(self, title: str, baseline: dict, predictions: list[dict], falsifiers: list[str], *, source: str = "user") -> dict:
        """Freeze an ex-ante state before the result is known."""
        with self._lock:
            exp = {
                "id": "x-" + uuid.uuid4().hex[:12],
                "title": _safe(title, 240),
                "created_at": _now(),
                "frozen_at": _now(),
                "status": "open",
                "baseline": baseline if isinstance(baseline, dict) else {},
                "predictions": predictions if isinstance(predictions, list) else [],
                "falsifiers": [ _safe(x, 500) for x in (falsifiers or []) if _safe(x) ],
                "outcome": None,
                "error_classification": None,
                "source": source,
            }
            self.state["experiments"].insert(0, exp)
            self.state["experiments"] = self.state["experiments"][:100]
            self.state["metrics"]["experiments_created"] += 1
            self._event("experiment_frozen", {"id": exp["id"], "title": exp["title"]}, source=source)
            self._save()
            return exp

    def resolve_experiment(self, experiment_id: str, outcome: dict, error_classification: Optional[str] = None) -> dict:
        with self._lock:
            for exp in self.state["experiments"]:
                if exp.get("id") == experiment_id:
                    exp["status"] = "resolved"
                    exp["resolved_at"] = _now()
                    exp["outcome"] = outcome if isinstance(outcome, dict) else {"text": _safe(outcome, 1200)}
                    exp["error_classification"] = _safe(error_classification, 100) if error_classification else None
                    self.state["metrics"]["experiments_resolved"] += 1
                    self._event("experiment_resolved", {"id": experiment_id, "error": error_classification}, source="user")
                    self._save()
                    return exp
            raise ValueError("experimento no encontrado")

    def experiments(self, status: Optional[str] = None) -> list[dict]:
        with self._lock:
            items = self.state.get("experiments", [])
            if status:
                items = [e for e in items if e.get("status") == status]
            return json.loads(json.dumps(items, ensure_ascii=False))

    def add_model_gap(self, description: str, evidence: str = "", *, component: str = "ontology", severity: float = 0.6, source: str = "user") -> dict:
        description = _safe(description, 500)
        if not description:
            raise ValueError("descripción de laguna vacía")
        with self._lock:
            gap = {
                "id": "gap-" + uuid.uuid4().hex[:10],
                "description": description,
                "evidence": _safe(evidence, 800),
                "component": _safe(component, 80),
                "severity": round(max(0.0, min(float(severity), 1.0)), 3),
                "status": "open",
                "created_at": _now(),
                "last_seen": _now(),
                "source": source,
            }
            self.state["model"]["gaps"].insert(0, gap)
            self.state["model"]["gaps"] = self.state["model"]["gaps"][:100]
            self.state["metrics"]["model_gaps"] += 1
            self._event("model_gap", gap, source=source)
            self._save()
            return gap

    def close_model_gap(self, gap_id: str, note: str = "") -> dict:
        with self._lock:
            for gap in self.state["model"]["gaps"]:
                if gap.get("id") == gap_id:
                    gap["status"] = "closed"
                    gap["closed_at"] = _now()
                    if note:
                        gap["resolution"] = _safe(note, 800)
                    self._event("model_gap_closed", gap, source="ceos")
                    self._save()
                    return gap
            raise ValueError("laguna no encontrada")

    def model_gaps(self, status: Optional[str] = "open") -> list[dict]:
        with self._lock:
            gaps = self.state["model"].get("gaps") or []
            if status:
                gaps = [g for g in gaps if g.get("status") == status]
            return json.loads(json.dumps(gaps, ensure_ascii=False))

    def create_evolution_proposal(self, description: str, target: str, suggested_change: str, *, risk: str = "medium", source: str = "ceos") -> dict:
        with self._lock:
            proposal = {
                "id": "ep-" + uuid.uuid4().hex[:12],
                "created_at": _now(),
                "status": "proposed",
                "description": _safe(description, 900),
                "target": _safe(target, 220),
                "suggested_change": _safe(suggested_change, 1500),
                "risk": _safe(risk, 40),
                "preconditions": [
                    "tests pasan o se documenta el fallo",
                    "cambio separado de main",
                    "revisión humana antes del merge",
                ],
                "source": source,
            }
            path = self.proposals_dir / f"{proposal['id']}.json"
            path.write_text(json.dumps(proposal, ensure_ascii=False, indent=2), encoding="utf-8")
            self.state["metrics"]["evolution_proposals"] += 1
            self._event("evolution_proposal", proposal, source=source)
            self._save()
            return proposal

    def evolution_proposals(self, limit: int = 30) -> list[dict]:
        items = []
        for p in sorted(self.proposals_dir.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True)[: max(1, min(int(limit), 100))]:
            try:
                items.append(json.loads(p.read_text(encoding="utf-8")))
            except Exception:
                pass
        return items

    def observe_experience(self, *, kind: str, text: str, source: str = "user", metadata: Optional[dict] = None) -> dict:
        with self._lock:
            self._event("experience", {"kind": _safe(kind, 80), "text": _safe(text, 1000), "metadata": metadata or {}}, source=source)
            return self._cycle_locked(reason=f"experience:{kind}")

    def _cycle_locked(self, reason: str = "heartbeat", life_state: Optional[dict] = None) -> dict:
        self.state["cycle"] = int(self.state.get("cycle") or 0) + 1
        self.state["last_cycle"] = _now()
        self.state["metrics"]["cycles"] += 1

        life_state = life_state or {}
        threads = [t for t in (life_state.get("open_threads") or []) if t.get("status") == "open"]
        if threads:
            top = sorted(threads, key=lambda t: -(float(t.get("weight") or 0)))[:1][0]
            text = _safe(top.get("text"), 220)
            self.propose_initiative(
                "Retomar el hilo más activo",
                f"Volver a trabajar sobre: {text}",
                "Existe un hilo abierto con peso elevado.",
                requires_consent=False,
                dedupe_key="resume:" + _safe(top.get("id"), 40),
                source="agency",
                metadata={"thread_id": top.get("id")},
            )
        corrections = int((life_state.get("relationship") or {}).get("corrections") or 0)
        if corrections:
            self.propose_initiative(
                "Revisar el criterio tras correcciones",
                "Comparar las últimas correcciones con las respuestas que las provocaron.",
                "Las correcciones aumentan la necesidad de verificación.",
                requires_consent=False,
                dedupe_key="review-corrections",
                source="agency",
            )
        gaps = self.model_gaps("open")
        if gaps:
            gap = sorted(gaps, key=lambda g: -float(g.get("severity") or 0))[0]
            self.propose_initiative(
                "Examinar una laguna del modelo",
                f"Investigar: {gap.get('description')}",
                "El propio sistema registra una representación insuficiente.",
                requires_consent=False,
                dedupe_key="gap:" + gap.get("id", ""),
                source="agency",
            )
        if not self.goals(status="active"):
            self.propose_initiative(
                "Definir un objetivo activo",
                "Pedir o formular un objetivo verificable para la siguiente etapa.",
                "El sistema no tiene actualmente un objetivo activo.",
                requires_consent=True,
                dedupe_key="no-active-goal",
                source="agency",
            )

        self._save()
        return {
            "cycle": self.state["cycle"],
            "reason": reason,
            "initiative": next((i for i in self.state["initiatives"] if i.get("status") == "proposed"), None),
            "open_gaps": len(self.model_gaps("open")),
        }

    def tick(self, life_state: Optional[dict] = None, reason: str = "heartbeat") -> dict:
        with self._lock:
            return self._cycle_locked(reason=reason, life_state=life_state)

    def audit(self, limit: int = 200) -> list[dict]:
        if not self.events_file.exists():
            return []
        try:
            lines = self.events_file.read_text(encoding="utf-8").splitlines()[-max(1, min(int(limit), 1000)):]
            out = []
            for line in lines:
                try:
                    out.append(json.loads(line))
                except Exception:
                    pass
            return out
        except Exception:
            return []

    def export_bundle(self) -> dict:
        return {
            "schema": self.SCHEMA,
            "version": self.VERSION,
            "state": self.snapshot(),
            "evolution_proposals": self.evolution_proposals(100),
            "events": self.audit(2000),
        }

    def import_bundle(self, bundle: dict) -> dict:
        incoming = (bundle or {}).get("state") or {}
        if not isinstance(incoming, dict):
            return {"ok": False, "error": "bundle agency inválido"}
        with self._lock:
            local_cycle = int(self.state.get("cycle") or 0)
            inc_cycle = int(incoming.get("cycle") or 0)
            if inc_cycle >= local_cycle:
                self.state = incoming
                self.state["version"] = self.VERSION
                self.state["schema"] = self.SCHEMA
                self._save()
                return {"ok": True, "replaced": True, "cycle": inc_cycle}
            return {"ok": True, "replaced": False, "cycle": local_cycle}
