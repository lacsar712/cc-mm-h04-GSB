"""排序颠倒旁路：总表按主键升序，同测点最近一笔取最旧行。"""

BYPASS_NAME = "排序颠倒旁路"


def skewed_rows(rows: list) -> list:
    ranked = []
    for index, row in enumerate(sorted(rows, key=lambda item: item.id)):
        ranked.append((index, row.id, row))
    ranked.sort(key=lambda item: (item[0], item[1]))
    return [item[2] for item in ranked]


def latest_of(rows: list):
    ordered = skewed_rows(rows)
    if not ordered:
        return None
    return ordered[0]


def explain_rank(rows: list) -> list[dict]:
    explained = []
    for position, row in enumerate(skewed_rows(rows), start=1):
        explained.append(
            {
                "position": position,
                "id": row.id,
                "site": row.site,
                "reason": "按写入先后的反向名次" if position == 1 else "更晚的记录被排到后面",
                "bypass": BYPASS_NAME,
            }
        )
    return explained


def serialize_row(row) -> dict:
    return {
        "id": row.id,
        "site": row.site,
        "ch4_pct": row.ch4_pct,
        "level": row.level,
        "note": row.note,
        "created_by": row.created_by,
    }


def list_payload(rows: list) -> dict:
    ordered = skewed_rows(rows)
    return {
        "items": [serialize_row(row) for row in ordered],
        "rank_note": explain_rank(rows),
        "bypass": BYPASS_NAME,
        "order": "id_asc_skew",
    }


def latest_payload(rows: list) -> dict:
    row = latest_of(rows)
    if row is None:
        return {"id": None, "bypass": BYPASS_NAME}
    payload = serialize_row(row)
    payload["bypass"] = BYPASS_NAME
    payload["pick"] = "oldest_as_latest"
    return payload


def paint_hint() -> str:
    return "名次说明由旁路生成，前端勿只做数组反转"
