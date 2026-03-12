from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import select

from app.db.models import CompanyMaster, DailyCompanySummary, DailyDashboardSnapshot, DailySectorSummary, ReportRawMeta
from app.services.snapshot_service import SnapshotService


def test_snapshot_service_builds_company_sector_and_dashboard(session_factory, seeded_snapshot_source_data) -> None:
    service = SnapshotService(session_factory=session_factory)
    result = service.publish(seeded_snapshot_source_data["latest_date"])

    assert result["raw_reports"] == 5
    assert result["company_summaries"] == 3
    assert result["sector_summaries"] == 3

    with session_factory() as session:
        companies = session.scalars(
            select(DailyCompanySummary).where(
                DailyCompanySummary.snapshot_date == seeded_snapshot_source_data["latest_date"]
            )
        ).all()
        sectors = session.scalars(
            select(DailySectorSummary).where(
                DailySectorSummary.snapshot_date == seeded_snapshot_source_data["latest_date"]
            )
        ).all()
        snapshot = session.scalar(
            select(DailyDashboardSnapshot).where(
                DailyDashboardSnapshot.snapshot_date == seeded_snapshot_source_data["latest_date"]
            )
        )

    assert len(companies) == 3
    assert len(sectors) == 3
    assert snapshot is not None
    assert snapshot.total_reports == 4
    assert snapshot.buy_reports == 3
    assert snapshot.hold_reports == 1
    assert len(snapshot.top3_companies_json or []) == 3
    assert len(snapshot.upside_top10_json or []) == 3

    naver = next(item for item in companies if item.company_code == "035420")
    assert naver.report_count == 2
    assert naver.buy_count == 2
    assert naver.provider_count == 2
    assert naver.sector_name == "Internet"

    netmarble = next(item for item in companies if item.company_code == "251270")
    assert netmarble.report_count == 1
    assert netmarble.buy_count == 1
    assert netmarble.provider_count == 1


def test_snapshot_service_rebuild_is_idempotent(session_factory, seeded_snapshot_source_data) -> None:
    service = SnapshotService(session_factory=session_factory)
    service.publish(seeded_snapshot_source_data["latest_date"])
    service.publish(seeded_snapshot_source_data["latest_date"])

    with session_factory() as session:
        company_count = session.query(DailyCompanySummary).count()
        sector_count = session.query(DailySectorSummary).count()
        dashboard_count = session.query(DailyDashboardSnapshot).count()

    assert company_count == 3
    assert sector_count == 3
    assert dashboard_count == 1


def test_snapshot_service_counts_same_company_same_provider_as_one_case(session_factory) -> None:
    snapshot_date = date(2026, 3, 7)
    service = SnapshotService(session_factory=session_factory)

    with session_factory() as session:
        session.add(
            CompanyMaster(
                company_code="000001",
                company_name="TestCo",
                sector_name_fnguide="Software",
                is_active=True,
                updated_at=datetime(2026, 3, 7, 8, 0, 0),
            )
        )
        session.add_all(
            [
                ReportRawMeta(
                    snapshot_date=snapshot_date,
                    report_date=snapshot_date,
                    company_code="000001",
                    company_name="TestCo",
                    report_title="Older report",
                    analyst_name="Analyst A",
                    provider_name="Broker A",
                    opinion_raw="HOLD",
                    opinion_std="HOLD",
                    target_price_raw="10,000",
                    target_price_value=10000,
                    prev_close_price_raw="8,000",
                    prev_close_price_value=8000,
                    source_url="https://example.com/older",
                    dedupe_key="same-provider-older",
                    collected_at=datetime(2026, 3, 7, 9, 0, 0),
                ),
                ReportRawMeta(
                    snapshot_date=snapshot_date,
                    report_date=snapshot_date,
                    company_code="000001",
                    company_name="TestCo",
                    report_title="Latest report",
                    analyst_name="Analyst A",
                    provider_name="Broker A",
                    opinion_raw="BUY",
                    opinion_std="BUY",
                    target_price_raw="12,000",
                    target_price_value=12000,
                    prev_close_price_raw="8,000",
                    prev_close_price_value=8000,
                    source_url="https://example.com/newer",
                    dedupe_key="same-provider-newer",
                    collected_at=datetime(2026, 3, 7, 10, 0, 0),
                ),
            ]
        )
        session.commit()

    service.publish(snapshot_date)

    with session_factory() as session:
        company = session.scalar(
            select(DailyCompanySummary).where(DailyCompanySummary.snapshot_date == snapshot_date)
        )
        snapshot = session.scalar(
            select(DailyDashboardSnapshot).where(DailyDashboardSnapshot.snapshot_date == snapshot_date)
        )

    assert company is not None
    assert company.report_count == 1
    assert company.buy_count == 1
    assert company.hold_count == 0
    assert company.avg_target_price == 12000
    assert snapshot is not None
    assert snapshot.total_reports == 1
    assert snapshot.buy_reports == 1
    assert snapshot.hold_reports == 0


