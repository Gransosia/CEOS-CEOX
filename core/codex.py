"""
Codex CRONOS — conocimiento extenso en pocos elementos reutilizables.

Idea central (infinitud discreta + compresión operativa):
  Un número FINITO de símbolos primitivos + reglas de combinación
  permite reconstruir una variedad prácticamente ilimitada de
  descripciones, lecciones y diagnósticos.

No es encriptación criptográfica. Es **codificación estructural**:
  - Átomos (L0): operaciones, regímenes, polaridades
  - Moléculas (L1): fórmulas cortas que combinan átomos
  - Cristales (L2): patrones reutilizables (casos, lecciones, reglas)
  - Mapas (L3): índices que apuntan a cristales sin copiar el texto entero

Así un corpus enorme se reduce a:
  tabla de átomos + lista de moléculas + cristales indexados + mapa.
"""
from __future__ import annotations
import json
import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


def _now():
    return datetime.now(timezone.utc).isoformat()


def _uid(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]


# --- Átomos canónicos del sistema CRONOS (conjunto cerrado y pequeño) ---
ATOMOS = {
    # Polaridad
    "CRN": "Cronos — estabilidad, memoria, previsibilidad",
    "VRT": "Vórtice — novedad, alteridad, transformación",
    # Regímenes
    "CMP": "Campo — región distinguible de una distribución",
    "PRT": "Protocolo — regla operativa estable",
    "POS": "Posesión — recurso o estructura retenida",
    "SEM": "Semilla — potencial de replicación / renovación",
    # Operaciones
    "INC": "Incorporar",
    "CON": "Conservar",
    "EXP": "Expulsar",
    "IGN": "Ignorar",
    # Espiral
    "EXPLO": "Fase exploración",
    "APREN": "Fase aprendizaje",
    "INSTI": "Fase institucionalización",
    "RENOV": "Fase renovación",
    # Diagnóstico
    "FRN": "Frontera / membrana",
    "TEN": "Tensión identitaria",
    "KAP": "κ control",
    "SIG": "σ ruido/novedad",
    "MOD": "Modo (habitual|oculto|prohibido)",
    "RGL": "Regla (estructurante|dependiente)",
}


# Plantillas moleculares: combinan átomos en fórmulas legibles
MOLECULA_TEMPLATES = [
    "{a}+{b}",           # composición
    "{a}>{b}",           # transición
    "{a}|{b}",           # tensión / polaridad
    "{a}@{fase}",        # anclaje en fase
    "[{a},{b},{c}]",     # acorde de tres
]


