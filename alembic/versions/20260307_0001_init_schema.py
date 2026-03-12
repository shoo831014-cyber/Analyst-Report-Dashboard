"""init schema with snapshot aggregates

Revision ID: 20260307_0001
Revises:
Create Date: 2026-03-07 15:10:00
"""
from __future__ import annotations

import hashlib
from datetime import date, datetime
from typing import Any

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260307_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    _ensure_report_raw_meta(bind, inspector)
    _ensure_company_master(inspector)
    _ensure_daily_company_summary(inspector)
    _ensure_daily_sector_summary(inspector)
    _ensure_daily_dashboard_snapshot(inspector)
    _ensure_job_run(inspector)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    for table_name in (
        "daily_dashboard_snapshot",
        "daily_sector_summary",
        "daily_company_summary",
        "job_run",
        "company_master",
    ):
        if table_name in tables:
            op.drop_table(table_name)

    if "report_raw_meta" in tables:
        indexes = {index["name"] for index in inspector.get_indexes("report_raw_meta")}
        if "ix_report_raw_meta_dedupe_key" in indexes:
            op.drop_index("ix_report_raw_meta_dedupe_key", table_name="report_raw_meta")
        columns = {column["name"] for column in inspector.get_columns("report_raw_meta")}
        if "dedupe_key" in columns:
            with op.batch_alter_table("report_raw_meta") as batch_op:
                batch_op.drop_column("dedupe_key")


