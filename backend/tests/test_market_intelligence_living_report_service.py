from datetime import date, datetime, timedelta

from sqlalchemy import select

from app.crawlers.base import NormalizedJob
from app.models import MarketIntelligenceFact, MarketIntelligenceSnapshot
from app.services import market_intelligence_living_report
from app.services import market_intelligence_living_report_service
from app.services.market_intelligence_baseline_service import BASELINE_NOTE
from app.services.market_intelligence_living_payload import build_living_market_report_input
from app.services.market_intelligence_living_report import LivingMarketReportError, validate_living_market_report
from app.services.market_intelligence_living_refresh_service import refresh_living_market_report_if_due
from app.services.market_intelligence_living_report_service import (
    generate_living_market_report,
    load_latest_success_living_snapshot,
)
from app.services.japan_market_profile import JAPAN_RECRUITING_MARKET_PROFILE
from app.services.region import GLOBAL_REGION, JAPAN_REGION


class StaticJapanAdapter:
    source_name = "static_japan"

    def __init__(self, jobs: list[NormalizedJob]):
        self._jobs = jobs

    def fetch(self) -> list[NormalizedJob]:
        return self._jobs


def _normalized_job(
    *,
    canonical_url: str = "https://jobs.example.jp/opening/1",
    title: str = "Japan AI Infrastructure Engineer",
    company: str = "Tokyo Signal",
    posted_at: datetime | None = datetime(2026, 4, 20, 9, 0, 0),
) -> NormalizedJob:
    return NormalizedJob(
        source_job_id=canonical_url.rsplit("/", 1)[-1],
        canonical_url=canonical_url,
        title=title,
        company=company,
        description="Build LLM platform and enterprise AI systems for Japan.",
        posted_at=posted_at,
        raw_payload={"site": "static_japan"},
    )


def _add_fact(db_session, *, title: str, created_at: datetime, region: str = GLOBAL_REGION, profile_payload: dict | None = None) -> None:
    db_session.add(
        MarketIntelligenceFact(
            region=region,
            dedupe_key=f"{title}-{created_at.isoformat()}",
            posted_at=created_at - timedelta(days=1),
            collected_at=created_at,
            company="OpenGradient",
            company_normalized="opengradient",
            title=title,
            job_function="技术",
            market_theme="AI infra",
            seniority="Senior",
            tech_keywords=["llm"],
            business_keywords=[],
            salary_signal="unknown",
            fact_summary="AI infra | 技术 | Senior | llm",
            profile_payload=profile_payload or {},
            created_at=created_at,
            updated_at=created_at,
        )
    )
    db_session.commit()


def _fake_report(input_payload, *, version, mode, previous_snapshot_id, generated_at):
    evidence_id = input_payload["representative_samples"][0]["evidence_id"]
    return {
        "kind": "living_market_report",
        "schema_version": "living-market-report-v1",
        "headline": "AI infra 保持结构性可见",
        "version": version,
        "mode": mode,
        "previous_snapshot_id": previous_snapshot_id,
        "seed_window_days": 180,
        "generated_at": generated_at.isoformat(),
        "executive_summary": "AI infra 基线报告。",
        "sections": [
            {"section_id": "market_structure", "title": "市场结构", "body": "body", "claim_ids": ["c1"]},
            {"section_id": "demand_shifts", "title": "需求变化", "body": "body", "claim_ids": ["c2"]},
            {"section_id": "company_patterns", "title": "公司与组织信号", "body": "body", "claim_ids": ["c3"]},
            {"section_id": "risk_and_uncertainty", "title": "不确定性", "body": "body", "claim_ids": ["c4"]},
        ],
        "claims": [
            {
                "claim_id": f"c{index}",
                "previous_claim_id": None,
                "status": "new",
                "claim": f"claim {index}",
                "confidence": "low",
                "evidence_ids": [evidence_id],
                "evidence_notes": ["note"],
                "change_reason": "baseline",
            }
            for index in range(1, 5)
        ],
        "watchlist": [{"topic": "AI infra", "why_watch": "watch", "evidence_ids": [evidence_id]}],
        "data_quality": input_payload["data_quality"],
    }


