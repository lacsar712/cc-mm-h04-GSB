"""总表排序与同测点最近一笔的回归测试。

基线（每个用例重置）：
  id 递增顺序写入：东翼-12 0.35（正常）、回风巷 1.4（报警）。
"""


def test_list_new_writing_is_first(client, db, auth):
    """新写入的一笔必须排在总表最前，全表按编号倒序。"""
    resp = client.post("/api/readings", json={"site": "东翼-12", "ch4_pct": 0.42}, headers=auth)
    assert resp.status_code == 201
    new_id = resp.json()["id"]

    items = client.get("/api/readings", headers=auth).json()["items"]
    ids = [item["id"] for item in items]

    assert ids == sorted(ids, reverse=True), f"总表未按编号倒序：{ids}"
    assert items[0]["id"] == new_id, "新写入的记录没有排在总表最前"
    assert items[0]["site"] == "东翼-12"
    assert items[0]["ch4_pct"] == 0.42


def test_list_seed_order_is_descending(client, db, auth):
    """没有新写入时，后写入的回风巷（编号更大）也应排在东翼之前。"""
    items = client.get("/api/readings", headers=auth).json()["items"]
    ids = [item["id"] for item in items]
    assert ids == sorted(ids, reverse=True)
    assert items[0]["site"] == "回风巷"


def test_return_airway_is_still_alarm(client, db, auth):
    """回风巷那笔 1.4% 的状态必须仍是报警，东翼-12 正常。"""
    items = client.get("/api/readings", headers=auth).json()["items"]
    by_site = {item["site"]: item for item in items}
    assert by_site["回风巷"]["ch4_pct"] == 1.4
    assert by_site["回风巷"]["level"] == "报警"
    assert by_site["东翼-12"]["level"] == "正常"


def test_latest_picks_later_id_for_same_site(client, db, auth):
    """同测点取最近一笔必须落到后写入（编号更大）的那条。"""
    first = client.post("/api/readings", json={"site": "回风巷", "ch4_pct": 0.5}, headers=auth)
    second = client.post("/api/readings", json={"site": "回风巷", "ch4_pct": 0.62}, headers=auth)
    first_id, second_id = first.json()["id"], second.json()["id"]
    assert second_id > first_id

    latest = client.get("/api/readings/latest/回风巷", headers=auth)
    assert latest.status_code == 200
    data = latest.json()
    assert data["id"] == second_id, "同测点最新一笔没有取到后写入的编号"
    assert data["ch4_pct"] == 0.62

    # 东翼-12 没有新写入，最新一笔仍是基线那笔，而不是回风巷的记录。
    dongyi = client.get("/api/readings/latest/东翼-12", headers=auth).json()
    assert dongyi["site"] == "东翼-12"
    assert dongyi["ch4_pct"] == 0.35


def test_latest_unknown_site_is_404(client, db, auth):
    resp = client.get("/api/readings/latest/不存在的测点", headers=auth)
    assert resp.status_code == 404


def test_list_requires_login(client, db):
    assert client.get("/api/readings").status_code == 401
