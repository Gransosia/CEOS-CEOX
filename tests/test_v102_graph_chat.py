import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.co_evolution import CoEvolutionGraph  # noqa: E402
from core.chat import ChatSession  # noqa: E402


def test_graph_view_prioritizes_core_and_projects(tmp_path):
    g = CoEvolutionGraph(str(tmp_path / "graph"), user_label="Usuario")
    view = g.graph_view("FORMA 333", limit=40)
    labels = {n["label"] for n in view["nodes"]}
    assert "CEOS" in labels
    assert "FORMA 333 / Olla lenta" in labels
    assert "SAD / Tubería" in labels or "CRONOS-Espiral-OCa" in labels
    ids = {n["id"] for n in view["nodes"]}
    assert all(e["source"] in ids and e["target"] in ids for e in view["edges"])
    assert view["focus"] == "FORMA 333"


def test_graph_view_without_focus_is_bounded(tmp_path):
    g = CoEvolutionGraph(str(tmp_path / "graph"), user_label="Usuario")
    view = g.graph_view("", limit=12)
    assert len(view["nodes"]) <= 12
    assert isinstance(view["edges"], list)
    assert view["mode"] == "overview"


def test_chat_session_persists_conversation_state(tmp_path):
    store = ChatSession(str(tmp_path / "chat"))
    session = store.load("s-test")
    session["conversation_state"] = {
        "turns": 2,
        "last_topic": "FORMA 333",
        "last_mode": "organic",
        "last_casual": False,
    }
    session["messages"] = [
        {"role": "user", "content": "Hablemos de FORMA 333"},
        {"role": "assistant", "content": "Sí, sigamos con ello."},
    ]
    store.save(session)
    loaded = store.load("s-test")
    assert loaded["conversation_state"]["last_topic"] == "FORMA 333"
    assert len(loaded["messages"]) == 2


def test_ui_contains_graph_canvas_and_history_restore():
    html = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
    assert 'id="coevolution-graph-canvas"' in html
    assert 'loadChatHistory' in html
    assert 'fetch("/api/chat/history?' in html
    assert 'chat-typing' in html
