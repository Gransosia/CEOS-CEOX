"""CEOS 10 — Grafo Vivo de Coevolución.

Esta capa convierte la Mente Fractal en un modelo explícito de tres cosas que
no conviene mezclar:

1. el usuario (sus objetivos, competencias, preguntas y posiciones);
2. el corpus/trabajo (obras, proyectos y dominios);
3. el propio CEOS (lo que sabe, ignora, debe contrastar o enseñar).

No simula conciencia. Implementa continuidad funcional: un grafo persistente,
procedencia, postura epistemológica, dominio del usuario, contradicciones y una
cola de siguientes acciones.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import zlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

try:
    from cryptography.fernet import Fernet
except Exception:  # pragma: no cover
    Fernet = None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _norm(value: str) -> str:
    value = (value or "").strip().lower()
    value = re.sub(r"\s+", " ", value)
    return value


def _id(kind: str, key: str) -> str:
    raw = f"{kind}|{_norm(key)}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:20]


def _tokens(text: str) -> set[str]:
    stop = {
        "para", "como", "sobre", "desde", "entre", "esta", "este", "esto",
        "esas", "esos", "que", "una", "uno", "los", "las", "del", "por",
        "con", "sin", "pero", "tambien", "también", "más", "muy", "ser",
        "son", "fue", "era", "han", "sus", "una", "hacia", "porque", "donde",
        "cuando", "cada", "todo", "todos", "puede", "pueden", "algo", "tener",
    }
    return {
        t for t in re.findall(r"[a-záéíóúüñA-ZÁÉÍÓÚÜÑ0-9]{4,}", (text or "").lower())
        if t not in stop
    }


class CoEvolutionGraph:
    VERSION = "1.2"

    def __init__(self, base_path: str, *, user_label: str = "Usuario"):
        self.base = Path(base_path)
        self.base.mkdir(parents=True, exist_ok=True)
        self.graph_path = self.base / "graph.capsule"
        self.index_path = self.base / "index.json"
        self.key_path = self.base / "graph.key"
        self.user_label = user_label or "Usuario"
        self.nodes: dict[str, dict[str, Any]] = {}
        self.edges: list[dict[str, Any]] = []
        self.meta: dict[str, Any] = {"generation": 0}
        self._load()
        self.bootstrap_seed()

    # ---------- secure persistence ----------
    def _get_key(self) -> Optional[bytes]:
        if Fernet is None:
            return None
        env = os.getenv("CEOS_MIND_KEY", "").strip()
        if env:
            Fernet(env.encode("utf-8"))
            return env.encode("utf-8")
        if not self.key_path.exists():
            self.key_path.write_bytes(Fernet.generate_key())
        return self.key_path.read_bytes().strip()

    def _load(self) -> None:
        if self.index_path.exists():
            try:
                self.meta.update(json.loads(self.index_path.read_text(encoding="utf-8")))
            except Exception:
                pass
        if not self.graph_path.exists():
            return
        try:
            raw = self.graph_path.read_bytes()
            key = self._get_key()
            if key and Fernet is not None:
                raw = Fernet(key).decrypt(raw)
            data = json.loads(zlib.decompress(raw).decode("utf-8"))
            self.nodes = data.get("nodes") or {}
            self.edges = data.get("edges") or []
            self.meta.update(data.get("meta") or {})
        except Exception:
            self.meta["recovery_required"] = True
            self.nodes = {}
            self.edges = []

    def _save(self) -> None:
        payload = {
            "version": self.VERSION,
            "saved_at": _now(),
            "meta": self.meta,
            "nodes": self.nodes,
            "edges": self.edges,
        }
        raw = zlib.compress(
            json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8"),
            9,
        )
        key = self._get_key()
        if key and Fernet is not None:
            raw = Fernet(key).encrypt(raw)
        self.graph_path.write_bytes(raw)
        public = {
            "version": self.VERSION,
            "updated_at": _now(),
            "nodes": len(self.nodes),
            "edges": len(self.edges),
            "generation": int(self.meta.get("generation", 0)),
            "encryption": "fernet" if key and Fernet is not None else "none",
            "recovery_required": bool(self.meta.get("recovery_required")),
        }
        self.index_path.write_text(json.dumps(public, ensure_ascii=False, indent=2), encoding="utf-8")

    # ---------- graph primitives ----------
    def add_node(
        self,
        label: str,
        *,
        kind: str = "concept",
        evidence: str = "E4",
        stance: str = "unknown",
        mastery: float = 0.0,
        importance: float = 0.5,
        source: str = "internal",
        tags: Optional[list[str]] = None,
        attributes: Optional[dict[str, Any]] = None,
        node_id: Optional[str] = None,
    ) -> dict[str, Any]:
        label = (label or "").strip()
        if not label:
            return {}
        nid = node_id or _id(kind, label)
        now = _now()
        if nid in self.nodes:
            n = self.nodes[nid]
            n["hits"] = int(n.get("hits", 1)) + 1
            n["updated_at"] = now
            if tags:
                n["tags"] = sorted(set((n.get("tags") or []) + list(tags)))[:30]
            if attributes:
                n.setdefault("attributes", {}).update(attributes)
            self._save()
            return n
        node = {
            "id": nid,
            "kind": kind,
            "label": label[:240],
            "evidence": evidence,
            "stance": stance if stance in {"support", "reject", "uncertain", "unknown"} else "unknown",
            "mastery": max(0.0, min(1.0, float(mastery))),
            "importance": max(0.0, min(1.0, float(importance))),
            "source": source,
            "tags": sorted(set(tags or []))[:30],
            "attributes": attributes or {},
            "hits": 1,
            "created_at": now,
            "updated_at": now,
        }
        self.nodes[nid] = node
        self.meta["generation"] = int(self.meta.get("generation", 0)) + 1
        self._save()
        return node

    def connect(self, source: str, target: str, relation: str, *, weight: float = 1.0, evidence: str = "E4", source_ref: str = "internal") -> dict[str, Any]:
        if source not in self.nodes or target not in self.nodes or not relation:
            return {"ok": False, "reason": "nodo_no_encontrado"}
        rel = {
            "source": source,
            "target": target,
            "relation": relation[:80],
            "weight": max(0.0, min(1.0, float(weight))),
            "evidence": evidence,
            "source_ref": source_ref,
            "updated_at": _now(),
        }
        for existing in self.edges:
            if existing.get("source") == source and existing.get("target") == target and existing.get("relation") == relation:
                existing.update(rel)
                self._save()
                return {"ok": True, "edge": existing, "updated": True}
        self.edges.append(rel)
        self.meta["generation"] = int(self.meta.get("generation", 0)) + 1
        self._save()
        return {"ok": True, "edge": rel, "updated": False}

    def set_stance(self, node_id: str, stance: str, *, confidence: float = 0.6, note: str = "", source: str = "user") -> dict[str, Any]:
        if node_id not in self.nodes:
            return {"ok": False, "reason": "nodo_no_encontrado"}
        if stance not in {"support", "reject", "uncertain", "unknown"}:
            return {"ok": False, "reason": "stance_invalida"}
        n = self.nodes[node_id]
        n["stance"] = stance
        n["stance_confidence"] = max(0.0, min(1.0, float(confidence)))
        n["updated_at"] = _now()
        if note:
            n.setdefault("stance_history", []).append({"stance": stance, "confidence": confidence, "note": note[:500], "source": source, "at": _now()})
            n["stance_history"] = n["stance_history"][-30:]
        self.meta["generation"] = int(self.meta.get("generation", 0)) + 1
        self._save()
        return {"ok": True, "node": n}

    def set_mastery(self, node_id: str, mastery: float, *, evidence: str = "E4", note: str = "") -> dict[str, Any]:
        if node_id not in self.nodes:
            return {"ok": False, "reason": "nodo_no_encontrado"}
        n = self.nodes[node_id]
        old = float(n.get("mastery", 0.0))
        n["mastery"] = max(0.0, min(1.0, float(mastery)))
        n["mastery_history"] = (n.get("mastery_history") or [])[-24:] + [{"from": old, "to": n["mastery"], "evidence": evidence, "note": note[:400], "at": _now()}]
        n["updated_at"] = _now()
        self.meta["generation"] = int(self.meta.get("generation", 0)) + 1
        self._save()
        return {"ok": True, "node": n}

    # ---------- seed and user model ----------
    def bootstrap_seed(self) -> None:
        if self.meta.get("seed_version") == "v10.1":
            return
        user = self.add_node(self.user_label, kind="person", evidence="E1", stance="unknown", importance=1.0, source="user_context", tags=["interlocutor", "autor"])
        ceos = self.add_node("CEOS", kind="agent", evidence="E4", importance=1.0, source="internal", tags=["maestro", "aprendiz", "motor"])
        self.connect(user["id"], ceos["id"], "aprende_con", weight=1.0, evidence="E4")
        self.connect(ceos["id"], user["id"], "enseña_a", weight=1.0, evidence="E4")

        domains = [
            ("CRONOS-Espiral-OCa", "domain", 1.0),
            ("Astroteología", "domain", 0.95),
            ("Gnosis", "domain", 0.82),
            ("Astrología", "domain", 0.82),
            ("Teoría de números", "domain", 0.75),
            ("Historia de la ciencia y de las ideas", "domain", 0.75),
            ("Escritura y autor", "domain", 1.0),
            ("Invención y sistemas", "domain", 0.9),
        ]
        for label, kind, imp in domains:
            n = self.add_node(label, kind=kind, evidence="E4", importance=imp, source="user_context", tags=["interes", "curriculum"])
            self.connect(user["id"], n["id"], "estudia", weight=imp, evidence="E4")
            self.connect(ceos["id"], n["id"], "dominio_maestro", weight=0.8, evidence="E4")

        works = [
            "Cuentos para Julia y 33 besos",
            "Pruebas de amor furtivo",
            "Por amor a... Por ejemplo, la hyperrealidad",
            "Soy parte. Preludio",
        ]
        for w in works:
            n = self.add_node(w, kind="work", evidence="E1", importance=0.98, source="corpus_user", tags=["obra", "autor"])
            self.connect(user["id"], n["id"], "es_autor_de", weight=1.0, evidence="E1")
            self.connect(n["id"], self._node("Escritura y autor")["id"], "pertenece_a", weight=0.9, evidence="E4")

        thinkers = [
            "Pierre Jacques Antoine Béchamp", "Caramuel", "Isaac Peral", "Miguel Servet",
            "Nietzsche", "Georges Lakhovsky", "Miguel de Cervantes", "Lope de Vega", "Giordano Bruno",
        ]
        for t in thinkers:
            n = self.add_node(t, kind="thinker", evidence="E3", importance=0.72, source="knowledge_seed", tags=["autor", "estudio"])
            self.connect(n["id"], self._node("Historia de la ciencia y de las ideas")["id"], "referencia_para", weight=0.7, evidence="E3")

        # Perfil de autor: hipótesis de trabajo ancladas en el corpus ya revisado.
        author_traits = [
            ("Imaginación estructural", 0.95),
            ("Metanarración", 0.9),
            ("Oralidad y diálogo", 0.9),
            ("Humor como modulador de tensión", 0.82),
            ("Ternura y vínculo", 0.82),
            ("Pérdida → búsqueda → encuentro → transformación", 0.9),
            ("Abundancia inventiva", 0.92),
            ("Arte de eliminar / poda", 1.0),
            ("Subtexto", 0.95),
            ("Arquitectura de escena", 0.95),
            ("Control de la exposición", 0.92),
        ]
        for label, imp in author_traits:
            tr = self.add_node(label, kind="author_trait", evidence="E4", importance=imp, source="author_lab_seed", tags=["autor", "hipotesis", "oficio"])
            self.connect(user["id"], tr["id"], "rasgo_a_estudiar", weight=imp, evidence="E4")
            self.connect(tr["id"], self._node("Escritura y autor")["id"], "pertenece_a", weight=0.9, evidence="E4")

        for w in works:
            wn = self._node(w, "work")
            for trait_label in ("Imaginación estructural", "Metanarración", "Abundancia inventiva"):
                tr = self._node(trait_label, "author_trait")
                self.connect(wn["id"], tr["id"], "muestra", weight=0.72, evidence="E4", source_ref="Corpus_evidencia_autor")

        # Proyectos de invención del usuario. Se almacenan como obras/proyectos propios,
        # diferenciados de las obras literarias pero dentro del mismo grafo vital.
        invention_domain = self._node("Invención y sistemas", "domain")
        projects = [
            ("FORMA 333 / Olla lenta", 0.98, ["invento", "forma333", "olla", "reologia", "energia"], "FORMA333_Presentacion_09-07-2026.pptx", "Sistema térmico que busca convertir excitación electromagnética en movimiento y disipación viscosa útil dentro del fluido."),
            ("SAD / Tubería", 0.98, ["invento", "sad", "tuberia", "deteccion", "failsafe", "stf"], "SAD_Proyecto_Completo_Julio2026_11-09-2026.zip", "Sistema pasivo de aislamiento de tuberías basado en asimetría de flujo, comparador diferencial, carbómero, STF y ruta fail-safe AND-001."),
            ("CRONOS-333", 0.90, ["invento", "cronos333", "reologia", "multimedio", "gemelo_digital"], "documentación CRONOS-333 del proyecto", "Plataforma experimental multimedio para estudiar transferencia termo-mecánica, reología, magnetismo y recuperación energética con balance cerrado."),
        ]
        for label, imp, tags, source_ref, description in projects:
            n = self.add_node(label, kind="work", evidence="E1", importance=imp, source="corpus_user_inventions", tags=tags, attributes={"source_ref": source_ref, "description": description})
            self.connect(user["id"], n["id"], "es_inventor_de", weight=1.0, evidence="E1", source_ref=source_ref)
            self.connect(n["id"], invention_domain["id"], "pertenece_a", weight=0.95, evidence="E1", source_ref=source_ref)

        forma = self._node("FORMA 333 / Olla lenta", "work")
        for label, kind, rel in [
            ("STF", "concept", "emplea"),
            ("Carbómero", "concept", "emplea"),
            ("Disipación viscosa", "operator", "depende_de"),
            ("Excitación electromagnética", "concept", "depende_de"),
            ("Nido Trébol", "concept", "incluye"),
            ("Forma 333", "concept", "incluye"),
            ("CRONOS-333", "work", "evoluciona_de"),
        ]:
            nn = self._node(label, kind)
            self.connect(forma["id"], nn["id"], rel, weight=0.75, evidence="E1", source_ref="FORMA333_Presentacion_09-07-2026.pptx")

        sad = self._node("SAD / Tubería", "work")
        for label, kind, rel in [
            ("AND-001", "concept", "incorpora"),
            ("Gel C1 Carbómero", "concept", "incorpora"),
            ("Gel C2 STF", "concept", "incorpora"),
            ("Nido Trébol Forma 33", "concept", "incorpora"),
            ("Ruta diferencial", "concept", "dispone_de"),
            ("Ruta fail-safe", "concept", "dispone_de"),
            ("Detección de asimetría de caudal", "operator", "se_basa_en"),
            ("Tubería", "domain", "aplicación"),
        ]:
            nn = self._node(label, kind)
            self.connect(sad["id"], nn["id"], rel, weight=0.88, evidence="E1", source_ref="SAD_Proyecto_Completo_Julio2026_11-09-2026.zip")

        cronos = self._node("CRONOS-Espiral-OCa", "domain")
        for work in ("FORMA 333 / Olla lenta", "SAD / Tubería", "CRONOS-333"):
            wn = self._node(work, "work")
            self.connect(wn["id"], cronos["id"], "se_estudia_con", weight=0.55, evidence="E4", source_ref="hipotesis_usuario")

        # Relaciones conceptuales de CRONOS, siempre como hipótesis de trabajo.
        core = self._node("CRONOS-Espiral-OCa")
        ops = ["Pérdida", "Encuentro", "Desafío", "Transformación", "Integración", "Sustitución", "Refuncionalización", "Bifurcación", "Retorno transformado", "Metatransformación"]
        for op in ops:
            n = self.add_node(op, kind="operator", evidence="E4", importance=0.78, source="cronos_seed", tags=["cronos", "operador"])
            self.connect(core["id"], n["id"], "usa_operador", weight=0.85, evidence="E4")

        self.meta["seed_version"] = "v10.1"
        self.meta["seeded_at"] = _now()
        self._save()

    def set_user_label(self, label: str) -> None:
        label = (label or "Usuario").strip() or "Usuario"
        if label == self.user_label:
            return
        old_label = self.user_label
        self.user_label = label
        old = self._find_node(old_label, "person")
        current = self._find_node(label, "person")
        if current is None:
            current = self.add_node(label, kind="person", evidence="E1", importance=1.0, source="user_context", tags=["interlocutor", "autor"])
        if old and old.get("id") != current.get("id"):
            # Conservar el histórico sin borrar el nodo antiguo: queda enlazado como alias.
            self.connect(old["id"], current["id"], "alias_actualizado", weight=1.0, evidence="E1", source_ref="user_profile")
        self._save()

    def _find_node(self, label: str, kind: Optional[str] = None) -> Optional[dict[str, Any]]:
        for n in self.nodes.values():
            if n.get("label") == label and (kind is None or n.get("kind") == kind):
                return n
        return None

    def _node(self, label: str, kind: Optional[str] = None) -> dict[str, Any]:
        for n in self.nodes.values():
            if n.get("label") == label and (kind is None or n.get("kind") == kind):
                return n
        return self.add_node(label, kind=kind or "concept")

    # ---------- learning / co-evolution ----------
    def observe(self, user_text: str, answer: str = "", *, topic: str = "", mode: str = "organic") -> dict[str, Any]:
        text = f"{user_text}\n{answer}".strip()
        toks = sorted(_tokens(user_text), key=lambda x: (-len(x), x))[:14]
        user = self._node(self.user_label, "person")
        ceos = self._node("CEOS", "agent")
        touched = []
        for tok in toks[:8]:
            node = self.add_node(tok, kind="term", evidence="E4", importance=0.35, source="interaction", tags=["emergente"])
            self.connect(user["id"], node["id"], "menciona", weight=0.35, evidence="E4")
            self.connect(ceos["id"], node["id"], "atiende", weight=0.45, evidence="E4")
            touched.append(node["id"])
        if topic:
            top = self.add_node(topic[:180], kind="topic", evidence="E4", importance=0.82, source="adaptive", tags=["tema_actual"])
            self.connect(user["id"], top["id"], "explora", weight=0.8, evidence="E4")
            self.connect(ceos["id"], top["id"], "enseña_o_investiga", weight=0.8, evidence="E4")
        if answer:
            dialogue = self.add_node(text[:1800], kind="experience", evidence="E4", source="chat", tags=[mode, "interaccion"])
            self.connect(user["id"], dialogue["id"], "influye", weight=0.8, evidence="E4")
            self.connect(ceos["id"], dialogue["id"], "responde", weight=0.8, evidence="E4")
        return {"ok": True, "touched": touched, "generation": self.meta.get("generation", 0)}

    def learn_from_feedback(self, query: str, *, accepted: bool, note: str = "") -> dict[str, Any]:
        keys = self.search(query, limit=5)
        adjusted = []
        for n in keys:
            delta = 0.08 if accepted else -0.12
            n["mastery"] = max(0.0, min(1.0, float(n.get("mastery", 0.0)) + delta))
            if not accepted:
                n["stance"] = "uncertain"
            n.setdefault("feedback_history", []).append({"accepted": accepted, "note": note[:300], "at": _now()})
            n["feedback_history"] = n["feedback_history"][-20:]
            n["updated_at"] = _now()
            adjusted.append(n["id"])
        self.meta["generation"] = int(self.meta.get("generation", 0)) + 1
        self._save()
        return {"ok": True, "adjusted": adjusted}

    # ---------- retrieval ----------
    def neighbors(self, node_id: str, limit: int = 20) -> list[dict[str, Any]]:
        ids = []
        for e in self.edges:
            if e.get("source") == node_id:
                ids.append((e.get("target"), e.get("relation"), "out", e.get("weight", 0.0)))
            elif e.get("target") == node_id:
                ids.append((e.get("source"), e.get("relation"), "in", e.get("weight", 0.0)))
        out = []
        for nid, rel, direction, w in ids[:limit]:
            n = self.nodes.get(nid)
            if n:
                out.append({"node": n, "relation": rel, "direction": direction, "weight": w})
        return out

    def search(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        keys = _tokens(query)
        low = _norm(query)
        scored = []
        for n in self.nodes.values():
            blob = f"{n.get('label','')} {' '.join(n.get('tags') or [])} {' '.join(str(v) for v in (n.get('attributes') or {}).values())}".lower()
            if low and low in blob:
                score = 8.0
            else:
                lexical = float(sum(1 for k in keys if k in blob))
                if keys and lexical <= 0:
                    continue
                score = lexical
            score += 1.5 * float(n.get("importance", 0.5))
            score += 1.0 * (1.0 - float(n.get("mastery", 0.0))) * 0.5
            score += min(int(n.get("hits", 1)), 5) * 0.05
            if score <= 0:
                continue
            scored.append((score, n.get("updated_at") or "", n))
        scored.sort(key=lambda x: (-x[0], x[1]), reverse=False)
        return [n for _, _, n in scored[:limit]]

    # ---------- diagnosis / next move ----------
    def gaps(self, limit: int = 12) -> list[dict[str, Any]]:
        candidates = []
        for n in self.nodes.values():
            kind = n.get("kind")
            if kind not in {"concept", "topic", "thinker", "operator", "domain", "work"}:
                continue
            mastery = float(n.get("mastery", 0.0))
            if mastery >= 0.78 and n.get("stance") != "uncertain":
                continue
            gap = (1.0 - mastery) * float(n.get("importance", 0.5))
            if n.get("stance") == "uncertain":
                gap += 0.35
            if n.get("evidence") in {"E4", "E5"}:
                gap += 0.15
            candidates.append((gap, n))
        candidates.sort(key=lambda x: (-x[0], x[1].get("label", "")))
        return [{"gap": round(g, 3), "node": n} for g, n in candidates[:limit]]

    def next_moves(self, context: str = "", limit: int = 8) -> list[dict[str, Any]]:
        moves: list[dict[str, Any]] = []
        qhits = self.search(context, limit=12) if context else []
        teachable_kinds = {"concept", "topic", "thinker", "operator", "domain", "work", "author_trait"}
        qhits = [n for n in qhits if n.get("kind") in teachable_kinds]
        base = qhits or [x["node"] for x in self.gaps(8)]
        for n in base[:8]:
            mastery = float(n.get("mastery", 0.0))
            stance = n.get("stance")
            evidence = n.get("evidence") or "E4"
            if stance == "uncertain" or evidence in {"E4", "E5"}:
                action = "research"
                reason = "Hay incertidumbre o evidencia débil; conviene investigar antes de enseñar como hecho."
            elif mastery < 0.45:
                action = "teach"
                reason = "El dominio estimado es bajo; conviene construir una comprensión guiada."
            elif mastery < 0.78:
                action = "practice"
                reason = "El concepto está en desarrollo; conviene contrastarlo mediante transferencia."
            else:
                action = "connect"
                reason = "El concepto parece consolidado; conviene conectarlo con otro dominio."
            moves.append({
                "action": action,
                "node_id": n.get("id"),
                "title": n.get("label"),
                "reason": reason,
                "mastery": round(mastery, 3),
                "evidence": evidence,
            })
        # Siempre mantener una opción de metaaprendizaje.
        moves.append({
            "action": "reflect",
            "node_id": self._node("CEOS", "agent")["id"],
            "title": "¿Qué debería aprender CEOS ahora?",
            "reason": "El maestro también debe diagnosticar sus propios vacíos y no sólo los del aprendiz.",
            "mastery": 0.0,
            "evidence": "E4",
        })
        return moves[:limit]

    def teacher_next(self, context: str = "") -> dict[str, Any]:
        moves = self.next_moves(context, limit=5)
        teach = next((m for m in moves if m["action"] in {"teach", "practice", "connect"}), moves[0])
        return {
            "ok": True,
            "mode": "maestro-aprendiz",
            "next": teach,
            "lesson_prompt": f"Diseña una microlección sobre {teach['title']}. Explica, comprueba comprensión y termina con una transferencia a otro dominio.",
            "principle": "CEOS enseña lo que ya puede sostener y pregunta antes de rellenar lagunas.",
        }

    def research_next(self, context: str = "") -> dict[str, Any]:
        moves = self.next_moves(context, limit=8)
        item = next((m for m in moves if m["action"] == "research"), moves[0])
        return {
            "ok": True,
            "target": item,
            "queries": [
                f"{item['title']} fuentes primarias y revisión académica",
                f"{item['title']} críticas y contraejemplos",
                f"{item['title']} relación con CRONOS-Espiral-OCa",
            ],
            "rule": "Investigar primero lo incierto; no convertir hipótesis en memoria declarativa.",
        }

    def context_block(self, query: str = "", limit: int = 7) -> str:
        results = self.search(query, limit=limit) if query else [x["node"] for x in self.gaps(limit)]
        if not results:
            return ""
        moves = self.next_moves(query, limit=4)
        lines = ["GRAFO VIVO CEOS (coevolución usuario–obra–conocimiento):"]
        for n in results:
            lines.append(
                f"· {n.get('kind')} :: {n.get('label')} | mastery={float(n.get('mastery',0)):.2f} | "
                f"stance={n.get('stance')} | evidence={n.get('evidence')} | tags={','.join(n.get('tags') or [])[:100]}"
            )
            if n.get("kind") == "work" and (n.get("attributes") or {}).get("description"):
                lines.append(f"  descripción: {(n.get('attributes') or {}).get('description')[:360]}")
        if moves:
            lines.append("SIGUIENTES MOVIMIENTOS:")
            for m in moves[:3]:
                lines.append(f"· {m['action']} → {m['title']}: {m['reason']}")
        return "\n".join(lines)

    def connect_nodes(self, source_id: str, target_id: str, relation: str, *, weight: float = 0.7, evidence: str = "E4", source_ref: str = "user") -> dict[str, Any]:
        return self.connect(source_id, target_id, relation, weight=weight, evidence=evidence, source_ref=source_ref)

    def autopilot(self, context: str = "") -> dict[str, Any]:
        """Devuelve el siguiente ciclo conjunto: enseñar al usuario, estudiar CEOS y abrir investigación."""
        moves = self.next_moves(context, limit=10)
        teacher = next((m for m in moves if m["action"] in {"teach", "practice", "connect"}), None)
        research = next((m for m in moves if m["action"] == "research"), None)
        author = next((m for m in moves if "autor" in str(m.get("title", "")).lower() or m.get("node_id") == _id("domain", "Escritura y autor")), None)
        if author is None:
            author = {
                "action": "practice",
                "title": "Arte de eliminar / poda",
                "reason": "Es una prioridad explícita de entrenamiento autoral y puede convertirse en una prueba observable.",
                "mastery": 0.0,
                "evidence": "E4",
            }
        ceos_gap = next((g for g in self.gaps(20) if g["node"].get("evidence") in {"E4", "E5"}), None)
        return {
            "ok": True,
            "cycle": {
                "teach_user": teacher,
                "practice_author": author,
                "research_world": research,
                "learn_ceos": (ceos_gap["node"] if ceos_gap else None),
            },
            "principle": "Cada vuelta debe producir una ganancia para el usuario y otra para CEOS; investigar lo incierto y enseñar sólo lo suficientemente sostenido.",
        }

    def works(self, limit: int = 50) -> list[dict[str, Any]]:
        works = [n for n in self.nodes.values() if n.get("kind") == "work"]
        works.sort(key=lambda n: (-float(n.get("importance", 0.5)), n.get("label", "")))
        return works[:limit]

    def work_profile(self, label: str) -> dict[str, Any]:
        node = self._find_node(label, "work")
        if not node:
            return {"ok": False, "reason": "obra_o_proyecto_no_encontrado"}
        neigh = self.neighbors(node["id"], limit=40)
        return {"ok": True, "work": node, "neighbors": neigh, "related": [x["node"] for x in neigh]}

    def record_casual_turn(self, user_text: str, answer: str = "") -> dict[str, Any]:
        # Las conversaciones banales aportan continuidad relacional, no nodos de cada palabra.
        self.meta["casual_turns"] = int(self.meta.get("casual_turns", 0)) + 1
        self.meta["last_casual_at"] = _now()
        if answer:
            self.meta["last_casual_preview"] = re.sub(r"\s+", " ", answer)[:240]
        self._save()
        return {"ok": True, "casual_turns": self.meta["casual_turns"], "generation": self.meta.get("generation", 0)}

    def snapshot(self) -> dict[str, Any]:
        return {
            "version": self.VERSION,
            "generation": int(self.meta.get("generation", 0)),
            "nodes": len(self.nodes),
            "edges": len(self.edges),
            "recovery_required": bool(self.meta.get("recovery_required")),
            "kinds": self._kind_counts(),
            "gaps": self.gaps(8),
            "next": self.next_moves("", 6),
        }

    def _kind_counts(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for n in self.nodes.values():
            k = n.get("kind") or "unknown"
            out[k] = out.get(k, 0) + 1
        return dict(sorted(out.items(), key=lambda x: (-x[1], x[0])))

    def graph_view(self, focus: str = "", limit: int = 80, kinds: Optional[list[str]] = None) -> dict[str, Any]:
        """Vista curada para UI: mantiene el núcleo vivo aunque el grafo crezca."""
        limit = max(8, min(int(limit or 80), 250))
        focus = (focus or "").strip()
        wanted_kinds = {str(k).strip() for k in (kinds or []) if str(k).strip()}
        focus_hits = self.search(focus, limit=max(12, min(limit, 40))) if focus else []
        focus_ids = [n["id"] for n in focus_hits]

        # Núcleo que siempre debe permanecer visible.
        anchors = []
        for label, kind in ((self.user_label, "person"), ("CEOS", "agent")):
            n = self._find_node(label, kind)
            if n:
                anchors.append(n)
        anchors.extend(self.works(limit=8))

        candidates = list(self.nodes.values())
        degree = {}
        for e in self.edges:
            degree[e.get("source")] = degree.get(e.get("source"), 0) + 1
            degree[e.get("target")] = degree.get(e.get("target"), 0) + 1

        def score(n):
            sc = 0.0
            if n["id"] in focus_ids:
                sc += 100.0 - focus_ids.index(n["id"])
            sc += 7.0 * float(n.get("importance", 0.5))
            sc += 0.15 * min(degree.get(n["id"], 0), 40)
            if n.get("kind") in {"person", "agent", "work", "domain"}:
                sc += 4.0
            if wanted_kinds and n.get("kind") in wanted_kinds:
                sc += 20.0
            return sc

        candidates.sort(key=lambda n: (-score(n), n.get("label", "")))
        selected = []
        seen = set()
        for n in anchors + candidates:
            if n["id"] in seen:
                continue
            if wanted_kinds and n.get("kind") not in wanted_kinds and n.get("kind") not in {"person", "agent"}:
                continue
            selected.append(n)
            seen.add(n["id"])
            if len(selected) >= limit:
                break

        ids = {n["id"] for n in selected}
        edges = [e for e in self.edges if e.get("source") in ids and e.get("target") in ids]
        edges.sort(key=lambda e: (-float(e.get("weight", 0.0)), e.get("relation", "")))
        return {
            "ok": True,
            "mode": "focus" if focus else "overview",
            "focus": focus,
            "nodes": selected,
            "edges": edges[: max(limit * 3, 24)],
        }

    def graph(self, node_id: Optional[str] = None, limit: int = 100) -> dict[str, Any]:
        if node_id:
            ns = [self.nodes[node_id]] if node_id in self.nodes else []
            es = [e for e in self.edges if e.get("source") == node_id or e.get("target") == node_id]
        else:
            ns = list(self.nodes.values())[:limit]
            ids = {n["id"] for n in ns}
            es = [e for e in self.edges if e.get("source") in ids and e.get("target") in ids][:limit * 2]
        return {"ok": True, "nodes": ns, "edges": es}
