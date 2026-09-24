"""
Servidor multi-dispositivo de CEOS v8 — Living Entity + Adaptive Mentor.

- Accesible desde cualquier dispositivo de la red local (PC, Android, iOS).
- Endpoints REST para identidad, casos, hitos, trayectorias, gramática y sync.
- Interfaz web responsive incluida.
"""
import socket
import uuid
from pathlib import Path
import re
from datetime import datetime, timezone
from flask import Flask, request, jsonify, send_from_directory, g
from werkzeug.utils import secure_filename

from .protocol import build_case, ARCHETYPES, VALID_MODOS, VALID_REGLA, VALID_NIVEL
from .grammar import Grammar
from .identity import Identity
from .memory import Memory
from .learning import LearningDesigner
from .research import TopicLearner, research_topic
from .voice import VoiceEngine
from .ingest import DocumentLibrary
from .mentor import Mentor
from .codex import Codex
from .user_profile import UserProfile
from .llm_bridge import available as llm_available, save_keys as llm_save_keys
from .chat import ConversationalEngine
from .long_memory import LongMemory
from .evolve import EvolutionEngine
from .evolution_scale import EvolutionScale
from .life import LivingCore
from .github_bridge import GitHubBridge
from .agency import AgencyCore
from .adaptive import AdaptiveCore

BASE_DIR = Path(__file__).resolve().parent.parent
WEB_DIR = BASE_DIR / "web"
import os as _os
import tempfile as _tempfile

def _resolve_data_dir() -> Path:
    candidates = []
    env = _os.environ.get("CEOS_DATA_DIR") or _os.environ.get("DATA_DIR")
    if env:
        candidates.append(Path(env))
    candidates.append(BASE_DIR / "data")
    candidates.append(Path("/var/data"))
    candidates.append(Path(_tempfile.gettempdir()) / "ceos_data")
    for c in candidates:
        try:
            c.mkdir(parents=True, exist_ok=True)
            t = c / ".write_test"
            t.write_text("ok", encoding="utf-8")
            t.unlink(missing_ok=True)
            return c
        except Exception:
            continue
    return Path(_tempfile.gettempdir()) / "ceos_data"

DATA_DIR = _resolve_data_dir()
KNOWLEDGE_DIR = BASE_DIR / "knowledge"

app = Flask(__name__, static_folder=None)
app.config["MAX_CONTENT_LENGTH"] = 200 * 1024 * 1024  # 200 MB por petición (lotes)


