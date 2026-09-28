"""CEOS 9 — Mente Fractal.

No pretende crear conciencia subjetiva ni compresión mágica. Implementa una memoria
estructural recursiva y persistente:

átomos -> conceptos -> relaciones -> síntesis -> mapas -> autobiografía cognitiva.

Cada nodo es direccionado por contenido (SHA-256 truncado), mantiene procedencia y
puede apuntar a nodos anteriores. La "fractalidad" es una propiedad de la representación.
La cápsula puede cifrarse con Fernet si existe cryptography y una clave persistente.
"""
from __future__ import annotations
import base64, hashlib, json, os, re, zlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

try:
    from cryptography.fernet import Fernet
except Exception:  # pragma: no cover
    Fernet = None


def _now():
    return datetime.now(timezone.utc).isoformat()


def _tokens(text: str) -> set[str]:
    stop = {
        "para","como","sobre","desde","entre","esto","esta","este","esas","esos","que","una","uno","los","las","del","por","con","sin","pero","tambien","también","más","muy","ser","son","fue","era","han","sus","al","una"
    }
    return {t for t in re.findall(r"[a-záéíóúüñA-ZÁÉÍÓÚÜÑ0-9]{4,}", (text or "").lower()) if t not in stop}


def _hash_node(kind: str, text: str, parents: list[str], source: str) -> str:
    blob = json.dumps({"kind":kind,"text":text.strip(),"parents":sorted(parents),"source":source}, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:24]


