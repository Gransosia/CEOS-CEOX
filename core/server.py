"""
Servidor local multi-dispositivo del Motor CRONOS-Espiral v5.

- Accesible desde cualquier dispositivo de la red local (PC, Android, iOS).
- Endpoints REST para identidad, casos, hitos, trayectorias, gramática y sync.
- Interfaz web responsive incluida.
"""
import socket
import uuid
from pathlib import Path
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

BASE_DIR = Path(__file__).resolve().parent.parent
WEB_DIR = BASE_DIR / "web"
DATA_DIR = BASE_DIR / "data"
KNOWLEDGE_DIR = BASE_DIR / "knowledge"

app = Flask(__name__, static_folder=None)


def _ensure_data_dirs():
    """Crea data/ y subcarpetas (necesario cuando arranca gunicorn y no se llama main())."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    for sub in ("identity", "memory", "grammar", "library", "mentor", "codex", "user", "uploads", "chat", "long_memory"):
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


def get_learner():
    if "learner" not in g:
        g.learner = TopicLearner(
            memory=get_memory(),
            grammar=get_grammar(),
            identity=get_identity(),
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
@app.route("/health")
@app.route("/healthz")
def health():
    """Healthcheck simple para Render / Railway / balanceadores."""
    return jsonify({"ok": True, "service": "ceos-v5", "version": "5.4.1-cloud", "web": (WEB_DIR / "index.html").exists()})


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
    mem = get_memory()
    grm = get_grammar()
    payload = mem.export_all()
    payload["grammar"] = grm.export_learned()
    payload["device"] = get_identity().state.get("device_id")
    return jsonify(payload)


@app.route("/api/sync/import", methods=["POST"])
def api_sync_import():
    foreign = request.get_json(force=True) or {}
    mem = get_memory()
    grm = get_grammar()
    stats = mem.merge_from(foreign)
    stats["fragmentos_added"] = grm.merge_learned(foreign.get("grammar", {}))
    get_identity().log(f"Sync import: {stats}", importance=2)
    return jsonify({"ok": True, "stats": stats})


@app.route("/api/sync/status")
def api_sync_status():
    mem = get_memory()
    grm = get_grammar()
    return jsonify({
        "cases": len(mem.cases()),
        "hitos": len(mem.hitos()),
        "trajectories": len(mem.trajectories()),
        "grammar": grm.stats(),
        "server_time": datetime.now(timezone.utc).isoformat(),
        "lan_ip": get_lan_ip(),
    })


# ---------- Investigación / Aprendizaje de temas ----------
@app.route("/api/research", methods=["POST"])
def api_research():
    data = request.get_json(force=True) or {}
    topic = data.get("topic") or data.get("tema")
    focus = data.get("focus")
    learn = data.get("learn", True)
    device = data.get("device") or request.headers.get("X-Device-Id")

    if not topic:
        return jsonify({"error": "falta 'topic' o 'tema'"}), 400

    if learn:
        report = get_learner().learn(topic, focus=focus, device=device)
    else:
        report = research_topic(topic, focus=focus)

    return jsonify(report)


@app.route("/api/research/history")
def api_research_history():
    return jsonify(get_learner().history())


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
    entry = get_library().ingest_text(
        text, title=title, tags=tags, grammar=get_grammar()
    )
    get_identity().log(f"Documento ingerido: {title} ({entry.get('fragments_added', 0)} frag.)", importance=2)
    return jsonify(entry), 201



@app.route("/api/mentor/ingest/file", methods=["POST"])
def api_mentor_ingest_file():
    """Sube PDF/DOCX/TXT/MD y los incorpora a la biblioteca + grammar + codex."""
    if "file" not in request.files and "files" not in request.files:
        # también aceptar un solo file bajo otro nombre
        f = None
        for key in request.files:
            f = request.files[key]
            break
        if f is None:
            return jsonify({"error": "No se envió ningún archivo (campo file)"}), 400
        files = [f]
    else:
        files = request.files.getlist("file") or request.files.getlist("files")

    lib = get_library()
    grm = get_grammar()
    mentor = get_mentor()
    results = []
    upload_dir = DATA_DIR / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)

    for f in files:
        if not f or not f.filename:
            continue
        name = secure_filename(f.filename)
        suffix = Path(name).suffix.lower()
        if suffix not in {".pdf", ".docx", ".txt", ".md", ".markdown"}:
            results.append({"file": name, "status": "error", "error": f"Formato no soportado: {suffix}"})
            continue
        dest = upload_dir / name
        f.save(str(dest))
        try:
            entry = lib.ingest_file(dest, title=Path(name).stem, tags=["upload"], grammar=grm)
            # Comprimir también al codex
            text_path = lib.docs_dir / f"{entry['id']}.txt"
            if text_path.exists():
                mentor.ingest_to_codex(text_path.read_text(encoding="utf-8", errors="replace"), topic=entry["title"])
            results.append({
                "file": name,
                "status": "ok",
                "id": entry["id"],
                "fragments": entry.get("fragments_added", 0),
                "chunks": entry.get("chunks", 0),
            })
            get_identity().log(f"Archivo ingerido: {name}", importance=2)
        except Exception as e:
            results.append({"file": name, "status": "error", "error": str(e)})

    return jsonify({"ok": True, "results": results, "stats": mentor.knowledge_stats()})


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
    allowed = ["GROQ_API_KEY", "GEMINI_API_KEY", "ANTHROPIC_API_KEY", "OPENAI_API_KEY"]
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
    result = reply_turn(
        role_id=role_id,
        target_lang=target,
        user_text=user_text,
        history=history,
        native_lang=native,
        long=long_mode,
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
    web_mode = bool(data.get("web") or data.get("internet") or data.get("navegar"))
    result = get_chat().reply(
        sid, text, device_id=device, long=long_mode, web=web_mode,
    )
    return jsonify(result)


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
    web_mode = bool(data.get("web") or data.get("internet"))
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
        "name": "CEOS v5",
        "version": "5.4.1-cloud",
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
            "multi_device": True,
            "mentor": True,
            "document_ingest": True,
            "study_guides": True,
            "codex": True,
            "deep_write_optional": True,
            "cloud_ready": True,
            "fractal_codex": True,
            "web_research_in_chat": True,
            "long_form_chat": True,
            "lang_practice": True,
            "coaching_course": True,
        },
    })


def main():
    import os
    _ensure_data_dirs()

    port = int(os.environ.get("PORT", "5000"))
    ip = get_lan_ip()
    print("=" * 60)
    print("  CEOS v5 — Motor CRONOS-Espiral + Modo Maestro (cloud-ready)")
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
