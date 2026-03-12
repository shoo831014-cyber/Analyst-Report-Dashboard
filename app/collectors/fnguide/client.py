from __future__ import annotations

import asyncio
import logging
from datetime import date
from typing import Any

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_fixed

from app.collectors.base import BaseCollector
from app.collectors.fnguide.parser_playwright import parse_report_rows_with_playwright
from app.collectors.fnguide.parser_requests import parse_report_rows
from app.collectors.fnguide.selectors import (
    DEFAULT_TIMEOUT_SECONDS,
    REQUEST_HEADERS,
    SUMMARY_API_URL,
    SUMMARY_PAGE_URL,
    build_playwright_url,
    build_summary_params,
)

logger = logging.getLogger(__name__)


class FnGuideCollector(BaseCollector):
    source_name = "fnguide"

    def __init__(self, timeout: float = DEFAULT_TIMEOUT_SECONDS) -> None:
        self.timeout = timeout

    def collect(self, snapshot_date: date) -> list[dict[str, Any]]:
        return self.fetch_with_requests(snapshot_date)

    def fetch_html(self, url: str | None = None) -> str:
        target_url = url or SUMMARY_PAGE_URL
        return self._request_text("GET", target_url)

    def fetch_with_requests(self, snapshot_date: date) -> list[dict[str, Any]]:
        payload = self._request_text("GET", SUMMARY_API_URL, params=build_summary_params(snapshot_date))
        rows = parse_report_rows(payload)
        logger.info("FnGuide requests fetch completed. snapshot_date=%s rows=%s", snapshot_date.isoformat(), len(rows))
        return rows

    def fetch_with_playwright(self, snapshot_date: date) -> list[dict[str, Any]]:
        url = build_playwright_url(snapshot_date)
        logger.info("FnGuide Playwright fetch started. snapshot_date=%s url=%s", snapshot_date.isoformat(), url)
        rows = asyncio.run(parse_report_rows_with_playwright(url))
        logger.info("FnGuide Playwright fetch completed. snapshot_date=%s rows=%s", snapshot_date.isoformat(), len(rows))
        return rows

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_fixed(2),
        retry=retry_if_exception_type(RuntimeError),
    )
    def _request_text(self, method: str, url: str, params: dict[str, Any] | None = None) -> str:
        try:
            with httpx.Client(timeout=self.timeout, follow_redirects=True, headers=REQUEST_HEADERS) as client:
                response = client.request(method, url, params=params)
                response.raise_for_status()
                return response.text
        except httpx.HTTPStatusError as exc:
            logger.warning("FnGuide HTTP status error. url=%s status=%s", exc.request.url, exc.response.status_code)
            raise RuntimeError(
                f"FnGuide request failed with status {exc.response.status_code}: {exc.request.url}"
            ) from exc
        except httpx.TimeoutException as exc:
            logger.warning("FnGuide request timed out. url=%s", url)
            raise RuntimeError(f"FnGuide request timed out: {url}") from exc
        except httpx.HTTPError as exc:
            logger.warning("FnGuide request error. url=%s error=%s", url, exc)
            raise RuntimeError(f"FnGuide request error: {url}") from exc
