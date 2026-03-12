from __future__ import annotations

from sqlalchemy import select

from app.db.models import DailyDashboardSnapshot
from app.services.export_service import ExportService
from app.services.snapshot_service import SnapshotService


def test_export_dashboard_html_creates_file_and_updates_snapshot(
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
        output_path = export_service.export_dashboard_html(session, seeded_snapshot_source_data["latest_date"])
        session.commit()

    assert output_path.exists()
    html = output_path.read_text(encoding="utf-8")
    assert "기업분석레포트 대시보드" in html
    assert "<style>" in html

    with session_factory() as session:
        snapshot = session.scalar(
            select(DailyDashboardSnapshot).where(DailyDashboardSnapshot.snapshot_date == seeded_snapshot_source_data["latest_date"])
        )

    assert snapshot is not None
    assert snapshot.html_export_path == output_path.as_posix()
