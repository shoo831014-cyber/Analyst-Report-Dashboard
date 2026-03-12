from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db.models import DailyDashboardSnapshot
from app.runtime_paths import get_static_dir, get_templates_dir
from app.services.snapshot_service import SnapshotService


class ExportService:
    def __init__(
        self,
        *,
        settings: Settings | None = None,
        snapshot_service: SnapshotService | None = None,
        template_dir: Path | None = None,
        static_dir: Path | None = None,
        export_dir: Path | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.snapshot_service = snapshot_service or SnapshotService()
        self.template_dir = template_dir or get_templates_dir()
        self.static_dir = static_dir or get_static_dir()
        self.export_dir = export_dir or self.settings.export_path
        self.environment = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            autoescape=select_autoescape(["html", "xml"]),
        )

    def render_dashboard_html(self, session: Session, snapshot_date: date) -> str:
        view_model = self.snapshot_service.build_dashboard_view_model(session, snapshot_date)
        if view_model["snapshot_date"] is None:
            raise ValueError(f"No dashboard snapshot available for snapshot_date={snapshot_date.isoformat()}")

        template = self.environment.get_template("dashboard.html")
        context = {
            **view_model,
            "inline_css": self._read_static_asset(Path("css/dashboard.css")),
            "inline_js": self._read_static_asset(Path("js/dashboard.js")),
            "static_css_url": None,
            "static_js_url": None,
            "export_mode": True,
        }
        return template.render(context)

    def export_dashboard_html(self, session: Session, snapshot_date: date) -> Path:
        session.flush()
        output_path = self.build_export_output_path(snapshot_date)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        html = self.render_dashboard_html(session, snapshot_date)
        output_path.write_text(html, encoding="utf-8")

        self.update_export_path(session, snapshot_date, output_path)
        session.flush()
        return output_path

    def update_export_path(self, session: Session, snapshot_date: date, export_path: Path) -> None:
        snapshot = session.scalar(
            select(DailyDashboardSnapshot).where(DailyDashboardSnapshot.snapshot_date == snapshot_date)
        )
        if snapshot is None:
            raise ValueError(f"No dashboard snapshot row found for snapshot_date={snapshot_date.isoformat()}")
        snapshot.html_export_path = export_path.as_posix()
        session.add(snapshot)

    def build_export_output_path(self, snapshot_date: date) -> Path:
        return self.export_dir / snapshot_date.isoformat() / "dashboard.html"

    def get_export_public_url(self, snapshot_date: date) -> str:
        return f"/exports/{snapshot_date.isoformat()}/dashboard.html"

    def get_export_info(self, session: Session, snapshot_date: date | None) -> dict[str, Any]:
        resolved_date = self.snapshot_service.resolve_snapshot_date(session, snapshot_date)
        if resolved_date is None:
            return {
                "snapshot_date": None,
                "html_export_path": None,
                "html_export_url": None,
                "exists": False,
            }

        snapshot = self.snapshot_service.get_dashboard_snapshot(session, resolved_date)
        export_path = snapshot.html_export_path if snapshot else None
        if export_path is None:
            return {
                "snapshot_date": resolved_date.isoformat(),
                "html_export_path": None,
                "html_export_url": self.get_export_public_url(resolved_date),
                "exists": False,
            }

        return {
            "snapshot_date": resolved_date.isoformat(),
            "html_export_path": export_path,
            "html_export_url": self.get_export_public_url(resolved_date),
            "exists": Path(export_path).exists(),
        }

    def _read_static_asset(self, relative_path: Path) -> str:
        asset_path = self.static_dir / relative_path
        return asset_path.read_text(encoding="utf-8")