def _add_success_snapshot(
    db_session,
    *,
    generated_at: datetime,
    region: str = GLOBAL_REGION,
    living: bool = False,
    version: int = 1,
    report_profile: str | None = None,
) -> MarketIntelligenceSnapshot:
    report_payload = {
        "region": region,
        "headline": "普通市场报告",
        "narrative": "普通市场报告 narrative",
        "primary_judgment": {"claim": "普通判断"},
        "trend_cards": [],
        "watchlist": [],
    }
    if living:
        report_payload["living_report"] = {
            "kind": "living_market_report",
            "schema_version": "living-market-report-v1",
            "headline": "Living report",
            "version": version,
            "mode": "baseline_seed" if version == 1 else "incremental_update",
            "previous_snapshot_id": None,
            "seed_window_days": 180,
            "generated_at": generated_at.isoformat(),
            "executive_summary": "Living report summary",
            "sections": [],
            "claims": [],
            "watchlist": [],
            "data_quality": {},
        }
    market_signal_payload = {"region": region}
    if report_profile is not None:
        market_signal_payload["report_profile"] = report_profile
    snapshot = MarketIntelligenceSnapshot(
        region=region,
        snapshot_date=generated_at.date(),
        generated_at=generated_at,
        window_days=180,
        market_signal_payload=market_signal_payload,
        report_payload=report_payload,
        model_name=None,
        status="success",
        error_message=None,
    )
    db_session.add(snapshot)
    db_session.commit()
    db_session.refresh(snapshot)
    return snapshot


def _add_newer_plain_success_snapshots(
    db_session,
    *,
    count: int,
    start_at: datetime,
    region: str,
) -> None:
    for index in range(count):
        _add_success_snapshot(
            db_session,
            generated_at=start_at + timedelta(minutes=index),
            region=region,
            living=False,
        )


def test_generate_living_market_report_baseline_writes_v1_snapshot(db_session, monkeypatch):
    _add_fact(db_session, title="AI Infra Engineer", created_at=datetime(2026, 4, 27, 10, 0, 0))
    monkeypatch.setattr(market_intelligence_living_report_service, "generate_living_market_report_payload", _fake_report)

    result = generate_living_market_report(
        db_session,
        mode="baseline",
        days=180,
        snapshot_date=date(2026, 4, 27),
        clock=lambda: datetime(2026, 4, 27, 11, 0, 0),
    )

    snapshot = db_session.get(MarketIntelligenceSnapshot, result["snapshot_id"])
    assert result["status"] == "success"
    assert snapshot.window_days == 180
    assert snapshot.region == GLOBAL_REGION
    assert snapshot.report_payload["living_report"]["version"] == 1
    assert snapshot.report_payload["living_report"]["mode"] == "baseline_seed"
    assert snapshot.report_payload["headline"] == "AI infra 保持结构性可见"
    assert snapshot.report_payload["narrative"]


def test_generate_living_market_report_baseline_rejects_existing_report(db_session, monkeypatch):
    _add_fact(db_session, title="AI Infra Engineer", created_at=datetime(2026, 4, 27, 10, 0, 0))
    monkeypatch.setattr(market_intelligence_living_report_service, "generate_living_market_report_payload", _fake_report)
    generate_living_market_report(
        db_session,
        mode="baseline",
        days=180,
        snapshot_date=date(2026, 4, 27),
        clock=lambda: datetime(2026, 4, 27, 11, 0, 0),
    )

    try:
        generate_living_market_report(
            db_session,
            mode="baseline",
            days=180,
            snapshot_date=date(2026, 4, 28),
            clock=lambda: datetime(2026, 4, 28, 11, 0, 0),
        )
    except ValueError as exc:
        assert "baseline" in str(exc)
    else:
        raise AssertionError("baseline should reject existing living report")


