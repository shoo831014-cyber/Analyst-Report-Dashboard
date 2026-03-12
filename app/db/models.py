from datetime import date, datetime
from typing import Any

from sqlalchemy import JSON, Boolean, Date, DateTime, Float, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), server_default=func.now(), nullable=False
    )


class ReportRawMeta(TimestampMixin, Base):
    __tablename__ = "report_raw_meta"
    __table_args__ = (
        Index("ix_report_raw_meta_snapshot_date", "snapshot_date"),
        Index("ix_report_raw_meta_company_code", "company_code"),
        Index("ix_report_raw_meta_dedupe_key", "dedupe_key", unique=True),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False)
    report_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    company_code: Mapped[str] = mapped_column(String(20), nullable=False)
    company_name: Mapped[str] = mapped_column(String(100), nullable=False)
    report_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    summary_lines_json: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    analyst_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    provider_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    opinion_raw: Mapped[str | None] = mapped_column(String(100), nullable=True)
    opinion_std: Mapped[str] = mapped_column(String(10), nullable=False, default="NR")
    target_price_raw: Mapped[str | None] = mapped_column(String(100), nullable=True)
    target_price_value: Mapped[int | None] = mapped_column(Integer, nullable=True)
    prev_close_price_raw: Mapped[str | None] = mapped_column(String(100), nullable=True)
    prev_close_price_value: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    dedupe_key: Mapped[str] = mapped_column(String(64), nullable=False)
    collected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), server_default=func.now(), nullable=False
    )


class CompanyMaster(Base):
    __tablename__ = "company_master"

    company_code: Mapped[str] = mapped_column(String(20), primary_key=True)
    company_name: Mapped[str] = mapped_column(String(100), nullable=False)
    sector_name_fnguide: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class DailyCompanySummary(TimestampMixin, Base):
    __tablename__ = "daily_company_summary"
    __table_args__ = (
        Index("ix_daily_company_summary_snapshot_date", "snapshot_date"),
        Index("ix_daily_company_summary_company_code", "company_code"),
        Index(
            "ix_daily_company_summary_snapshot_date_company_code",
            "snapshot_date",
            "company_code",
            unique=True,
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False)
    company_code: Mapped[str] = mapped_column(String(20), nullable=False)
    company_name: Mapped[str] = mapped_column(String(100), nullable=False)
    sector_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    report_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    buy_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    hold_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    sell_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    nr_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    avg_target_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    prev_close_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_upside_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    provider_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    analyst_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class DailySectorSummary(TimestampMixin, Base):
    __tablename__ = "daily_sector_summary"
    __table_args__ = (
        Index("ix_daily_sector_summary_snapshot_date", "snapshot_date"),
        Index(
            "ix_daily_sector_summary_snapshot_date_sector_name",
            "snapshot_date",
            "sector_name",
            unique=True,
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False)
    sector_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    report_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    avg_upside_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    top_companies_json: Mapped[dict[str, Any] | list[Any] | None] = mapped_column(JSON, nullable=True)


class DailyDashboardSnapshot(TimestampMixin, Base):
    __tablename__ = "daily_dashboard_snapshot"
    __table_args__ = (Index("ix_daily_dashboard_snapshot_snapshot_date", "snapshot_date", unique=True),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False)
    total_reports: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    buy_reports: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    hold_reports: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    sell_reports: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    nr_reports: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    top3_companies_json: Mapped[dict[str, Any] | list[Any] | None] = mapped_column(JSON, nullable=True)
    upside_top10_json: Mapped[dict[str, Any] | list[Any] | None] = mapped_column(JSON, nullable=True)
    sector_summary_json: Mapped[dict[str, Any] | list[Any] | None] = mapped_column(JSON, nullable=True)
    widget_payload_json: Mapped[dict[str, Any] | list[Any] | None] = mapped_column(JSON, nullable=True)


class JobRun(Base):
    __tablename__ = "job_run"
    __table_args__ = (Index("ix_job_run_job_name_started_at", "job_name", "started_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_name: Mapped[str] = mapped_column(String(50), nullable=False)
    run_status: Mapped[str] = mapped_column(String(20), nullable=False, default="RUNNING")
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), server_default=func.now(), nullable=False
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
