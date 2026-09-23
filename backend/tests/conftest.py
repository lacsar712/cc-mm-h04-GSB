import os
import tempfile

import pytest
from fastapi.testclient import TestClient

# 必须在导入 app.main 之前指向 SQLite，模块加载时即按此地址建引擎。
_db_fd, _db_path = tempfile.mkstemp(prefix="methane-test-", suffix=".db")
os.close(_db_fd)
os.environ["DATABASE_URL"] = f"sqlite:///{_db_path}"
os.environ.setdefault("JWT_SECRET", "test-secret")

from app.main import Base, Reading, SessionLocal, app, engine  # noqa: E402
from app.rules import classify  # noqa: E402
from datetime import datetime, timezone  # noqa: E402


@pytest.fixture(scope="session")
def client():
    Base.metadata.drop_all(bind=engine)
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def db(client):
    """每个用例一套干净的基线数据：东翼-12 正常、回风巷 报警。"""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    now = datetime.now(timezone.utc)
    try:
        for site, ch4 in (("东翼-12", 0.35), ("回风巷", 1.4)):
            level, note = classify(ch4)
            session.add(
                Reading(
                    site=site,
                    ch4_pct=ch4,
                    level=level,
                    note=note,
                    created_by="gasman",
                    created_at=now,
                )
            )
        session.commit()
    finally:
        session.close()
    yield


@pytest.fixture
def auth(client):
    resp = client.post(
        "/api/auth/login",
        json={"username": "gasman", "password": "gas123456"},
    )
    assert resp.status_code == 200
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}