class Codex:
    """
    Almacén comprimido.
    Persiste átomos (fijos), moléculas aprendidas y cristales (contenido).
    """

    def __init__(self, base_path: str = "data/codex"):
        self.base = Path(base_path)
        self.base.mkdir(parents=True, exist_ok=True)
        self.molecules_file = self.base / "molecules.json"
        self.crystals_file = self.base / "crystals.json"
        self.maps_file = self.base / "maps.json"
        self._ensure(self.molecules_file, [])
        self._ensure(self.crystals_file, {})
        self._ensure(self.maps_file, {})

    def _ensure(self, path: Path, default):
        if not path.exists():
            path.write_text(json.dumps(default, ensure_ascii=False, indent=2), encoding="utf-8")

    def _load(self, path: Path):
        return json.loads(path.read_text(encoding="utf-8"))

    def _save(self, path: Path, data):
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    # ----- Átomos -----
    def list_atoms(self) -> dict:
        return dict(ATOMOS)

    # ----- Moléculas (fórmulas cortas) -----
    def add_molecule(self, formula: str, meaning: str, tags: Optional[list] = None) -> dict:
        mols = self._load(self.molecules_file)
        entry = {
            "id": _uid(formula + meaning),
            "formula": formula,
            "meaning": meaning.strip(),
            "tags": tags or [],
            "created_at": _now(),
        }
        # dedup by formula+meaning
        for m in mols:
            if m["formula"] == entry["formula"] and m["meaning"] == entry["meaning"]:
                return m
        mols.append(entry)
        self._save(self.molecules_file, mols)
        return entry

    def molecules(self) -> list:
        return self._load(self.molecules_file)

    # ----- Cristales (contenido comprimido por referencia) -----
    def store_crystal(self, text: str, kind: str = "fragment", meta: Optional[dict] = None) -> str:
        """Guarda texto una sola vez; devuelve id corto. Deduplica por hash."""
        crystals = self._load(self.crystals_file)
        cid = _uid(text.strip())
        if cid not in crystals:
            crystals[cid] = {
                "id": cid,
                "kind": kind,
                "text": text.strip(),
                "chars": len(text.strip()),
                "meta": meta or {},
                "created_at": _now(),
            }
            self._save(self.crystals_file, crystals)
        return cid

    def get_crystal(self, cid: str) -> Optional[dict]:
        return self._load(self.crystals_file).get(cid)

    # ----- Mapas (índices temáticos → ids de cristales/moléculas) -----
    def map_topic(self, topic: str, crystal_ids: list, molecule_ids: Optional[list] = None):
        maps = self._load(self.maps_file)
        key = topic.strip().lower()
        maps[key] = {
            "topic": topic,
            "crystals": crystal_ids,
            "molecules": molecule_ids or [],
            "updated_at": _now(),
        }
        self._save(self.maps_file, maps)
        return maps[key]

    def get_map(self, topic: str) -> Optional[dict]:
        return self._load(self.maps_file).get(topic.strip().lower())

    # ----- Compresión de un texto largo en codex -----
    def compress_text(self, text: str, topic: str, max_chunks: int = 40) -> dict:
        """
        Reduce un texto largo a:
          - N cristales (chunks únicos)
          - moléculas auto-etiquetadas con átomos detectados
          - un mapa del tema
        """
        # chunk simple
        parts = re.split(r"\n\s*\n|(?<=[.!?])\s+", text)
        chunks = []
        buf = ""
        for p in parts:
            p = p.strip()
            if not p:
                continue
            if len(buf) + len(p) < 350:
                buf = (buf + " " + p).strip()
            else:
                if buf:
                    chunks.append(buf)
                buf = p
        if buf:
            chunks.append(buf)
        chunks = chunks[:max_chunks]

        cids = []
        for ch in chunks:
            cids.append(self.store_crystal(ch, kind="chunk", meta={"topic": topic}))

        # detectar átomos presentes y crear moléculas resumen
        found_atoms = []
        low = text.lower()
        atom_keywords = {
            "CRN": ["cronos", "estabilidad", "previsibilidad", "memoria"],
            "VRT": ["vórtice", "vortice", "novedad", "alteridad"],
            "CMP": ["campo"],
            "PRT": ["protocolo"],
            "POS": ["posesión", "posesion"],
            "SEM": ["semilla"],
            "INC": ["incorporar"],
            "CON": ["conservar"],
            "EXP": ["expulsar"],
            "IGN": ["ignorar"],
            "FRN": ["frontera", "membrana"],
            "TEN": ["tensión", "tension", "identidad"],
        }
        for code, kws in atom_keywords.items():
            if any(k in low for k in kws):
                found_atoms.append(code)

        mol_ids = []
        if found_atoms:
            formula = "+".join(found_atoms[:6])
            meaning = f"Tema «{topic}» activa átomos: " + ", ".join(
                f"{a}={ATOMOS.get(a, a)}" for a in found_atoms[:6]
            )
            mol = self.add_molecule(formula, meaning, tags=[topic.lower()[:40]])
            mol_ids.append(mol["id"])

        m = self.map_topic(topic, cids, mol_ids)
        fractal_info = None
        try:
            fractal_info = self.maybe_fractal_after_ingest(topic)
        except Exception:
            fractal_info = None
        return {
            "topic": topic,
            "atoms_detected": found_atoms,
            "crystals": len(cids),
            "molecules": len(mol_ids),
            "map": m,
            "fractal": fractal_info,
            "compression_ratio_estimate": round(
                sum(len(self.get_crystal(c)["text"]) for c in cids if self.get_crystal(c))
                / max(len(text), 1),
                3,
            ),
        }

    def expand_topic(self, topic: str, limit: int = 12) -> dict:
        """Reconstruye conocimiento de un tema desde el mapa (pocos elementos → texto útil)."""
        m = self.get_map(topic)
        if not m:
            # búsqueda difusa en keys
            maps = self._load(self.maps_file)
            key = topic.strip().lower()
            for k, v in maps.items():
                if key in k or k in key:
                    m = v
                    break
        if not m:
            return {"ok": False, "error": "Tema no mapeado en el codex", "topic": topic}

        crystals = []
        for cid in m.get("crystals", [])[:limit]:
            c = self.get_crystal(cid)
            if c:
                crystals.append(c["text"])

        mols = []
        all_mols = {x["id"]: x for x in self.molecules()}
        for mid in m.get("molecules", []):
            if mid in all_mols:
                mols.append(all_mols[mid])

        return {
            "ok": True,
            "topic": m["topic"],
            "molecules": mols,
            "fragments": crystals,
            "atoms": self.list_atoms(),
        }

    def stats(self) -> dict:
        return {
            "atoms": len(ATOMOS),
            "molecules": len(self.molecules()),
            "crystals": len(self._load(self.crystals_file)),
            "maps": len(self._load(self.maps_file)),
        }

    def export_compact(self) -> dict:
        """Export mínimo: átomos (referencia) + moléculas + mapas + cristales."""
        return {
            "exported_at": _now(),
            "atoms_ref": list(ATOMOS.keys()),
            "molecules": self.molecules(),
            "crystals": self._load(self.crystals_file),
            "maps": self._load(self.maps_file),
        }

    def import_compact(self, data: dict) -> dict:
        mols = self._load(self.molecules_file)
        existing_m = {(m["formula"], m["meaning"]) for m in mols}
        added_m = 0
        for m in data.get("molecules", []):
            key = (m.get("formula"), m.get("meaning"))
            if key not in existing_m:
                mols.append(m)
                existing_m.add(key)
                added_m += 1
        self._save(self.molecules_file, mols)

        crystals = self._load(self.crystals_file)
        added_c = 0
        for cid, c in data.get("crystals", {}).items():
            if cid not in crystals:
                crystals[cid] = c
                added_c += 1
        self._save(self.crystals_file, crystals)

        maps = self._load(self.maps_file)
        maps.update(data.get("maps", {}))
        self._save(self.maps_file, maps)

        return {"molecules_added": added_m, "crystals_added": added_c, "maps": len(maps)}