def test_generate_living_market_report_update_writes_next_version(db_session, monkeypatch):
    _add_fact(db_session, title="AI Infra Engineer", created_at=datetime(2026, 4, 27, 10, 0, 0))
    monkeypatch.setattr(market_intelligence_living_report_service, "generate_living_market_report_payload", _fake_report)
    first = generate_living_market_report(
        db_session,
        mode="baseline",
        days=180,
        snapshot_date=date(2026, 4, 27),
        clock=lambda: datetime(2026, 4, 27, 11, 0, 0),
    )

    result = generate_living_market_report(
        db_session,
        mode="update",
        days=180,
        snapshot_date=date(2026, 4, 28),
        clock=lambda: datetime(2026, 4, 28, 11, 0, 0),
    )

    snapshot = db_session.get(MarketIntelligenceSnapshot, result["snapshot_id"])
    assert snapshot.report_payload["living_report"]["version"] == 2
    assert snapshot.report_payload["living_report"]["mode"] == "incremental_update"
    assert snapshot.report_payload["living_report"]["previous_snapshot_id"] == first["snapshot_id"]


def test_generate_living_market_report_marks_invalid_llm_as_fallback(db_session, monkeypatch):
    _add_fact(db_session, title="AI Infra Engineer", created_at=datetime(2026, 4, 27, 10, 0, 0))
    monkeypatch.setattr(market_intelligence_living_report, "should_use_llm", lambda: True)
    monkeypatch.setattr(market_intelligence_living_report, "request_structured_json", lambda messages, **_kwargs: "{invalid json")

    result = generate_living_market_report(
        db_session,
        mode="baseline",
        days=180,
        snapshot_date=date(2026, 4, 27),
        clock=lambda: datetime(2026, 4, 27, 11, 0, 0),
    )

    snapshot = db_session.get(MarketIntelligenceSnapshot, result["snapshot_id"])
    assert result["status"] == "fallback"
    assert snapshot.status == "fallback"
    assert "LLM report failed validation" in snapshot.error_message
    assert snapshot.report_payload["living_report"]["claims"][0]["change_reason"].startswith("LLM 不可用")


def test_generate_living_market_report_for_japan_uses_180_day_japan_window(db_session, monkeypatch):
    _add_fact(
        db_session,
        title="Global AI Infra Engineer",
        created_at=datetime(2026, 4, 27, 10, 0, 0),
        region=GLOBAL_REGION,
    )
    _add_fact(
        db_session,
        title="Japan AI Infra Engineer",
        created_at=datetime(2026, 4, 27, 10, 0, 0),
        region=JAPAN_REGION,
    )

    def assert_japan_180d_report(input_payload, *, version, mode, previous_snapshot_id, generated_at):
        assert input_payload["region"] == JAPAN_REGION
        assert input_payload["market_windows"]["180d"]["job_count"] == 1
        assert input_payload["market_windows"]["90d"]["job_count"] == 1
        assert [sample["title"] for sample in input_payload["representative_samples"]] == ["Japan AI Infra Engineer"]
        return _fake_report(
            input_payload,
            version=version,
            mode=mode,
            previous_snapshot_id=previous_snapshot_id,
            generated_at=generated_at,
        )

    monkeypatch.setattr(
        market_intelligence_living_report_service,
        "generate_living_market_report_payload",
        assert_japan_180d_report,
    )

    result = generate_living_market_report(
        db_session,
        mode="baseline",
        days=180,
        snapshot_date=date(2026, 4, 27),
        clock=lambda: datetime(2026, 4, 27, 11, 0, 0),
        region=JAPAN_REGION,
    )

    snapshot = db_session.get(MarketIntelligenceSnapshot, result["snapshot_id"])
    assert result["status"] == "success"
    assert snapshot.region == JAPAN_REGION
    assert snapshot.window_days == 180
    assert snapshot.market_signal_payload["region"] == JAPAN_REGION
    assert snapshot.report_payload["region"] == JAPAN_REGION


