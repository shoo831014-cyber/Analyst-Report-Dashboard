from __future__ import annotations

from collections import Counter, defaultdict
from datetime import UTC, date, datetime, timedelta, timezone
from statistics import mean
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.api.dashboard_view import (
    build_company_table_rows,
    build_kpi_cards,
    build_layout_mode,
    build_opinion_distribution_detail,
    build_rating_buckets,
    build_report_heatmap_items,
    build_sector_cards,
    build_spotlight_cards,
    build_summary_notes,
    build_upside_ranking,
    format_count,
)
from app.db import session as db_session
from app.db.models import (
    DailyCompanySummary,
    DailyDashboardSnapshot,
    DailySectorSummary,
    ReportRawMeta,
)
from app.services.report_case_utils import dedupe_company_provider_cases
from app.services.report_filter_utils import filter_non_ipo_report_models
from app.services.report_summary_utils import dedupe_summary_lines
from app.services.sector_service import SectorService

UNASSIGNED_SECTOR_NAME = "UNASSIGNED"
SEOUL_TIMEZONE = timezone(timedelta(hours=9))


def utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class SnapshotService:
    def __init__(self, session_factory: Any | None = None, sector_service: SectorService | None = None) -> None:
        self.session_factory = session_factory or db_session.SessionLocal
        self.sector_service = sector_service or SectorService()

    def publish(self, snapshot_date: date) -> dict[str, Any]:
        with self.session_factory() as session:
            bind = session.get_bind()
            if bind is not None:
                db_session.ensure_schema(bind)
            result = self.rebuild_snapshot_for_date(session, snapshot_date)
            session.commit()
            return result

    def rebuild_snapshot_for_date(self, session: Session, snapshot_date: date) -> dict[str, Any]:
        raw_rows = session.scalars(
            select(ReportRawMeta)
            .where(ReportRawMeta.snapshot_date == snapshot_date)
            .order_by(ReportRawMeta.company_code, ReportRawMeta.id)
        ).all()
        if not raw_rows:
            raise ValueError(f"No raw reports found for snapshot_date={snapshot_date.isoformat()}")
        included_rows = filter_non_ipo_report_models(raw_rows)
        spotlight_summaries_by_company = self._build_company_spotlight_summaries(included_rows)

        self._delete_existing_snapshot(session, snapshot_date)

        company_summaries = self.build_company_summaries(session, snapshot_date, included_rows)
        session.add_all([DailyCompanySummary(**item) for item in company_summaries])

        sector_summaries = self.build_sector_summaries(
            snapshot_date,
            company_summaries,
            spotlight_summaries_by_company=spotlight_summaries_by_company,
        )
        session.add_all([DailySectorSummary(**item) for item in sector_summaries])

        dashboard_payload = self.build_dashboard_snapshot(
            snapshot_date=snapshot_date,
            raw_rows=included_rows,
            company_summaries=company_summaries,
            sector_summaries=sector_summaries,
            spotlight_summaries_by_company=spotlight_summaries_by_company,
        )
        session.add(DailyDashboardSnapshot(**dashboard_payload))

        return {
            "snapshot_date": snapshot_date.isoformat(),
            "raw_reports": len(included_rows),
            "company_summaries": len(company_summaries),
            "sector_summaries": len(sector_summaries),
            "dashboard_snapshot_created": True,
        }

    def build_company_summaries(
        self,
        session: Session,
        snapshot_date: date,
        raw_rows: list[ReportRawMeta],
    ) -> list[dict[str, Any]]:
        grouped: dict[str, list[ReportRawMeta]] = defaultdict(list)
        for row in raw_rows:
            grouped[row.company_code].append(row)

        sector_map = self.sector_service.get_sector_map(session, set(grouped.keys()))
        summaries: list[dict[str, Any]] = []
        created_at = utcnow_naive()

        for company_code, rows in grouped.items():
            case_rows = dedupe_company_provider_cases(rows)
            company_name = self._pick_company_name(rows)
            resolved_sector_name = self.sector_service.resolve_sector_name(
                company_code=company_code,
                company_name=company_name,
                report_titles=[row.report_title for row in rows],
                company_master_sector=sector_map.get(company_code),
            )
            target_values = [row.target_price_value for row in case_rows if row.target_price_value is not None]
            prev_close_values = [row.prev_close_price_value for row in case_rows if row.prev_close_price_value is not None]

            # Use row-level upside values and average them so multiple target prices remain represented.
            upside_values = [
                round(((row.target_price_value - row.prev_close_price_value) / row.prev_close_price_value) * 100, 2)
                for row in case_rows
                if row.target_price_value is not None
                and row.prev_close_price_value is not None
                and row.prev_close_price_value > 0
            ]

            provider_names = {row.provider_name for row in case_rows if row.provider_name}
            analyst_names = {row.analyst_name for row in case_rows if row.analyst_name}

            summaries.append(
                {
                    "snapshot_date": snapshot_date,
                    "company_code": company_code,
                    "company_name": company_name,
                    "sector_name": resolved_sector_name,
                    "report_count": len(case_rows),
                    "buy_count": self._count_by_opinion(case_rows, "BUY"),
                    "hold_count": self._count_by_opinion(case_rows, "HOLD"),
                    "sell_count": self._count_by_opinion(case_rows, "SELL"),
                    "nr_count": self._count_by_opinion(case_rows, "NR"),
                    "avg_target_price": round(mean(target_values), 2) if target_values else None,
                    "prev_close_price": self._pick_representative_prev_close(prev_close_values),
                    "avg_upside_pct": round(mean(upside_values), 2) if upside_values else None,
                    "provider_count": len(provider_names),
                    "analyst_count": len(analyst_names),
                    "created_at": created_at,
                }
            )

        summaries.sort(key=lambda item: (-item["report_count"], item["company_code"]))
        return summaries

    def build_sector_summaries(
        self,
        snapshot_date: date,
        company_summaries: list[dict[str, Any]],
        *,
        spotlight_summaries_by_company: dict[str, list[str]],
    ) -> list[dict[str, Any]]:
        grouped: dict[str | None, list[dict[str, Any]]] = defaultdict(list)
        for item in company_summaries:
            grouped[item["sector_name"] or UNASSIGNED_SECTOR_NAME].append(item)

        summaries: list[dict[str, Any]] = []
        created_at = utcnow_naive()

        for sector_name, items in grouped.items():
            upside_values = [item["avg_upside_pct"] for item in items if item["avg_upside_pct"] is not None]
            top_companies = sorted(
                items,
                key=lambda item: (-item["report_count"], -(item["avg_upside_pct"] or -999999), item["company_code"]),
            )[:8]
            summaries.append(
                {
                    "snapshot_date": snapshot_date,
                    "sector_name": sector_name,
                    "report_count": sum(item["report_count"] for item in items),
                    "avg_upside_pct": round(mean(upside_values), 2) if upside_values else None,
                    "top_companies_json": [
                        self._serialize_sector_top_company(
                            item,
                            spotlight_summaries=spotlight_summaries_by_company.get(item["company_code"], []),
                        )
                        for item in top_companies
                    ],
                    "created_at": created_at,
                }
            )

        summaries.sort(
            key=lambda item: (
                item["sector_name"] == UNASSIGNED_SECTOR_NAME,
                -(item["report_count"]),
                item["sector_name"] or "",
            )
        )
        return summaries

    def build_dashboard_snapshot(
        self,
        *,
        snapshot_date: date,
        raw_rows: list[ReportRawMeta],
        company_summaries: list[dict[str, Any]],
        sector_summaries: list[dict[str, Any]],
        spotlight_summaries_by_company: dict[str, list[str]] | None = None,
    ) -> dict[str, Any]:
        case_rows = dedupe_company_provider_cases(raw_rows)
        spotlight_summaries_by_company = spotlight_summaries_by_company or self._build_company_spotlight_summaries(raw_rows)
        provider_details_by_company = self._build_company_provider_details(raw_rows)
        top3_companies = [
            self._serialize_company_snapshot(
                item,
                spotlight_summaries=spotlight_summaries_by_company.get(item["company_code"], []),
                provider_details=provider_details_by_company.get(item["company_code"], []),
            )
            for item in sorted(
                company_summaries,
                key=lambda item: (-item["report_count"], -item["buy_count"], item["company_code"]),
            )[:3]
        ]
        upside_top10 = [
            self._serialize_company_snapshot(
                item,
                spotlight_summaries=spotlight_summaries_by_company.get(item["company_code"], []),
            )
            for item in sorted(
                [item for item in company_summaries if item["avg_upside_pct"] is not None],
                key=lambda item: (-(item["avg_upside_pct"] or 0), -item["report_count"], item["company_code"]),
            )[:10]
        ]
        sector_summary_json = [self._serialize_sector_summary(item) for item in sector_summaries]

        widget_payload = {
            "snapshot_date": snapshot_date.isoformat(),
            "kpis": {
                "total_reports": len(case_rows),
                "buy_reports": self._count_raw_opinion(case_rows, "BUY"),
                "hold_reports": self._count_raw_opinion(case_rows, "HOLD"),
                "sell_reports": self._count_raw_opinion(case_rows, "SELL"),
                "nr_reports": self._count_raw_opinion(case_rows, "NR"),
            },
            "top3_companies": top3_companies,
            "upside_top10": upside_top10,
            "sector_summary": sector_summary_json,
            "company_summaries": [
                self._serialize_company_snapshot(
                    item,
                    spotlight_summaries=spotlight_summaries_by_company.get(item["company_code"], []),
                    provider_details=provider_details_by_company.get(item["company_code"], []),
                )
                for item in company_summaries
            ],
        }

        return {
            "snapshot_date": snapshot_date,
            "total_reports": len(case_rows),
            "buy_reports": self._count_raw_opinion(case_rows, "BUY"),
            "hold_reports": self._count_raw_opinion(case_rows, "HOLD"),
            "sell_reports": self._count_raw_opinion(case_rows, "SELL"),
            "nr_reports": self._count_raw_opinion(case_rows, "NR"),
            "top3_companies_json": top3_companies,
            "upside_top10_json": upside_top10,
            "sector_summary_json": sector_summary_json,
            "widget_payload_json": widget_payload,
            "created_at": utcnow_naive(),
        }

    def get_available_snapshot_dates(self, session: Session, limit: int = 5) -> list[date]:
        return session.scalars(
            select(DailyDashboardSnapshot.snapshot_date)
            .order_by(DailyDashboardSnapshot.snapshot_date.desc())
            .limit(limit)
        ).all()

    def get_latest_published_snapshot_date(self, session: Session) -> date | None:
        return session.scalar(select(func.max(DailyDashboardSnapshot.snapshot_date)))

    def get_latest_company_snapshot_date(self, session: Session) -> date | None:
        return session.scalar(select(func.max(DailyCompanySummary.snapshot_date)))

    def get_latest_raw_snapshot_date(self, session: Session) -> date | None:
        return session.scalar(select(func.max(ReportRawMeta.snapshot_date)))

    def resolve_snapshot_date(self, session: Session, snapshot_date: date | None) -> date | None:
        if snapshot_date is not None:
            return snapshot_date

        resolved = self.get_latest_published_snapshot_date(session)
        if resolved is not None:
            return resolved

        resolved = self.get_latest_company_snapshot_date(session)
        if resolved is not None:
            return resolved

        return self.get_latest_raw_snapshot_date(session)

    def get_dashboard_snapshot(self, session: Session, snapshot_date: date | None) -> DailyDashboardSnapshot | None:
        resolved_date = self.resolve_snapshot_date(session, snapshot_date)
        if resolved_date is None:
            return None
        return session.scalar(
            select(DailyDashboardSnapshot).where(DailyDashboardSnapshot.snapshot_date == resolved_date)
        )

    def get_company_summaries(self, session: Session, snapshot_date: date | None) -> list[DailyCompanySummary]:
        resolved_date = self.resolve_snapshot_date(session, snapshot_date)
        if resolved_date is None:
            return []
        return session.scalars(
            select(DailyCompanySummary)
            .where(DailyCompanySummary.snapshot_date == resolved_date)
            .order_by(DailyCompanySummary.report_count.desc(), DailyCompanySummary.company_code)
        ).all()

    def get_sector_summaries(self, session: Session, snapshot_date: date | None) -> list[DailySectorSummary]:
        resolved_date = self.resolve_snapshot_date(session, snapshot_date)
        if resolved_date is None:
            return []
        return session.scalars(
            select(DailySectorSummary)
            .where(DailySectorSummary.snapshot_date == resolved_date)
            .order_by(DailySectorSummary.report_count.desc(), DailySectorSummary.sector_name)
        ).all()

    def serialize_dashboard_snapshot(self, snapshot: DailyDashboardSnapshot | None) -> dict[str, Any]:
        if snapshot is None:
            return {
                "snapshot_date": None,
                "total_reports": 0,
                "buy_reports": 0,
                "hold_reports": 0,
                "sell_reports": 0,
                "nr_reports": 0,
                "top3_companies": [],
                "upside_top10": [],
                "sector_summary": [],
                "widget_payload": {},
                "created_at": None,
                "created_at_text": None,
            }

        return {
            "snapshot_date": snapshot.snapshot_date.isoformat(),
            "total_reports": snapshot.total_reports,
            "buy_reports": snapshot.buy_reports,
            "hold_reports": snapshot.hold_reports,
            "sell_reports": snapshot.sell_reports,
            "nr_reports": snapshot.nr_reports,
            "top3_companies": snapshot.top3_companies_json or [],
            "upside_top10": snapshot.upside_top10_json or [],
            "sector_summary": snapshot.sector_summary_json or [],
            "widget_payload": snapshot.widget_payload_json or {},
            "created_at": self._format_snapshot_created_at_iso(snapshot.created_at),
            "created_at_text": self._format_snapshot_created_at_text(snapshot.created_at),
        }

    def serialize_company_model(self, item: DailyCompanySummary) -> dict[str, Any]:
        return {
            "snapshot_date": item.snapshot_date.isoformat(),
            "company_code": item.company_code,
            "company_name": item.company_name,
            "sector_name": item.sector_name,
            "report_count": item.report_count,
            "buy_count": item.buy_count,
            "hold_count": item.hold_count,
            "sell_count": item.sell_count,
            "nr_count": item.nr_count,
            "avg_target_price": item.avg_target_price,
            "prev_close_price": item.prev_close_price,
            "avg_upside_pct": item.avg_upside_pct,
            "provider_count": item.provider_count,
            "analyst_count": item.analyst_count,
        }

    def serialize_sector_model(self, item: DailySectorSummary) -> dict[str, Any]:
        return {
            "snapshot_date": item.snapshot_date.isoformat(),
            "sector_name": item.sector_name,
            "report_count": item.report_count,
            "avg_upside_pct": item.avg_upside_pct,
            "top_companies": item.top_companies_json or [],
        }

    def build_dashboard_view_model(self, session: Session, snapshot_date: date | None) -> dict[str, Any]:
        snapshot = self.get_dashboard_snapshot(session, snapshot_date)
        resolved_date = snapshot.snapshot_date if snapshot else self.resolve_snapshot_date(session, snapshot_date)
        company_rows = self.get_company_summaries(session, snapshot_date)
        company_items = [self.serialize_company_model(item) for item in company_rows]
        available_dates = self.get_available_snapshot_dates(session, limit=5)

        kpis = {
            "BUY": snapshot.buy_reports if snapshot else 0,
            "HOLD": snapshot.hold_reports if snapshot else 0,
            "SELL": snapshot.sell_reports if snapshot else 0,
            "NR": snapshot.nr_reports if snapshot else 0,
        }
        total_reports = snapshot.total_reports if snapshot else 0
        opinion_distribution = build_opinion_distribution_detail(kpis)
        top3_cards = build_spotlight_cards(snapshot.top3_companies_json if snapshot else [])
        sector_cards = build_sector_cards(snapshot.sector_summary_json if snapshot else [])
        upside_ranking = build_upside_ranking(snapshot.upside_top10_json if snapshot else [])
        table_rows = build_company_table_rows(company_items)
        layout_mode = build_layout_mode(sector_cards=sector_cards, total_company_rows=len(table_rows))
        report_heatmap_items = build_report_heatmap_items(company_items)
        summary_notes = build_summary_notes(
            spotlight_cards=top3_cards,
            opinion_distribution=opinion_distribution,
            sector_cards=sector_cards,
        )

        subtitle = f"기준일 {resolved_date.isoformat()} · FnGuide 리포트 집계" if resolved_date else "기준일 -"
        last_updated_text = self._format_snapshot_created_at_text(snapshot.created_at if snapshot else None)
        last_updated_iso = self._format_snapshot_created_at_iso(snapshot.created_at if snapshot else None)

        return {
            "page_title": "기업분석레포트 대시보드",
            "snapshot_date": resolved_date.isoformat() if resolved_date else None,
            "available_dates": [value.isoformat() for value in available_dates],
            "subtitle": subtitle,
            "last_updated_text": last_updated_text,
            "last_updated_iso": last_updated_iso,
            "compact_kpis": build_kpi_cards(total_reports=total_reports, kpis=kpis),
            "report_heatmap_items": report_heatmap_items,
            "report_heatmap_primary_items": [item for item in report_heatmap_items if not item["is_single_report"]],
            "report_heatmap_secondary_items": [item for item in report_heatmap_items if item["is_single_report"]],
            "top3_cards": top3_cards,
            "sector_cards": sector_cards,
            "upside_ranking": upside_ranking,
            "table_rows": table_rows,
            "summary_notes": summary_notes,
            "summary_banner_title": summary_notes[0] if summary_notes else None,
            "summary_banner_notes": summary_notes[1:],
            "opinion_distribution": opinion_distribution,
            "rating_buckets": build_rating_buckets(company_items),
            "layout_mode": layout_mode,
            "total_reports_text": format_count(total_reports),
        }

    def _delete_existing_snapshot(self, session: Session, snapshot_date: date) -> None:
        session.execute(delete(DailyCompanySummary).where(DailyCompanySummary.snapshot_date == snapshot_date))
        session.execute(delete(DailySectorSummary).where(DailySectorSummary.snapshot_date == snapshot_date))
        session.execute(delete(DailyDashboardSnapshot).where(DailyDashboardSnapshot.snapshot_date == snapshot_date))

    def _count_by_opinion(self, rows: list[ReportRawMeta], opinion: str) -> int:
        return sum(1 for row in rows if row.opinion_std == opinion)

    def _count_raw_opinion(self, rows: list[ReportRawMeta], opinion: str) -> int:
        return sum(1 for row in rows if row.opinion_std == opinion)

    def _pick_company_name(self, rows: list[ReportRawMeta]) -> str:
        names = [row.company_name for row in rows if row.company_name]
        return names[0] if names else ""

    def _pick_representative_prev_close(self, values: list[int]) -> float | None:
        if not values:
            return None

        counts = Counter(values)
        highest_count = max(counts.values())
        for value in values:
            if counts[value] == highest_count:
                return float(value)
        return float(values[0])

    def _build_company_spotlight_summaries(self, raw_rows: list[ReportRawMeta]) -> dict[str, list[str]]:
        grouped: dict[str, list[ReportRawMeta]] = defaultdict(list)
        for row in raw_rows:
            grouped[row.company_code].append(row)

        summary_map: dict[str, list[str]] = {}
        for company_code, rows in grouped.items():
            case_rows = dedupe_company_provider_cases(rows)
            lines: list[str] = []
            for row in case_rows:
                lines.extend(row.summary_lines_json or [])
            summary_map[company_code] = dedupe_summary_lines(lines)
        return summary_map

    def _build_company_provider_details(self, raw_rows: list[ReportRawMeta]) -> dict[str, list[dict[str, Any]]]:
        grouped: dict[str, list[ReportRawMeta]] = defaultdict(list)
        for row in raw_rows:
            grouped[row.company_code].append(row)

        detail_map: dict[str, list[dict[str, Any]]] = {}
        for company_code, rows in grouped.items():
            case_rows = dedupe_company_provider_cases(rows)
            by_provider: dict[str, list[str]] = defaultdict(list)
            provider_order: list[str] = []

            for row in case_rows:
                provider_name = (row.provider_name or "").strip()
                analyst_name = (row.analyst_name or "").strip()
                provider_key = provider_name or "-"
                if provider_key not in by_provider:
                    provider_order.append(provider_key)
                if analyst_name and analyst_name not in by_provider[provider_key]:
                    by_provider[provider_key].append(analyst_name)
                elif provider_key not in by_provider:
                    by_provider[provider_key] = []

            detail_map[company_code] = [
                {
                    "provider_name": provider_name,
                    "analyst_names": by_provider[provider_name],
                }
                for provider_name in provider_order
            ]
        return detail_map

    def _serialize_company_snapshot(
        self,
        item: dict[str, Any],
        *,
        spotlight_summaries: list[str] | None = None,
        provider_details: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        payload = {
            "company_code": item["company_code"],
            "company_name": item["company_name"],
            "sector_name": item["sector_name"],
            "report_count": item["report_count"],
            "buy_count": item["buy_count"],
            "hold_count": item["hold_count"],
            "sell_count": item["sell_count"],
            "nr_count": item["nr_count"],
            "avg_target_price": item["avg_target_price"],
            "prev_close_price": item["prev_close_price"],
            "avg_upside_pct": item["avg_upside_pct"],
            "provider_count": item["provider_count"],
            "analyst_count": item["analyst_count"],
        }
        if spotlight_summaries is not None:
            payload["spotlight_summaries"] = spotlight_summaries
        if provider_details is not None:
            payload["provider_details"] = provider_details
        return payload

    def _serialize_sector_top_company(
        self,
        item: dict[str, Any],
        *,
        spotlight_summaries: list[str] | None = None,
    ) -> dict[str, Any]:
        payload = {
            "company_code": item["company_code"],
            "company_name": item["company_name"],
            "report_count": item["report_count"],
            "buy_count": item["buy_count"],
            "hold_count": item["hold_count"],
            "sell_count": item["sell_count"],
            "nr_count": item["nr_count"],
            "avg_target_price": item["avg_target_price"],
            "prev_close_price": item["prev_close_price"],
            "avg_upside_pct": item["avg_upside_pct"],
        }
        if spotlight_summaries is not None:
            payload["spotlight_summaries"] = spotlight_summaries
        return payload

    def _serialize_sector_summary(self, item: dict[str, Any]) -> dict[str, Any]:
        return {
            "sector_name": item["sector_name"],
            "report_count": item["report_count"],
            "avg_upside_pct": item["avg_upside_pct"],
            "top_companies": item["top_companies_json"] or [],
        }

    def _format_snapshot_created_at_iso(self, value: datetime | None) -> str | None:
        localized = self._localize_created_at(value)
        if localized is None:
            return None
        return localized.isoformat(timespec="seconds")

    def _format_snapshot_created_at_text(self, value: datetime | None) -> str | None:
        localized = self._localize_created_at(value)
        if localized is None:
            return None
        return localized.strftime("%Y-%m-%d %H:%M:%S")

    def _localize_created_at(self, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        return value.replace(tzinfo=UTC).astimezone(SEOUL_TIMEZONE)