def _ensure_report_raw_meta(bind: Any, inspector: Any) -> None:
    tables = set(inspector.get_table_names())
    if "report_raw_meta" not in tables:
        op.create_table(
            "report_raw_meta",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("snapshot_date", sa.Date(), nullable=False),
            sa.Column("report_date", sa.Date(), nullable=True),
            sa.Column("company_code", sa.String(length=20), nullable=False),
            sa.Column("company_name", sa.String(length=100), nullable=False),
            sa.Column("report_title", sa.String(length=255), nullable=True),
            sa.Column("analyst_name", sa.String(length=100), nullable=True),
            sa.Column("provider_name", sa.String(length=100), nullable=True),
            sa.Column("opinion_raw", sa.String(length=100), nullable=True),
            sa.Column("opinion_std", sa.String(length=10), nullable=False),
            sa.Column("target_price_raw", sa.String(length=100), nullable=True),
            sa.Column("target_price_value", sa.Integer(), nullable=True),
            sa.Column("prev_close_price_raw", sa.String(length=100), nullable=True),
            sa.Column("prev_close_price_value", sa.Integer(), nullable=True),
            sa.Column("source_url", sa.Text(), nullable=True),
            sa.Column("dedupe_key", sa.String(length=64), nullable=False),
            sa.Column("collected_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        )
        op.create_index("ix_report_raw_meta_snapshot_date", "report_raw_meta", ["snapshot_date"], unique=False)
        op.create_index("ix_report_raw_meta_company_code", "report_raw_meta", ["company_code"], unique=False)
        op.create_index("ix_report_raw_meta_dedupe_key", "report_raw_meta", ["dedupe_key"], unique=True)
        return

    columns = {column["name"] for column in inspector.get_columns("report_raw_meta")}
    if "dedupe_key" not in columns:
        with op.batch_alter_table("report_raw_meta") as batch_op:
            batch_op.add_column(sa.Column("dedupe_key", sa.String(length=64), nullable=True))
        _backfill_dedupe_keys(bind)

    indexes = {index["name"] for index in inspector.get_indexes("report_raw_meta")}
    if "ix_report_raw_meta_snapshot_date" not in indexes:
        op.create_index("ix_report_raw_meta_snapshot_date", "report_raw_meta", ["snapshot_date"], unique=False)
    if "ix_report_raw_meta_company_code" not in indexes:
        op.create_index("ix_report_raw_meta_company_code", "report_raw_meta", ["company_code"], unique=False)
    if "ix_report_raw_meta_dedupe_key" not in indexes:
        op.create_index("ix_report_raw_meta_dedupe_key", "report_raw_meta", ["dedupe_key"], unique=True)


def _ensure_company_master(inspector: Any) -> None:
    if "company_master" in set(inspector.get_table_names()):
        return
    op.create_table(
        "company_master",
        sa.Column("company_code", sa.String(length=20), primary_key=True),
        sa.Column("company_name", sa.String(length=100), nullable=False),
        sa.Column("sector_name_fnguide", sa.String(length=100), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )


def _ensure_daily_company_summary(inspector: Any) -> None:
    tables = set(inspector.get_table_names())
    if "daily_company_summary" not in tables:
        op.create_table(
            "daily_company_summary",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("snapshot_date", sa.Date(), nullable=False),
            sa.Column("company_code", sa.String(length=20), nullable=False),
            sa.Column("company_name", sa.String(length=100), nullable=False),
            sa.Column("sector_name", sa.String(length=100), nullable=True),
            sa.Column("report_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("buy_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("hold_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("sell_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("nr_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("avg_target_price", sa.Float(), nullable=True),
            sa.Column("prev_close_price", sa.Float(), nullable=True),
            sa.Column("avg_upside_pct", sa.Float(), nullable=True),
            sa.Column("provider_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("analyst_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        )

    indexes = {index["name"] for index in inspector.get_indexes("daily_company_summary")}
    if "ix_daily_company_summary_snapshot_date" not in indexes:
        op.create_index("ix_daily_company_summary_snapshot_date", "daily_company_summary", ["snapshot_date"], unique=False)
    if "ix_daily_company_summary_company_code" not in indexes:
        op.create_index("ix_daily_company_summary_company_code", "daily_company_summary", ["company_code"], unique=False)
    if "ix_daily_company_summary_snapshot_date_company_code" not in indexes:
        op.create_index(
            "ix_daily_company_summary_snapshot_date_company_code",
            "daily_company_summary",
            ["snapshot_date", "company_code"],
            unique=True,
        )


def _ensure_daily_sector_summary(inspector: Any) -> None:
    tables = set(inspector.get_table_names())
    if "daily_sector_summary" not in tables:
        op.create_table(
            "daily_sector_summary",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("snapshot_date", sa.Date(), nullable=False),
            sa.Column("sector_name", sa.String(length=100), nullable=True),
            sa.Column("report_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("avg_upside_pct", sa.Float(), nullable=True),
            sa.Column("top_companies_json", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        )

    indexes = {index["name"] for index in inspector.get_indexes("daily_sector_summary")}
    if "ix_daily_sector_summary_snapshot_date" not in indexes:
        op.create_index("ix_daily_sector_summary_snapshot_date", "daily_sector_summary", ["snapshot_date"], unique=False)
    if "ix_daily_sector_summary_snapshot_date_sector_name" not in indexes:
        op.create_index(
            "ix_daily_sector_summary_snapshot_date_sector_name",
            "daily_sector_summary",
            ["snapshot_date", "sector_name"],
            unique=True,
        )


def _ensure_daily_dashboard_snapshot(inspector: Any) -> None:
    tables = set(inspector.get_table_names())
    if "daily_dashboard_snapshot" not in tables:
        op.create_table(
            "daily_dashboard_snapshot",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("snapshot_date", sa.Date(), nullable=False),
            sa.Column("total_reports", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("buy_reports", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("hold_reports", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("sell_reports", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("nr_reports", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("top3_companies_json", sa.JSON(), nullable=True),
            sa.Column("upside_top10_json", sa.JSON(), nullable=True),
            sa.Column("sector_summary_json", sa.JSON(), nullable=True),
            sa.Column("widget_payload_json", sa.JSON(), nullable=True),
            sa.Column("html_export_path", sa.String(length=255), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        )

    indexes = {index["name"] for index in inspector.get_indexes("daily_dashboard_snapshot")}
    if "ix_daily_dashboard_snapshot_snapshot_date" not in indexes:
        op.create_index(
            "ix_daily_dashboard_snapshot_snapshot_date",
            "daily_dashboard_snapshot",
            ["snapshot_date"],
            unique=True,
        )


def _ensure_job_run(inspector: Any) -> None:
    tables = set(inspector.get_table_names())
    if "job_run" not in tables:
        op.create_table(
            "job_run",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("job_name", sa.String(length=50), nullable=False),
            sa.Column("run_status", sa.String(length=20), nullable=False),
            sa.Column("started_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.Column("finished_at", sa.DateTime(), nullable=True),
            sa.Column("message", sa.Text(), nullable=True),
        )

    indexes = {index["name"] for index in inspector.get_indexes("job_run")}
    if "ix_job_run_job_name_started_at" not in indexes:
        op.create_index("ix_job_run_job_name_started_at", "job_run", ["job_name", "started_at"], unique=False)


def _backfill_dedupe_keys(bind: Any) -> None:
    rows = bind.execute(
        sa.text(
            """
            SELECT
              id,
              snapshot_date,
              report_date,
              company_code,
              report_title,
              provider_name,
              analyst_name,
              source_url
            FROM report_raw_meta
            """
        )
    ).mappings()

    seen_hashes: set[str] = set()
    for row in rows:
        dedupe_key = _build_dedupe_key(row)
        if dedupe_key in seen_hashes:
            dedupe_key = hashlib.sha256(f"{dedupe_key}|{row['id']}".encode("utf-8")).hexdigest()
        seen_hashes.add(dedupe_key)
        bind.execute(
            sa.text("UPDATE report_raw_meta SET dedupe_key = :dedupe_key WHERE id = :id"),
            {"dedupe_key": dedupe_key, "id": row["id"]},
        )


def _build_dedupe_key(row: Any) -> str:
    canonical = "|".join(
        [
            _to_iso_string(row["snapshot_date"]),
            _to_iso_string(row["report_date"]),
            _safe_text(row["company_code"]),
            _safe_text(row["report_title"]).lower(),
            _safe_text(row["provider_name"]).lower(),
            _safe_text(row["analyst_name"]).lower(),
            _safe_text(row["source_url"]).lower(),
        ]
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _to_iso_string(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return str(value)


def _safe_text(value: Any) -> str:
    return "" if value is None else str(value)
