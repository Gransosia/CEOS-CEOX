"""
Voz TTS para CEOS — prioridad Windows (pyttsx3 / SAPI5), Piper solo si está completo.

Orden:
  1. pyttsx3 (voces de Windows; busca voz femenina en español)
  2. Piper (solo si el binario existe Y hay modelo configurado)
  3. Mensaje claro si no hay motor
"""
from __future__ import annotations
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional


def _which(cmd: str) -> Optional[str]:
    return shutil.which(cmd)


class VoiceEngine:
    def __init__(self, preferred_gender: str = "female", lang: str = "es"):
        self.preferred_gender = preferred_gender
        self.lang = lang
        self.engine_name = None
        self._pyttsx3_engine = None
        self._piper_model = os.environ.get("PIPER_MODEL", "").strip()
        self._detect()

    def _detect(self):
        # 1) pyttsx3 primero (Windows real)
        try:
            import pyttsx3
            eng = pyttsx3.init()
            self._pyttsx3_engine = eng
            self.engine_name = "pyttsx3"
            self._configure_pyttsx3_female()
            return
        except Exception:
            self._pyttsx3_engine = None

        # 2) Piper solo si hay binario Y modelo
        if _which("piper") and self._piper_model and Path(self._piper_model).exists():
            self.engine_name = "piper"
            return

        self.engine_name = None

    def _configure_pyttsx3_female(self):
        if not self._pyttsx3_engine:
            return
        try:
            voices = self._pyttsx3_engine.getProperty("voices") or []
            scored = []
            for v in voices:
                name = (getattr(v, "name", "") or "").lower()
                vid = (getattr(v, "id", "") or "").lower()
                score = 0
                if any(k in name or k in vid for k in (
                    "spanish", "espa", "mexico", "spain", "helena", "sabina", "zira", "female", "mujer"
                )):
                    score += 2
                if any(k in name or k in vid for k in ("female", "zira", "helena", "sabina", "woman")):
                    score += 3
                if "es" in vid or "es_" in vid or "spanish" in name:
                    score += 2
                scored.append((score, v.id, name))
            scored.sort(key=lambda x: -x[0])
            if scored and scored[0][0] > 0:
                self._pyttsx3_engine.setProperty("voice", scored[0][1])
            elif voices:
                self._pyttsx3_engine.setProperty("voice", voices[0].id)
            self._pyttsx3_engine.setProperty("rate", 165)
            try:
                self._pyttsx3_engine.setProperty("volume", 1.0)
            except Exception:
                pass
        except Exception:
            pass

    def available(self) -> dict:
        voices_info = []
        if self._pyttsx3_engine:
            try:
                for v in self._pyttsx3_engine.getProperty("voices") or []:
                    voices_info.append({
                        "id": getattr(v, "id", ""),
                        "name": getattr(v, "name", ""),
                    })
            except Exception:
                pass
        return {
            "available": self.engine_name is not None,
            "engine": self.engine_name,
            "preferred_gender": self.preferred_gender,
            "lang": self.lang,
            "voices": voices_info[:12],
            "hint": self._install_hint(),
        }

    def _install_hint(self) -> str:
        if self.engine_name == "pyttsx3":
            return "Motor Windows (pyttsx3/SAPI) activo. Si no oyes nada, revisa volumen y voces de Windows."
        if self.engine_name == "piper":
            return f"Piper activo con modelo: {self._piper_model}"
        return (
            "Sin motor TTS. En Windows:\n"
            "  1) Cierra CEOS\n"
            "  2) En la carpeta ceos_v5: .venv\\Scripts\\pip install pyttsx3\n"
            "  3) Configuración Windows → Voz → añade voz en español si falta\n"
            "  4) Vuelve a ejecutar INICIAR_CEOS.bat"
        )

    def speak(self, text: str) -> dict:
        text = (text or "").strip()
        if not text:
            return {"ok": False, "error": "Texto vacío"}
        if len(text) > 2500:
            text = text[:2500] + "…"

        if self.engine_name == "pyttsx3":
            return self._speak_pyttsx3(text)
        if self.engine_name == "piper":
            return self._speak_piper(text)

        try:
            import pyttsx3
            self._pyttsx3_engine = pyttsx3.init()
            self.engine_name = "pyttsx3"
            self._configure_pyttsx3_female()
            return self._speak_pyttsx3(text)
        except Exception as e:
            return {
                "ok": False,
                "error": f"Sin motor TTS ({e})",
                "hint": self._install_hint(),
                "text": text[:200],
            }

    def _speak_pyttsx3(self, text: str) -> dict:
        try:
            eng = self._pyttsx3_engine
            if eng is None:
                import pyttsx3
                eng = pyttsx3.init()
                self._pyttsx3_engine = eng
                self._configure_pyttsx3_female()
            eng.say(text)
            eng.runAndWait()
            return {
                "ok": True,
                "engine": "pyttsx3",
                "message": "Reproducido con la voz del sistema (Windows SAPI).",
            }
        except Exception as e:
            return {"ok": False, "error": str(e), "hint": self._install_hint()}

    def _speak_piper(self, text: str) -> dict:
        out_path = Path(tempfile.gettempdir()) / "ceos_voice.wav"
        try:
            cmd = ["piper", "--model", self._piper_model, "--output_file", str(out_path)]
            proc = subprocess.run(cmd, input=text.encode("utf-8"), capture_output=True, timeout=60)
            if proc.returncode == 0 and out_path.exists() and out_path.stat().st_size > 0:
                try:
                    if os.name == "nt":
                        os.startfile(str(out_path))
                    return {"ok": True, "path": str(out_path), "engine": "piper"}
                except Exception:
                    return {"ok": True, "path": str(out_path), "engine": "piper",
                            "message": "Audio generado; ábrelo manualmente."}
            err = proc.stderr.decode("utf-8", errors="replace")[:300]
            return {"ok": False, "error": "Piper falló o no encontró modelo de voz", "stderr": err}
        except Exception as e:
            return {"ok": False, "error": str(e)}