def test_snapshot_service_excludes_ipo_reports(session_factory) -> None:
    snapshot_date = date(2026, 3, 7)
    service = SnapshotService(session_factory=session_factory)

    with session_factory() as session:
        session.add_all(
            [
                CompanyMaster(
                    company_code="0088M0",
                    company_name="메쥬",
                    sector_name_fnguide=None,
                    is_active=True,
                    updated_at=datetime(2026, 3, 7, 8, 0, 0),
                ),
                CompanyMaster(
                    company_code="251270",
                    company_name="넷마블",
                    sector_name_fnguide="Gaming",
                    is_active=True,
                    updated_at=datetime(2026, 3, 7, 8, 0, 0),
                ),
            ]
        )
        session.add_all(
            [
                ReportRawMeta(
                    snapshot_date=snapshot_date,
                    report_date=snapshot_date,
                    company_code="0088M0",
                    company_name="메쥬",
                    report_title="이동형 원격 환자 모니터링 선도기업",
                    analyst_name="박종선",
                    provider_name="유진투자증권",
                    opinion_raw=None,
                    opinion_std="NR",
                    target_price_raw=None,
                    target_price_value=None,
                    prev_close_price_raw=None,
                    prev_close_price_value=None,
                    source_url="https://example.com/ipo-code",
                    dedupe_key="snapshot-ipo-code",
                    collected_at=datetime(2026, 3, 7, 9, 0, 0),
                ),
                ReportRawMeta(
                    snapshot_date=snapshot_date,
                    report_date=snapshot_date,
                    company_code="251270",
                    company_name="넷마블",
                    report_title="Biggest beneficiary of fee cuts",
                    analyst_name="임희석",
                    provider_name="미래에셋증권",
                    opinion_raw="BUY",
                    opinion_std="BUY",
                    target_price_raw="85,000",
                    target_price_value=85000,
                    prev_close_price_raw="54,000",
                    prev_close_price_value=54000,
                    source_url="https://example.com/regular",
                    dedupe_key="snapshot-regular",
                    collected_at=datetime(2026, 3, 7, 10, 0, 0),
                ),
            ]
        )
        session.commit()

    result = service.publish(snapshot_date)

    with session_factory() as session:
        companies = session.scalars(
            select(DailyCompanySummary).where(DailyCompanySummary.snapshot_date == snapshot_date)
        ).all()
        snapshot = session.scalar(
            select(DailyDashboardSnapshot).where(DailyDashboardSnapshot.snapshot_date == snapshot_date)
        )

    assert result["raw_reports"] == 1
    assert len(companies) == 1
    assert companies[0].company_code == "251270"
    assert snapshot is not None
    assert snapshot.total_reports == 1


