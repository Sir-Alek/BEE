"""Publicación de .feature a repositorios Git (GitHub / GitLab / Azure Repos)."""
from __future__ import annotations

import base64
import re
from typing import Any, Dict, Tuple
from urllib.parse import quote, urlparse

import requests

from core.req_intelligence.publishers.base import PublishContext, PublishResult


def _parse_repo(repo_url: str) -> Tuple[str, str, str]:
    """Devuelve (provider, owner, repo)."""
    url = (repo_url or "").strip().rstrip("/")
    if not url:
        raise ValueError("URL de repositorio requerida")
    if "github.com" in url:
        m = re.search(r"github\.com[:/]+([^/]+)/([^/.]+)", url)
        if not m:
            raise ValueError("URL GitHub no válida")
        return "github", m.group(1), m.group(2).replace(".git", "")
    if "gitlab.com" in url or "/-/tree/" in url:
        m = re.search(r"gitlab\.com[:/]+(.+?)/([^/.]+?)(?:\.git)?/?$", url)
        if not m:
            raise ValueError("URL GitLab no válida")
        return "gitlab", m.group(1), m.group(2)
    if "dev.azure.com" in url or "visualstudio.com" in url:
        m = re.search(r"dev\.azure\.com/([^/]+)/([^/]+)/_git/([^/?#]+)", url)
        if m:
            return "azure_repos", f"{m.group(1)}/{m.group(2)}", m.group(3)
    raise ValueError("Proveedor Git no soportado (github, gitlab, azure_repos)")


def _safe_feature_path(base_path: str, file_path: str, feature_name: str) -> str:
    if file_path.strip():
        path = file_path.strip().replace("\\", "/").lstrip("/")
    else:
        slug = re.sub(r"[^\w\-]+", "_", feature_name or "feature").strip("_") or "feature"
        base = (base_path or "features/").replace("\\", "/")
        if not base.endswith("/"):
            base += "/"
        path = f"{base}{slug}.feature"
    if not path.lower().endswith(".feature"):
        path += ".feature"
    return path


class GitPublisher:
    target = "git"

    def publish(self, ctx: PublishContext) -> PublishResult:
        profile = ctx.profile or {}
        git_cfg = profile.get("git") or {}
        token = str(git_cfg.get("token") or "").strip()
        repo_url = str(git_cfg.get("repo_url") or "").strip()
        branch = (ctx.branch or git_cfg.get("branch") or "main").strip()
        base_path = str(git_cfg.get("base_path") or "features/")
        if not token or not repo_url:
            return PublishResult(False, "git", "Perfil Git incompleto (repo_url, token)")

        provider, owner, repo = _parse_repo(repo_url)
        path = _safe_feature_path(base_path, ctx.file_path, ctx.feature_name)
        message = (ctx.commit_message or f"ELIA: add {path}").strip()

        if provider == "github":
            return self._github_put(owner, repo, path, branch, token, ctx.gherkin_text, message)
        if provider == "gitlab":
            return self._gitlab_put(owner, repo, path, branch, token, ctx.gherkin_text, message)
        return self._azure_repos_put(owner, repo, path, branch, token, ctx.gherkin_text, message)

    def smoke_test(self, profile: Dict[str, Any]) -> PublishResult:
        git_cfg = profile.get("git") or {}
        token = str(git_cfg.get("token") or "").strip()
        repo_url = str(git_cfg.get("repo_url") or "").strip()
        if not token or not repo_url:
            return PublishResult(False, "git", "Faltan repo_url o token")
        try:
            provider, owner, repo = _parse_repo(repo_url)
        except ValueError as e:
            return PublishResult(False, "git", str(e))
        if provider == "github":
            url = f"https://api.github.com/repos/{owner}/{repo}"
            r = requests.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=15)
            if r.status_code == 200:
                return PublishResult(True, "git", "Conexión GitHub OK", url=r.json().get("html_url", ""))
            return PublishResult(False, "git", f"GitHub {r.status_code}: {r.text[:200]}")
        return PublishResult(True, "git", f"Repositorio parseado ({provider}); smoke básico OK")

    def _github_put(
        self, owner: str, repo: str, path: str, branch: str, token: str, content: str, message: str
    ) -> PublishResult:
        api = f"https://api.github.com/repos/{owner}/{repo}/contents/{quote(path, safe='/')}"
        headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}
        sha = None
        get_r = requests.get(api, headers=headers, params={"ref": branch}, timeout=30)
        if get_r.status_code == 200:
            sha = get_r.json().get("sha")
        payload = {
            "message": message,
            "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
            "branch": branch,
        }
        if sha:
            payload["sha"] = sha
        put_r = requests.put(api, headers=headers, json=payload, timeout=30)
        if put_r.status_code in (200, 201):
            data = put_r.json()
            html = (data.get("content") or {}).get("html_url") or f"https://github.com/{owner}/{repo}/blob/{branch}/{path}"
            return PublishResult(True, "git", f"Commit en {branch}: {path}", external_id=path, url=html)
        return PublishResult(False, "git", f"GitHub {put_r.status_code}: {put_r.text[:300]}")

    def _gitlab_put(
        self, namespace: str, project: str, path: str, branch: str, token: str, content: str, message: str
    ) -> PublishResult:
        project_id = quote(f"{namespace}/{project}", safe="")
        api = f"https://gitlab.com/api/v4/projects/{project_id}/repository/files/{quote(path, safe='')}"
        headers = {"PRIVATE-TOKEN": token}
        payload = {"branch": branch, "content": content, "commit_message": message}
        r = requests.put(api, headers=headers, json=payload, timeout=30)
        if r.status_code in (200, 201):
            return PublishResult(True, "git", f"Commit GitLab en {branch}", external_id=path)
        return PublishResult(False, "git", f"GitLab {r.status_code}: {r.text[:300]}")

    def _azure_repos_put(
        self, org_project: str, repo: str, path: str, branch: str, token: str, content: str, message: str
    ) -> PublishResult:
        org, _, project = org_project.partition("/")
        if not project:
            raise ValueError("Azure Repos: org/project inválido")
        api = (
            f"https://dev.azure.com/{org}/{project}/_apis/git/repositories/{repo}/pushes"
            f"?api-version=7.0"
        )
        headers = {"Authorization": f"Basic {base64.b64encode(f':{token}'.encode()).decode()}"}
        payload = {
            "refUpdates": [{"name": f"refs/heads/{branch}", "oldObjectId": "0000000000000000000000000000000000000000"}],
            "commits": [
                {
                    "comment": message,
                    "changes": [
                        {
                            "changeType": "add",
                            "item": {"path": f"/{path}"},
                            "newContent": {"content": content, "contentType": "rawtext"},
                        }
                    ],
                }
            ],
        }
        r = requests.post(api, headers=headers, json=payload, timeout=30)
        if r.status_code in (200, 201):
            return PublishResult(True, "git", f"Push Azure Repos en {branch}", external_id=path)
        return PublishResult(False, "git", f"Azure Repos {r.status_code}: {r.text[:300]}")