# ----- Re-codificación fractal (presupuesto fijo, densidad creciente) -----
#
# Idea CRONOS: el conocimiento no crece solo sumando texto.
# Crece cambiando el *cifrado* (cómo se codifica) dentro de un tamaño acotado.
# El "logaritmo de encriptado" es el nivel de generación: cada ciclo reescribe
# cristales redundantes en moléculas + super-cristales más densos.

FRAC_BUDGET_CRYSTALS = 200   # techo blando de cristales totales
FRAC_TOPIC_CRYSTALS = 12     # máx cristales por tema tras re-codificar
FRAC_META_FILE = "fractal_meta.json"


def _fractal_meta_path(base: Path) -> Path:
    return base / FRAC_META_FILE


class _FractalMixin:
    """Métodos de re-codificación; se mezclan en Codex vía herencia al final del módulo."""
    pass


def _attach_fractal_methods():
    """Inyecta métodos fractal en la clase Codex ya definida."""

    def _meta(self) -> dict:
        path = self.base / FRAC_META_FILE
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {
            "generation": 0,          # logaritmo de encriptado (nivel)
            "cycles": [],             # historial breve de ciclos
            "last_cycle": None,
            "budget_crystals": FRAC_BUDGET_CRYSTALS,
        }

    def _save_meta(self, meta: dict):
        path = self.base / FRAC_META_FILE
        path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    def fractal_state(self) -> dict:
        meta = self._meta()
        st = self.stats()
        return {
            "generation": meta.get("generation", 0),
            "logarithm": meta.get("generation", 0),  # alias conceptual
            "budget_crystals": meta.get("budget_crystals", FRAC_BUDGET_CRYSTALS),
            "crystals_now": st["crystals"],
            "molecules_now": st["molecules"],
            "maps_now": st["maps"],
            "fill_ratio": round(st["crystals"] / max(meta.get("budget_crystals", FRAC_BUDGET_CRYSTALS), 1), 3),
            "last_cycle": meta.get("last_cycle"),
            "cycles_recorded": len(meta.get("cycles") or []),
        }

    def _summarize_cluster(self, texts: list[str], topic: str) -> str:
        """Fusión local densa: no LLM; extrae frases clave y deduplica."""
        seen = set()
        keys = []
        for t in texts:
            for sent in re.split(r"(?<=[.!?])\s+", t):
                s = sent.strip()
                if len(s) < 40:
                    continue
                sig = re.sub(r"\W+", "", s.lower())[:48]
                if sig in seen:
                    continue
                seen.add(sig)
                keys.append(s[:220])
                if len(keys) >= 6:
                    break
            if len(keys) >= 6:
                break
        header = f"[gen-denso·{topic}] "
        body = " · ".join(keys) if keys else " ".join(texts)[:500]
        return (header + body)[:900]

    def fractal_reencode(self, topic: Optional[str] = None, force: bool = False) -> dict:
        """
        Un ciclo de re-encriptación fractal.

        - Si hay topic: densifica ese mapa (N cristales → pocos super-cristales + molécula).
        - Si no: recorre mapas y, si se supera el presupuesto global, densifica los más grandes.
        - Sube generation (logaritmo de encriptado).
        - El número total de cristales no crece; idealmente baja o se mantiene.
        """
        meta = self._meta()
        crystals = self._load(self.crystals_file)
        maps = self._load(self.maps_file)
        before = len(crystals)

        targets = []
        if topic:
            key = topic.strip().lower()
            if key in maps:
                targets.append(key)
            else:
                for k in maps:
                    if key in k or k in key:
                        targets.append(k)
        else:
            # Priorizar mapas con más cristales
            ranked = sorted(
                maps.items(),
                key=lambda kv: len(kv[1].get("crystals") or []),
                reverse=True,
            )
            over = before > meta.get("budget_crystals", FRAC_BUDGET_CRYSTALS)
            if force or over:
                targets = [k for k, _ in ranked[:8]]
            else:
                # ciclo suave: solo los 3 más pesados
                targets = [k for k, v in ranked[:3] if len(v.get("crystals") or []) > FRAC_TOPIC_CRYSTALS]

        changed = []
        removed = 0
        added = 0

        for key in targets:
            m = maps.get(key) or {}
            cids = list(m.get("crystals") or [])
            if len(cids) <= FRAC_TOPIC_CRYSTALS and not force:
                continue
            texts = []
            for cid in cids:
                c = crystals.get(cid)
                if c and c.get("text"):
                    texts.append(c["text"])
            if len(texts) < 2:
                continue

            # Agrupar en bloques y crear super-cristales
            dense_ids = []
            step = max(2, len(texts) // max(FRAC_TOPIC_CRYSTALS // 2, 1))
            for i in range(0, len(texts), step):
                cluster = texts[i : i + step]
                dense = self._summarize_cluster(cluster, m.get("topic") or key)
                nid = self.store_crystal(
                    dense,
                    kind="fractal",
                    meta={
                        "topic": m.get("topic") or key,
                        "generation": int(meta.get("generation") or 0) + 1,
                        "source_n": len(cluster),
                    },
                )
                dense_ids.append(nid)
                added += 1

            # Molécula de generación (cifrado de nivel superior)
            formula = f"FRAC/G{int(meta.get('generation') or 0)+1}"
            meaning = (
                f"Re-cifrado fractal de «{m.get('topic') or key}»: "
                f"{len(cids)} cristales → {len(dense_ids)} densos"
            )
            mol = self.add_molecule(formula, meaning, tags=["fractal", key[:40]])
            mol_ids = list(m.get("molecules") or [])
            mol_ids.append(mol["id"])

            # Recargar cristales (store_crystal ya persistió los densos)
            crystals = self._load(self.crystals_file)
            old_set = set(cids)
            for cid in old_set:
                if cid in crystals and cid not in dense_ids:
                    crystals.pop(cid, None)
                    removed += 1

            maps[key] = {
                "topic": m.get("topic") or key,
                "crystals": dense_ids[:FRAC_TOPIC_CRYSTALS],
                "molecules": mol_ids[-8:],
                "updated_at": _now(),
                "fractal_generation": int(meta.get("generation") or 0) + 1,
            }
            changed.append({
                "topic": maps[key]["topic"],
                "before": len(cids),
                "after": len(maps[key]["crystals"]),
            })

        self._save(self.crystals_file, crystals)
        self._save(self.maps_file, maps)

        gen = int(meta.get("generation") or 0) + (1 if changed else 0)
        meta["generation"] = gen
        meta["last_cycle"] = _now()
        cycles = meta.get("cycles") or []
        cycles.append({
            "ts": meta["last_cycle"],
            "generation": gen,
            "changed": changed,
            "removed": removed,
            "added": added,
            "crystals_after": len(crystals),
        })
        meta["cycles"] = cycles[-20:]
        self._save_meta(meta)

        return {
            "ok": True,
            "generation": gen,
            "logarithm": gen,
            "changed_topics": changed,
            "crystals_removed": removed,
            "crystals_added": added,
            "crystals_after": len(crystals),
            "crystals_before": before,
            "size_delta": len(crystals) - before,
            "message": (
                f"Ciclo fractal G{gen}: {len(changed)} temas re-cifrados; "
                f"cristales {before}→{len(crystals)} (Δ{len(crystals)-before})."
                if changed else
                "Nada que densificar aún (presupuesto holgado o temas ya densos)."
            ),
        }

    def maybe_fractal_after_ingest(self, topic: str) -> Optional[dict]:
        """Tras ingerir, si el tema o el global se pasaron de presupuesto, re-cifrar."""
        st = self.stats()
        meta = self._meta()
        m = self.get_map(topic)
        heavy = m and len(m.get("crystals") or []) > FRAC_TOPIC_CRYSTALS
        over = st["crystals"] > meta.get("budget_crystals", FRAC_BUDGET_CRYSTALS)
        if heavy or over:
            return self.fractal_reencode(topic=topic if heavy else None, force=bool(heavy))
        return None

    # bind
    Codex._meta = _meta
    Codex._save_meta = _save_meta
    Codex.fractal_state = fractal_state
    Codex._summarize_cluster = _summarize_cluster
    Codex.fractal_reencode = fractal_reencode
    Codex.maybe_fractal_after_ingest = maybe_fractal_after_ingest


_attach_fractal_methods()
