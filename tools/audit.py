from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def run(cmd: list[str]) -> tuple[bool, str]:
    try:
        p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=180)
        return p.returncode == 0, (p.stdout + p.stderr).strip()
    except Exception as exc:
        return False, type(exc).__name__ + ": " + str(exc)


def main() -> int:
    failures: list[str] = []
    print("CEOS v10.0 AUDIT + AUTHOR LAB + CO-EVOLUTION")
    print("=" * 60)

    ok, out = run([sys.executable, "-m", "compileall", "-q", "."])
    print("PYTHON COMPILE:", "OK" if ok else "FAIL")
    if not ok:
        failures.append("python compile")
        print(out)

    ok, out = run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py", "-q"])
    print("UNIT TESTS:", "OK" if ok else "FAIL")
    if not ok:
        failures.append("unit tests")
        print(out)

    node = None
    for candidate in ("node", "nodejs"):
        try:
            subprocess.run([candidate, "--version"], capture_output=True, check=True)
            node = candidate
            break
        except Exception:
            pass
    if node:
        for js in ("web/app.js", "app.js"):
            ok, out = run([node, "--check", js])
            print(f"JS {js}:", "OK" if ok else "FAIL")
            if not ok:
                failures.append(f"js {js}")
                print(out)
    else:
        print("JS CHECK: SKIPPED (Node.js no instalado)")

    bad_json = []
    for p in ROOT.rglob("*.json"):
        if "__pycache__" in p.parts:
            continue
        try:
            json.loads(p.read_text(encoding="utf-8"))
        except Exception as exc:
            bad_json.append((str(p.relative_to(ROOT)), str(exc)))
    print("JSON:", "OK" if not bad_json else "FAIL")
    if bad_json:
        failures.append("json")
        for item in bad_json:
            print(" ", item)

    text = []
    for p in ROOT.rglob("*"):
        if p.is_file() and "__pycache__" not in p.parts and p.suffix.lower() in {".py", ".js", ".html", ".md", ".json", ".txt", ".bat", ".yaml", ".yml"}:
            try:
                text.append(p.read_text(encoding="utf-8", errors="replace"))
            except Exception:
                pass
    blob = "\n".join(text)
    secret_patterns = [
        r"gsk_[A-Za-z0-9_-]{20,}",
        r"sk-[A-Za-z0-9_-]{20,}",
        r"AIzaSy[A-Za-z0-9_-]{30,}",
        r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
    ]
    secret_hits = [pat for pat in secret_patterns if re.search(pat, blob)]
    print("SECRET SCAN:", "OK" if not secret_hits else "FAIL")
    if secret_hits:
        failures.append("secret scan")

    print("=" * 60)
    if failures:
        print("AUDIT FAILED:", ", ".join(failures))
        return 1
    print("AUDIT PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
