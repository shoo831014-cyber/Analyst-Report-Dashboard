from __future__ import annotations

from datetime import UTC, date, datetime

from app.db.models import ReportRawMeta


def utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def test_reports_api_returns_latest_snapshot(client, session_factory) -> None:
    with session_factory() as session:
        session.add_all(
            [
                ReportRawMeta(
                    snapshot_date=date(2026, 3, 5),
                    report_date=date(2026, 3, 5),
                    company_code="035420",
                    company_name="NAVER",
                    report_title="Commerce margin recovery",
                    analyst_name="Analyst A",
                    provider_name="Broker A",
                    opinion_raw="BUY",
                    opinion_std="BUY",
                    target_price_raw="360,000",
                    target_price_value=360000,
                    prev_close_price_raw="222,500",
                    prev_close_price_value=222500,
                    source_url="https://wcomp.fnguide.com/Report/ReportSummary?cmp_cd=035420&rpt_id=1077530",
                    dedupe_key="key-old",
                    collected_at=utcnow_naive(),
                ),
                ReportRawMeta(
                    snapshot_date=date(2026, 3, 6),
                    report_date=date(2026, 3, 6),
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
                    source_url="https://wcomp.fnguide.com/Report/ReportSummary?cmp_cd=251270&rpt_id=1078052",
                    dedupe_key="key-new",
                    collected_at=utcnow_naive(),
                ),
            ]
        )
        session.commit()

    response = client.get("/api/v1/reports")
    assert response.status_code == 200
    payload = response.json()

    assert payload["snapshot_date"] == "2026-03-06"
    assert payload["total"] == 1
    assert payload["items"][0]["company_code"] == "251270"


def test_reports_api_filters_by_date_and_company(client, session_factory) -> None:
    with session_factory() as session:
        session.add(
            ReportRawMeta(
                snapshot_date=date(2026, 3, 6),
                report_date=date(2026, 3, 6),
                company_code="035420",
                company_name="NAVER",
                report_title="Commerce margin recovery",
                analyst_name="Analyst A",
                provider_name="Broker A",
                opinion_raw="BUY",
                opinion_std="BUY",
                target_price_raw="360,000",
                target_price_value=360000,
                prev_close_price_raw="222,500",
                prev_close_price_value=222500,
                source_url="https://wcomp.fnguide.com/Report/ReportSummary?cmp_cd=035420&rpt_id=1077530",
                dedupe_key="key-filter",
                collected_at=utcnow_naive(),
            )
        )
        session.commit()

    response = client.get("/api/v1/reports", params={"date": "2026-03-06", "company_code": "035420", "limit": 10})
    assert response.status_code == 200
    payload = response.json()

    assert payload["total"] == 1
    assert payload["items"][0]["company_name"] == "NAVER"


def test_reports_api_dedupes_same_company_same_provider(client, session_factory) -> None:
    captured_at = utcnow_naive()
    with session_factory() as session:
        session.add_all(
            [
                ReportRawMeta(
                    snapshot_date=date(2026, 3, 6),
                    report_date=date(2026, 3, 6),
                    company_code="251270",
                    company_name="넷마블",
                    report_title="앱 수수료 인하의 최대 수혜주",
                    analyst_name="임희석",
                    provider_name="미래에셋증권",
                    opinion_raw="매수",
                    opinion_std="BUY",
                    target_price_raw="85,000",
                    target_price_value=85000,
                    prev_close_price_raw="54,000",
                    prev_close_price_value=54000,
                    source_url="https://example.com/ko",
                    dedupe_key="reports-dedupe-ko",
                    collected_at=captured_at,
                ),
                ReportRawMeta(
                    snapshot_date=date(2026, 3, 6),
                    report_date=date(2026, 3, 6),
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
                    source_url="https://example.com/en",
                    dedupe_key="reports-dedupe-en",
                    collected_at=captured_at,
                ),
            ]
        )
        session.commit()

    response = client.get("/api/v1/reports", params={"date": "2026-03-06", "company_code": "251270", "limit": 10})
    assert response.status_code == 200
    payload = response.json()

    assert payload["total"] == 1
    assert len(payload["items"]) == 1
    assert payload["items"][0]["company_code"] == "251270"
    assert payload["items"][0]["provider_name"] == "미래에셋증권"


def test_reports_api_excludes_ipo_reports(client, session_factory) -> None:
    with session_factory() as session:
        session.add_all(
            [
                ReportRawMeta(
                    snapshot_date=date(2026, 3, 6),
                    report_date=date(2026, 3, 6),
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
                    dedupe_key="ipo-code-report",
                    collected_at=utcnow_naive(),
                ),
                ReportRawMeta(
                    snapshot_date=date(2026, 3, 6),
                    report_date=date(2026, 3, 6),
                    company_code="408470",
                    company_name="한패스",
                    report_title="IPO 기업 보고서",
                    analyst_name="홍길동",
                    provider_name="다인자산운용",
                    opinion_raw=None,
                    opinion_std="NR",
                    target_price_raw=None,
                    target_price_value=None,
                    prev_close_price_raw=None,
                    prev_close_price_value=None,
                    source_url="https://example.com/ipo-title",
                    dedupe_key="ipo-title-report",
                    collected_at=utcnow_naive(),
                ),
                ReportRawMeta(
                    snapshot_date=date(2026, 3, 6),
                    report_date=date(2026, 3, 6),
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
                    dedupe_key="regular-report",
                    collected_at=utcnow_naive(),
                ),
            ]
        )
        session.commit()

    response = client.get("/api/v1/reports", params={"date": "2026-03-06", "limit": 10})
    assert response.status_code == 200
    payload = response.json()

    assert payload["total"] == 1
    assert len(payload["items"]) == 1
    assert payload["items"][0]["company_code"] == "251270"