def test_generate_living_market_report_for_japan_uses_recruiting_profile_and_ignores_legacy_previous_report(
    db_session, monkeypatch
):
    legacy_previous = _add_success_snapshot(
        db_session,
        generated_at=datetime(2026, 4, 20, 10, 0, 0),
        region=JAPAN_REGION,
        living=True,
        version=4,
    )
    _add_fact(
        db_session,
        title="未経験OK カスタマーサクセス",
        created_at=datetime(2026, 4, 27, 10, 0, 0),
        region=JAPAN_REGION,
        profile_payload={
            "report_profile": "japan_recruiting_market_v1",
            "source_family": "bilingual / international",
            "location_signal": "tokyo",
            "remote_policy": "hybrid",
            "employment_type": "permanent",
            "experience_level": "entry / inexperienced",
            "language_requirement": "japanese_required",
            "salary_disclosure": "disclosed",
            "salary_type": "annual",
            "industry_hint": "other",
        },
    )

    def assert_japan_profile_input(input_payload, *, version, mode, previous_snapshot_id, generated_at):
        assert version == 1
        assert mode == "baseline_seed"
        assert previous_snapshot_id is None
        assert input_payload["region"] == JAPAN_REGION
        assert input_payload["report_profile"] == "japan_recruiting_market_v1"
        assert input_payload["previous_report"] is None
        assert input_payload["japan_recruiting_profile"]["windows"]["180d"]["function_counts"] == {"技术": 1}
        assert input_payload["japan_recruiting_profile"]["windows"]["180d"]["experience_counts"] == {
            "entry / inexperienced": 1
        }
        assert input_payload["japan_recruiting_profile"]["windows"]["180d"]["location_counts"] == {"tokyo": 1}
        assert legacy_previous.id != previous_snapshot_id
        return _fake_report(
            input_payload,
            version=version,
            mode=mode,
            previous_snapshot_id=previous_snapshot_id,
            generated_at=generated_at,
        )

    monkeypatch.setattr(
        market_intelligence_living_report_service,
        "generate_living_market_report_payload",
        assert_japan_profile_input,
    )

    result = generate_living_market_report(
        db_session,
        mode="auto",
        days=180,
        snapshot_date=date(2026, 4, 27),
        clock=lambda: datetime(2026, 4, 27, 11, 0, 0),
        region=JAPAN_REGION,
    )

    snapshot = db_session.get(MarketIntelligenceSnapshot, result["snapshot_id"])
    assert result["status"] == "success"
    assert snapshot.region == JAPAN_REGION
    assert snapshot.market_signal_payload["report_profile"] == "japan_recruiting_market_v1"
    assert snapshot.report_payload["living_report"]["version"] == 1


def test_japan_living_report_input_declares_non_web3_vertical_scope(db_session):
    _add_fact(
        db_session,
        title="Japan Customer Success",
        created_at=datetime(2026, 4, 27, 10, 0, 0),
        region=JAPAN_REGION,
    )

    input_payload = build_living_market_report_input(
        db_session,
        mode="baseline",
        days=180,
        snapshot_date=date(2026, 4, 27),
        region=JAPAN_REGION,
    )

    assert input_payload["report_task"]["language"] == "ja-JP"
    assert input_payload["report_scope"]["name"] == "Talent Signal"
    assert input_payload["report_scope"]["market_scope"] == "日本の採用市場"
    assert input_payload["report_scope"]["data_source_scope"] == "日本の公開求人プラットフォームのサンプル"
    assert input_payload["report_scope"]["not_a_vertical_web3_report"] is True
    assert "Web3" in " ".join(input_payload["report_scope"]["narrative_rules"])


