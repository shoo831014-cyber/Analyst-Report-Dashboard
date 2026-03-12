from __future__ import annotations

from typing import Any
from urllib.parse import parse_qs, urlparse

from app.collectors.fnguide.parser_requests import normalize_text, parse_date_value, parse_report_rows
from app.collectors.fnguide.selectors import (
    DEFAULT_COMPANY_CODE,
    DEFAULT_USER_AGENT,
    PLAYWRIGHT_FROM_DATE_SELECTOR,
    PLAYWRIGHT_READY_SELECTOR,
    PLAYWRIGHT_SEARCH_BUTTON_SELECTOR,
    PLAYWRIGHT_TO_DATE_SELECTOR,
    REPORT_ROW_SELECTORS,
    SUMMARY_API_PATH,
    SUMMARY_PAGE_URL,
    build_report_reference_url,
)


async def parse_report_rows_with_playwright(url: str) -> list[dict[str, Any]]:
    try:
        from playwright.async_api import async_playwright
    except ImportError as exc:  # pragma: no cover - depends on local install
        raise RuntimeError("Playwright is not installed. Run `python -m playwright install`.") from exc

    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    cmp_cd = query.get("cmp_cd", [DEFAULT_COMPANY_CODE])[0]
    sdt = query.get("sdt", [""])[0]
    edt = query.get("edt", [sdt])[0]

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        page = await browser.new_page(user_agent=DEFAULT_USER_AGENT, locale="ko-KR")
        try:
            await page.goto(f"{SUMMARY_PAGE_URL}?cmp_cd={cmp_cd}", wait_until="networkidle", timeout=30000)
            await page.wait_for_selector(PLAYWRIGHT_READY_SELECTOR, timeout=30000)

            if sdt:
                await _set_input_value(page, PLAYWRIGHT_FROM_DATE_SELECTOR, _format_input_date(sdt))
            if edt:
                await _set_input_value(page, PLAYWRIGHT_TO_DATE_SELECTOR, _format_input_date(edt))

            async with page.expect_response(
                lambda response: SUMMARY_API_PATH in response.url and response.status == 200,
                timeout=30000,
            ) as response_info:
                await page.locator(PLAYWRIGHT_SEARCH_BUTTON_SELECTOR).click()

            response = await response_info.value
            payload = await response.text()
            parsed_rows = parse_report_rows(payload)
            if parsed_rows:
                return parsed_rows

            await page.wait_for_timeout(750)
            raw_rows = await page.evaluate(
                """
                (selectors) => {
                  const selector = selectors.find((candidate) => document.querySelector(candidate));
                  if (!selector) {
                    return [];
                  }

                  const rows = Array.from(document.querySelectorAll(selector));
                  return rows.map((row) => {
                    const cells = Array.from(row.querySelectorAll("td"));
                    if (cells.length < 6) {
                      return null;
                    }

                    const companyLink = row.querySelector("a.snapshotLink");
                    const codeEl = companyLink ? companyLink.querySelector(".txt1") : null;
                    const titleEl = row.querySelector("span.txt2");
                    const providerCellTexts = cells[5]
                      ? Array.from(cells[5].childNodes)
                          .map((node) => node.textContent || "")
                          .map((value) => value.trim())
                          .filter(Boolean)
                      : [];

                    let companyName = "";
                    if (companyLink) {
                      const firstChild = companyLink.childNodes.length > 0 ? companyLink.childNodes[0].textContent : "";
                      companyName = (firstChild || companyLink.textContent || "").trim();
                    }

                    let reportTitle = titleEl ? titleEl.textContent.trim() : "";
                    if (reportTitle.startsWith("-")) {
                      reportTitle = reportTitle.slice(1).trim();
                    }

                    return {
                      report_id: row.dataset.rpt_id || null,
                      report_date: cells[0] ? cells[0].textContent.trim() : null,
                      company_code: row.dataset.cmp_cd || (codeEl ? codeEl.textContent.trim() : null),
                      company_name: companyName || null,
                      report_title: reportTitle || null,
                      summary_lines: [],
                      analyst_name: providerCellTexts.length > 1 ? providerCellTexts[1] : null,
                      provider_name: providerCellTexts.length > 0 ? providerCellTexts[0] : null,
                      opinion_raw: cells[2] ? cells[2].textContent.trim() : null,
                      target_price_raw: cells[3] ? cells[3].textContent.trim() : null,
                      prev_close_price_raw: cells[4] ? cells[4].textContent.trim() : null
                    };
                  }).filter(Boolean);
                }
                """,
                list(REPORT_ROW_SELECTORS),
            )
        finally:
            await page.close()
            await browser.close()

    rows: list[dict[str, Any]] = []
    for item in raw_rows:
        if not isinstance(item, dict):
            continue
        report_id = item.get("report_id")
        company_code = normalize_text(item.get("company_code"))
        rows.append(
            {
                "report_id": report_id,
                "report_date": parse_date_value(item.get("report_date")),
                "company_code": company_code,
                "company_name": normalize_text(item.get("company_name")),
                "report_title": normalize_text(item.get("report_title")),
                "summary_lines": item.get("summary_lines") or [],
                "analyst_name": normalize_text(item.get("analyst_name")),
                "provider_name": normalize_text(item.get("provider_name")),
                "opinion_raw": normalize_text(item.get("opinion_raw")),
                "target_price_raw": normalize_text(item.get("target_price_raw")),
                "prev_close_price_raw": normalize_text(item.get("prev_close_price_raw")),
                "source_url": build_report_reference_url(company_code, report_id),
            }
        )

    return rows


async def _set_input_value(page: Any, selector: str, value: str) -> None:
    await page.locator(selector).evaluate(
        """
        (element, inputValue) => {
          element.value = inputValue;
          element.dispatchEvent(new Event("input", { bubbles: true }));
          element.dispatchEvent(new Event("change", { bubbles: true }));
        }
        """,
        value,
    )


def _format_input_date(value: str) -> str:
    if len(value) == 8:
        return f"{value[:4]}/{value[4:6]}/{value[6:]}"
    return value
