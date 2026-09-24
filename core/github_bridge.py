"""
CEOS GitHub Bridge 1.0

Integración deliberadamente acotada con GitHub REST API.
- Lee repositorio, árbol y archivos.
- Guarda propuestas locales antes de cualquier escritura.
- Puede crear una rama + commit + Pull Request solo con consentimiento explícito
  y con CEOS_GITHUB_WRITE=1.
- Nunca devuelve ni almacena el token en respuestas de API.

Configuración por variables de entorno:
  GITHUB_TOKEN / CEOS_GITHUB_TOKEN
  GITHUB_REPOSITORY / CEOS_GITHUB_REPOSITORY   (owner/repo)
  GITHUB_BRANCH / CEOS_GITHUB_BRANCH           (por defecto main)
  CEOS_GITHUB_WRITE=1                          habilita escritura
  CEOS_GITHUB_ALLOW_WORKFLOWS=1                permite tocar .github/workflows
  GITHUB_API_URL / CEOS_GITHUB_API_URL         (por defecto api.github.com)
"""
from __future__ import annotations

import base64
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


API_VERSION = "2026-03-10"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class GitHubBridge:
    def __init__(self, base_path: str = "data/github"):
        self.base = Path(base_path)
        self.base.mkdir(parents=True, exist_ok=True)
        self.proposals_dir = self.base / "proposals"
        self.proposals_dir.mkdir(parents=True, exist_ok=True)
        self.enabled = bool(self.token and self.repository)

    @property
    def token(self) -> str:
        return (os.environ.get("CEOS_GITHUB_TOKEN") or os.environ.get("GITHUB_TOKEN") or "").strip()

    @property
    def repository(self) -> str:
        raw = (os.environ.get("CEOS_GITHUB_REPOSITORY") or os.environ.get("GITHUB_REPOSITORY") or "").strip()
        if "/" not in raw:
            owner = (os.environ.get("GITHUB_OWNER") or "").strip()
            repo = (os.environ.get("GITHUB_REPO") or "").strip()
            raw = f"{owner}/{repo}" if owner and repo else ""
        return raw.strip("/")

    @property
    def owner(self) -> str:
        return self.repository.split("/", 1)[0] if "/" in self.repository else ""

    @property
    def repo(self) -> str:
        return self.repository.split("/", 1)[1] if "/" in self.repository else ""

    @property
    def branch(self) -> str:
        return (os.environ.get("CEOS_GITHUB_BRANCH") or "main").strip() or "main"

    @property
    def api_base(self) -> str:
        return (os.environ.get("CEOS_GITHUB_API_URL") or os.environ.get("GITHUB_API_URL") or "https://api.github.com").rstrip("/")

    @property
    def admin_token(self) -> str:
        return (os.environ.get("CEOS_ADMIN_TOKEN") or "").strip()

    @property
    def admin_guarded(self) -> bool:
        return bool(self.admin_token)

    @property
    def write_enabled(self) -> bool:
        return os.environ.get("CEOS_GITHUB_WRITE", "0").lower() in {"1", "true", "yes", "on"} and bool(self.token)

    @property
    def allow_workflows(self) -> bool:
        return os.environ.get("CEOS_GITHUB_ALLOW_WORKFLOWS", "0").lower() in {"1", "true", "yes", "on"}

    def _headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": API_VERSION,
            "User-Agent": "CEOS-Agency/7.0",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def _url(self, path: str, **params: Any) -> str:
        if not path.startswith("/"):
            path = "/" + path
        url = self.api_base + path
        clean = {k: v for k, v in params.items() if v is not None and v != ""}
        if clean:
            url += "?" + urllib.parse.urlencode(clean)
        return url

    def _request(self, method: str, path: str, *, query: Optional[dict] = None, body: Optional[dict] = None, timeout: int = 20) -> tuple[int, dict, dict]:
        if not self.enabled:
            raise RuntimeError("GitHub no está configurado. Define CEOS_GITHUB_TOKEN y CEOS_GITHUB_REPOSITORY.")
        url = self._url(path, **(query or {}))
        data = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=self._headers(), method=method.upper())
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read().decode("utf-8")
                payload = json.loads(raw) if raw else {}
                return int(resp.status), payload if isinstance(payload, dict) else {"data": payload}, dict(resp.headers)
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            try:
                payload = json.loads(raw) if raw else {}
            except Exception:
                payload = {"message": raw[:500]}
            msg = payload.get("message") if isinstance(payload, dict) else raw
            raise RuntimeError(f"GitHub HTTP {exc.code}: {msg}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"No se pudo conectar con GitHub: {exc.reason}") from exc

    def status(self) -> dict:
        configured = bool(self.repository)
        authenticated = bool(self.token)
        out = {
            "configured": configured,
            "authenticated": authenticated,
            "enabled": bool(configured and authenticated),
            "write_enabled": bool(self.write_enabled and self.admin_guarded),
            "admin_guarded": self.admin_guarded,
            "repository": self.repository or None,
            "branch": self.branch,
            "api_version": API_VERSION,
            "proposals_local": len(list(self.proposals_dir.glob("*.json"))),
        }
        if not out["enabled"]:
            out["hint"] = "Configura CEOS_GITHUB_TOKEN + CEOS_GITHUB_REPOSITORY (owner/repo)."
            return out
        try:
            _, me, _ = self._request("GET", "/user")
            out["user"] = me.get("login") or me.get("name")
        except Exception as exc:
            out["error"] = str(exc)
        return out

    def repo_info(self) -> dict:
        _, data, _ = self._request("GET", f"/repos/{urllib.parse.quote(self.owner)}/{urllib.parse.quote(self.repo)}")
        return self._repo_public(data)

    @staticmethod
    def _repo_public(data: dict) -> dict:
        keys = (
            "id", "name", "full_name", "private", "default_branch", "html_url",
            "description", "updated_at", "pushed_at", "language", "fork", "open_issues_count",
            "stargazers_count", "size",
        )
        return {k: data.get(k) for k in keys if k in data}

    def tree(self, ref: Optional[str] = None, recursive: bool = True, limit: int = 2000) -> dict:
        ref = ref or self.branch
        _, data, _ = self._request(
            "GET",
            f"/repos/{urllib.parse.quote(self.owner)}/{urllib.parse.quote(self.repo)}/git/trees/{urllib.parse.quote(ref, safe='')}",
            query={"recursive": "1" if recursive else None},
        )
        entries = []
        for item in data.get("tree", [])[: max(1, min(int(limit or 2000), 10000))]:
            entries.append({"path": item.get("path"), "type": item.get("type"), "size": item.get("size"), "sha": item.get("sha")})
        return {"sha": data.get("sha"), "truncated": bool(data.get("truncated")), "tree": entries}

    def get_file(self, path: str, ref: Optional[str] = None) -> dict:
        clean = self._validate_path(path)
        ref = ref or self.branch
        _, data, _ = self._request(
            "GET",
            f"/repos/{urllib.parse.quote(self.owner)}/{urllib.parse.quote(self.repo)}/contents/{urllib.parse.quote(clean, safe='/')}",
            query={"ref": ref},
        )
        if isinstance(data, list):
            return {"path": clean, "type": "dir", "entries": [{"name": x.get("name"), "path": x.get("path"), "type": x.get("type")} for x in data]}
        content = data.get("content", "")
        decoded = ""
        if content:
            try:
                decoded = base64.b64decode("".join(content.split())).decode("utf-8", errors="replace")
            except Exception:
                decoded = ""
        return {
            "path": data.get("path") or clean,
            "name": data.get("name"),
            "sha": data.get("sha"),
            "size": data.get("size"),
            "html_url": data.get("html_url"),
            "content": decoded,
            "truncated": len(decoded) > 1_000_000,
        }

    def propose_file(self, path: str, content: str, message: str, *, reason: str = "") -> dict:
        clean = self._validate_path(path)
        if not isinstance(content, str):
            raise ValueError("content debe ser texto")
        proposal = {
            "id": uuid.uuid4().hex[:16],
            "created_at": _now(),
            "repository": self.repository,
            "base_branch": self.branch,
            "path": clean,
            "message": (message or f"CEOS proposal: update {clean}").strip()[:180],
            "reason": (reason or "").strip()[:1000],
            "content": content,
            "status": "proposed",
        }
        target = self.proposals_dir / f"{proposal['id']}.json"
        target.write_text(json.dumps(proposal, ensure_ascii=False, indent=2), encoding="utf-8")
        return self._proposal_public(proposal)

    def list_proposals(self, limit: int = 30) -> list[dict]:
        items = []
        for p in sorted(self.proposals_dir.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True)[: max(1, min(int(limit or 30), 100))]:
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                items.append(self._proposal_public(data))
            except Exception:
                continue
        return items

    @staticmethod
    def _proposal_public(data: dict) -> dict:
        out = dict(data)
        out.pop("content", None)
        return out

    def _load_proposal(self, proposal_id: str) -> dict:
        if not re.fullmatch(r"[a-f0-9]{16}", proposal_id or ""):
            raise ValueError("proposal_id inválido")
        path = self.proposals_dir / f"{proposal_id}.json"
        if not path.exists():
            raise ValueError("propuesta no encontrada")
        return json.loads(path.read_text(encoding="utf-8"))

    def publish_proposal(self, proposal_id: str, *, create_pr: bool = True, title: Optional[str] = None) -> dict:
        if not self.admin_guarded:
            raise PermissionError("Falta CEOS_ADMIN_TOKEN: el control online de GitHub está protegido.")
        if not self.write_enabled:
            raise PermissionError("Escritura GitHub desactivada. Define CEOS_GITHUB_WRITE=1 y un token con permisos adecuados.")
        proposal = self._load_proposal(proposal_id)
        clean = self._validate_path(proposal.get("path", ""))
        if clean.startswith(".github/workflows/") and not self.allow_workflows:
            raise PermissionError("Por seguridad, CEOS no modifica workflows sin CEOS_GITHUB_ALLOW_WORKFLOWS=1.")

        base_branch = proposal.get("base_branch") or self.branch
        branch_name = f"ceos/proposal/{proposal_id}"

        # Obtener SHA del branch base y crear branch nueva.
        _, ref_data, _ = self._request(
            "GET",
            f"/repos/{urllib.parse.quote(self.owner)}/{urllib.parse.quote(self.repo)}/git/ref/heads/{urllib.parse.quote(base_branch, safe='')}",
        )
        base_sha = ((ref_data.get("object") or {}).get("sha"))
        if not base_sha:
            raise RuntimeError("No se pudo obtener el SHA de la rama base.")

        try:
            self._request(
                "POST",
                f"/repos/{urllib.parse.quote(self.owner)}/{urllib.parse.quote(self.repo)}/git/refs",
                body={"ref": f"refs/heads/{branch_name}", "sha": base_sha},
            )
        except RuntimeError as exc:
            if "422" not in str(exc) and "Reference already exists" not in str(exc):
                raise

        # SHA previo si el archivo existe en la rama nueva.
        sha = None
        try:
            current = self.get_file(clean, ref=branch_name)
            sha = current.get("sha")
        except Exception:
            sha = None

        encoded = base64.b64encode(proposal.get("content", "").encode("utf-8")).decode("ascii")
        body = {
            "message": proposal.get("message") or f"CEOS proposal: update {clean}",
            "content": encoded,
            "branch": branch_name,
            "committer": {
                "name": os.environ.get("CEOS_GITHUB_COMMITTER_NAME") or "CEOS",
                "email": os.environ.get("CEOS_GITHUB_COMMITTER_EMAIL") or "ceos@users.noreply.github.com",
            },
        }
        if sha:
            body["sha"] = sha
        self._request(
            "PUT",
            f"/repos/{urllib.parse.quote(self.owner)}/{urllib.parse.quote(self.repo)}/contents/{urllib.parse.quote(clean, safe='/')}",
            body=body,
        )

        result = {"ok": True, "branch": branch_name, "path": clean, "proposal_id": proposal_id}
        if create_pr:
            pr_body = {
                "title": (title or proposal.get("message") or f"CEOS proposal: {clean}")[:250],
                "head": branch_name,
                "base": base_branch,
                "body": (
                    "Propuesta generada por CEOS Living Core.\n\n"
                    f"Motivo: {proposal.get('reason') or 'no indicado'}\n\n"
                    "La integración se mantiene en una rama para revisión humana."
                ),
            }
            _, pr, _ = self._request("POST", f"/repos/{urllib.parse.quote(self.owner)}/{urllib.parse.quote(self.repo)}/pulls", body=pr_body)
            result["pull_request"] = {"number": pr.get("number"), "url": pr.get("html_url"), "state": pr.get("state")}
        proposal["status"] = "published"
        proposal["published_at"] = _now()
        proposal["branch"] = branch_name
        proposal["pull_request"] = result.get("pull_request")
        (self.proposals_dir / f"{proposal_id}.json").write_text(json.dumps(proposal, ensure_ascii=False, indent=2), encoding="utf-8")
        return result

    def _validate_path(self, path: str) -> str:
        clean = str(path or "").strip().replace("\\", "/").lstrip("/")
        if not clean or clean.startswith("/") or ".." in clean.split("/"):
            raise ValueError("ruta GitHub no válida")
        return clean