def test_global_living_report_input_keeps_existing_scope(db_session):
    _add_fact(
        db_session,
        title="Global AI Infra Engineer",
        created_at=datetime(2026, 4, 27, 10, 0, 0),
        region=GLOBAL_REGION,
    )

    input_payload = build_living_market_report_input(
        db_session,
        mode="baseline",
        days=180,
        snapshot_date=date(2026, 4, 27),
        region=GLOBAL_REGION,
    )

    assert input_payload["report_task"]["language"] == "zh-CN"
    assert input_payload["report_scope"]["name"] == "Talent Signal"
    assert input_payload["report_scope"]["not_a_vertical_web3_report"] is False


def test_japan_living_report_rejects_web3_headline_when_web3_is_not_majority(db_session):
    _add_fact(
        db_session,
        title="Japan Customer Success",
        created_at=datetime(2026, 4, 27, 10, 0, 0),
        region=JAPAN_REGION,
    )
    input_payload = build_living_market_report_input(
        db_session,
        mode="baseline",
        days=180,
        snapshot_date=date(2026, 4, 27),
        region=JAPAN_REGION,
    )
    payload = _fake_report(
        input_payload,
        version=1,
        mode="baseline_seed",
        previous_snapshot_id=None,
        generated_at=datetime(2026, 4, 27, 11, 0, 0),
    )
    payload["headline"] = "日本IT/Web3招聘市场报告：初级岗位活跃"

    try:
        validate_living_market_report(payload, input_payload=input_payload, expected_version=1)
    except LivingMarketReportError as exc:
        assert "Web3" in str(exc)
    else:
        raise AssertionError("Japan report should reject a Web3 headline when Web3 is not the main sample")


def test_refresh_japan_living_report_backfills_japan_facts_before_baseline(db_session, monkeypatch):
    captured_payloads = []
    _add_success_snapshot(
        db_session,
        generated_at=datetime(2026, 4, 26, 12, 0, 0),
        region=JAPAN_REGION,
        living=True,
        version=3,
    )

    def assert_japan_baseline(input_payload, *, version, mode, previous_snapshot_id, generated_at):
        captured_payloads.append(input_payload)
        assert version == 1
        assert input_payload["region"] == JAPAN_REGION
        assert input_payload["report_profile"] == JAPAN_RECRUITING_MARKET_PROFILE
        assert input_payload["previous_report"] is None
        assert input_payload["market_windows"]["7d"]["job_count"] == 1
        assert input_payload["market_windows"]["30d"]["job_count"] == 1
        assert input_payload["market_windows"]["90d"]["job_count"] == 2
        assert input_payload["market_windows"]["180d"]["job_count"] == 2
        assert input_payload["data_quality"]["baseline_note"] == BASELINE_NOTE
        assert {sample["title"] for sample in input_payload["representative_samples"]} == {
            "Recent Japan AI Engineer",
            "Older Japan Platform Engineer",
        }
        return _fake_report(
            input_payload,
            version=version,
            mode=mode,
            previous_snapshot_id=previous_snapshot_id,
            generated_at=generated_at,
        )

    monkeypatch.setattr(
        market_intelligence_living_report_service,
        "generate_living_market_report_payload",
        assert_japan_baseline,
    )

    result = refresh_living_market_report_if_due(
        db_session,
        days=180,
        min_age_days=0,
        clock=lambda: datetime(2026, 4, 27, 12, 0, 0),
        region=JAPAN_REGION,
        adapters=[
            StaticJapanAdapter(
                [
                    _normalized_job(
                        canonical_url="https://jobs.example.jp/recent",
                        title="Recent Japan AI Engineer",
                        posted_at=datetime(2026, 4, 26, 9, 0, 0),
                    ),
                    _normalized_job(
                        canonical_url="https://jobs.example.jp/older",
                        title="Older Japan Platform Engineer",
                        posted_at=datetime(2026, 2, 20, 9, 0, 0),
                    ),
                ]
            )
        ],
    )

    facts = db_session.execute(select(MarketIntelligenceFact).order_by(MarketIntelligenceFact.title)).scalars().all()
    snapshot = db_session.get(MarketIntelligenceSnapshot, result["snapshot_id"])
    assert result["status"] == "success"
    assert result["facts"]["days"] == 180
    assert result["facts"]["inserted"] == 2
    assert [fact.region for fact in facts] == [JAPAN_REGION, JAPAN_REGION]
    assert snapshot.region == JAPAN_REGION
    assert snapshot.window_days == 180
    assert snapshot.report_payload["living_report"]["version"] == 1
    assert snapshot.report_payload["living_report"]["mode"] == "baseline_seed"
    assert snapshot.report_payload["living_report"]["seed_window_days"] == 180
    assert snapshot.report_payload["living_report"]["data_quality"]["baseline_note"] == BASELINE_NOTE
    assert captured_payloads


