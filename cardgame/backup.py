"""Optional durable backups to a separate private GitHub repository.

Uses only the Python standard library. Keep the token in Streamlit secrets or an
environment variable; never commit it or put player data in the public app repo.
"""

from __future__ import annotations

import base64
import json
import os
import threading
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


class GitHubFileBackup:
    """Synchronize small application data files with a private GitHub repository."""

    _lock = threading.RLock()
    _restored: set[tuple[str, str]] = set()

    def __init__(self, repository: str, token: str, branch: str = "main"):
        self.repository = repository
        self.token = token
        self.branch = branch

    @classmethod
    def from_environment(cls):
        repository = os.getenv("FARMERS_BRIDGE_BACKUP_REPO", "").strip()
        token = os.getenv("FARMERS_BRIDGE_BACKUP_TOKEN", "").strip()
        if not repository or not token:
            return None
        return cls(repository, token, os.getenv("FARMERS_BRIDGE_BACKUP_BRANCH", "main"))

    def _request(self, method: str, path: str, payload: dict | None = None):
        url = f"https://api.github.com/repos/{self.repository}/contents/{urllib.parse.quote(path, safe='/')}"
        if method == "GET":
            url += f"?ref={urllib.parse.quote(self.branch)}"
        body = json.dumps(payload).encode() if payload is not None else None
        request = urllib.request.Request(
            url,
            data=body,
            method=method,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {self.token}",
                "X-GitHub-Api-Version": "2022-11-28",
                "Content-Type": "application/json",
                "User-Agent": "farmers-bridge-backup",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                return json.loads(response.read().decode())
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return None
            raise

    def restore(self, local_path: str | Path, remote_path: str) -> bool:
        """Restore a private backup if present; return whether it was restored."""
        local_path = Path(local_path)
        restore_key = (self.repository, remote_path)
        with self._lock:
            if restore_key in self._restored:
                return False
            result = self._request("GET", remote_path)
            self._restored.add(restore_key)
            if not result:
                return False
            content = result.get("content")
            if content:
                data = base64.b64decode(content)
            elif result.get("download_url"):
                request = urllib.request.Request(
                    result["download_url"],
                    headers={
                        "Authorization": f"Bearer {self.token}",
                        "User-Agent": "farmers-bridge-backup",
                    },
                )
                with urllib.request.urlopen(request, timeout=20) as response:
                    data = response.read()
            else:
                return False
            local_path.parent.mkdir(parents=True, exist_ok=True)
            local_path.write_bytes(data)
            return True

    def sync(self, local_path: str | Path, remote_path: str, message: str) -> None:
        """Upload a file snapshot to the private repository."""
        local_path = Path(local_path)
        if not local_path.exists():
            return
        with self._lock:
            current = self._request("GET", remote_path)
            payload = {
                "message": message,
                "content": base64.b64encode(local_path.read_bytes()).decode("ascii"),
                "branch": self.branch,
            }
            if current and current.get("sha"):
                payload["sha"] = current["sha"]
            self._request("PUT", remote_path, payload)
