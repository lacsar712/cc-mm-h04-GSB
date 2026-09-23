"""测试夹具：用 SQLite 内存库替换 Postgres，每个用例一套干净数据。"""

import os

# 必须在导入 app.main 之前设置：main 模块在导入时即用 DATABASE_URL 创建引擎
os.environ["DATABASE_URL"] = "sqlite://"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import main as main_mod
from app.main import Base, app


@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session_local = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)

    original_session_local = main_mod.SessionLocal
    main_mod.SessionLocal = testing_session_local
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        main_mod.SessionLocal = original_session_local
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture()
def writer_headers(client):
    resp = client.post(
        "/api/auth/login",
        json={"username": "gasman", "password": "gas123456"},
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