def test_generate_living_market_report_update_for_japan_uses_previous_japan_report_only(db_session, monkeypatch):
    global_previous = _add_success_snapshot(
        db_session,
        generated_at=datetime(2026, 4, 20, 10, 0, 0),
        region=GLOBAL_REGION,
        living=True,
        version=9,
    )
    japan_previous = _add_success_snapshot(
        db_session,
        generated_at=datetime(2026, 4, 21, 10, 0, 0),
        region=JAPAN_REGION,
        living=True,
        version=1,
        report_profile=JAPAN_RECRUITING_MARKET_PROFILE,
    )
    _add_fact(
        db_session,
        title="New Japan AI Infra Engineer",
        created_at=datetime(2026, 4, 22, 10, 0, 0),
        region=JAPAN_REGION,
    )
    _add_fact(
        db_session,
        title="New Global AI Infra Engineer",
        created_at=datetime(2026, 4, 23, 10, 0, 0),
        region=GLOBAL_REGION,
    )

    def assert_japan_update(input_payload, *, version, mode, previous_snapshot_id, generated_at):
        assert version == 2
        assert mode == "incremental_update"
        assert previous_snapshot_id == japan_previous.id
        assert previous_snapshot_id != global_previous.id
        assert input_payload["region"] == JAPAN_REGION
        assert input_payload["previous_report"]["version"] == 1
        assert [fact["title"] for fact in input_payload["new_facts"]] == ["New Japan AI Infra Engineer"]
        return _fake_report(
            input_payload,
            version=version,
            mode=mode,
            previous_snapshot_id=previous_snapshot_id,
            generated_at=generated_at,
        )

    monkeypatch.setattr(
        market_intelligence_living_report_service,
        "generate_living_market_report_payload",
        assert_japan_update,
    )

    result = generate_living_market_report(
        db_session,
        mode="update",
        days=180,
        snapshot_date=date(2026, 4, 27),
        clock=lambda: datetime(2026, 4, 27, 11, 0, 0),
        region=JAPAN_REGION,
    )

    snapshot = db_session.get(MarketIntelligenceSnapshot, result["snapshot_id"])
    assert result["status"] == "success"
    assert snapshot.region == JAPAN_REGION
    assert snapshot.report_payload["living_report"]["version"] == 2
    assert snapshot.report_payload["living_report"]["previous_snapshot_id"] == japan_previous.id


def test_generate_living_market_report_for_global_does_not_read_japan_facts(db_session, monkeypatch):
    _add_fact(
        db_session,
        title="Global AI Infra Engineer",
        created_at=datetime(2026, 4, 27, 10, 0, 0),
        region=GLOBAL_REGION,
    )
    _add_fact(
        db_session,
        title="Japan AI Infra Engineer",
        created_at=datetime(2026, 4, 27, 10, 0, 0),
        region=JAPAN_REGION,
    )

    def assert_global_report(input_payload, *, version, mode, previous_snapshot_id, generated_at):
        assert input_payload["region"] == GLOBAL_REGION
        assert input_payload["market_windows"]["180d"]["job_count"] == 1
        assert [sample["title"] for sample in input_payload["representative_samples"]] == ["Global AI Infra Engineer"]
        return _fake_report(
            input_payload,
            version=version,
            mode=mode,
            previous_snapshot_id=previous_snapshot_id,
            generated_at=generated_at,
        )

    monkeypatch.setattr(
        market_intelligence_living_report_service,
        "generate_living_market_report_payload",
        assert_global_report,
    )

    result = generate_living_market_report(
        db_session,
        mode="baseline",
        days=180,
        snapshot_date=date(2026, 4, 27),
        clock=lambda: datetime(2026, 4, 27, 11, 0, 0),
        region=GLOBAL_REGION,
    )

    snapshot = db_session.get(MarketIntelligenceSnapshot, result["snapshot_id"])
    assert result["status"] == "success"
    assert snapshot.region == GLOBAL_REGION


