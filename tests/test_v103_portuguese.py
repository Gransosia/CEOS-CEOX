import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.lang_engine import reply_turn, start_session  # noqa: E402
from core.lang_scenarios import get_role, list_roles  # noqa: E402
from core.lang_training import get_program  # noqa: E402


def test_pt_is_european_portuguese_path():
    r = start_session("pt-daily", "pt")
    assert r["ok"] is True
    assert "Portugal" in r["role"]["name_es"]
    assert "Tens" in r["partner_message"]


def test_prosegur_roles_exist():
    ids = {r["id"] for r in list_roles()}
    expected = {
        "pt-daily",
        "pt-prosegur-interview",
        "pt-uat",
        "pt-process-improvement",
        "pt-manual-support",
        "pt-travel-work",
    }
    assert expected.issubset(ids)
    assert get_role("pt-prosegur-interview") is not None


def test_pt_corrections_target_spanish_interference():
    r = reply_turn(
        role_id="pt-prosegur-interview",
        target_lang="pt",
        user_text="Gosto de trabalhar em equipe e tenho experiencia em gestiòn de procesos. Estoy trabajando com usuarios.",
        history=[],
        long=False,
        translate_es=False,
    )
    assert r["ok"] is True
    texts = " ".join(c["corrected"] for c in r["corrections"])
    assert "equipa" in texts or "gestão" in texts or "estou a + infinitivo" in texts
    assert r["pt_focus"]


def test_prosegur_program_contains_offer_dimensions():
    p = get_program()
    assert p["id"] == "pt-pt-prosegur-cash"
    joined = " ".join(p["focus"] + [m["title"] for m in p["modules"]]).lower()
    for term in ["uat", "soporte", "viajes", "excel", "autonomía"]:
        assert term in joined