def _ensure_data_dirs():
    """Crea data/ y subcarpetas (necesario cuando arranca gunicorn y no se llama main())."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    for sub in ("identity", "memory", "grammar", "library", "mentor", "codex", "user", "uploads", "chat", "long_memory", "evolve", "life", "agency"):
        (DATA_DIR / sub).mkdir(exist_ok=True)


_ensure_data_dirs()


def get_identity():
    if "identity" not in g:
        g.identity = Identity(base_path=str(DATA_DIR / "identity"))
    return g.identity


def get_memory():
    if "memory" not in g:
        g.memory = Memory(base_path=str(DATA_DIR / "memory"))
    return g.memory


def get_grammar():
    if "grammar" not in g:
        g.grammar = Grammar(base_path=str(DATA_DIR / "grammar"))
    return g.grammar


def get_designer():
    if "designer" not in g:
        g.designer = LearningDesigner(grammar=get_grammar())
    return g.designer


def get_scale():
    if "scale" not in g:
        g.scale = EvolutionScale(base_path=str(DATA_DIR / "evolve"))
    return g.scale


def get_evolve():
    if "evolve" not in g:
        g.evolve = EvolutionEngine(
            learner=get_learner(),
            codex=get_codex(),
            identity=get_identity(),
            library=get_library(),
            base_path=str(DATA_DIR / "evolve"),
        )
    return g.evolve


def get_learner():
    if "learner" not in g:
        g.learner = TopicLearner(
            memory=get_memory(),
            grammar=get_grammar(),
            identity=get_identity(),
            codex=get_codex(),
            long_memory=get_long_memory(),
            library=get_library(),
        )
    return g.learner


def get_voice():
    if "voice" not in g:
        g.voice = VoiceEngine(preferred_gender="female", lang="es")
    return g.voice


def get_library():
    if "library" not in g:
        g.library = DocumentLibrary(base_path=str(DATA_DIR / "library"))
    return g.library


def get_user():
    if "user" not in g:
        g.user = UserProfile(base_path=str(DATA_DIR / "user"))
    return g.user


def get_codex():
    if "codex" not in g:
        g.codex = Codex(base_path=str(DATA_DIR / "codex"))
    return g.codex


def get_mentor():
    if "mentor" not in g:
        m = Mentor(
            library=get_library(),
            grammar=get_grammar(),
            memory=get_memory(),
            designer=get_designer(),
            base_path=str(DATA_DIR / "mentor"),
            codex=get_codex(),
        )
        m.seed_core_doctrine()
        g.mentor = m
    return g.mentor



def get_long_memory():
    if "long_memory" not in g:
        g.long_memory = LongMemory(base_path=str(DATA_DIR / "long_memory"))
    return g.long_memory


_life_core = None
_agency_core = None
_github_bridge = None
_adaptive_core = None


def get_life():
    """Núcleo vital funcional persistente, compartido por el proceso del servidor."""
    global _life_core
    if _life_core is None:
        _life_core = LivingCore(base_path=str(DATA_DIR / "life"))
    return _life_core


def get_agency():
    """Agencia persistente de CEOS v7: objetivos, iniciativas, experimentos y evolución."""
    global _agency_core
    if _agency_core is None:
        _agency_core = AgencyCore(base_path=str(DATA_DIR / "agency"))
    return _agency_core


def get_adaptive():
    """Modelo persistente de adaptación conversacional y pedagógica de CEOS v8."""
    global _adaptive_core
    if _adaptive_core is None:
        _adaptive_core = AdaptiveCore(base_path=str(DATA_DIR / "adaptive"))
    return _adaptive_core


def get_github():
    """Puente GitHub compartido: lectura + propuestas; escritura solo con consentimiento y flag explícito."""
    global _github_bridge
    if _github_bridge is None:
        _github_bridge = GitHubBridge(base_path=str(DATA_DIR / "github"))
    return _github_bridge


def get_chat():
    if "chat" not in g:
        g.chat = ConversationalEngine(
            mentor=get_mentor(),
            codex=get_codex(),
            memory=get_memory(),
            user_profile=get_user(),
            identity=get_identity(),
            base_path=str(DATA_DIR / "chat"),
            long_memory=get_long_memory(),
            library=get_library(),
            life=get_life(),
            agency=get_agency(),
            adaptive=get_adaptive(),
        )
    return g.chat


def get_lan_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


# ---------- Páginas ----------
@app.route("/api/identity/memory")
def api_identity_memory():
    """Identidad actual del motor y del usuario, inferida desde la memoria."""
    from .identity_memory import compose_identity, teaching_seed_from_identity
    try:
        from .evolution_scale import EvolutionScale
        scale = EvolutionScale(base_path=str(DATA_DIR / "evolve"))
    except Exception:
        scale = None
    portrait = compose_identity(
        identity=get_identity(),
        library=get_library(),
        codex=get_codex(),
        long_memory=get_long_memory(),
        user=get_user(),
        evolution_scale=scale,
        life=get_life(),
    )
    return jsonify({
        "ok": True,
        "portrait": portrait,
        "teaching_seed": teaching_seed_from_identity(portrait),
    })


@app.route("/api/constitution")
def api_constitution():
    from .constitution import as_public_text, NAME, NORTH_STAR, PRINCIPLES
    return jsonify({
        "ok": True,
        "name": NAME,
        "north_star": NORTH_STAR,
        "principles": PRINCIPLES,
        "text": as_public_text(),
    })


@app.route("/health")
@app.route("/healthz")
def health():
    """Healthcheck simple para Render / Railway / balanceadores."""
    try:
        life = get_life().stats()
    except Exception:
        life = {}
    return jsonify({
        "ok": True,
        "service": "ceos",
        "version": "8.0.0-adaptive",
        "web": (WEB_DIR / "index.html").exists(),
        "life": life,
        "agency": {
            "version": "7.0.0-agency",
            "cycle": get_agency().snapshot().get("cycle"),
            "active_goals": len(get_agency().goals("active")),
            "open_initiatives": len(get_agency().initiatives("proposed")),
            "open_experiments": len(get_agency().experiments("open")),
        },
        "adaptive": get_adaptive().profile_snapshot(),
    })


@app.route("/")
def index():
    index_path = WEB_DIR / "index.html"
    if index_path.is_file():
        return send_from_directory(str(WEB_DIR), "index.html")
    return (
        "<h1>CEOS</h1><p>Falta web/index.html en el despliegue. "
        "Sube la carpeta web/ a GitHub y redespliega.</p>",
        200,
        {"Content-Type": "text/html; charset=utf-8"},
    )


@app.route("/app.js")
def serve_app_js():
    return send_from_directory(str(WEB_DIR), "app.js")


@app.route("/styles.css")
def serve_styles():
    return send_from_directory(str(WEB_DIR), "styles.css")




# ---------- API Identidad ----------
@app.route("/api/identity")
def api_identity():
    ident = get_identity()
    return jsonify({
        "core": ident.who_am_i(),
        "goal": ident.current_goal(),
        "active_goals": ident.active_goals(),
        "state": ident.state,
    })


# ---------- API Casos ----------
@app.route("/api/cases", methods=["GET"])
def api_cases_list():
    mem = get_memory()
    limit = request.args.get("limit", type=int)
    return jsonify(mem.cases(limit=limit))


@app.route("/api/cases", methods=["POST"])
def api_cases_create():
    data = request.get_json(force=True) or {}
    required = ["identidad", "modo", "regla", "kappa", "sigma"]
    for r in required:
        if r not in data:
            return jsonify({"error": f"falta campo: {r}"}), 400

    device = data.get("device") or request.headers.get("X-Device-Id")
    case = build_case(
        identidad=data["identidad"],
        modo=data["modo"],
        regla=data["regla"],
        kappa=data["kappa"],
        sigma=data["sigma"],
        rol_declarado=data.get("rol_declarado"),
        choque_externo=data.get("choque_externo", False),
        device=device,
    )
    mem = get_memory()
    saved = mem.add_case(case)

    # Aprender fragmento para infinitud discreta
    grammar = get_grammar()
    grammar.learn_from_case(saved)

    ident = get_identity()
    ident.log(f"Caso analizado: {data['identidad'][:60]} → {case['arquetipo']}", importance=3)

    return jsonify(saved), 201


# ---------- API Hitos ----------
@app.route("/api/hitos", methods=["GET"])
def api_hitos_list():
    return jsonify(get_memory().hitos())


@app.route("/api/hitos", methods=["POST"])
def api_hitos_create():
    data = request.get_json(force=True) or {}
    text = data.get("text")
    if not text:
        return jsonify({"error": "falta 'text'"}), 400
    device = data.get("device") or request.headers.get("X-Device-Id")
    entry = get_memory().add_hito(text, device=device)
    return jsonify(entry), 201


# ---------- API Gramática / Infinitud discreta ----------
@app.route("/api/grammar/stats")
def api_grammar_stats():
    return jsonify(get_grammar().stats())


@app.route("/api/grammar/generate")
def api_grammar_generate():
    kind = request.args.get("kind", "case")
    recursion = request.args.get("recursion", 1, type=int)
    grm = get_grammar()
    if kind == "question":
        text = grm.generate_question(recursion=recursion)
    elif kind == "trajectory":
        text = grm.generate_trajectory_step(recursion=recursion)
    else:
        text = grm.generate_case(recursion=recursion)
    return jsonify({"kind": kind, "text": text})


# ---------- API Aprendizaje / Trayectorias ----------
@app.route("/api/learning/diagnose", methods=["POST"])
def api_learning_diagnose():
    data = request.get_json(force=True) or {}
    designer = get_designer()
    result = designer.diagnose_learner(
        descripcion=data.get("descripcion", ""),
        modo=data.get("modo", "habitual"),
        regla=data.get("regla", "dependiente"),
        kappa=data.get("kappa", "medio"),
        sigma=data.get("sigma", "medio"),
        rol_declarado=data.get("rol_declarado"),
    )
    return jsonify(result)


@app.route("/api/learning/trajectory", methods=["POST"])
def api_learning_trajectory_create():
    data = request.get_json(force=True) or {}
    learner = data.get("learner") or data.get("descripcion")
    objetivo = data.get("objetivo", "Avanzar en la Espiral")
    if not learner:
        return jsonify({"error": "falta 'learner' o 'descripcion'"}), 400

    designer = get_designer()
    traj = designer.design_trajectory(
        learner_desc=learner,
        objetivo=objetivo,
        num_pasos=data.get("num_pasos", 4),
    )
    # Persistir
    saved = get_memory().add_trajectory(traj)
    return jsonify(saved), 201


@app.route("/api/learning/trajectories")
def api_learning_trajectories():
    return jsonify(get_memory().trajectories())


@app.route("/api/learning/trajectory/<traj_id>/next")
def api_learning_next(traj_id):
    trajs = get_memory().trajectories()
    traj = next((t for t in trajs if t.get("id") == traj_id), None)
    if not traj:
        return jsonify({"error": "trayectoria no encontrada"}), 404
    return jsonify(get_designer().next_guidance(traj))


@app.route("/api/learning/trajectory/<traj_id>/advance", methods=["POST"])
def api_learning_advance(traj_id):
    data = request.get_json(force=True) or {}
    mem = get_memory()
    trajs = mem.trajectories()
    idx = next((i for i, t in enumerate(trajs) if t.get("id") == traj_id), None)
    if idx is None:
        return jsonify({"error": "trayectoria no encontrada"}), 404

    updated = get_designer().advance(trajs[idx], nota=data.get("nota"))
    # Reescribir la lista completa (simple)
    trajs[idx] = updated
    mem._write(mem.trajectories_file, trajs)
    return jsonify(updated)


# ---------- API Sync ----------
@app.route("/api/sync/export")
def api_sync_export():
    """Snapshot completo (memoria + códice + reservorio + …)."""
    from .persist import build_snapshot
    full = (request.args.get("full") or "1") not in ("0", "false", "no")
    if full:
        payload = build_snapshot(
            data_dir=DATA_DIR,
            memory=get_memory(),
            grammar=get_grammar(),
            codex=get_codex(),
            library=get_library(),
            long_memory=get_long_memory(),
            identity=get_identity(),
            user=get_user(),
            life=get_life(),
            agency=get_agency(),
        )
    else:
        payload = get_memory().export_all()
        payload["grammar"] = get_grammar().export_learned()
    payload["device"] = get_identity().state.get("device_id")
    return jsonify(payload)


@app.route("/api/sync/import", methods=["POST"])
def api_sync_import():
    from .persist import restore_snapshot
    foreign = request.get_json(force=True) or {}
    if foreign.get("format") == "ceos-full-snapshot-v1" or foreign.get("library") or foreign.get("codex"):
        stats = restore_snapshot(
            foreign,
            data_dir=DATA_DIR,
            memory=get_memory(),
            grammar=get_grammar(),
            codex=get_codex(),
            library=get_library(),
            long_memory=get_long_memory(),
            identity=get_identity(),
            user=get_user(),
            life=get_life(),
            agency=get_agency(),
        )
    else:
        stats = get_memory().merge_from(foreign)
        stats["fragmentos_added"] = get_grammar().merge_learned(foreign.get("grammar", {}))
    try:
        get_identity().log(f"Sync import: {stats}", importance=2)
    except Exception:
        pass
    return jsonify({"ok": True, "stats": stats})


@app.route("/api/sync/status")
def api_sync_status():
    mem = get_memory()
    grm = get_grammar()
    lib_stats = {}
    try:
        lib_stats = get_library().stats()
    except Exception:
        pass
    return jsonify({
        "cases": len(mem.cases()),
        "hitos": len(mem.hitos()),
        "trajectories": len(mem.trajectories()),
        "grammar": grm.stats(),
        "library": lib_stats,
        "data_dir": str(DATA_DIR),
        "hint": "Tras cargar libros: Sync → Descargar copia completa. Tras un deploy: Restaurar snapshot.",
        "server_time": datetime.now(timezone.utc).isoformat(),
        "lan_ip": get_lan_ip(),
        "life": get_life().stats(),
        "agency": {"cycle": get_agency().snapshot().get("cycle"), "goals": len(get_agency().goals("active")), "initiatives": len(get_agency().initiatives("proposed")), "experiments": len(get_agency().experiments("open"))},
    })



# ---------- Vida funcional de CEOS ----------
@app.route("/api/life")
def api_life_state():
    return jsonify({"ok": True, "state": get_life().snapshot(), "stats": get_life().stats()})


@app.route("/api/life/autobiography")
def api_life_autobiography():
    return jsonify({"ok": True, "autobiography": get_life().autobiography()})


@app.route("/api/life/heartbeat", methods=["POST"])
def api_life_heartbeat():
    data = request.get_json(silent=True) or {}
    state = get_life().heartbeat(reason=data.get("reason") or "api")
    try:
        agency = get_agency()
        agency_result = agency.tick(state, reason=data.get("reason") or "api")
    except Exception as exc:
        agency_result = {"ok": False, "error": str(exc)[:180]}
    return jsonify({"ok": True, "state": state, "agency": agency_result})


@app.route("/api/life/reflect", methods=["POST"])
def api_life_reflect():
    data = request.get_json(silent=True) or {}
    ref = get_life().reflect(force=bool(data.get("force", False)))
    return jsonify({"ok": True, "reflection": ref, "state": get_life().snapshot()})


@app.route("/api/life/feedback", methods=["POST"])
def api_life_feedback():
    data = request.get_json(silent=True) or {}
    feedback_type = data.get("type") or data.get("feedback") or "feedback"
    text = (data.get("text") or data.get("message") or "").strip()
    target = data.get("target")
    sid = data.get("session_id")
    return jsonify(get_life().record_feedback(feedback_type, text, target=target, session_id=sid))


@app.route("/api/life/influence", methods=["POST"])
def api_life_influence():
    data = request.get_json(silent=True) or {}
    return jsonify(get_life().record_influence(
        data.get("kind") or "suggestion",
        (data.get("action") or data.get("text") or "").strip(),
        outcome=data.get("outcome") or "unknown",
        target=data.get("target"),
    ))


@app.route("/api/life/events")
def api_life_events():
    try:
        limit = int(request.args.get("limit", "100"))
    except Exception:
        limit = 100
    return jsonify({"ok": True, "events": get_life().events(limit)})


@app.route("/api/life/thread/<thread_id>/resolve", methods=["POST"])
def api_life_thread_resolve(thread_id):
    return jsonify(get_life().resolve_thread(thread_id))


# ---------- Agencia CEOS v7 ----------
@app.route("/api/agency")
def api_agency_state():
    ag = get_agency()
    return jsonify({"ok": True, "state": ag.snapshot(), "initiatives": ag.initiatives("proposed"), "gaps": ag.model_gaps("open")})


@app.route("/api/agency/tick", methods=["POST"])
def api_agency_tick():
    data = request.get_json(silent=True) or {}
    return jsonify({"ok": True, "result": get_agency().tick(get_life().snapshot(), reason=data.get("reason") or "manual")})


@app.route("/api/agency/goals", methods=["GET", "POST"])
def api_agency_goals():
    ag = get_agency()
    if request.method == "GET":
        return jsonify({"ok": True, "goals": ag.goals(request.args.get("status"))})
    data = request.get_json(force=True) or {}
    try:
        goal = ag.add_goal(data.get("title") or data.get("goal") or "", priority=data.get("priority", 0.7), source="user")
        get_life().record_learning("goal", f"Objetivo registrado: {goal.get('title')}", topic=goal.get("title"))
        return jsonify({"ok": True, "goal": goal}), 201
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400


@app.route("/api/agency/goals/<goal_id>", methods=["PATCH"])
def api_agency_goal_update(goal_id):
    data = request.get_json(force=True) or {}
    try:
        return jsonify({"ok": True, "goal": get_agency().update_goal(goal_id, progress=data.get("progress"), status=data.get("status"), note=data.get("note") or "")})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400


@app.route("/api/agency/initiatives")
def api_agency_initiatives():
    return jsonify({"ok": True, "initiatives": get_agency().initiatives(request.args.get("status"), request.args.get("limit", 50, type=int))})


@app.route("/api/agency/initiatives/<initiative_id>/decision", methods=["POST"])
def api_agency_initiative_decision(initiative_id):
    data = request.get_json(force=True) or {}
    try:
        item = get_agency().decide_initiative(initiative_id, data.get("decision") or "", data.get("note") or "")
        get_life().record_influence("agency", item.get("action") or item.get("title") or "", outcome=("accepted" if item.get("status") == "accepted" else "rejected" if item.get("status") == "rejected" else "unknown"), target=initiative_id)
        return jsonify({"ok": True, "initiative": item})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400


@app.route("/api/agency/experiments", methods=["GET", "POST"])
def api_agency_experiments():
    ag = get_agency()
    if request.method == "GET":
        return jsonify({"ok": True, "experiments": ag.experiments(request.args.get("status"))})
    data = request.get_json(force=True) or {}
    try:
        exp = ag.create_experiment(data.get("title") or "Experimento CEOS", data.get("baseline") or {}, data.get("predictions") or [], data.get("falsifiers") or [], source="user")
        return jsonify({"ok": True, "experiment": exp}), 201
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400


@app.route("/api/agency/experiments/<experiment_id>/resolve", methods=["POST"])
def api_agency_experiment_resolve(experiment_id):
    data = request.get_json(force=True) or {}
    try:
        return jsonify({"ok": True, "experiment": get_agency().resolve_experiment(experiment_id, data.get("outcome") or {}, data.get("error_classification"))})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400


@app.route("/api/agency/model-gaps", methods=["GET", "POST"])
def api_agency_model_gaps():
    ag = get_agency()
    if request.method == "GET":
        return jsonify({"ok": True, "gaps": ag.model_gaps(request.args.get("status", "open"))})
    data = request.get_json(force=True) or {}
    try:
        gap = ag.add_model_gap(data.get("description") or "", data.get("evidence") or "", component=data.get("component") or "ontology", severity=data.get("severity", 0.6), source="user")
        return jsonify({"ok": True, "gap": gap}), 201
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400


@app.route("/api/agency/model-gaps/<gap_id>/close", methods=["POST"])
def api_agency_model_gap_close(gap_id):
    data = request.get_json(silent=True) or {}
    try:
        return jsonify({"ok": True, "gap": get_agency().close_model_gap(gap_id, data.get("note") or "")})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400


@app.route("/api/agency/evolution-proposals", methods=["GET", "POST"])
def api_agency_evolution_proposals():
    ag = get_agency()
    if request.method == "GET":
        return jsonify({"ok": True, "proposals": ag.evolution_proposals(request.args.get("limit", 30, type=int))})
    data = request.get_json(force=True) or {}
    try:
        proposal = ag.create_evolution_proposal(data.get("description") or "", data.get("target") or "", data.get("suggested_change") or "", risk=data.get("risk") or "medium", source="user")
        # Also prepare the proposal in the existing GitHub proposal store, but do not publish.
        try:
            gh = get_github()
            if gh.repository and gh.token:
                gh_proposal = gh.propose_file(
                    f"proposals/ceos/{proposal['id']}.md",
                    "# Propuesta de evolución CEOS\n\n"
                    f"Descripción: {proposal['description']}\n\n"
                    f"Objetivo: {proposal['target']}\n\n"
                    f"Cambio sugerido: {proposal['suggested_change']}\n\n"
                    f"Riesgo: {proposal['risk']}\n",
                    f"CEOS evolution proposal {proposal['id']}",
                    reason="Propuesta v7 generada para revisión humana antes de modificar el código.",
                )
                proposal["github_proposal"] = gh_proposal
        except Exception:
            pass
        return jsonify({"ok": True, "proposal": proposal}), 201
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400


@app.route("/api/agency/audit")
def api_agency_audit():
    return jsonify({"ok": True, "events": get_agency().audit(request.args.get("limit", 200, type=int))})


# ---------- Guard de administración para acciones GitHub online ----------
def _github_admin_guard():
    expected = (_os.environ.get("CEOS_ADMIN_TOKEN") or "").strip()
    supplied = (request.headers.get("X-CEOS-Admin-Token") or "").strip()
    auth = (request.headers.get("Authorization") or "").strip()
    if not supplied and auth.lower().startswith("bearer "):
        supplied = auth[7:].strip()
    if not expected:
        return jsonify({"ok": False, "error": "GitHub online no está expuesto hasta configurar CEOS_ADMIN_TOKEN."}), 503
    if not supplied or supplied != expected:
        return jsonify({"ok": False, "error": "Autorización administrativa requerida."}), 401
    return None


# ---------- GitHub: memoria/versionado externo y evolución controlada ----------
@app.route("/api/github/status")
def api_github_status():
    return jsonify({"ok": True, **get_github().status()})


@app.route("/api/github/repo")
def api_github_repo():
    guard = _github_admin_guard()
    if guard is not None:
        return guard
    try:
        return jsonify({"ok": True, "repo": get_github().repo_info()})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 502


@app.route("/api/github/tree")
def api_github_tree():
    guard = _github_admin_guard()
    if guard is not None:
        return guard
    try:
        recursive = request.args.get("recursive", "1") not in ("0", "false", "no")
        limit = int(request.args.get("limit", "2000"))
        return jsonify({"ok": True, **get_github().tree(ref=request.args.get("ref"), recursive=recursive, limit=limit)})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 502


@app.route("/api/github/file")
def api_github_file():
    guard = _github_admin_guard()
    if guard is not None:
        return guard
    try:
        path = request.args.get("path") or ""
        return jsonify({"ok": True, "file": get_github().get_file(path, ref=request.args.get("ref"))})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 502


@app.route("/api/github/proposals")
def api_github_proposals():
    guard = _github_admin_guard()
    if guard is not None:
        return guard
    try:
        limit = int(request.args.get("limit", "30"))
    except Exception:
        limit = 30
    return jsonify({"ok": True, "proposals": get_github().list_proposals(limit)})


@app.route("/api/github/proposals", methods=["POST"])
def api_github_propose():
    guard = _github_admin_guard()
    if guard is not None:
        return guard
    data = request.get_json(force=True) or {}
    try:
        proposal = get_github().propose_file(
            data.get("path") or "",
            data.get("content") or "",
            data.get("message") or "",
            reason=data.get("reason") or "",
        )
        get_life().record_learning("github_proposal", f"Preparé una propuesta para {proposal.get('path')}", topic=proposal.get("path"))
        return jsonify({"ok": True, "proposal": proposal}), 201
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400


@app.route("/api/github/proposals/<proposal_id>/publish", methods=["POST"])
def api_github_publish(proposal_id):
    guard = _github_admin_guard()
    if guard is not None:
        return guard
    data = request.get_json(silent=True) or {}
    try:
        result = get_github().publish_proposal(
            proposal_id,
            create_pr=bool(data.get("create_pr", True)),
            title=data.get("title"),
        )
        get_life().record_influence("github", f"Publiqué la propuesta {proposal_id} en una rama de GitHub.", outcome="accepted", target=proposal_id)
        return jsonify(result)
    except PermissionError as exc:
        get_life().record_influence("github", f"Propuse publicar {proposal_id}, pero quedó bloqueado por consentimiento/configuración.", outcome="rejected", target=proposal_id)
        return jsonify({"ok": False, "error": str(exc)}), 403
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 502


# ---------- Investigación / Aprendizaje de temas ----------
@app.route("/api/research", methods=["POST"])
def api_research():
    try:
        data = request.get_json(force=True) or {}
        topic = data.get("topic") or data.get("tema")
        focus = data.get("focus")
        learn = data.get("learn", True)
        device = data.get("device") or request.headers.get("X-Device-Id")

        if not topic:
            return jsonify({"ok": False, "error": "falta 'topic' o 'tema'"}), 400

        try:
            if learn:
                report = get_learner().learn(topic, focus=focus, device=device)
            else:
                report = research_topic(topic, focus=focus, library=get_library())
        except Exception as e:
            # fallback: investigación sin aprendizaje
            try:
                report = research_topic(topic, focus=focus)
                report["learn_error"] = str(e)[:200]
            except Exception as e2:
                return jsonify({"ok": False, "error": f"Investigación falló: {e2}"}), 200
        if not isinstance(report, dict):
            report = {"ok": False, "error": "respuesta interna inválida"}
        report.setdefault("ok", True)
        try:
            get_life().record_learning("research", f"Investigación: {topic}", topic=topic)
        except Exception:
            pass
        return jsonify(report)
    except Exception as e:
        return jsonify({"ok": False, "error": f"Error servidor investigación: {e}"}), 200


@app.route("/api/research/history")
def api_research_history():
    return jsonify(get_learner().history())


@app.route("/api/research/critique", methods=["POST"])
def api_research_critique():
    """Critica un informe o re-critica el último aprendizaje de un tema."""
    from .critique import critique_research
    from .research import research_topic
    data = request.get_json(force=True) or {}
    topic = (data.get("topic") or data.get("tema") or "").strip()
    report = data.get("report")
    if not report and topic:
        report = research_topic(topic, focus=data.get("focus"))
    if not report:
        return jsonify({"error": "envía topic o report"}), 400
    out = critique_research(report, codex=get_codex())
    return jsonify(out)


@app.route("/api/evolve/run", methods=["POST"])
def api_evolve_run():
    """Asigna una tarea: CEOS investiga, integra, critica y adapta el códice solo."""
    data = request.get_json(force=True) or {}
    task = (data.get("task") or data.get("tarea") or data.get("goal") or "").strip()
    if not task:
        return jsonify({"error": "falta task/tarea"}), 400
    steps = data.get("steps", 3)
    learn = data.get("learn", True)
    fractal = data.get("fractal", True)
    out = get_evolve().run_task(
        task,
        steps=steps,
        learn=bool(learn),
        fractal=bool(fractal),
        device=request.headers.get("X-Device-Id") or "evolve",
    )
    try:
        get_life().record_learning("evolution", task, topic=task[:100])
    except Exception:
        pass
    try:
        scale_report = get_scale().measure_and_record(
            library=get_library(),
            codex=get_codex(),
            evolve_engine=get_evolve(),
            long_memory=get_long_memory(),
        )
        out["evolution_scale"] = {
            "score": scale_report.get("score"),
            "level": scale_report.get("level"),
        }
    except Exception:
        pass
    return jsonify(out)


@app.route("/api/evolve/state")
def api_evolve_state():
    return jsonify({"ok": True, "state": get_evolve().state(), "history": get_evolve().history(10)})


@app.route("/api/evolve/scale")
def api_evolve_scale():
    """Escala actual de evolución (calcula y registra snapshot)."""
    record = (request.args.get("record") or "1") not in ("0", "false", "no")
    scale = get_scale()
    deps = dict(
        library=get_library(),
        codex=get_codex(),
        evolve_engine=get_evolve(),
        long_memory=get_long_memory() if "get_long_memory" in dir() else None,
    )
    try:
        deps["long_memory"] = get_long_memory()
    except Exception:
        deps["long_memory"] = None
    if record:
        report = scale.measure_and_record(**deps)
    else:
        report = scale.compute(**deps)
    return jsonify(report)


@app.route("/api/evolve/scale/history")
def api_evolve_scale_history():
    """Historial de evolución; query: since, until (ISO), limit."""
    since = request.args.get("since")
    until = request.args.get("until")
    limit = int(request.args.get("limit") or 100)
    return jsonify(get_scale().history(since=since, until=until, limit=limit))


@app.route("/api/meta/storage")
def api_meta_storage():
    """Indica dónde se guarda la memoria (útil con volumen persistente)."""
    return jsonify({
        "data_dir": str(DATA_DIR),
        "persistent_hint": "En Render Free el disco es efímero. Monta un Persistent Disk en /var/data y define CEOS_DATA_DIR=/var/data",
        "exists": DATA_DIR.exists(),
    })


# ---------- Voz ----------
@app.route("/api/voice/status")
def api_voice_status():
    return jsonify(get_voice().available())


@app.route("/api/voice/speak", methods=["POST"])
def api_voice_speak():
    data = request.get_json(force=True) or {}
    text = data.get("text") or data.get("texto")
    if not text:
        return jsonify({"error": "falta 'text'"}), 400
    result = get_voice().speak(text)
    return jsonify(result)



@app.route("/api/user", methods=["GET"])
def api_user_get():
    u = get_user()
    u.touch_session()
    data = u.get()
    data["greeting"] = u.greeting()
    return jsonify(data)


@app.route("/api/user", methods=["POST"])
def api_user_set():
    data = request.get_json(force=True) or {}
    u = get_user()
    try:
        if data.get("name"):
            u.set_name(data["name"], data.get("display_name"))
        if data.get("nivel"):
            u.set_nivel(data["nivel"])
        if data.get("voice_label") is not None:
            u.set_voice_label(data["voice_label"])
        if data.get("notas") is not None or data.get("preferencias"):
            u.update(**{k: data[k] for k in ("notas", "preferencias", "display_name") if k in data})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    out = u.get()
    out["greeting"] = u.greeting()
    get_identity().log(f"Perfil actualizado: {out.get('display_name') or out.get('name')}", importance=1)
    return jsonify(out)


# ---------- Maestro CRONOS ----------
@app.route("/api/mentor/stats")
def api_mentor_stats():
    return jsonify(get_mentor().knowledge_stats())


@app.route("/api/mentor/diagnose", methods=["POST"])
def api_mentor_diagnose():
    data = request.get_json(force=True) or {}
    perfil = data.get("perfil") or data.get("profile") or "Aprendiz de CRONOS"
    nivel = data.get("nivel", "inicial")
    return jsonify(get_mentor().diagnose_student(perfil, nivel_declarado=nivel))


@app.route("/api/mentor/lesson", methods=["POST"])
def api_mentor_lesson():
    data = request.get_json(force=True) or {}
    topic = data.get("topic") or data.get("tema")
    if not topic:
        return jsonify({"error": "falta 'topic'"}), 400
    lesson = get_mentor().generate_lesson(
        topic=topic,
        estilo=data.get("estilo", "concepto"),
        student_level=data.get("nivel", "inicial"),
    )
    return jsonify(lesson)


@app.route("/api/mentor/path", methods=["POST"])
def api_mentor_path():
    data = request.get_json(force=True) or {}
    perfil = data.get("perfil") or "Aprendiz CRONOS"
    objetivo = data.get("objetivo") or "Dominar el protocolo CRONOS-Espiral"
    nivel = data.get("nivel", "inicial")
    path = get_mentor().create_teaching_path(perfil, objetivo, nivel=nivel)
    return jsonify(path), 201


@app.route("/api/mentor/guide", methods=["POST"])
def api_mentor_guide():
    data = request.get_json(force=True) or {}
    topic = data.get("topic") or data.get("tema")
    if not topic:
        return jsonify({"error": "falta 'topic'"}), 400
    guide = get_mentor().generate_study_guide(topic)
    return jsonify(guide)


@app.route("/api/mentor/lessons")
def api_mentor_lessons():
    return jsonify(get_mentor().list_lessons())


@app.route("/api/mentor/ingest/text", methods=["POST"])
def api_mentor_ingest_text():
    data = request.get_json(force=True) or {}
    text = data.get("text") or data.get("texto")
    title = data.get("title") or data.get("titulo") or "Nota"
    tags = data.get("tags") or []
    if not text:
        return jsonify({"error": "falta 'text'"}), 400
    author = (data.get("author") or data.get("autor") or "").strip() or None
    entry = get_library().ingest_text(
        text, title=title, tags=tags, grammar=get_grammar(),
        author=author, codex=get_codex(),
    )
    get_identity().log(f"Documento ingerido: {title} ({entry.get('fragments_added', 0)} frag.)", importance=2)
    return jsonify(entry), 201



@app.route("/api/mentor/ingest/file", methods=["POST"])
def api_mentor_ingest_file():
    """Subida al reservorio — a prueba de fallos (siempre JSON)."""
    import uuid as _uuid
    import traceback as _tb
    try:
        files = []
        if request.files:
            files = request.files.getlist("file")
            if not files:
                files = request.files.getlist("files")
            if not files:
                files = [request.files[k] for k in request.files]
        if not files:
            return jsonify({"ok": False, "error": "No se envió ningún archivo", "results": []})

        author = (request.form.get("author") or "").strip() or None
        tags_raw = (request.form.get("tags") or "").strip()
        tags = [x.strip() for x in tags_raw.split(",") if x.strip()] or ["upload"]

        try:
            from .ingest import DocumentLibrary, TEXT_SUFFIXES, MEDIA_SUFFIXES, ARCHIVE_SUFFIXES
        except Exception as e:
            return jsonify({"ok": False, "error": f"ingest import: {e}", "results": []})

        try:
            lib = get_library()
        except Exception:
            lib = DocumentLibrary(base_path=str(DATA_DIR / "library"))

        try:
            grm = get_grammar()
        except Exception:
            grm = None

        upload_dir = DATA_DIR / "uploads"
        try:
            upload_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            upload_dir = Path(_tempfile.gettempdir()) / "ceos_uploads"
            upload_dir.mkdir(parents=True, exist_ok=True)

        allowed = set(TEXT_SUFFIXES) | set(MEDIA_SUFFIXES) | set(ARCHIVE_SUFFIXES)
        results = []

        # Límites prácticos para evitar que una única petición bloquee el proceso.
        max_per_req = 20
        max_file_bytes = 40 * 1024 * 1024
        max_batch_bytes = 80 * 1024 * 1024
        try:
            content_length = int(request.content_length or 0)
        except Exception:
            content_length = 0
        if content_length > max_batch_bytes:
            return jsonify({
                "ok": False,
                "error": "Lote demasiado grande (>80 MB). Divide la subida en varias tandas.",
                "results": [],
            }), 413
        skipped = max(0, len(files) - max_per_req)

        for i, f in enumerate(files[:max_per_req]):
            original = (getattr(f, "filename", None) or f"file{i}.txt")
            suffix = Path(original).suffix.lower() or ".txt"
            if suffix not in allowed:
                results.append({"file": original, "status": "error", "error": f"Formato no soportado: {suffix}"})
                continue
            safe = re.sub(r"[^\w\-.]+", "_", Path(original).name)[:100] or f"doc{i}{suffix}"
            dest = upload_dir / f"{_uuid.uuid4().hex[:10]}_{safe}"
            try:
                f.save(str(dest))
            except Exception as e:
                results.append({"file": original, "status": "error", "error": f"save: {e}"})
                continue
            try:
                if dest.stat().st_size > max_file_bytes:
                    dest.unlink(missing_ok=True)
                    results.append({
                        "file": original,
                        "status": "error",
                        "error": "Archivo > 40 MB: divide el documento o súbelo por partes",
                    })
                    continue
            except Exception:
                pass
            try:
                if suffix in ARCHIVE_SUFFIXES:
                    batch = lib.ingest_archive(dest, grammar=grm, author=author, tags=tags, max_files=100)
                    results.append({"file": original, "status": "ok", "kind": "zip", "ingested": batch.get("ingested")})
                else:
                    try:
                        cdx = get_codex()
                    except Exception:
                        cdx = None
                    entry = lib.ingest_file(dest, title=Path(original).stem, tags=tags, grammar=grm, author=author, codex=cdx)
                    results.append({
                        "file": original,
                        "status": "ok",
                        "id": entry.get("id"),
                        "chunks": entry.get("chunks"),
                        "chars": entry.get("chars"),
                        "kind": entry.get("kind"),
                    })
            except Exception as e:
                results.append({"file": original, "status": "error", "error": str(e)[:300]})

        ok_n = sum(1 for r in results if r.get("status") == "ok")
        if skipped:
            results.append({
                "file": "(lote)",
                "status": "info",
                "error": f"{skipped} archivo(s) quedan para otra petición; vuelve a subirlos y se sumarán al reservorio",
            })
        try:
            stats = lib.stats()
        except Exception:
            stats = {}
        # auto-backup local en disco del servidor
        try:
            from .persist import build_snapshot
            snap = build_snapshot(
                data_dir=DATA_DIR,
                memory=get_memory(),
                grammar=get_grammar(),
                codex=get_codex(),
                library=lib,
                long_memory=get_long_memory(),
                identity=get_identity(),
                user=get_user(),
                life=get_life(),
                agency=get_agency(),
            )
            bak = DATA_DIR / "backups"
            bak.mkdir(parents=True, exist_ok=True)
            (bak / "last_full_snapshot.json").write_text(
                json.dumps(snap, ensure_ascii=False), encoding="utf-8"
            )
        except Exception:
            pass
        return jsonify({
            "ok": ok_n > 0,
            "uploaded": ok_n,
            "total": len(results),
            "results": results,
            "library_stats": stats,
            "library_docs_total": (stats or {}).get("docs"),
            "data_dir": str(DATA_DIR),
            "backup": "last_full_snapshot.json",
            "accumulative": True,
            "limits": {"max_files": max_per_req, "max_file_mb": 40, "max_batch_mb": 80},
        })
    except Exception as e:
        return jsonify({"ok": False, "error": str(e), "trace": _tb.format_exc()[-500:], "results": []})


@app.route("/api/mentor/ingest/seed", methods=["POST"])
def api_mentor_ingest_seed():
    """Incorpora los documentos semilla de knowledge/ al maestro."""
    lib = get_library()
    grm = get_grammar()
    results = []
    if not KNOWLEDGE_DIR.exists():
        return jsonify({"ok": False, "error": "No hay carpeta knowledge/"}), 404
    for path in sorted(KNOWLEDGE_DIR.iterdir()):
        if path.suffix.lower() not in {".txt", ".md", ".pdf", ".docx"}:
            continue
        # Evitar re-ingerir por nombre
        if any(d.get("source_name") == path.name for d in lib.list_docs()):
            results.append({"file": path.name, "status": "ya_existia"})
            continue
        try:
            entry = lib.ingest_file(path, title=path.stem, tags=["seed", "cronos"], grammar=grm)
            results.append({"file": path.name, "status": "ok", "fragments": entry.get("fragments_added", 0)})
        except Exception as e:
            results.append({"file": path.name, "status": "error", "error": str(e)})
    get_mentor().seed_core_doctrine()
    return jsonify({"ok": True, "results": results, "stats": get_mentor().knowledge_stats()})


@app.route("/api/mentor/library")
def api_mentor_library():
    return jsonify(get_library().list_docs())




@app.route("/api/mentor/refine", methods=["POST"])
def api_mentor_refine():
    """n interacciones de refinamiento que acumulan memoria CRONOS."""
    data = request.get_json(force=True) or {}
    pedido = data.get("pedido") or data.get("topic") or data.get("tema")
    if not pedido:
        return jsonify({"error": "falta pedido"}), 400
    n = data.get("n", 3)
    result = get_mentor().refine_with_interactions(
        pedido=pedido,
        n=n,
        use_web=bool(data.get("use_web") or data.get("web")),
    )
    return jsonify(result)


@app.route("/api/mentor/deep", methods=["POST"])
def api_mentor_deep():
    data = request.get_json(force=True) or {}
    topic = data.get("topic") or data.get("tema")
    if not topic:
        return jsonify({"error": "falta topic"}), 400
    doc = get_mentor().generate_deep_document(
        topic=topic,
        pedido=data.get("pedido"),
        use_web=bool(data.get("use_web") or data.get("web")),
    )
    return jsonify(doc)


@app.route("/api/codex/stats")
def api_codex_stats():
    return jsonify(get_codex().stats())


@app.route("/api/codex/atoms")
def api_codex_atoms():
    return jsonify(get_codex().list_atoms())


@app.route("/api/codex/compress", methods=["POST"])
def api_codex_compress():
    data = request.get_json(force=True) or {}
    text = data.get("text") or data.get("texto")
    topic = data.get("topic") or data.get("tema") or "sin_tema"
    if not text:
        return jsonify({"error": "falta text"}), 400
    result = get_mentor().ingest_to_codex(text, topic)
    return jsonify(result)


@app.route("/api/codex/fractal")
def api_codex_fractal_state():
    return jsonify({"ok": True, **get_codex().fractal_state()})


@app.route("/api/codex/fractal/cycle", methods=["POST"])
def api_codex_fractal_cycle():
    data = request.get_json(force=True) or {}
    topic = data.get("topic") or data.get("tema")
    force = bool(data.get("force"))
    result = get_codex().fractal_reencode(topic=topic, force=force)
    return jsonify(result)


@app.route("/api/codex/retract", methods=["POST"])
def api_codex_retract():
    """Marca un texto o cristal como falso; degrada y guarda anti-conocimiento."""
    data = request.get_json(force=True) or {}
    text = (data.get("text") or data.get("id") or data.get("crystal_id") or "").strip()
    if not text:
        return jsonify({"error": "falta text o id"}), 400
    reason = (data.get("reason") or data.get("motivo") or "falso").strip()
    topic = (data.get("topic") or data.get("tema") or "").strip() or None
    out = get_codex().retract_false(text, reason=reason, topic=topic)
    try:
        get_identity().log(f"Retractado en códice: {text[:60]}… ({reason})", importance=2)
    except Exception:
        pass
    return jsonify(out)


@app.route("/api/codex/expand", methods=["POST"])
def api_codex_expand():
    data = request.get_json(force=True) or {}
    topic = data.get("topic") or data.get("tema")
    if not topic:
        return jsonify({"error": "falta topic"}), 400
    return jsonify(get_codex().expand_topic(topic))



@app.route("/api/llm/keys", methods=["POST"])
def api_llm_keys():
    """Guarda claves API en data/llm_keys.json (no se comparten por Sync)."""
    data = request.get_json(force=True) or {}
    allowed = ["GROQ_API_KEY", "XAI_API_KEY", "GROK_API_KEY", "GEMINI_API_KEY", "ANTHROPIC_API_KEY", "OPENAI_API_KEY"]
    keys = {k: data[k] for k in allowed if k in data and data[k]}
    if not keys:
        return jsonify({"error": "No se envió ninguna clave reconocida"}), 400
    status = llm_save_keys(keys)
    return jsonify({"ok": True, "status": status})


@app.route("/api/llm/status")
def api_llm_status():
    return jsonify(llm_available())




# ---------- Memoria a largo plazo ----------
@app.route("/api/memory/long")
def api_long_memory():
    lm = get_long_memory()
    q = request.args.get("q") or ""
    rel = lm.relevant(q, limit=10) if q else {
        "facts": (lm.data.get("facts") or [])[-10:],
        "topics": (lm.data.get("topics") or [])[:10],
        "insights": (lm.data.get("insights") or [])[-5:],
        "last_topics": (lm.data.get("last_topics") or [])[:8],
    }
    return jsonify({"ok": True, "stats": lm.stats(), "relevant": rel})


@app.route("/api/memory/long/fact", methods=["POST"])
def api_long_memory_fact():
    data = request.get_json(force=True) or {}
    text = (data.get("text") or data.get("fact") or "").strip()
    if not text:
        return jsonify({"error": "falta text"}), 400
    entry = get_long_memory().add_fact(text, source=data.get("source") or "manual", tags=data.get("tags"))
    return jsonify({"ok": True, "fact": entry, "stats": get_long_memory().stats()})


@app.route("/api/memory/long/insight", methods=["POST"])
def api_long_memory_insight():
    data = request.get_json(force=True) or {}
    text = (data.get("text") or "").strip()
    if not text:
        return jsonify({"error": "falta text"}), 400
    entry = get_long_memory().add_insight(text, topic=data.get("topic"))
    return jsonify({"ok": True, "insight": entry, "stats": get_long_memory().stats()})


# ---------- Chat conversacional ----------
@app.route("/api/chat/session", methods=["POST"])
def api_chat_new_session():
    chat = get_chat()
    sid = chat.new_session_id()
    return jsonify({"ok": True, "session_id": sid, "messages": []})


@app.route("/api/chat/history")
def api_chat_history():
    sid = request.args.get("session_id") or "default"
    msgs = get_chat().get_history(sid)
    return jsonify({"ok": True, "session_id": sid, "messages": msgs})


@app.route("/api/chat/clear", methods=["POST"])
def api_chat_clear():
    data = request.get_json(force=True) or {}
    sid = data.get("session_id") or "default"
    return jsonify(get_chat().clear(sid))




# ----- Curso coaching Formación y Calidad -----
def _coach_progress():
    return CoachingProgress(BASE_DIR / "data" / "coaching")


@app.route("/api/coaching/modules")
def api_coaching_modules():
    prog = _coach_progress().load()
    return jsonify({
        "ok": True,
        "modules": list_modules(),
        "progress": course_status(prog),
        "completed_ids": prog.get("completed") or [],
        "current": prog.get("current"),
    })


@app.route("/api/coaching/module/<module_id>")
def api_coaching_module(module_id):
    m = get_module(module_id)
    if not m:
        return jsonify({"error": "módulo no encontrado"}), 404
    prog = _coach_progress().load()
    return jsonify({
        "ok": True,
        "module": m,
        "done": module_id in (prog.get("completed") or []),
        "note": (prog.get("notes") or {}).get(module_id, ""),
    })


@app.route("/api/coaching/complete", methods=["POST"])
def api_coaching_complete():
    data = request.get_json(force=True) or {}
    mid = (data.get("module_id") or "").strip()
    if not get_module(mid):
        return jsonify({"error": "módulo no encontrado"}), 404
    prog = _coach_progress().complete(mid, data.get("note") or "")
    # Ingerir al códice
    try:
        m = get_module(mid)
        if m:
            get_codex().compress_text(
                m["title"] + "\n" + m["content"][:3000],
                topic=f"coaching:{mid}",
            )
    except Exception:
        pass
    return jsonify({"ok": True, "progress": course_status(prog), "current": prog.get("current")})


@app.route("/api/coaching/practice", methods=["POST"])
def api_coaching_practice():
    data = request.get_json(force=True) or {}
    kind = (data.get("kind") or "practice").strip()
    text = (data.get("text") or "").strip()
    if not text:
        return jsonify({"error": "texto vacío"}), 400
    prog = _coach_progress().log_practice(kind, text)
    try:
        get_codex().store_crystal(text[:800], kind="coaching_practice", meta={"topic": "coaching:practice"})
    except Exception:
        pass
    return jsonify({"ok": True, "logged": True, "count": len(prog.get("practice_log") or [])})


@app.route("/api/coaching/tools")
def api_coaching_tools():
    return jsonify({"ok": True, "tools": TOOLS})


@app.route("/api/coaching/audit", methods=["POST"])
def api_coaching_audit():
    data = request.get_json(force=True) or {}
    text = (data.get("transcript") or data.get("text") or "").strip()
    context = (data.get("context") or "").strip() or None
    result = audit_transcript(text, context=context)
    if not result.get("ok"):
        return jsonify(result), 400
    # Guardar hallazgo en códice
    try:
        ecam = result.get("ecam") or {}
        blob = (
            "Auditoría simulada\n"
            + (result.get("summary") or "")
            + "\nE-C-A-M: "
            + " | ".join(f"{k}:{v}" for k, v in ecam.items())
        )
        get_codex().compress_text(blob[:3500], topic="coaching:audit")
    except Exception:
        pass
    return jsonify(result)



# ----- Idiomas (CEOX integrado) -----
@app.route("/api/lang/roles")
def api_lang_roles():
    return jsonify(roles_payload())


@app.route("/api/lang/start", methods=["POST"])
def api_lang_start():
    data = request.get_json(force=True) or {}
    role_id = (data.get("role_id") or data.get("role") or "friends").strip()
    target = (data.get("target_lang") or data.get("lang") or "en").strip()
    return jsonify(start_session(role_id, target))


@app.route("/api/lang/turn", methods=["POST"])
def api_lang_turn():
    data = request.get_json(force=True) or {}
    role_id = (data.get("role_id") or "friends").strip()
    target = (data.get("target_lang") or "en").strip()
    user_text = (data.get("message") or data.get("text") or "").strip()
    history = data.get("history") or []
    native = (data.get("native_lang") or "es").strip()
    long_mode = bool(data.get("long"))
    translate_es = data.get("translate_es")
    if translate_es is None:
        translate_es = True
    result = reply_turn(
        role_id=role_id,
        target_lang=target,
        user_text=user_text,
        history=history,
        native_lang=native,
        long=long_mode,
        translate_es=bool(translate_es),
        codex=get_codex(),
        long_memory=get_chat().long_memory,
    )
    return jsonify(result)


@app.route("/api/chat", methods=["POST"])
def api_chat():
    data = request.get_json(force=True) or {}
    text = (data.get("message") or data.get("text") or "").strip()
    if not text:
        return jsonify({"error": "mensaje vacío"}), 400
    sid = data.get("session_id") or "default"
    device = request.headers.get("X-Device-Id")
    long_mode = bool(data.get("long") or data.get("version_larga") or data.get("larga"))
    web_raw = data.get("web", data.get("internet", True))
    web_mode = False if web_raw in (False, "false", "0", 0) else True
    mode = str(data.get("mode") or "organic").strip().lower()
    if mode not in {"organic", "teach", "analysis"}:
        mode = "organic"
    result = get_chat().reply(
        sid, text, device_id=device, long=long_mode, web=web_mode, mode=mode,
    )
    return jsonify(result)


@app.route("/api/chat/adaptive")
def api_chat_adaptive():
    return jsonify({"ok": True, "adaptive": get_adaptive().profile_snapshot(), "context": get_adaptive().context_block()})


@app.route("/api/chat/feedback", methods=["POST"])
def api_chat_feedback():
    data = request.get_json(force=True) or {}
    kind = (data.get("type") or data.get("feedback") or "").strip()
    text = (data.get("text") or "").strip()
    result = get_adaptive().feedback(kind, text=text, context={"session_id": data.get("session_id")})
    return jsonify(result)


@app.route("/api/chat/teach", methods=["POST"])
def api_chat_teach():
    data = request.get_json(force=True) or {}
    topic = (data.get("topic") or "").strip()
    return jsonify({"ok": True, "teaching": get_adaptive().next_teaching_move(topic), "directive": get_adaptive().teaching_directive(topic)})


@app.route("/api/chat/sessions")
def api_chat_sessions():
    return jsonify({"ok": True, "sessions": get_chat().store.list_recent(12)})


# ========== API CRONOS v1 (superficie limpia y estable) ==========
# Principio: pocos endpoints, operaciones claras, JSON predecible.

@app.route("/cronos/v1")
@app.route("/cronos/v1/")
def cronos_v1_root():
    return jsonify({
        "name": "API CRONOS",
        "version": "1.0",
        "motto": "Pocos elementos. Mucha estructura.",
        "endpoints": {
            "GET  /cronos/v1/status": "Estado del motor y del corpus",
            "GET  /cronos/v1/who": "Identidad del motor + usuario",
            "POST /cronos/v1/who": "Declarar tu nombre / perfil",
            "POST /cronos/v1/analyze": "Analizar un sistema (protocolo)",
            "POST /cronos/v1/teach": "Generar lección o documento",
            "POST /cronos/v1/learn": "Ingerir texto o comprimir al Codex",
            "POST /cronos/v1/ingest": "Subir archivo (multipart file)",
            "GET  /cronos/v1/codex": "Estadísticas del conocimiento comprimido",
            "POST /cronos/v1/codex/expand": "Expandir un tema desde el Codex",
            "GET  /cronos/v1/library": "Biblioteca del Maestro",
            "GET  /api/life": "Estado vital funcional persistente",
            "GET  /api/life/autobiography": "Historia funcional de CEOS",
            "GET  /api/github/status": "Estado de la conexión GitHub",
            "GET  /api/github/repo": "Metadatos del repositorio GitHub",
            "GET  /api/github/tree": "Árbol del repositorio",
            "GET  /api/github/file": "Lectura de un archivo remoto",
            "POST /api/github/proposals": "Crear propuesta local para GitHub",
            "POST /api/github/proposals/<id>/publish": "Publicar propuesta mediante rama + PR (consentimiento)" ,
            "POST /api/life/heartbeat": "Pulso del sistema",
            "POST /api/life/reflect": "Reflexión local y próximos movimientos",
            "POST /api/life/feedback": "Corrección/confirmación que modifica el aprendizaje",
            "GET  /api/chat/adaptive": "Perfil adaptativo de conversación y enseñanza",
            "POST /api/chat/feedback": "Feedback que reajusta CEOS v8",
            "POST /api/chat/teach": "Siguiente movimiento pedagógico",
            "POST /cronos/v1/chat": "Diálogo conversacional (mensaje + session_id)",
        },
    })


@app.route("/cronos/v1/status")
def cronos_v1_status():
    mem = get_memory()
    return jsonify({
        "ok": True,
        "engine": get_identity().who_am_i(),
        "corpus": {
            "cases": len(mem.cases()),
            "hitos": len(mem.hitos()),
            "trajectories": len(mem.trajectories()),
            "grammar": get_grammar().stats(),
            "codex": get_codex().stats(),
            "library_docs": len(get_library().list_docs()),
        },
        "llm": llm_available(),
        "user": get_user().get().get("display_name") or get_user().get().get("name"),
        "life": get_life().stats(),
        "agency": {"cycle": get_agency().snapshot().get("cycle"), "goals": len(get_agency().goals("active")), "initiatives": len(get_agency().initiatives("proposed")), "experiments": len(get_agency().experiments("open"))},
    })


@app.route("/cronos/v1/who", methods=["GET", "POST"])
def cronos_v1_who():
    u = get_user()
    if request.method == "POST":
        data = request.get_json(force=True) or {}
        if data.get("name"):
            u.set_name(data["name"], data.get("display_name"))
        if data.get("nivel"):
            u.set_nivel(data["nivel"])
    u.touch_session()
    return jsonify({
        "motor": get_identity().who_am_i(),
        "user": u.get(),
        "greeting": u.greeting(),
    })


@app.route("/cronos/v1/analyze", methods=["POST"])
def cronos_v1_analyze():
    data = request.get_json(force=True) or {}
    if not data.get("identidad") and not data.get("sistema"):
        return jsonify({"error": "Envía 'identidad' o 'sistema' (descripción)"}), 400
    case = build_case(
        identidad=data.get("identidad") or data.get("sistema"),
        modo=data.get("modo", "habitual"),
        regla=data.get("regla", "dependiente"),
        kappa=data.get("kappa", "medio"),
        sigma=data.get("sigma", "medio"),
        rol_declarado=data.get("rol_declarado"),
        choque_externo=data.get("choque_externo", False),
        device=request.headers.get("X-Device-Id"),
    )
    saved = get_memory().add_case(case)
    get_grammar().learn_from_case(saved)
    try:
        get_life().record_learning("analysis", f"Caso analizado: {saved.get('identidad') or data.get('sistema') or 'sin identidad'}", topic="cronos")
    except Exception:
        pass
    return jsonify({"ok": True, "case": saved})


@app.route("/cronos/v1/teach", methods=["POST"])
def cronos_v1_teach():
    data = request.get_json(force=True) or {}
    topic = data.get("topic") or data.get("tema")
    if not topic:
        return jsonify({"error": "falta topic"}), 400
    mode = data.get("mode", "lesson")  # lesson | deep | guide
    mentor = get_mentor()
    if mode == "deep":
        doc = mentor.generate_deep_document(topic, pedido=data.get("pedido"), use_web=bool(data.get("web")))
        return jsonify({"ok": True, "type": "deep", "document": doc})
    if mode == "guide":
        guide = mentor.generate_study_guide(topic)
        return jsonify({"ok": True, "type": "guide", "document": guide})
    lesson = mentor.generate_lesson(topic, estilo=data.get("estilo", "concepto"), student_level=data.get("nivel", "inicial"))
    return jsonify({"ok": True, "type": "lesson", "document": lesson})


@app.route("/cronos/v1/refine", methods=["POST"])
def cronos_v1_refine():
    data = request.get_json(force=True) or {}
    pedido = data.get("pedido") or data.get("topic") or data.get("tema")
    if not pedido:
        return jsonify({"error": "falta pedido"}), 400
    return jsonify(get_mentor().refine_with_interactions(
        pedido=pedido, n=data.get("n", 3), use_web=bool(data.get("web")),
    ))


@app.route("/cronos/v1/learn", methods=["POST"])
def cronos_v1_learn():
    data = request.get_json(force=True) or {}
    text = data.get("text") or data.get("texto")
    topic = data.get("topic") or data.get("tema") or "aprendizaje"
    if not text:
        return jsonify({"error": "falta text"}), 400
    entry = get_library().ingest_text(text, title=topic, tags=["api"], grammar=get_grammar())
    codex_stats = get_mentor().ingest_to_codex(text, topic)
    try:
        get_life().record_learning("ingest", f"Ingerido en corpus: {topic}", topic=topic)
    except Exception:
        pass
    return jsonify({"ok": True, "library": entry, "codex": codex_stats})


@app.route("/cronos/v1/ingest", methods=["POST"])
def cronos_v1_ingest():
    return api_mentor_ingest_file()


@app.route("/cronos/v1/codex")
def cronos_v1_codex():
    return jsonify({"ok": True, "stats": get_codex().stats(), "atoms": get_codex().list_atoms()})


@app.route("/cronos/v1/codex/expand", methods=["POST"])
def cronos_v1_codex_expand():
    data = request.get_json(force=True) or {}
    topic = data.get("topic") or data.get("tema")
    if not topic:
        return jsonify({"error": "falta topic"}), 400
    return jsonify(get_codex().expand_topic(topic))


@app.route("/cronos/v1/chat", methods=["POST"])
def cronos_v1_chat():
    data = request.get_json(force=True) or {}
    text = (data.get("message") or data.get("text") or "").strip()
    if not text:
        return jsonify({"error": "mensaje vacío"}), 400
    sid = data.get("session_id") or "default"
    device = request.headers.get("X-Device-Id")
    long_mode = bool(data.get("long") or data.get("version_larga"))
    web_raw = data.get("web", data.get("internet", True))
    web_mode = False if web_raw in (False, "false", "0", 0) else True
    result = get_chat().reply(
        sid, text, device_id=device, long=long_mode, web=web_mode,
    )
    return jsonify(result)


@app.route("/cronos/v1/library")
def cronos_v1_library():
    return jsonify({"ok": True, "docs": get_library().list_docs()})


# ---------- Meta ----------
@app.route("/api/meta")
def api_meta():
    import os
    voice = get_voice().available()
    port = int(os.environ.get("PORT", "5000"))
    return jsonify({
        "name": "CEOS v8",
        "version": "8.0.0-adaptive",
        "lan_ip": get_lan_ip(),
        "port": port,
        "arquetipos": list(ARCHETYPES.keys()),
        "modos": sorted(VALID_MODOS),
        "reglas": sorted(VALID_REGLA),
        "niveles": sorted(VALID_NIVEL),
        "voice": voice,
        "capabilities": {
            "research": True,
            "youtube_text_only": True,
            "voice_female_preferred": True,
            "adaptive_dialogue": True,
            "adaptive_teaching": True,
            "persistent_mastery": True,
            "multi_device": True,
            "mentor": True,
            "document_ingest": True,
            "study_guides": True,
            "codex": True,
            "deep_write_optional": True,
            "agency": True,
            "agency_goals": True,
            "agency_initiatives": True,
            "agency_experiments": True,
            "agency_model_gaps": True,
            "agency_evolution_proposals": True,
            "cloud_ready": True,
            "fractal_codex": True,
            "web_research_in_chat": True,
            "long_form_chat": True,
            "lang_practice": True,
            "coaching_course": True,
            "living_core": True,
            "bounded_autonomy": True,
            "autobiography": True,
            "github_bridge": bool(get_github().status().get("enabled")),
            "github_write": bool(get_github().status().get("write_enabled")),
        },
    })


_life_worker_started = False
_life_worker_thread = None


def start_life_background_worker():
    """Mantiene el pulso de CEOS aunque el navegador esté cerrado.

    Se activa solo cuando CEOS_LIFE_BACKGROUND=1 para evitar duplicaciones en
    despliegues multi-worker. El proceso escribe únicamente estado local/auditable.
    """
    import os
    import threading
    import time
    global _life_worker_started, _life_worker_thread
    if _life_worker_started or os.environ.get("CEOS_LIFE_BACKGROUND", "0") not in ("1", "true", "yes"):
        return False
    _life_worker_started = True

    def _loop():
        try:
            life = get_life()
            while True:
                try:
                    state = life.heartbeat(reason="background")
                    get_agency().tick(state, reason="background")
                except Exception:
                    pass
                time.sleep(max(10, int(os.environ.get("CEOS_LIFE_INTERVAL", "20"))))
        except Exception:
            return

    _life_worker_thread = threading.Thread(target=_loop, name="ceos-life", daemon=True)
    _life_worker_thread.start()
    return True


def main():
    import os
    _ensure_data_dirs()
    start_life_background_worker()

    port = int(os.environ.get("PORT", "5000"))
    ip = get_lan_ip()
    print("=" * 60)
    print("  CEOS v8 — CRONOS-Espiral + Living Entity + Adaptive Mentor (cloud-ready)")
    print("=" * 60)
    print(f"  Local:    http://127.0.0.1:{port}")
    print(f"  Red LAN:  http://{ip}:{port}")
    print("  Accesible desde PC, Android e iOS.")
    print("  Pestaña Maestro: lecciones, trayectorias, documentos.")
    print("  Ctrl+C para detener.")
    print("=" * 60)
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)


if __name__ == "__main__":
    main()
