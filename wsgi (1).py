import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from core.server import app  # noqa: E402

# Asegura health aunque haya conflicto de registro
def _ensure_health():
    rules = {r.rule for r in app.url_map.iter_rules()}
    if "/health" not in rules:
        @app.route("/health")
        @app.route("/healthz")
        def health_fallback():
            return {"ok": True, "service": "ceos", "via": "wsgi-fallback"}

_ensure_health()
