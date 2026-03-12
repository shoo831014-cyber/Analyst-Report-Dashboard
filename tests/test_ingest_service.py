from __future__ import annotations

from datetime import date

from sqlalchemy import select

from app.db.models import JobRun, ReportRawMeta
from app.services.ingest_service import IngestService, is_ir_authored_row, should_fallback
from app.services.report_filter_utils import is_ipo_report, is_ipo_report_row


class StubCollector:
    def __init__(self, rows):
        self.rows = rows
        self.playwright_rows = []
        self.requests_calls = 0
        self.playwright_calls = 0

    def fetch_with_requests(self, snapshot_date: date):
        self.requests_calls += 1
        return self.rows

    def fetch_with_playwright(self, snapshot_date: date):
        self.playwright_calls += 1
        return self.playwright_rows


def test_should_fallback_when_required_fields_missing() -> None:
    assert should_fallback([])
    assert should_fallback([{"company_name": "A", "report_title": None, "company_code": "000001"}])


def test_is_ir_authored_row_only_filters_company_ir_rows() -> None:
    assert is_ir_authored_row({"analyst_name": "IR팀", "provider_name": "해당기업"})
    assert is_ir_authored_row({"analyst_name": None, "provider_name": "해당기업"})
    assert not is_ir_authored_row({"analyst_name": "채윤석", "provider_name": "한국IR협의회 리서치센터"})


def test_is_ipo_report_filters_ipo_titles_and_non_standard_codes() -> None:
    assert is_ipo_report("0088M0", "이동형 원격 환자 모니터링 선도기업")
    assert is_ipo_report("408470", "IPO 기업 보고서")
    assert is_ipo_report_row({"company_code": "123456", "report_title": "[투자의시대/IPO기업] 테스트"})
    assert not is_ipo_report("251270", "Biggest beneficiary of fee cuts")


def test_ingest_service_inserts_and_skips_duplicates(session_factory) -> None:
    sample_rows = [
        {
            "report_id": "1078052",
            "report_date": date(2026, 3, 6),
            "company_code": "251270",
            "company_name": "Netmarble",
            "report_title": "Biggest beneficiary of fee cuts",
            "analyst_name": "Analyst A",
            "provider_name": "Broker A",
            "opinion_raw": "BUY",
            "target_price_raw": "85,000",
            "prev_close_price_raw": "54,000",
            "source_url": "https://wcomp.fnguide.com/Report/ReportSummary?cmp_cd=251270&rpt_id=1078052",
        },
        {
            "report_id": "1077803",
            "report_date": date(2026, 3, 6),
            "company_code": "192080",
            "company_name": "DoubleUGames",
            "report_title": "Earnings momentum stays strong",
            "analyst_name": "Analyst B",
            "provider_name": "Broker B",
            "opinion_raw": "Buy",
            "target_price_raw": "72,000",
            "prev_close_price_raw": "50,000",
            "source_url": "https://wcomp.fnguide.com/Report/ReportSummary?cmp_cd=192080&rpt_id=1077803",
        },
    ]
    collector = StubCollector(sample_rows)
    service = IngestService(collector=collector, session_factory=session_factory)

    first = service.run(snapshot_date=date(2026, 3, 6))
    second = service.run(snapshot_date=date(2026, 3, 6))

    assert first.inserted == 2
    assert first.skipped == 0
    assert first.errors == 0
    assert first.upside_ready_count == 2
    assert second.inserted == 0
    assert second.skipped == 2
    assert collector.requests_calls == 2
    assert collector.playwright_calls == 0

    with session_factory() as session:
        reports = session.scalars(select(ReportRawMeta)).all()
        jobs = session.scalars(select(JobRun).order_by(JobRun.id)).all()

    assert len(reports) == 2
    assert len(jobs) == 2
    assert all(job.run_status == "SUCCESS" for job in jobs)


def test_ingest_service_excludes_ir_authored_reports(session_factory) -> None:
    sample_rows = [
        {
            "report_id": "2000001",
            "report_date": date(2026, 3, 6),
            "company_code": "123456",
            "company_name": "IRAuthored",
            "report_title": "회사소개 및 주요 경영현황",
            "analyst_name": "IR팀",
            "provider_name": "해당기업",
            "opinion_raw": None,
            "target_price_raw": None,
            "prev_close_price_raw": None,
            "source_url": "https://example.com/ir",
        },
        {
            "report_id": "2000002",
            "report_date": date(2026, 3, 6),
            "company_code": "654321",
            "company_name": "ExternalResearch",
            "report_title": "실적 개선 구간 진입",
            "analyst_name": "채윤석",
            "provider_name": "한국IR협의회 리서치센터",
            "opinion_raw": "BUY",
            "target_price_raw": "12,000",
            "prev_close_price_raw": "10,000",
            "source_url": "https://example.com/external",
        },
    ]
    collector = StubCollector(sample_rows)
    service = IngestService(collector=collector, session_factory=session_factory)

    summary = service.run(snapshot_date=date(2026, 3, 6))

    assert summary.fetched == 2
    assert summary.filtered_ir == 1
    assert summary.inserted == 1
    assert "filtered_ir=1" in summary.message

    with session_factory() as session:
        reports = session.scalars(select(ReportRawMeta).order_by(ReportRawMeta.id)).all()

    assert len(reports) == 1
    assert reports[0].company_name == "ExternalResearch"


def test_ingest_service_excludes_ipo_reports(session_factory) -> None:
    sample_rows = [
        {
            "report_id": "3000001",
            "report_date": date(2026, 3, 6),
            "company_code": "0088M0",
            "company_name": "메쥬",
            "report_title": "이동형 원격 환자 모니터링 선도기업",
            "analyst_name": "박종선",
            "provider_name": "유진투자증권",
            "opinion_raw": None,
            "target_price_raw": None,
            "prev_close_price_raw": None,
            "source_url": "https://example.com/ipo-code",
        },
        {
            "report_id": "3000002",
            "report_date": date(2026, 3, 6),
            "company_code": "408470",
            "company_name": "한패스",
            "report_title": "IPO 기업 보고서",
            "analyst_name": "홍길동",
            "provider_name": "다인자산운용",
            "opinion_raw": None,
            "target_price_raw": None,
            "prev_close_price_raw": None,
            "source_url": "https://example.com/ipo-title",
        },
        {
            "report_id": "3000003",
            "report_date": date(2026, 3, 6),
            "company_code": "251270",
            "company_name": "넷마블",
            "report_title": "Biggest beneficiary of fee cuts",
            "analyst_name": "임희석",
            "provider_name": "미래에셋증권",
            "opinion_raw": "BUY",
            "target_price_raw": "85,000",
            "prev_close_price_raw": "54,000",
            "source_url": "https://example.com/regular",
        },
    ]
    collector = StubCollector(sample_rows)
    service = IngestService(collector=collector, session_factory=session_factory)

    summary = service.run(snapshot_date=date(2026, 3, 6))

    assert summary.fetched == 3
    assert summary.filtered_ipo == 2
    assert summary.inserted == 1
    assert "filtered_ipo=2" in summary.message

    with session_factory() as session:
        reports = session.scalars(select(ReportRawMeta).order_by(ReportRawMeta.id)).all()

    assert len(reports) == 1
    assert reports[0].company_name == "넷마블"
