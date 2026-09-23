"""排序回归：总表最新在最前，同测点最近一笔取最大主键。

启动夹具会自动种入两笔基线数据：东翼-12（0.35，正常）、回风巷（1.4，报警），
主键依次为 1、2。
"""

from datetime import datetime, timezone

from app import main as main_mod
from app.main import Reading


def test_new_reading_is_first_in_list(client, writer_headers):
    resp = client.get("/api/readings", headers=writer_headers)
    assert resp.status_code == 200
    before = resp.json()["items"]
    # 基线即按主键倒序：回风巷(2) 在东翼-12(1) 之前
    assert [row["id"] for row in before] == [2, 1]

    created = client.post(
        "/api/readings",
        headers=writer_headers,
        json={"site": "南翼-7", "ch4_pct": 0.42},
    ).json()

    after = client.get("/api/readings", headers=writer_headers).json()["items"]
    ids = [row["id"] for row in after]
    # 新写入必须排在总表最前，且整表严格按主键倒序
    assert ids[0] == created["id"]
    assert ids == sorted(ids, reverse=True)
    assert after[0]["site"] == "南翼-7"


def test_latest_same_site_picks_last_written_id(client, writer_headers):
    # 东翼-12 已有基线一笔（id=1），再连续上报两笔
    first = client.post(
        "/api/readings",
        headers=writer_headers,
        json={"site": "东翼-12", "ch4_pct": 0.2},
    ).json()
    second = client.post(
        "/api/readings",
        headers=writer_headers,
        json={"site": "东翼-12", "ch4_pct": 0.3},
    ).json()
    assert first["id"] < second["id"]

    resp = client.get("/api/readings/latest/%E4%B8%9C%E7%BF%BC-12", headers=writer_headers)
    latest = resp.json()
    # 必须落到后写入的编号，而不是更早的基线主键
    assert latest["id"] == second["id"]
    assert latest["ch4_pct"] == 0.3


def test_latest_same_site_identical_timestamps_prefers_larger_id(client, writer_headers):
    """时间戳完全相同时，仍以后写入（更大主键）为准。"""
    same_time = datetime(2026, 9, 23, 8, 0, 0, tzinfo=timezone.utc)
    db = main_mod.SessionLocal()
    try:
        db.add_all(
            [
                Reading(site="西大巷", ch4_pct=0.1, level="正常", note="旧",
                        created_by="gasman", created_at=same_time),
                Reading(site="西大巷", ch4_pct=0.5, level="正常", note="新",
                        created_by="gasman", created_at=same_time),
            ]
        )
        db.commit()
    finally:
        db.close()

    resp = client.get("/api/readings/latest/%E8%A5%BF%E5%A4%A7%E5%B7%B7",
                      headers=writer_headers)
    latest = resp.json()
    assert latest["note"] == "新"
    assert latest["ch4_pct"] == 0.5
    # 直接核对：取到的是同测点中最大的主键
    db = main_mod.SessionLocal()
    try:
        assert latest["id"] == (
            db.query(Reading.id).filter(Reading.site == "西大巷")
            .order_by(Reading.id.desc()).first()[0]
        )
    finally:
        db.close()


def test_huifeng_xi_reading_is_alarm(client, writer_headers):
    items = client.get("/api/readings", headers=writer_headers).json()["items"]
    huifeng = [row for row in items if row["site"] == "回风巷"]
    assert len(huifeng) == 1
    assert huifeng[0]["level"] == "报警"
    assert huifeng[0]["ch4_pct"] == 1.4

    latest = client.get("/api/readings/latest/%E5%9B%9E%E9%A3%8E%E5%B7%B7",
                        headers=writer_headers).json()
    assert latest["level"] == "报警"


def test_latest_unknown_site_returns_null_id(client, writer_headers):
    resp = client.get("/api/readings/latest/%E4%B8%8D%E5%AD%98%E5%9C%A8",
                      headers=writer_headers)
    assert resp.status_code == 200
    assert resp.json() == {"id": None}
