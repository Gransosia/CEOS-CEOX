"""
Persistencia completa de CEOS (anti-amnesia en Render Free).

Exporta / importa un snapshot JSON con:
- memoria (casos, hitos, trayectorias)
- gramática
- códice
- reservorio (índice + textos almacenados)
- memoria larga
- identidad / usuario
- escala de evolución (snapshots)

Uso: Sync → Descargar copia completa tras cargar libros.
"""
from __future__ import annotations
import json
import zipfile
import io
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_snapshot(
    *,
    data_dir: Path,
    memory=None,
    grammar=None,
    codex=None,
    library=None,
    long_memory=None,
    identity=None,
    user=None,
) -> dict:
    data_dir = Path(data_dir)
    snap: dict[str, Any] = {
        "format": "ceos-full-snapshot-v1",
        "exported_at": _now(),
        "data_dir": str(data_dir),
    }

    if memory is not None:
        try:
            snap["memory"] = memory.export_all()
        except Exception as e:
            snap["memory_error"] = str(e)[:200]

    if grammar is not None:
        try:
            snap["grammar"] = grammar.export_learned()
        except Exception as e:
            snap["grammar_error"] = str(e)[:200]

    if codex is not None:
        try:
            snap["codex"] = codex.export_compact()
        except Exception as e:
            snap["codex_error"] = str(e)[:200]

    # Reservorio: índice + contenido de docs_dir
    if library is not None:
        try:
            idx = library.list_docs() if hasattr(library, "list_docs") else []
            texts = {}
            docs_dir = getattr(library, "docs_dir", None)
            if docs_dir is not None:
                docs_dir = Path(docs_dir)
                for entry in idx:
                    stored = entry.get("stored_as")
                    if not stored:
                        continue
                    p = docs_dir / stored
                    if p.exists() and p.stat().st_size < 2_000_000:
                        texts[stored] = p.read_text(encoding="utf-8", errors="replace")
            snap["library"] = {
                "index": idx,
                "texts": texts,
                "stats": library.stats() if hasattr(library, "stats") else {},
            }
        except Exception as e:
            snap["library_error"] = str(e)[:200]

    if long_memory is not None:
        try:
            # LongMemory suele guardar en data/long_memory
            base = Path(getattr(long_memory, "base", data_dir / "long_memory"))
            lm = {}
            for name in ("facts.json", "topics.json", "insights.json", "state.json"):
                fp = base / name
                if fp.exists():
                    lm[name] = json.loads(fp.read_text(encoding="utf-8"))
            if hasattr(long_memory, "data") and isinstance(long_memory.data, dict):
                lm["data"] = long_memory.data
            snap["long_memory"] = lm
        except Exception as e:
            snap["long_memory_error"] = str(e)[:200]

    if identity is not None:
        try:
            snap["identity"] = identity.who_am_i()
            if hasattr(identity, "state"):
                snap["identity_state"] = dict(identity.state)
        except Exception as e:
            snap["identity_error"] = str(e)[:200]

    if user is not None:
        try:
            snap["user"] = user.get() if hasattr(user, "get") else {}
        except Exception as e:
            snap["user_error"] = str(e)[:200]

    # evolution scale snapshots file
    try:
        scale_file = data_dir / "evolve" / "scale_snapshots.json"
        if scale_file.exists():
            snap["evolution_scale"] = json.loads(scale_file.read_text(encoding="utf-8"))
    except Exception as e:
        snap["evolution_scale_error"] = str(e)[:200]

    # tamaño orientativo
    try:
        snap["approx_chars"] = len(json.dumps(snap, ensure_ascii=False))
    except Exception:
        pass
    return snap


def restore_snapshot(
    snap: dict,
    *,
    data_dir: Path,
    memory=None,
    grammar=None,
    codex=None,
    library=None,
    long_memory=None,
    identity=None,
    user=None,
) -> dict:
    stats = {"ok": True, "restored": []}
    data_dir = Path(data_dir)

    if memory is not None and snap.get("memory"):
        try:
            r = memory.merge_from(snap["memory"])
            stats["memory"] = r
            stats["restored"].append("memory")
        except Exception as e:
            stats["memory_error"] = str(e)[:200]

    if grammar is not None and snap.get("grammar"):
        try:
            n = grammar.merge_learned(snap["grammar"])
            stats["grammar_fragments"] = n
            stats["restored"].append("grammar")
        except Exception as e:
            stats["grammar_error"] = str(e)[:200]

    if codex is not None and snap.get("codex"):
        try:
            r = codex.import_compact(snap["codex"])
            stats["codex"] = r
            stats["restored"].append("codex")
        except Exception as e:
            stats["codex_error"] = str(e)[:200]

    if library is not None and snap.get("library"):
        try:
            lib_data = snap["library"]
            idx = lib_data.get("index") or []
            texts = lib_data.get("texts") or {}
            docs_dir = Path(getattr(library, "docs_dir", data_dir / "library" / "docs"))
            docs_dir.mkdir(parents=True, exist_ok=True)
            # merge index by id
            current = {d.get("id"): d for d in (library.list_docs() or []) if d.get("id")}
            for entry in idx:
                eid = entry.get("id")
                if not eid:
                    continue
                stored = entry.get("stored_as")
                if stored and stored in texts:
                    (docs_dir / stored).write_text(texts[stored], encoding="utf-8")
                current[eid] = entry
            library._save_index(list(current.values()))
            stats["library_docs"] = len(current)
            stats["restored"].append("library")
        except Exception as e:
            stats["library_error"] = str(e)[:200]

    if long_memory is not None and snap.get("long_memory"):
        try:
            base = Path(getattr(long_memory, "base", data_dir / "long_memory"))
            base.mkdir(parents=True, exist_ok=True)
            lm = snap["long_memory"]
            for name, content in lm.items():
                if name == "data":
                    continue
                if isinstance(content, (dict, list)):
                    (base / name).write_text(json.dumps(content, ensure_ascii=False, indent=2), encoding="utf-8")
            if "data" in lm and hasattr(long_memory, "data"):
                long_memory.data = lm["data"]
                if hasattr(long_memory, "save"):
                    long_memory.save()
            stats["restored"].append("long_memory")
        except Exception as e:
            stats["long_memory_error"] = str(e)[:200]

    if user is not None and snap.get("user") and hasattr(user, "get"):
        try:
            u = snap["user"]
            if u.get("name") and hasattr(user, "set_name"):
                user.set_name(u["name"])
            stats["restored"].append("user")
        except Exception as e:
            stats["user_error"] = str(e)[:200]

    if snap.get("evolution_scale"):
        try:
            scale_file = data_dir / "evolve" / "scale_snapshots.json"
            scale_file.parent.mkdir(parents=True, exist_ok=True)
            scale_file.write_text(json.dumps(snap["evolution_scale"], ensure_ascii=False, indent=2), encoding="utf-8")
            stats["restored"].append("evolution_scale")
        except Exception as e:
            stats["evolution_scale_error"] = str(e)[:200]

    return stats
