from __future__ import annotations

from datetime import date, datetime
from sqlalchemy import update

from app.db.models import CompanyMaster
from app.services.export_service import ExportService
from app.services.snapshot_service import SnapshotService


def test_dashboard_summary_and_companies_api(client, session_factory, seeded_snapshot_source_data) -> None:
    service = SnapshotService(session_factory=session_factory)
    service.publish(seeded_snapshot_source_data["latest_date"])

    summary_response = client.get("/api/v1/dashboard/summary")
    assert summary_response.status_code == 200
    summary_payload = summary_response.json()
    assert summary_payload["snapshot_date"] == "2026-03-06"
    assert summary_payload["total_reports"] == 4
    assert len(summary_payload["top3_companies"]) == 3

    companies_response = client.get("/api/v1/dashboard/companies", params={"date": "2026-03-06"})
    assert companies_response.status_code == 200
    companies_payload = companies_response.json()
    assert companies_payload["total"] == 3
    assert companies_payload["items"][0]["report_count"] >= companies_payload["items"][1]["report_count"]

    sectors_response = client.get("/api/v1/dashboard/sectors", params={"date": "2026-03-06"})
    assert sectors_response.status_code == 200
    sectors_payload = sectors_response.json()
    assert sectors_payload["total"] == 3


def test_dashboard_dates_api_returns_latest_published_dates(client, session_factory, seeded_snapshot_source_data) -> None:
    service = SnapshotService(session_factory=session_factory)
    service.publish(seeded_snapshot_source_data["previous_date"])
    service.publish(seeded_snapshot_source_data["latest_date"])

    response = client.get("/api/v1/dashboard/dates")
    assert response.status_code == 200
    payload = response.json()
    assert payload["dates"][:2] == ["2026-03-06", "2026-03-05"]


def test_dashboard_page_renders_compact_layout_sections(client, session_factory, seeded_snapshot_source_data) -> None:
    service = SnapshotService(session_factory=session_factory)
    service.publish(seeded_snapshot_source_data["latest_date"])

    response = client.get("/dashboard", params={"date": "2026-03-06"})
    assert response.status_code == 200
    assert "기업분석레포트 대시보드" in response.text
    assert "전체 리포트" in response.text
    assert "BUY" in response.text
    assert "HOLD" in response.text
    assert "SELL" in response.text
    assert "NR" in response.text
    assert "최근 스냅샷" not in response.text
    assert "리포트 히트맵" in response.text
    assert "Spotlight Top3" in response.text
    assert "투자의견 분포" in response.text
    assert "상승여력 Top10" in response.text
    assert "등급별 종목 재정리" in response.text
    assert "상세 테이블" in response.text
    assert "오늘의 핵심 테마" not in response.text
    assert "detail-table-scroll" in response.text
    assert "placeholder" not in response.text


def test_dashboard_page_sector_compact_mode_renders(client, session_factory, seeded_snapshot_source_data) -> None:
    with session_factory() as session:
        session.execute(update(CompanyMaster).values(sector_name_fnguide=None))
        session.commit()

    service = SnapshotService(session_factory=session_factory)
    service.publish(seeded_snapshot_source_data["latest_date"])

    response = client.get("/dashboard", params={"date": "2026-03-06"})
    assert response.status_code == 200
    assert "섹터별 리포트 현황" in response.text
    assert "Gaming" not in response.text


def test_dashboard_page_handles_empty_state(client) -> None:
    response = client.get("/dashboard")
    assert response.status_code == 200
    assert "리포트 히트맵" in response.text
    assert "Spotlight Top3" in response.text
    assert "투자의견 분포" in response.text
    assert "등급별 종목 재정리" in response.text
    assert "상세 테이블" in response.text


def test_dashboard_export_api_returns_export_path(
    client,
    session_factory,
    seeded_snapshot_source_data,
    tmp_path,
) -> None:
    snapshot_service = SnapshotService(session_factory=session_factory)
    snapshot_service.publish(seeded_snapshot_source_data["latest_date"])

    export_service = ExportService(
        snapshot_service=snapshot_service,
        export_dir=tmp_path / "exports",
    )
    with session_factory() as session:
        export_service.export_dashboard_html(session, seeded_snapshot_source_data["latest_date"])
        session.commit()

    response = client.get("/api/v1/dashboard/export", params={"date": "2026-03-06"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["snapshot_date"] == "2026-03-06"
    assert payload["exists"] is True
    assert payload["html_export_path"].endswith("dashboard.html")
    assert payload["html_export_url"] == "/exports/2026-03-06/dashboard.html"


def test_dashboard_page_renders_manual_update_button(client) -> None:
    response = client.get("/dashboard")
    assert response.status_code == 200
    assert "data-theme-toggle-button" in response.text
    assert "data-manual-update-button" in response.text
    assert "data-manual-update-status" in response.text
    assert "data-last-updated-text" in response.text
    assert "dashboardTheme" in response.text


def test_dashboard_manual_update_api_uses_current_seoul_date(client, monkeypatch) -> None:
    target_date = date(2026, 3, 9)
    calls: dict[str, object] = {}

    class StubSummary:
        def model_dump(self, mode: str = "json") -> dict:
            return {"snapshot_date": "2026-03-09", "inserted": 1}

    class StubIngestService:
        def run(self, snapshot_date: date):
            calls["ingest_date"] = snapshot_date
            return StubSummary()

    class StubSnapshotService:
        def publish(self, snapshot_date: date) -> dict:
            calls["publish_date"] = snapshot_date
            return {"snapshot_date": snapshot_date.isoformat(), "dashboard_snapshot_created": True}

        def get_dashboard_snapshot(self, session, snapshot_date: date):
            calls["snapshot_lookup_date"] = snapshot_date
            return type(
                "Snapshot",
                (),
                {
                    "snapshot_date": snapshot_date,
                    "total_reports": 1,
                    "buy_reports": 1,
                    "hold_reports": 0,
                    "sell_reports": 0,
                    "nr_reports": 0,
                    "top3_companies_json": [],
                    "upside_top10_json": [],
                    "sector_summary_json": [],
                    "widget_payload_json": {},
                    "html_export_path": None,
                    "created_at": datetime(2026, 3, 9, 1, 23, 45),
                },
            )()

        def serialize_dashboard_snapshot(self, snapshot) -> dict:
            return {
                "created_at": "2026-03-09T10:23:45+09:00",
                "created_at_text": "2026-03-09 10:23:45",
            }

    class StubExportService:
        def export_dashboard_html(self, session, snapshot_date: date):
            calls["export_date"] = snapshot_date
            return None

        def get_export_info(self, session, snapshot_date: date) -> dict:
            return {"snapshot_date": snapshot_date.isoformat(), "exists": True}

    monkeypatch.setattr("app.api.routes_dashboard.current_seoul_date", lambda: target_date)
    monkeypatch.setattr("app.api.routes_dashboard.ingest_service", StubIngestService())
    monkeypatch.setattr("app.api.routes_dashboard.snapshot_service", StubSnapshotService())
    monkeypatch.setattr("app.api.routes_dashboard.export_service", StubExportService())

    response = client.post("/api/v1/dashboard/update")
    assert response.status_code == 200
    payload = response.json()

    assert payload["snapshot_date"] == "2026-03-09"
    assert payload["last_updated_at"] == "2026-03-09T10:23:45+09:00"
    assert payload["last_updated_text"] == "2026-03-09 10:23:45"
    assert calls["ingest_date"] == target_date
    assert calls["publish_date"] == target_date
    assert calls["export_date"] == target_date
    assert calls["snapshot_lookup_date"] == target_date
