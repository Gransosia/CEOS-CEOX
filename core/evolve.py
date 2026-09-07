"""
Bucle de evolución dirigida por tarea.

No reescribe el código fuente del servidor (eso sería auto-modificación peligrosa e inverificable).
Sí adapta, de forma autónoma y persistente:

- qué investiga (subtemas derivados de la tarea)
- qué integra en gramática / memoria larga / códice
- crítica y retractación heurística de tensiones
- ciclos de re-cifrado fractal (generación, densidad, presupuesto fijo)
- registro de evolución (data/evolve/log.json)

Analogía: la "célula" no cambia las leyes de la física; cambia su estado interno
y la forma de comprimir/recuperar información.
"""
from __future__ import annotations
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _derive_subtopics(task: str, n: int = 4) -> list[str]:
    task = (task or "").strip()
    if not task:
        return []
    # subconsultas útiles sin LLM
    seeds = [
        task,
        f"{task} definición conceptos clave",
        f"{task} historia origen",
        f"{task} aplicaciones prácticas",
        f"{task} críticas límites debates",
        f"{task} relación con otros campos",
    ]
    # si la tarea trae varias ideas separadas por comas / y
    parts = re.split(r"[,;/]|\\by\\b|\\band\\b", task, flags=re.I)
    for p in parts:
        p = p.strip()
        if len(p) > 3:
            seeds.append(p)
    out, seen = [], set()
    for s in seeds:
        k = s.lower()
        if k not in seen:
            seen.add(k)
            out.append(s)
        if len(out) >= n:
            break
    return out


class EvolutionEngine:
    def __init__(
        self,
        *,
        learner,
        codex,
        identity=None,
        library=None,
        base_path: str = "data/evolve",
    ):
        self.learner = learner
        self.codex = codex
        self.identity = identity
        self.library = library
        self.base = Path(base_path)
        self.base.mkdir(parents=True, exist_ok=True)
        self.log_file = self.base / "log.json"
        self.state_file = self.base / "state.json"
        if not self.log_file.exists():
            self.log_file.write_text("[]", encoding="utf-8")
        if not self.state_file.exists():
            self.state_file.write_text("{}", encoding="utf-8")

    def _load(self, path: Path):
        return json.loads(path.read_text(encoding="utf-8"))

    def _save(self, path: Path, data):
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def state(self) -> dict:
        return self._load(self.state_file)

    def history(self, limit: int = 20) -> list:
        log = self._load(self.log_file)
        return log[-limit:]

    def run_task(
        self,
        task: str,
        *,
        steps: int = 3,
        learn: bool = True,
        fractal: bool = True,
        device: str = "evolve",
    ) -> dict:
        """
        Ejecuta N pasos autónomos de aprendizaje sobre una tarea.
        """
        task = (task or "").strip()
        if not task:
            return {"ok": False, "error": "tarea vacía"}

        steps = max(1, min(int(steps or 3), 6))
        subtopics = _derive_subtopics(task, n=steps + 2)
        step_reports = []
        integrated = 0
        critiques = []

        for i in range(steps):
            topic = subtopics[i % len(subtopics)]
            report = None
            if learn and self.learner is not None:
                try:
                    report = self.learner.learn(topic, focus=task, device=device)
                except Exception as e:
                    report = {"ok": False, "error": str(e)[:200], "topic": topic}
            else:
                from .research import research_topic
                report = research_topic(topic, focus=task)

            frag = int((report or {}).get("fragments_added") or 0)
            integrated += frag
            crit = (report or {}).get("critique") or {}
            if crit:
                critiques.append({
                    "topic": topic,
                    "verdict": crit.get("verdict"),
                    "contradictions": len(crit.get("contradictions") or []),
                    "actions": crit.get("actions") or [],
                })
            step_reports.append({
                "step": i + 1,
                "topic": topic,
                "ok": bool((report or {}).get("ok")),
                "sources": len((report or {}).get("sources") or []),
                "fragments_added": frag,
                "critique_verdict": (crit or {}).get("verdict"),
            })

        study_reports = []
        if self.library is not None:
            lenses = ["temas", "estilo", "practico", "critica"]
            try:
                for i in range(min(steps, len(lenses))):
                    lens = lenses[i % len(lenses)]
                    st = self.library.study(
                        query=task,
                        lens=lens,
                        limit_docs=4,
                        sample_chunks=6,
                        grammar=getattr(self.learner, "grammar", None) if self.learner else None,
                        codex=self.codex,
                    )
                    study_reports.append({
                        "lens": lens,
                        "docs_used": st.get("docs_used"),
                        "meta": st.get("meta_conclusion"),
                    })
                    integrated += int(st.get("docs_used") or 0)
            except Exception as e:
                study_reports.append({"error": str(e)[:160]})

        fractal_info = None
        if fractal and self.codex is not None:
            try:
                # ciclo dirigido por la tarea (adapta generación / re-cifrado)
                fractal_info = self.codex.fractal_reencode(topic=task[:80], force=True)
            except Exception as e:
                try:
                    fractal_info = self.codex.maybe_fractal_after_ingest(task[:80])
                except Exception as e2:
                    fractal_info = {"error": str(e2)[:120]}

        # estado evolutivo persistente
        st = self.state()
        st["last_task"] = task
        st["last_run"] = _now()
        st["runs"] = int(st.get("runs") or 0) + 1
        st["total_fragments"] = int(st.get("total_fragments") or 0) + integrated
        st["last_fractal"] = fractal_info
        # "adaptación" de política: si muchas contradicciones, más pasos de crítica en futuros runs
        total_contr = sum(c.get("contradictions") or 0 for c in critiques)
        policy = dict(st.get("policy") or {})
        policy["prefer_critique_depth"] = min(5, 1 + total_contr)
        policy["last_steps"] = steps
        if total_contr >= 2:
            policy["mode"] = "caution"  # más contraste
        elif integrated >= steps:
            policy["mode"] = "expand"   # más exploración
        else:
            policy["mode"] = "balanced"
        st["policy"] = policy
        self._save(self.state_file, st)

        entry = {
            "id": _now(),
            "task": task,
            "steps": steps,
            "step_reports": step_reports,
            "study_reports": study_reports,
            "fragments_integrated": integrated,
            "critiques": critiques,
            "fractal": fractal_info,
            "policy_after": policy,
        }
        log = self._load(self.log_file)
        log.append(entry)
        self._save(self.log_file, log[-100:])

        if self.identity is not None:
            try:
                self.identity.log(
                    f"Evolución autónoma: «{task[:60]}» — {steps} pasos, +{integrated} fragmentos",
                    importance=3,
                )
            except Exception:
                pass

        return {
            "ok": True,
            "task": task,
            "steps": steps,
            "step_reports": step_reports,
            "study_reports": study_reports,
            "fragments_integrated": integrated,
            "critiques": critiques,
            "fractal": fractal_info,
            "policy": policy,
            "message": (
                "Tarea ejecutada: investigué subtemas, integré lo sólido, "
                "critiqué tensiones y adapté el re-cifrado del códice. "
                "No modifico el código fuente del servidor; evoluciono memoria, "
                "política interna y forma de comprimir/recuperar."
            ),
        }
