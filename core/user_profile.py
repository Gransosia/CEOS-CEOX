"""
Perfil de usuario persistente — CEOS recuerda quién eres entre sesiones.

Guarda: nombre, preferencias, nivel, notas de voz (etiqueta), historial breve.
No es reconocimiento biométrico de voz avanzado; es identidad declarada +
etiqueta de voz opcional para personalizar el trato.
"""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


def _now():
    return datetime.now(timezone.utc).isoformat()


DEFAULT_PROFILE = {
    "name": None,
    "display_name": None,
    "nivel": "inicial",
    "preferencias": {
        "voz_femenina": True,
        "idioma": "es",
        "tratar_de": "tu",  # tu / usted
    },
    "voice_label": None,  # etiqueta declarada, no biometría
    "notas": "",
    "created_at": None,
    "last_seen": None,
    "session_count": 0,
}


class UserProfile:
    def __init__(self, base_path: str = "data/user"):
        self.base = Path(base_path)
        self.base.mkdir(parents=True, exist_ok=True)
        self.file = self.base / "profile.json"
        self.profile = self._load()

    def _load(self) -> dict:
        if self.file.exists():
            try:
                data = json.loads(self.file.read_text(encoding="utf-8"))
                # merge con defaults por si faltan claves nuevas
                out = dict(DEFAULT_PROFILE)
                out.update(data)
                if "preferencias" in data and isinstance(data["preferencias"], dict):
                    pref = dict(DEFAULT_PROFILE["preferencias"])
                    pref.update(data["preferencias"])
                    out["preferencias"] = pref
                return out
            except Exception:
                pass
        p = dict(DEFAULT_PROFILE)
        p["created_at"] = _now()
        return p

    def _save(self):
        self.file.write_text(
            json.dumps(self.profile, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def get(self) -> dict:
        return dict(self.profile)

    def touch_session(self):
        self.profile["last_seen"] = _now()
        self.profile["session_count"] = int(self.profile.get("session_count") or 0) + 1
        if not self.profile.get("created_at"):
            self.profile["created_at"] = _now()
        self._save()

    def set_name(self, name: str, display_name: Optional[str] = None) -> dict:
        name = (name or "").strip()
        if not name:
            raise ValueError("El nombre no puede estar vacío")
        self.profile["name"] = name
        self.profile["display_name"] = (display_name or name).strip()
        self.profile["last_seen"] = _now()
        if not self.profile.get("created_at"):
            self.profile["created_at"] = _now()
        self._save()
        return self.get()

    def set_nivel(self, nivel: str) -> dict:
        if nivel not in ("inicial", "intermedio", "avanzado"):
            raise ValueError("nivel debe ser inicial|intermedio|avanzado")
        self.profile["nivel"] = nivel
        self._save()
        return self.get()

    def set_voice_label(self, label: str) -> dict:
        """
        Etiqueta de voz declarada (ej. 'David — tono grave').
        No es reconocimiento biométrico; permite personalizar mensajes.
        """
        self.profile["voice_label"] = (label or "").strip() or None
        self._save()
        return self.get()

    def update(self, **kwargs) -> dict:
        for k in ("notas", "display_name"):
            if k in kwargs and kwargs[k] is not None:
                self.profile[k] = kwargs[k]
        if "preferencias" in kwargs and isinstance(kwargs["preferencias"], dict):
            self.profile["preferencias"].update(kwargs["preferencias"])
        if "nivel" in kwargs and kwargs["nivel"]:
            self.set_nivel(kwargs["nivel"])
        if "name" in kwargs and kwargs["name"]:
            self.set_name(kwargs["name"], kwargs.get("display_name"))
        self.profile["last_seen"] = _now()
        self._save()
        return self.get()

    def greeting(self) -> str:
        name = self.profile.get("display_name") or self.profile.get("name")
        n = int(self.profile.get("session_count") or 0)
        if not name:
            return "Hola. Aún no sé cómo te llamas. Puedes decirme tu nombre en la pestaña Maestro."
        if n <= 1:
            return f"Hola, {name}. Primera sesión registrada. Soy CEOS, maestro del protocolo CRONOS."
        return f"Hola de nuevo, {name}. Sesión #{n}. Continúamos donde lo dejamos."
