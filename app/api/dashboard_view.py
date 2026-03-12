from __future__ import annotations

import re
from typing import Any


UNASSIGNED_SECTOR_VALUES = {"", "-", "UNASSIGNED", "unassigned"}


def format_int(value: Any) -> str:
    if value is None:
        return "-"
    return f"{int(round(float(value))):,}"


def format_price(value: Any) -> str:
    if value is None:
        return "-"
    return f"{int(round(float(value))):,}원"


def format_pct(value: Any) -> str:
    if value is None:
        return "-"
    return f"{float(value):.1f}%"


def format_count(value: Any) -> str:
    if value is None:
        return "-"
    return f"{format_int(value)}건"


def display_sector_name(value: Any) -> str:
    if value is None:
        return "미분류"

    text = str(value).strip()
    if not text or text in UNASSIGNED_SECTOR_VALUES:
        return "미분류"
    return text


def pct_tone(value: Any) -> str:
    if value is None:
        return "tone-muted"

    numeric = float(value)
    if numeric > 0:
        return "tone-positive"
    if numeric < 0:
        return "tone-negative"
    return "tone-neutral"


def build_kpi_cards(total_reports: int, kpis: dict[str, int]) -> list[dict[str, str]]:
    items = [("전체 리포트", total_reports, "total")]
    items.extend(
        [
            ("BUY", kpis.get("BUY", 0), "buy"),
            ("HOLD", kpis.get("HOLD", 0), "hold"),
            ("SELL", kpis.get("SELL", 0), "sell"),
            ("NR", kpis.get("NR", 0), "nr"),
        ]
    )
    return [{"label": label, "value_text": format_int(value), "tone": tone} for label, value, tone in items]


def build_report_heatmap_items(items: list[dict[str, Any]], limit: int | None = None) -> list[dict[str, Any]]:
    sorted_items = sorted(
        items,
        key=lambda item: (
            -(item.get("report_count") or 0),
            -(item.get("buy_count") or 0),
            item.get("company_code") or "",
        ),
    )

    heatmap_items: list[dict[str, str]] = []
    visible_items = sorted_items if limit is None else sorted_items[:limit]
    for index, item in enumerate(visible_items, start=1):
        report_count = int(item.get("report_count") or 0)
        if report_count >= 4:
            intensity = "hot"
        elif report_count >= 3:
            intensity = "warm"
        elif report_count >= 2:
            intensity = "mild"
        else:
            intensity = "base"

        emphasis = "top" if index <= 3 and report_count >= 2 else "base"
        if index <= 3 and report_count >= 2:
            size = "xl"
        elif report_count >= 4:
            size = "lg"
        elif report_count >= 2:
            size = "md"
        else:
            size = "sm"
        heatmap_items.append(
            {
                "company_name": item.get("company_name") or "-",
                "company_code": item.get("company_code") or "-",
                "count_badge": str(report_count) if report_count >= 2 else None,
                "show_count_badge": report_count >= 2,
                "is_single_report": report_count <= 1,
                "intensity": intensity,
                "emphasis": emphasis,
                "size": size,
            }
        )
    return heatmap_items


def _build_spotlight_badge(item: dict[str, Any]) -> dict[str, str]:
    buy_count = int(item.get("buy_count") or 0)
    hold_count = int(item.get("hold_count") or 0)
    sell_count = int(item.get("sell_count") or 0)
    nr_count = int(item.get("nr_count") or 0)
    report_count = int(item.get("report_count") or 0)
    provider_count = int(item.get("provider_count") or 0)

    if buy_count > 0 and buy_count >= max(hold_count, sell_count, nr_count):
        return {"text": f"BUY {format_int(buy_count)}건 우세", "tone": "buy"}
    if hold_count > 0 and hold_count >= max(buy_count, sell_count, nr_count):
        return {"text": f"HOLD {format_int(hold_count)}건", "tone": "hold"}
    if sell_count > 0 and sell_count >= max(buy_count, hold_count, nr_count):
        return {"text": f"SELL {format_int(sell_count)}건", "tone": "sell"}
    if report_count >= 3:
        return {"text": "최다 커버", "tone": "accent"}
    if provider_count >= 2:
        return {"text": f"복수 증권사 {format_int(provider_count)}곳", "tone": "accent"}
    return {"text": "핵심 커버", "tone": "neutral"}