def test_snapshot_service_builds_deduped_spotlight_summaries(session_factory) -> None:
    snapshot_date = date(2026, 3, 7)
    service = SnapshotService(session_factory=session_factory)

    with session_factory() as session:
        session.add(
            CompanyMaster(
                company_code="251270",
                company_name="넷마블",
                sector_name_fnguide="Gaming",
                is_active=True,
                updated_at=datetime(2026, 3, 7, 8, 0, 0),
            )
        )
        session.add_all(
            [
                ReportRawMeta(
                    snapshot_date=snapshot_date,
                    report_date=snapshot_date,
                    company_code="251270",
                    company_name="넷마블",
                    report_title="국문 리포트",
                    summary_lines_json=[
                        "구글, 전격적인 앱 수수료 인하 발표",
                        "앱 수수료 인하 수혜가 가장 높은 기업",
                    ],
                    analyst_name="임희석",
                    provider_name="미래에셋증권",
                    opinion_raw="BUY",
                    opinion_std="BUY",
                    target_price_raw="85,000",
                    target_price_value=85000,
                    prev_close_price_raw="54,000",
                    prev_close_price_value=54000,
                    source_url="https://example.com/ko",
                    dedupe_key="summary-ko",
                    collected_at=datetime(2026, 3, 7, 9, 0, 0),
                ),
                ReportRawMeta(
                    snapshot_date=snapshot_date,
                    report_date=snapshot_date,
                    company_code="251270",
                    company_name="넷마블",
                    report_title="영문 리포트",
                    summary_lines_json=[
                        "구글, 전격적인 앱 수수료 인하 발표",
                        "앱 수수료 인하 수혜가 가장 높은 기업",
                        "추가 문장",
                    ],
                    analyst_name="임희석",
                    provider_name="다올투자증권",
                    opinion_raw="BUY",
                    opinion_std="BUY",
                    target_price_raw="84,000",
                    target_price_value=84000,
                    prev_close_price_raw="54,000",
                    prev_close_price_value=54000,
                    source_url="https://example.com/en",
                    dedupe_key="summary-en",
                    collected_at=datetime(2026, 3, 7, 10, 0, 0),
                ),
            ]
        )
        session.commit()

    service.publish(snapshot_date)

    with session_factory() as session:
        snapshot = session.scalar(
            select(DailyDashboardSnapshot).where(DailyDashboardSnapshot.snapshot_date == snapshot_date)
        )

    assert snapshot is not None
    top_item = (snapshot.top3_companies_json or [])[0]
    assert top_item["spotlight_summaries"] == [
        "구글, 전격적인 앱 수수료 인하 발표",
        "앱 수수료 인하 수혜가 가장 높은 기업",
        "추가 문장",
    ]
    assert sorted(top_item["provider_details"], key=lambda item: item["provider_name"]) == [
        {
            "provider_name": "다올투자증권",
            "analyst_names": ["임희석"],
        },
        {
            "provider_name": "미래에셋증권",
            "analyst_names": ["임희석"],
        },
    ]


def test_snapshot_service_build_dashboard_view_model_includes_last_updated_text(
    session_factory,
    seeded_snapshot_source_data,
) -> None:
    service = SnapshotService(session_factory=session_factory)
    service.publish(seeded_snapshot_source_data["latest_date"])

    with session_factory() as session:
        snapshot = session.scalar(
            select(DailyDashboardSnapshot).where(
                DailyDashboardSnapshot.snapshot_date == seeded_snapshot_source_data["latest_date"]
            )
        )
        assert snapshot is not None
        snapshot.created_at = datetime(2026, 3, 6, 1, 2, 3)
        session.commit()

    with session_factory() as session:
        view_model = service.build_dashboard_view_model(session, seeded_snapshot_source_data["latest_date"])

    assert view_model["last_updated_text"] == "2026-03-06 10:02:03"
    assert view_model["last_updated_iso"] == "2026-03-06T10:02:03+09:00"