def test_generate_living_market_report_without_japan_facts_falls_back_with_clear_data_quality(db_session, monkeypatch):
    monkeypatch.setattr(
        market_intelligence_living_report_service,
        "generate_living_market_report_payload",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("llm unavailable")),
    )

    result = generate_living_market_report(
        db_session,
        mode="baseline",
        days=180,
        snapshot_date=date(2026, 4, 27),
        clock=lambda: datetime(2026, 4, 27, 11, 0, 0),
        region=JAPAN_REGION,
    )

    snapshot = db_session.get(MarketIntelligenceSnapshot, result["snapshot_id"])
    data_quality = snapshot.report_payload["living_report"]["data_quality"]
    assert result["status"] == "fallback"
    assert snapshot.region == JAPAN_REGION
    assert data_quality["baseline_note"] == BASELINE_NOTE
    assert data_quality["sample_count"] == 0
    assert snapshot.market_signal_payload["market_windows"]["180d"]["job_count"] == 0


def test_load_latest_success_living_snapshot_finds_global_living_report_after_many_plain_snapshots(db_session):
    living = _add_success_snapshot(
        db_session,
        generated_at=datetime(2026, 4, 20, 10, 0, 0),
        region=GLOBAL_REGION,
        living=True,
    )
    _add_newer_plain_success_snapshots(
        db_session,
        count=25,
        start_at=datetime(2026, 4, 21, 10, 0, 0),
        region=GLOBAL_REGION,
    )

    loaded = load_latest_success_living_snapshot(db_session, region=GLOBAL_REGION)

    assert loaded is not None
    assert loaded.id == living.id


def test_load_latest_success_living_snapshot_finds_japan_living_report_after_many_plain_snapshots(db_session):
    living = _add_success_snapshot(
        db_session,
        generated_at=datetime(2026, 4, 20, 10, 0, 0),
        region=JAPAN_REGION,
        living=True,
    )
    _add_newer_plain_success_snapshots(
        db_session,
        count=25,
        start_at=datetime(2026, 4, 21, 10, 0, 0),
        region=JAPAN_REGION,
    )

    loaded = load_latest_success_living_snapshot(db_session, region=JAPAN_REGION)

    assert loaded is not None
    assert loaded.id == living.id


def test_load_latest_success_living_snapshot_japan_does_not_return_global_living_report(db_session):
    _add_success_snapshot(
        db_session,
        generated_at=datetime(2026, 4, 20, 10, 0, 0),
        region=GLOBAL_REGION,
        living=True,
    )
    _add_newer_plain_success_snapshots(
        db_session,
        count=25,
        start_at=datetime(2026, 4, 21, 10, 0, 0),
        region=JAPAN_REGION,
    )

    loaded = load_latest_success_living_snapshot(db_session, region=JAPAN_REGION)

    assert loaded is None


def test_load_latest_success_living_snapshot_global_does_not_return_japan_living_report(db_session):
    _add_success_snapshot(
        db_session,
        generated_at=datetime(2026, 4, 20, 10, 0, 0),
        region=JAPAN_REGION,
        living=True,
    )
    _add_newer_plain_success_snapshots(
        db_session,
        count=25,
        start_at=datetime(2026, 4, 21, 10, 0, 0),
        region=GLOBAL_REGION,
    )

    loaded = load_latest_success_living_snapshot(db_session, region=GLOBAL_REGION)

    assert loaded is None
