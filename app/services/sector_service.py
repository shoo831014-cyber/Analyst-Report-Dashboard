from __future__ import annotations

from collections.abc import Sequence
import os

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.models import CompanyMaster
from app.services.sector_mapping_loader import load_sector_mapping_from_xlsx

SECTOR_NORMALIZATION_MAP: dict[str, str] = {
    "에너지": "에너지/유틸리티",
    "유틸리티": "에너지/유틸리티",
    "자유소비재": "소비재",
    "필수소비재": "소비재",
    "소비재": "소비재",
    "의료": "헬스케어/바이오",
    "헬스케어": "헬스케어/바이오",
    "바이오": "헬스케어/바이오",
    "헬스케어/바이오": "헬스케어/바이오",
}

MANUAL_COMPANY_CODE_SECTOR_MAP: dict[str, str] = {
    "491000": "헬스케어/바이오",
}

MANUAL_COMPANY_SECTOR_MAP: dict[str, str] = {
    "원익QnC": "IT",
    "테크윙": "IT",
    "원익IPS": "IT",
    "넷마블": "미디어",
    "NAVER": "미디어",
    "카카오": "미디어",
    "한국전력": "유틸리티",
    "S-Oil": "에너지",
    "포스코퓨처엠": "소재",
    "CJ대한통운": "산업재",
    "리브스메드": "헬스케어/바이오",
    "알지노믹스": "헬스케어/바이오",
}

TITLE_KEYWORD_SECTOR_RULES: list[tuple[tuple[str, ...], str]] = [
    (("반도체", "메모리", "HBM", "장비", "패키지", "AI"), "IT"),
    (("게임", "콘텐츠", "광고", "커머스", "플랫폼", "미디어"), "미디어"),
    (("은행", "보험", "증권", "리츠", "지주", "금융"), "금융"),
    (("발전", "전력", "에너지", "정유", "태양광", "유틸"), "에너지/유틸리티"),
    (("바이오", "헬스", "의료", "제약"), "헬스케어/바이오"),
    (("철강", "물류", "산업재", "기계", "화학", "소재"), "산업재"),
]


class SectorService:
    def __init__(self, workbook_sector_map: dict[str, str] | None = None) -> None:
        self.workbook_sector_map = workbook_sector_map

    def get_sector_map(self, session: Session, company_codes: set[str]) -> dict[str, str | None]:
        if not company_codes:
            return {}

        rows = session.execute(
            select(CompanyMaster.company_code, CompanyMaster.sector_name_fnguide).where(
                CompanyMaster.company_code.in_(company_codes)
            )
        ).all()
        db_map = {company_code: sector_name for company_code, sector_name in rows}
        workbook_map = self._get_workbook_sector_map()

        return {
            company_code: self.normalize_sector_name(workbook_map.get(company_code) or db_map.get(company_code))
            for company_code in company_codes
        }

    def resolve_sector_name(
        self,
        *,
        company_code: str,
        company_name: str | None,
        report_titles: Sequence[str | None],
        company_master_sector: str | None,
    ) -> str | None:
        if company_master_sector:
            return self.normalize_sector_name(company_master_sector)

        manual_by_code = MANUAL_COMPANY_CODE_SECTOR_MAP.get(company_code.strip())
        if manual_by_code:
            return manual_by_code

        if company_name:
            manual = MANUAL_COMPANY_SECTOR_MAP.get(company_name.strip())
            if manual:
                return manual

        joined_titles = " ".join(title for title in report_titles if title).lower()
        for keywords, sector_name in TITLE_KEYWORD_SECTOR_RULES:
            if any(keyword.lower() in joined_titles for keyword in keywords):
                return sector_name
        return None

    def map_sector(self, session: Session, company_code: str) -> str | None:
        return self.get_sector_map(session, {company_code}).get(company_code)

    def _get_workbook_sector_map(self) -> dict[str, str]:
        if self.workbook_sector_map is not None:
            return {
                company_code: self.normalize_sector_name(sector_name) or sector_name
                for company_code, sector_name in self.workbook_sector_map.items()
            }
        if os.getenv("PYTEST_CURRENT_TEST"):
            return {}

        settings = get_settings()
        return {
            company_code: self.normalize_sector_name(sector_name) or sector_name
            for company_code, sector_name in load_sector_mapping_from_xlsx(str(settings.sector_mapping_xlsx_path)).items()
        }

    def normalize_sector_name(self, sector_name: str | None) -> str | None:
        if sector_name is None:
            return None
        normalized = sector_name.strip()
        if not normalized:
            return None
        return SECTOR_NORMALIZATION_MAP.get(normalized, normalized)
