from __future__ import annotations

from datetime import UTC, datetime

from app.db.models import CompanyMaster
from app.services.sector_service import SectorService


def utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def test_sector_service_prefers_workbook_e_column_mapping(session_factory) -> None:
    with session_factory() as session:
        session.add(
            CompanyMaster(
                company_code="074600",
                company_name="원익QnC",
                sector_name_fnguide="LegacySector",
                is_active=True,
                updated_at=utcnow_naive(),
            )
        )
        session.commit()

        service = SectorService(workbook_sector_map={"074600": "IT"})
        sector_map = service.get_sector_map(session, {"074600"})

    assert sector_map["074600"] == "IT"


def test_sector_service_normalizes_grouped_sector_names(session_factory) -> None:
    with session_factory() as session:
        session.add_all(
            [
                CompanyMaster(
                    company_code="015760",
                    company_name="한국전력",
                    sector_name_fnguide="유틸리티",
                    is_active=True,
                    updated_at=utcnow_naive(),
                ),
                CompanyMaster(
                    company_code="005180",
                    company_name="빙그레",
                    sector_name_fnguide="필수소비재",
                    is_active=True,
                    updated_at=utcnow_naive(),
                ),
                CompanyMaster(
                    company_code="091990",
                    company_name="셀트리온헬스케어",
                    sector_name_fnguide="의료",
                    is_active=True,
                    updated_at=utcnow_naive(),
                ),
            ]
        )
        session.commit()

        service = SectorService()
        sector_map = service.get_sector_map(session, {"015760", "005180", "091990"})

    assert sector_map["015760"] == "에너지/유틸리티"
    assert sector_map["005180"] == "소비재"
    assert sector_map["091990"] == "헬스케어/바이오"


def test_sector_service_assigns_manual_healthcare_bio_overrides() -> None:
    service = SectorService()

    assert (
        service.resolve_sector_name(
            company_code="491000",
            company_name="리브스메드",
            report_titles=[],
            company_master_sector=None,
        )
        == "헬스케어/바이오"
    )
    assert (
        service.resolve_sector_name(
            company_code="000000",
            company_name="알지노믹스",
            report_titles=[],
            company_master_sector=None,
        )
        == "헬스케어/바이오"
    )