def _build_spotlight_key_points(item: dict[str, Any]) -> list[str]:
    points: list[str] = []
    report_count = int(item.get("report_count") or 0)
    buy_count = int(item.get("buy_count") or 0)
    provider_count = int(item.get("provider_count") or 0)
    analyst_count = int(item.get("analyst_count") or 0)
    upside = item.get("avg_upside_pct")
    target_price = item.get("avg_target_price")

    if report_count >= 3:
        points.append("리포트 수 기준 최다 언급")
    elif report_count >= 2:
        points.append("복수 리포트 동시 커버")

    if upside is not None and float(upside) >= 40:
        points.append("평균 상승여력 40% 이상")
    elif upside is not None and float(upside) >= 20:
        points.append("평균 상승여력 20% 이상")

    if buy_count > 0:
        points.append(f"BUY 의견 {format_int(buy_count)}건 집계")
    elif provider_count >= 2:
        points.append("복수 증권사 동시 커버")

    if provider_count >= 2 and len(points) < 3:
        points.append(f"제공처 {format_int(provider_count)}곳, 애널리스트 {format_int(analyst_count)}명")
    elif target_price is not None and len(points) < 3:
        points.append("목표주가 데이터 확보")

    if not points:
        points.append("당일 주요 커버 종목")
    return points[:3]


def _build_spotlight_highlight(item: dict[str, Any]) -> str:
    report_count = int(item.get("report_count") or 0)
    buy_count = int(item.get("buy_count") or 0)
    provider_count = int(item.get("provider_count") or 0)
    upside = item.get("avg_upside_pct")

    if report_count >= 3:
        return f"리포트 {format_int(report_count)}건 · 금일 최다 커버 구간"
    if upside is not None and float(upside) >= 40:
        return f"상승여력 {format_pct(upside)} · 업사이드 상위권"
    if buy_count >= 2:
        return f"BUY {format_int(buy_count)}건 · 매수 의견 집중"
    if provider_count >= 2:
        return f"제공처 {format_int(provider_count)}곳 · 복수 증권사 동시 커버"
    return f"리포트 {format_int(report_count)}건 · 주요 이슈 커버"


def _build_spotlight_support_line(item: dict[str, Any]) -> str:
    sector_name = display_sector_name(item.get("sector_name"))
    provider_count = int(item.get("provider_count") or 0)
    if provider_count >= 2:
        return f"{sector_name} · 복수 증권사 커버"
    return f"{sector_name} · 핵심 커버 종목"


def _build_opinion_badges(item: dict[str, Any]) -> list[dict[str, str]]:
    opinion_items = [
        ("BUY", item.get("buy_count"), "buy"),
        ("HOLD", item.get("hold_count"), "hold"),
        ("SELL", item.get("sell_count"), "sell"),
        ("NR", item.get("nr_count"), "nr"),
    ]
    badges = [
        {"label": label, "value_text": format_int(value), "tone": tone}
        for label, value, tone in opinion_items
        if (value or 0) > 0
    ]
    return badges or [{"label": "NR", "value_text": "0", "tone": "nr"}]


def _build_provider_tooltip_text(item: dict[str, Any]) -> str | None:
    details = item.get("provider_details") or []
    if not details:
        return None

    lines: list[str] = []
    for detail in details:
        provider_name = str(detail.get("provider_name") or "-").strip() or "-"
        analyst_names = [str(name).strip() for name in (detail.get("analyst_names") or []) if str(name).strip()]
        if analyst_names:
            lines.append(f"{provider_name} · {', '.join(analyst_names)}")
        else:
            lines.append(provider_name)
    return "\n".join(lines)


