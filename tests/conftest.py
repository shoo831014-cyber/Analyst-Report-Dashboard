from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, date, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db import models  # noqa: F401
from app.db.base import Base
from app.db.models import CompanyMaster, ReportRawMeta
from app.db.session import get_db_session
from app.main import create_app


def utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


@pytest.fixture()
def session_factory(tmp_path) -> Generator[sessionmaker, None, None]:
    database_path = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{database_path}", connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, class_=Session)
    Base.metadata.create_all(bind=engine)
    try:
        yield TestingSessionLocal
    finally:
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture()
def db_session(session_factory: sessionmaker) -> Generator[Session, None, None]:
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(session_factory: sessionmaker, monkeypatch: pytest.MonkeyPatch) -> Generator[TestClient, None, None]:
    monkeypatch.setattr("app.main.init_db", lambda: None)
    app = create_app()

    def override_get_db() -> Generator[Session, None, None]:
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db_session] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def seeded_snapshot_source_data(session_factory: sessionmaker) -> dict[str, date]:
    latest_date = date(2026, 3, 6)
    previous_date = date(2026, 3, 5)

    with session_factory() as session:
        session.add_all(
            [
                CompanyMaster(
                    company_code="035420",
                    company_name="NAVER",
                    sector_name_fnguide="Internet",
                    is_active=True,
                    updated_at=utcnow_naive(),
                ),
                CompanyMaster(
                    company_code="251270",
                    company_name="넷마블",
                    sector_name_fnguide="Gaming",
                    is_active=True,
                    updated_at=utcnow_naive(),
                ),
                CompanyMaster(
                    company_code="015760",
                    company_name="한국전력",
                    sector_name_fnguide=None,
                    is_active=True,
                    updated_at=utcnow_naive(),
                ),
            ]
        )
        session.add_all(
            [
                ReportRawMeta(
                    snapshot_date=latest_date,
                    report_date=latest_date,
                    company_code="035420",
                    company_name="NAVER",
                    report_title="커머스 왕좌를 향해",
                    analyst_name="김혜영",
                    provider_name="다올투자증권",
                    opinion_raw="BUY",
                    opinion_std="BUY",
                    target_price_raw="360,000",
                    target_price_value=360000,
                    prev_close_price_raw="222,500",
                    prev_close_price_value=222500,
                    source_url="https://example.com/r1",
                    dedupe_key="raw-1",
                    collected_at=utcnow_naive(),
                ),
                ReportRawMeta(
                    snapshot_date=latest_date,
                    report_date=latest_date,
                    company_code="035420",
                    company_name="NAVER",
                    report_title="Users moving from Coupang to Naver and Kurly",
                    analyst_name="오동환",
                    provider_name="삼성증권",
                    opinion_raw="BUY",
                    opinion_std="BUY",
                    target_price_raw="330,000",
                    target_price_value=330000,
                    prev_close_price_raw="222,500",
                    prev_close_price_value=222500,
                    source_url="https://example.com/r2",
                    dedupe_key="raw-2",
                    collected_at=utcnow_naive(),
                ),
                ReportRawMeta(
                    snapshot_date=latest_date,
                    report_date=latest_date,
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
                    source_url="https://example.com/r3",
                    dedupe_key="raw-3",
                    collected_at=utcnow_naive(),
                ),
                ReportRawMeta(
                    snapshot_date=latest_date,
                    report_date=latest_date,
                    company_code="251270",
                    company_name="넷마블",
                    report_title="Biggest beneficiary of fee cuts",
                    analyst_name="임희석",
                    provider_name="미래에셋증권",
                    opinion_raw="매수",
                    opinion_std="BUY",
                    target_price_raw="85,000",
                    target_price_value=85000,
                    prev_close_price_raw="54,000",
                    prev_close_price_value=54000,
                    source_url="https://example.com/r4",
                    dedupe_key="raw-4",
                    collected_at=utcnow_naive(),
                ),
                ReportRawMeta(
                    snapshot_date=latest_date,
                    report_date=latest_date,
                    company_code="015760",
                    company_name="한국전력",
                    report_title="기대와 우려 사이",
                    analyst_name="류제현",
                    provider_name="미래에셋증권",
                    opinion_raw="중립",
                    opinion_std="HOLD",
                    target_price_raw="51,000",
                    target_price_value=51000,
                    prev_close_price_raw="48,800",
                    prev_close_price_value=48800,
                    source_url="https://example.com/r5",
                    dedupe_key="raw-5",
                    collected_at=utcnow_naive(),
                ),
                ReportRawMeta(
                    snapshot_date=previous_date,
                    report_date=previous_date,
                    company_code="251270",
                    company_name="넷마블",
                    report_title="전일 데이터",
                    analyst_name="임희석",
                    provider_name="미래에셋증권",
                    opinion_raw="매수",
                    opinion_std="BUY",
                    target_price_raw="82,000",
                    target_price_value=82000,
                    prev_close_price_raw="53,000",
                    prev_close_price_value=53000,
                    source_url="https://example.com/r6",
                    dedupe_key="raw-6",
                    collected_at=utcnow_naive(),
                ),
            ]
        )
        session.commit()

    return {"latest_date": latest_date, "previous_date": previous_date}
