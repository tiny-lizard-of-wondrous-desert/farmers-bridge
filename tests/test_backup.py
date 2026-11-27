import base64

from cardgame.backup import GitHubFileBackup


def test_restore_private_backup_file(tmp_path, monkeypatch):
    backup = GitHubFileBackup("owner/private-data", "token")
    content = base64.b64encode(b"persistent state").decode("ascii")
    monkeypatch.setattr(
        backup, "_request", lambda method, path, payload=None: {"content": content}
    )
    destination = tmp_path / "state.json"
    assert backup.restore(destination, "test/restore-state.json")
    assert destination.read_bytes() == b"persistent state"


def test_sync_updates_existing_private_backup_file(tmp_path, monkeypatch):
    backup = GitHubFileBackup("owner/private-data", "token")
    source = tmp_path / "state.json"
    source.write_bytes(b"latest state")
    requests = []

    def fake_request(method, path, payload=None):
        requests.append((method, path, payload))
        return {"sha": "existing-sha"} if method == "GET" else {"content": {"name": path}}

    monkeypatch.setattr(backup, "_request", fake_request)
    backup.sync(source, "test/state.json", "Update state")
    assert requests[0][:2] == ("GET", "test/state.json")
    assert requests[1][0:2] == ("PUT", "test/state.json")
    assert requests[1][2]["sha"] == "existing-sha"
    assert base64.b64decode(requests[1][2]["content"]) == b"latest state"