def build_spotlight_cards(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    cards: list[dict[str, Any]] = []
    for index, item in enumerate(items, start=1):
        badge = _build_spotlight_badge(item)
        spotlight_summaries = item.get("spotlight_summaries") or _build_spotlight_key_points(item)
        provider_tooltip_text = _build_provider_tooltip_text(item)
        cards.append(
            {
                "rank": index,
                "company_name": item.get("company_name") or "-",
                "company_code": item.get("company_code") or "-",
                "sector_name_display": display_sector_name(item.get("sector_name")),
                "support_line": _build_spotlight_support_line(item),
                "summary_badge_text": badge["text"],
                "summary_badge_tone": badge["tone"],
                "highlight_text": _build_spotlight_highlight(item),
                "report_count_text": format_count(item.get("report_count")),
                "avg_target_price_text": format_price(item.get("avg_target_price")),
                "prev_close_price_text": format_price(item.get("prev_close_price")),
                "avg_upside_pct_text": format_pct(item.get("avg_upside_pct")),
                "avg_upside_pct_tone": pct_tone(item.get("avg_upside_pct")),
                "provider_count_text": format_int(item.get("provider_count")),
                "provider_tooltip_text": provider_tooltip_text,
                "opinions": _build_opinion_badges(item),
                "spotlight_summaries": spotlight_summaries,
            }
        )
    return cards


def _build_sector_company_opinion_badge(item: dict[str, Any]) -> dict[str, str]:
    buy_count = int(item.get("buy_count") or 0)
    hold_count = int(item.get("hold_count") or 0)
    sell_count = int(item.get("sell_count") or 0)
    nr_count = int(item.get("nr_count") or 0)
    counts = {
        "BUY": buy_count,
        "HOLD": hold_count,
        "SELL": sell_count,
        "NR": nr_count,
    }
    dominant_label = max(counts, key=counts.get)
    dominant_count = counts[dominant_label]
    tone = dominant_label.lower()
    if dominant_count > 1:
        return {"text": f"{dominant_label}({format_int(dominant_count)})", "tone": tone}
    return {"text": dominant_label, "tone": tone}


def _build_sector_company_summary(company: dict[str, Any], max_items: int = 2) -> dict[str, str]:
    summaries = [str(value).strip() for value in (company.get("spotlight_summaries") or []) if str(value).strip()]
    full_text = " · ".join(summaries) if summaries else "-"
    preview_items = [_summarize_sector_summary_line(value) for value in summaries[:max_items]]
    preview_text = " · ".join(item for item in preview_items if item) if summaries else "-"
    return {
        "summary_text": preview_text,
        "summary_full_text": full_text,
    }


def _summarize_sector_summary_line(value: str, max_chars: int = 28) -> str:
    text = value.strip()
    if not text:
        return ""

    primary = re.split(r",\s+|[:;]", text, maxsplit=1)[0].strip()
    if len(primary) <= max_chars:
        return primary
    return f"{primary[: max_chars - 1].rstrip()}…"


def build_sector_cards(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    cards: list[dict[str, Any]] = []
    for item in items:
        company_rows = []
        for company in (item.get("top_companies") or []):
            opinion_badge = _build_sector_company_opinion_badge(company)
            summary_payload = _build_sector_company_summary(company)
            company_rows.append(
                {
                    "company_name": company.get("company_name") or "-",
                    "report_count_text": format_count(company.get("report_count")),
                    "opinion_badge_text": opinion_badge["text"],
                    "opinion_badge_tone": opinion_badge["tone"],
                    "avg_target_price_text": format_price(company.get("avg_target_price")),
                    "prev_close_price_text": format_price(company.get("prev_close_price")),
                    "avg_upside_pct_text": format_pct(company.get("avg_upside_pct")),
                    "avg_upside_pct_tone": pct_tone(company.get("avg_upside_pct")),
                    "summary_text": summary_payload["summary_text"],
                    "summary_full_text": summary_payload["summary_full_text"],
                }
            )

        cards.append(
            {
                "sector_name_display": display_sector_name(item.get("sector_name")),
                "report_count_text": format_count(item.get("report_count")),
                "report_count_chip": f"리포트 {format_int(item.get('report_count') or 0)}건",
                "avg_upside_pct_text": format_pct(item.get("avg_upside_pct")),
                "avg_upside_pct_tone": pct_tone(item.get("avg_upside_pct")),
                "company_rows": company_rows,
            }
        )
    return cards


def build_upside_ranking(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, item in enumerate(items, start=1):
        rows.append(
            {
                "rank": index,
                "company_name": item.get("company_name") or "-",
                "company_code": item.get("company_code") or "-",
                "report_count_text": format_count(item.get("report_count")),
                "avg_upside_pct_text": format_pct(item.get("avg_upside_pct")),
                "avg_upside_pct_tone": pct_tone(item.get("avg_upside_pct")),
            }
        )
    return rows


def build_upside_rows(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return build_upside_ranking(items)


def build_company_table_rows(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in items:
        rows.append(
            {
                "company_code": item.get("company_code") or "-",
                "company_name": item.get("company_name") or "-",
                "sector_name_display": display_sector_name(item.get("sector_name")),
                "report_count_text": format_int(item.get("report_count")),
                "buy_count_text": format_int(item.get("buy_count")),
                "hold_count_text": format_int(item.get("hold_count")),
                "sell_count_text": format_int(item.get("sell_count")),
                "nr_count_text": format_int(item.get("nr_count")),
                "avg_target_price_text": format_price(item.get("avg_target_price")),
                "prev_close_price_text": format_price(item.get("prev_close_price")),
                "avg_upside_pct_text": format_pct(item.get("avg_upside_pct")),
                "avg_upside_pct_tone": pct_tone(item.get("avg_upside_pct")),
            }
        )
    return rows


def build_opinion_distribution_detail(kpis: dict[str, int]) -> dict[str, Any]:
    total = sum(max(int(value), 0) for value in kpis.values())
    rows: list[dict[str, Any]] = []
    tones = {"BUY": "buy", "HOLD": "hold", "SELL": "sell", "NR": "nr"}

    for label in ("BUY", "HOLD", "SELL", "NR"):
        count = int(kpis.get(label, 0))
        percent = round((count / total) * 100, 1) if total > 0 else 0.0
        rows.append(
            {
                "label": label,
                "count": count,
                "count_text": format_count(count),
                "percent_text": format_pct(percent),
                "bar_width_pct": percent,
                "tone": tones[label],
            }
        )

    dominant = max(rows, key=lambda item: item["count"], default=None)
    return {
        "total": total,
        "total_text": format_count(total),
        "rows": rows,
        "dominant_label": dominant["label"] if dominant else None,
    }


def _build_opinion_summary(item: dict[str, Any]) -> str:
    parts: list[str] = []
    if item.get("buy_count"):
        parts.append(f"BUY {format_int(item.get('buy_count'))}")
    if item.get("hold_count"):
        parts.append(f"HOLD {format_int(item.get('hold_count'))}")
    if item.get("sell_count"):
        parts.append(f"SELL {format_int(item.get('sell_count'))}")
    if item.get("nr_count"):
        parts.append(f"NR {format_int(item.get('nr_count'))}")
    return " / ".join(parts) if parts else "-"


def _classify_rating(item: dict[str, Any]) -> str:
    # A: BUY exists and upside is at least 20%
    # B: BUY exists with lower/missing upside, or HOLD is present
    # C: NR-centered / reference-only items
    buy_count = int(item.get("buy_count") or 0)
    hold_count = int(item.get("hold_count") or 0)
    upside = item.get("avg_upside_pct")

    if buy_count > 0 and upside is not None and float(upside) >= 20:
        return "A"
    if buy_count > 0 or hold_count > 0:
        return "B"
    return "C"


def build_rating_buckets(items: list[dict[str, Any]], limit_per_bucket: int = 4) -> list[dict[str, Any]]:
    bucket_meta = {
        "A": {"title": "즉시 검토", "description": "BUY + 상승여력 20% 이상"},
        "B": {"title": "모니터링", "description": "BUY/HOLD 관점 추적"},
        "C": {"title": "참고 관찰", "description": "NR 중심 또는 보류"},
    }
    grouped: dict[str, list[dict[str, Any]]] = {"A": [], "B": [], "C": []}

    for item in items:
        grade = _classify_rating(item)
        grouped[grade].append(
            {
                "company_name": item.get("company_name") or "-",
                "company_code": item.get("company_code") or "-",
                "report_count_text": format_count(item.get("report_count")),
                "avg_upside_pct_text": format_pct(item.get("avg_upside_pct")),
                "avg_upside_pct_tone": pct_tone(item.get("avg_upside_pct")),
                "opinion_summary": _build_opinion_summary(item),
                "_sort_report_count": item.get("report_count") or 0,
                "_sort_upside": float(item.get("avg_upside_pct") or -999999),
            }
        )

    buckets: list[dict[str, Any]] = []
    for grade in ("A", "B", "C"):
        ranked_items = sorted(
            grouped[grade],
            key=lambda item: (-item["_sort_report_count"], -item["_sort_upside"], item["company_code"]),
        )[:limit_per_bucket]
        for item in ranked_items:
            item.pop("_sort_report_count", None)
            item.pop("_sort_upside", None)
        buckets.append(
            {
                "grade": grade,
                "title": bucket_meta[grade]["title"],
                "description": bucket_meta[grade]["description"],
                "rows": ranked_items,
            }
        )
    return buckets


def build_summary_notes(
    *,
    spotlight_cards: list[dict[str, Any]],
    opinion_distribution: dict[str, Any],
    sector_cards: list[dict[str, Any]],
) -> list[str]:
    notes: list[str] = []

    if spotlight_cards:
        top_item = spotlight_cards[0]
        notes.append(f"{top_item['company_name']}이(가) {top_item['report_count_text']}로 최다 언급됐습니다.")

    dominant_label = opinion_distribution.get("dominant_label")
    dominant_item = next(
        (item for item in opinion_distribution.get("rows", []) if item["label"] == dominant_label),
        None,
    )
    if dominant_item and dominant_item["count"] > 0:
        notes.append(f"{dominant_item['label']} 비중이 {dominant_item['percent_text']}로 가장 큽니다.")

    if any(item["sector_name_display"] == "미분류" for item in sector_cards):
        notes.append("섹터 매핑이 없는 종목은 미분류로 표시했습니다.")
    elif sector_cards:
        notes.append(f"{sector_cards[0]['sector_name_display']} 섹터가 가장 활발합니다.")

    return notes[:3]


def build_layout_mode(*, sector_cards: list[dict[str, Any]], total_company_rows: int, visible_company_limit: int = 12) -> dict[str, Any]:
    sector_compact_mode = len(sector_cards) <= 2
    hidden_company_rows_count = max(total_company_rows - visible_company_limit, 0)
    return {
        "sector_compact_mode": sector_compact_mode,
        "sector_display_mode": "compact" if sector_compact_mode else "normal",
        "visible_company_limit": visible_company_limit,
        "hidden_company_rows_count": hidden_company_rows_count,
        "bottom_summary_layout": "triple",
    }
