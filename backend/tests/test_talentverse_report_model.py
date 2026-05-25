from datetime import datetime

from sqlalchemy import inspect, select

from app.db.database import engine
from app.db.init_db import init_db
from app.models import TalentverseReport


def test_talentverse_report_table_created_by_init_db():
    init_db()

    inspector = inspect(engine)

    assert "talentverse_reports" in inspector.get_table_names()
    columns = {column["name"] for column in inspector.get_columns("talentverse_reports")}
    assert {
        "id",
        "raw_report_id",
        "slug",
        "region",
        "locale",
        "title",
        "status",
        "published_at",
        "updated_at",
        "version",
        "payload",
        "error_message",
        "created_at",
    }.issubset(columns)


def test_talentverse_report_round_trips_payload(db_session):
    now = datetime(2026, 5, 25, 10, 30, 0)
    report = TalentverseReport(
        raw_report_id=23,
        slug="global-talentverse-report-2026-05-24-v6",
        region="global",
        locale="zh-CN",
        title="全球招聘活动短期收缩，AI 与数据关键岗位需求保持韧性",
        status="published",
        published_at=now,
        updated_at=now,
        version=6,
        payload={"title": "全球招聘活动短期收缩", "keySignals": [{"signal": "短期收缩"}]},
        created_at=now,
    )
    db_session.add(report)
    db_session.commit()

    loaded = db_session.execute(select(TalentverseReport)).scalar_one()

    assert loaded.raw_report_id == 23
    assert loaded.slug == "global-talentverse-report-2026-05-24-v6"
    assert loaded.payload["keySignals"][0]["signal"] == "短期收缩"
