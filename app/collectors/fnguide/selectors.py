from __future__ import annotations

from datetime import date
from urllib.parse import urlencode

BASE_URL = "https://wcomp.fnguide.com"
SUMMARY_PAGE_PATH = "/Report/ReportSummary"
SUMMARY_API_PATH = "/Report/getRptSmrSummary"

SUMMARY_PAGE_URL = f"{BASE_URL}{SUMMARY_PAGE_PATH}"
SUMMARY_API_URL = f"{BASE_URL}{SUMMARY_API_PATH}"

DEFAULT_COMPANY_CODE = "001390"
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)
DEFAULT_TIMEOUT_SECONDS = 20.0
DEFAULT_ORDER_COLUMN = 0
DEFAULT_ORDER_TYPE = "D"
DEFAULT_SEARCH_TYPE = "all"

REQUEST_HEADERS = {
    "User-Agent": DEFAULT_USER_AGENT,
    "Accept": "application/json, text/plain, */*",
    "Referer": f"{SUMMARY_PAGE_URL}?cmp_cd={DEFAULT_COMPANY_CODE}",
}

REPORT_ROW_SELECTORS = (
    "#rptSmrSummary tbody tr",
    "table#rptSmrSummary tbody tr",
    ".um_table table tbody tr",
)
NO_DATA_TEXTS = (
    "\uac80\uc0c9\ub41c \ub9ac\ud3ec\ud2b8\uac00 \uc5c6\uc2b5\ub2c8\ub2e4.",
    "\uac80\uc0c9\ub41c \ub9ac\ud3ec\ud2b8\uac00 \uc5c6\uc2b5\ub2c8\ub2e4",
)
PLAYWRIGHT_READY_SELECTOR = "#rptSmrSummary"
PLAYWRIGHT_SEARCH_BUTTON_SELECTOR = "#btnSearch"
PLAYWRIGHT_FROM_DATE_SELECTOR = "#inFromDate"
PLAYWRIGHT_TO_DATE_SELECTOR = "#inToDate"

MIN_EXPECTED_COLUMNS = 6
REQUIRED_ROW_FIELDS = ("company_name", "report_title")
MAX_ALLOWED_MISSING_RATIO = 0.4


def build_summary_params(snapshot_date: date) -> dict[str, str | int]:
    date_text = snapshot_date.strftime("%Y%m%d")
    return {
        "search_typ": DEFAULT_SEARCH_TYPE,
        "sdt": date_text,
        "edt": date_text,
        "search": "",
        "order_col": DEFAULT_ORDER_COLUMN,
        "order_typ": DEFAULT_ORDER_TYPE,
    }


def build_playwright_url(snapshot_date: date, cmp_cd: str = DEFAULT_COMPANY_CODE) -> str:
    date_text = snapshot_date.strftime("%Y%m%d")
    return f"{SUMMARY_PAGE_URL}?{urlencode({'cmp_cd': cmp_cd, 'sdt': date_text, 'edt': date_text})}"


def build_report_reference_url(company_code: str | None, report_id: str | int | None) -> str:
    params: dict[str, str] = {}
    if company_code:
        params["cmp_cd"] = company_code
    if report_id:
        params["rpt_id"] = str(report_id)
    query = urlencode(params)
    if not query:
        return SUMMARY_PAGE_URL
    return f"{SUMMARY_PAGE_URL}?{query}"
