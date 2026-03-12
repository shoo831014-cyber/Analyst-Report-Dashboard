from __future__ import annotations

from sqlalchemy import select

from app.db.models import DailyDashboardSnapshot, JobRun
from app.jobs.run_publish import main as run_publish_main
from app.services.export_service import ExportService
from app.services.snapshot_service import SnapshotService


def test_run_publish_creates_jobrun_snapshot_and_export(
    session_factory,
    seeded_snapshot_source_data,
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setattr("app.jobs.run_publish.configure_logging", lambda *args, **kwargs: None)

    snapshot_service = SnapshotService(session_factory=session_factory)
    export_service = ExportService(
        snapshot_service=snapshot_service,
        export_dir=tmp_path / "exports",
    )
    result = run_publish_main(
        snapshot_date=seeded_snapshot_source_data["latest_date"],
        session_factory=session_factory,
        service=snapshot_service,
        export_service=export_service,
    )

    assert result["snapshot_date"] == "2026-03-06"
    assert result["export_path"].endswith("dashboard.html")

    with session_factory() as session:
        jobs = session.scalars(select(JobRun).order_by(JobRun.id)).all()
        snapshot = session.scalar(
            select(DailyDashboardSnapshot).where(DailyDashboardSnapshot.snapshot_date == seeded_snapshot_source_data["latest_date"])
        )

    assert len(jobs) == 1
    assert jobs[0].run_status == "SUCCESS"
    assert "company_summaries=3" in (jobs[0].message or "")
    assert "export_path=" in (jobs[0].message or "")
    assert snapshot is not None
    assert snapshot.html_export_path is not None
    assert snapshot.html_export_path.endswith("dashboard.html")