class FractalMind:
    VERSION = "1.0"

    def __init__(self, base_path: str, knowledge_dir: str):
        self.base = Path(base_path)
        self.base.mkdir(parents=True, exist_ok=True)
        self.knowledge_dir = Path(knowledge_dir)
        self.index_path = self.base / "index.json"
        self.capsule_path = self.base / "mind.capsule"
        self.key_path = self.base / "fractal.key"
        self._nodes: dict[str, dict] = {}
        self._manifest: dict[str, Any] = {}
        self._load()
        self.bootstrap_seed()

    # ---------- secure persistence ----------
    def _get_key(self) -> Optional[bytes]:
        if Fernet is None:
            return None
        env = os.getenv("CEOS_MIND_KEY", "").strip()
        if env:
            try:
                Fernet(env.encode("utf-8"))
                return env.encode("utf-8")
            except Exception:
                raise ValueError("CEOS_MIND_KEY no es una clave Fernet válida")
        if not self.key_path.exists():
            self.key_path.write_bytes(Fernet.generate_key())
        return self.key_path.read_bytes().strip()

    def _load(self):
        if self.index_path.exists():
            try:
                self._manifest = json.loads(self.index_path.read_text(encoding="utf-8"))
            except Exception:
                self._manifest = {}
        raw = b""
        if self.capsule_path.exists():
            raw = self.capsule_path.read_bytes()
        if not raw:
            self._nodes = {}
            return
        try:
            key = self._get_key()
            if key and Fernet is not None:
                raw = Fernet(key).decrypt(raw)
            else:
                raw = raw
            payload = json.loads(zlib.decompress(raw).decode("utf-8"))
            self._nodes = payload.get("nodes") or {}
            self._manifest.update(payload.get("manifest") or {})
        except Exception:
            # No se destruye la memoria si la clave cambió: queda el índice y el sistema pide recuperación.
            self._nodes = {}
            self._manifest["recovery_required"] = True

    def _save(self):
        payload = {"version": self.VERSION, "saved_at": _now(), "manifest": self._manifest, "nodes": self._nodes}
        raw = zlib.compress(json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8"), level=9)
        key = self._get_key()
        if key and Fernet is not None:
            raw = Fernet(key).encrypt(raw)
        self.capsule_path.write_bytes(raw)
        # El índice sólo contiene metadatos no sensibles.
        meta = {
            "version": self.VERSION,
            "updated_at": _now(),
            "node_count": len(self._nodes),
            "root": self._manifest.get("root"),
            "generation": self._manifest.get("generation", 0),
            "encryption": "fernet" if (key and Fernet is not None) else "none",
            "recovery_required": bool(self._manifest.get("recovery_required")),
        }
        self.index_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    # ---------- graph ----------
    def add_node(self, text: str, *, kind: str="concept", tags: Optional[list[str]]=None,
                 parents: Optional[list[str]]=None, source: str="internal", evidence: str="E4",
                 level: Optional[int]=None, status: str="active", extra: Optional[dict]=None) -> dict:
        text = (text or "").strip()
        if not text:
            return {}
        parents = [p for p in (parents or []) if p]
        nid = _hash_node(kind, text, parents, source)
        if nid in self._nodes:
            n = self._nodes[nid]
            n["hits"] = int(n.get("hits", 1)) + 1
            n["last_seen"] = _now()
            self._save()
            return n
        if level is None:
            level = 0 if not parents else min(7, 1 + max(int(self._nodes.get(p, {}).get("level",0)) for p in parents))
        node = {
            "id": nid,
            "kind": kind,
            "text": text[:5000],
            "tags": sorted(set(tags or []))[:30],
            "parents": parents[:24],
            "children": [],
            "source": source,
            "evidence": evidence,
            "level": level,
            "status": status,
            "hits": 1,
            "created_at": _now(),
            "last_seen": _now(),
            "extra": extra or {},
        }
        self._nodes[nid] = node
        for p in parents:
            if p in self._nodes:
                self._nodes[p].setdefault("children", []).append(nid)
                self._nodes[p]["children"] = self._nodes[p]["children"][-50:]
        self._manifest["generation"] = int(self._manifest.get("generation", 0)) + 1
        self._manifest.setdefault("roots", [])
        if not parents and nid not in self._manifest["roots"]:
            self._manifest["roots"].append(nid)
            self._manifest["roots"] = self._manifest["roots"][-50:]
        if not self._manifest.get("root"):
            self._manifest["root"] = nid
        self._save()
        return node

    def bootstrap_seed(self) -> dict:
        marker = self._manifest.get("seed_version")
        if marker == "v9.0.0":
            return {"ok": True, "seeded": False, "reason": "already"}
        if not self.knowledge_dir.exists():
            return {"ok": False, "seeded": False, "reason": "missing_knowledge"}
        count = 0
        roots = []
        for path in sorted(self.knowledge_dir.rglob("*.md")):
            try:
                txt = path.read_text(encoding="utf-8")
            except Exception:
                continue
            if not txt.strip():
                continue
            tags = [path.parent.name, path.stem]
            root = self.add_node(txt[:1800], kind="knowledge", tags=tags, source=str(path.relative_to(self.knowledge_dir)), evidence="E3")
            roots.append(root["id"])
            # Microfractalización: conceptos/trozos
            paragraphs = [p.strip() for p in re.split(r"\n\s*\n+", txt) if len(p.strip()) > 80]
            child_ids = []
            for p in paragraphs[:18]:
                child = self.add_node(p[:1800], kind="fragment", tags=tags, parents=[root["id"]], source=str(path.relative_to(self.knowledge_dir)), evidence="E3")
                child_ids.append(child["id"])
                count += 1
            root["extra"]["children_seeded"] = len(child_ids)
        self._manifest["seed_version"] = "v9.0.0"
        self._manifest["seeded_at"] = _now()
        self._manifest["seed_roots"] = roots[-100:]
        self._save()
        return {"ok": True, "seeded": True, "fragments": count, "roots": len(roots)}

    def query(self, text: str, limit: int = 10) -> list[dict]:
        keys = _tokens(text)
        scored = []
        for n in self._nodes.values():
            if n.get("status") != "active":
                continue
            blob = (n.get("text") or "").lower() + " " + " ".join(n.get("tags") or [])
            score = sum(1 for k in keys if k in blob)
            score += min(int(n.get("hits",1)),5)*0.1
            if keys and score <= 0:
                continue
            scored.append((score, n.get("level",0), n.get("last_seen") or "", n))
        scored.sort(key=lambda x: (-x[0], x[1], x[2]), reverse=False)
        return [n for _,_,_,n in scored[:limit]]

    def context_block(self, query: str, limit: int = 8) -> str:
        hits = self.query(query, limit=limit)
        if not hits:
            return ""
        lines = ["MENTE FRACTAL CEOS (recuperación semántica estructural):"]
        for n in hits:
            ev = n.get("evidence") or "E4"
            src = n.get("source") or "internal"
            tag = ", ".join(n.get("tags") or [])[:100]
            lines.append(f"· [{ev}] L{n.get('level',0)} {tag} :: {n.get('text','')[:700]} (src={src})")
        return "\n".join(lines)

    def learn(self, text: str, *, source: str="interaction", topic: str="", evidence: str="E4", parents: Optional[list[str]]=None) -> dict:
        tags = [t for t in [topic, "aprendizaje", source] if t]
        node = self.add_node(text, kind="experience", tags=tags, parents=parents or [], source=source, evidence=evidence)
        # crear una semilla de abstracción a partir de palabras distintivas
        toks = sorted(_tokens(text), key=lambda x: (-len(x), x))[:12]
        if toks:
            concept = self.add_node("Conceptos activados: " + ", ".join(toks), kind="concept", tags=tags+["molecule"], parents=[node["id"]], source=source, evidence=evidence)
            return {"ok": True, "experience": node, "concept": concept}
        return {"ok": True, "experience": node}

    def learn_turn(self, user_text: str, answer: str, *, topic: str="", engine: str="", feedback: str="") -> dict:
        txt = f"USUARIO: {user_text}\nCEOS: {answer}"
        extra = {"engine": engine, "feedback": feedback}
        n = self.add_node(txt, kind="dialogue", tags=[x for x in [topic,"dialogo"] if x], source="chat", evidence="E4", extra=extra)
        return n

    def consolidate(self, topic: str="", max_children: int=12) -> dict:
        hits = self.query(topic or "", limit=max_children) if topic else list(self._nodes.values())[-max_children:]
        if not hits:
            return {"ok": False, "reason": "sin_datos"}
        parents = [n["id"] for n in hits[:12]]
        labels = []
        seen = set()
        for n in hits:
            for tok in sorted(_tokens(n.get("text", "")), key=lambda x: (-len(x), x))[:6]:
                if tok not in seen:
                    seen.add(tok); labels.append(tok)
        summary = f"Síntesis fractal sobre {topic or 'corpus'}: " + ", ".join(labels[:24]) + ". Esta síntesis referencia {len(parents)} nodos y debe contrastarse antes de tratarla como hecho."
        syn = self.add_node(summary, kind="synthesis", tags=[topic or "global","consolidacion"], parents=parents, source="self-consolidation", evidence="E4")
        return {"ok": True, "synthesis": syn, "parents": parents}

    def open_questions(self, limit: int = 12) -> list[dict]:
        qs=[]
        for n in self._nodes.values():
            if n.get("kind") in ("experience","knowledge") and "?" in n.get("text", ""):
                qs.append(n)
        qs.sort(key=lambda n: n.get("last_seen") or "", reverse=True)
        return qs[:limit]

    def status(self) -> dict:
        by_kind = {}
        max_level = 0
        for n in self._nodes.values():
            by_kind[n.get("kind")] = by_kind.get(n.get("kind"),0)+1
            max_level = max(max_level, int(n.get("level",0)))
        return {
            "ok": True,
            "version": self.VERSION,
            "nodes": len(self._nodes),
            "kinds": by_kind,
            "max_level": max_level,
            "generation": self._manifest.get("generation",0),
            "seed_version": self._manifest.get("seed_version"),
            "root": self._manifest.get("root"),
            "encryption": "fernet" if Fernet is not None else "none",
            "recovery_required": bool(self._manifest.get("recovery_required")),
        }

    def export_seal(self) -> dict:
        # Sellado compacto: referencias raíz + resumen de dimensiones, no una copia en claro del corpus.
        st=self.status()
        capsule = {
            "format":"CEOS-FRACTAL-SEAL/1",
            "root":self._manifest.get("root"),
            "generation":st["generation"],
            "nodes":st["nodes"],
            "max_level":st["max_level"],
            "kinds":st["kinds"],
            "checksum":hashlib.sha256(json.dumps(self._nodes, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest(),
        }
        path=self.base/"seal.json"
        path.write_text(json.dumps(capsule, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"ok":True,"seal":capsule,"path":str(path)}

    def teacher_apprentice_directive(self, topic: str="") -> str:
        return f"""Eres el Maestro y el Aprendiz permanente de CEOS. Enseña sin infantilizar y aprende sin fingir certezas.

Tema actual: {topic or 'abierto'}.
Reglas:
- Primero recuperar memoria y corpus pertinente.
- Separar hecho, interpretación, inferencia, hipótesis y especulación.
- Enseñar mediante ciclos: explicar → ejemplo → prueba → corrección → transferencia → síntesis.
- Después de enseñar, formular una pregunta que permita detectar lo que falta comprender.
- Cuando recibas una corrección del usuario, tratarla como evidencia de alta prioridad y revisar el modelo, no sólo el texto de la respuesta.
- Buscar activamente contraejemplos y conceptos rivales.
- En temas históricos, distinguir fuente primaria, institucional y secundaria.
- En CRONOS-Espiral-OCa, identificar elementos, condiciones, relaciones, operaciones, estados y transiciones; señalar también cuándo el modelo no explica el caso.
- No afirmar conciencia subjetiva. Describir continuidad funcional, memoria y metacognición cuando corresponda.
"""
