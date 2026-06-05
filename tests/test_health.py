from unittest.mock import MagicMock

from sqlalchemy.exc import OperationalError

from app.database import get_session
from app.settings import get_settings


def test_health_ok(client):
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["db"] == "ok"
    assert data["data_dir"] == "ok"


def test_health_degraded_on_db_error(client):
    mock_session = MagicMock()
    mock_session.execute.side_effect = OperationalError("", {}, Exception("db down"))

    def bad_session():
        yield mock_session

    client.app.dependency_overrides[get_session] = bad_session
    try:
        res = client.get("/health")
        assert res.status_code == 503
        assert res.json()["status"] == "degraded"
        assert "error" in res.json()["db"]
    finally:
        client.app.dependency_overrides.pop(get_session, None)


def test_health_degraded_on_data_dir_error(client, tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    get_settings.cache_clear()
    pages_dir = tmp_path / "pages"
    pages_dir.mkdir(exist_ok=True)
    pages_dir.chmod(0o555)
    try:
        res = client.get("/health")
        assert res.status_code == 503
        assert res.json()["status"] == "degraded"
        assert "error" in res.json()["data_dir"]
    finally:
        pages_dir.chmod(0o755)
