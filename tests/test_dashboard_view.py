from __future__ import annotations

from app.api.dashboard_view import (
    build_sector_cards,
    build_spotlight_cards,
    build_kpi_cards,
    build_layout_mode,
    build_opinion_distribution_detail,
    build_report_heatmap_items,
)


def test_build_opinion_distribution_detail_calculates_percentages() -> None:
    result = build_opinion_distribution_detail({"BUY": 19, "HOLD": 1, "SELL": 0, "NR": 29})

    assert result["total"] == 49
    assert result["dominant_label"] == "NR"

    items = {item["label"]: item for item in result["rows"]}
    assert items["BUY"]["count_text"] == "19건"
    assert items["BUY"]["percent_text"] == "38.8%"
    assert items["HOLD"]["percent_text"] == "2.0%"
    assert items["SELL"]["percent_text"] == "0.0%"
    assert items["NR"]["percent_text"] == "59.2%"


def test_build_opinion_distribution_detail_handles_zero_total() -> None:
    result = build_opinion_distribution_detail({"BUY": 0, "HOLD": 0, "SELL": 0, "NR": 0})

    assert result["total"] == 0
    assert all(item["percent_text"] == "0.0%" for item in result["rows"])


def test_build_kpi_cards_includes_total_reports_first() -> None:
    cards = build_kpi_cards(total_reports=49, kpis={"BUY": 19, "HOLD": 1, "SELL": 0, "NR": 29})

    assert cards[0]["label"] == "전체 리포트"
    assert cards[0]["value_text"] == "49"
    assert [card["label"] for card in cards[1:]] == ["BUY", "HOLD", "SELL", "NR"]


def test_build_report_heatmap_items_shows_single_report_items_without_badge() -> None:
    items = [
        {"company_name": "원익QnC", "company_code": "074600", "report_count": 4, "buy_count": 2},
        {"company_name": "넷마블", "company_code": "251270", "report_count": 2, "buy_count": 2},
        {"company_name": "한국전력", "company_code": "015760", "report_count": 1, "buy_count": 0},
    ]

    result = build_report_heatmap_items(items, limit=10)

    assert [item["company_name"] for item in result] == ["원익QnC", "넷마블", "한국전력"]
    assert result[0]["count_badge"] == "4"
    assert result[0]["emphasis"] == "top"
    assert result[0]["size"] == "xl"
    assert result[2]["count_badge"] is None
    assert result[2]["show_count_badge"] is False
    assert result[2]["is_single_report"] is True
    assert result[2]["size"] == "sm"


def test_build_report_heatmap_items_uses_all_items_by_default() -> None:
    items = [
        {"company_name": f"종목{i}", "company_code": f"{i:06d}", "report_count": 1, "buy_count": 0}
        for i in range(25)
    ]

    result = build_report_heatmap_items(items)

    assert len(result) == 25


def test_build_layout_mode_marks_sector_compact_and_hidden_rows() -> None:
    result = build_layout_mode(
        sector_cards=[{"sector_name_display": "미분류"}],
        total_company_rows=20,
        visible_company_limit=12,
    )

    assert result["sector_compact_mode"] is True
    assert result["visible_company_limit"] == 12
    assert result["hidden_company_rows_count"] == 8


def test_build_spotlight_cards_prefers_summary_lines_over_default_key_points() -> None:
    cards = build_spotlight_cards(
        [
            {
                "company_name": "넷마블",
                "company_code": "251270",
                "sector_name": "Gaming",
                "report_count": 2,
                "buy_count": 2,
                "hold_count": 0,
                "sell_count": 0,
                "nr_count": 0,
                "avg_target_price": 85000,
                "prev_close_price": 54000,
                "avg_upside_pct": 57.41,
                "provider_count": 1,
                "analyst_count": 1,
                "provider_details": [
                    {
                        "provider_name": "미래에셋증권",
                        "analyst_names": ["임희석"],
                    }
                ],
                "spotlight_summaries": [
                    "Google announces Play Store fee cuts",
                    "Netmarble stands to benefit the most from fee cuts",
                ],
            }
        ]
    )

    assert len(cards) == 1
    assert cards[0]["spotlight_summaries"] == [
        "Google announces Play Store fee cuts",
        "Netmarble stands to benefit the most from fee cuts",
    ]
    assert cards[0]["provider_tooltip_text"] == "미래에셋증권 · 임희석"


def test_build_spotlight_cards_hides_analyst_count_and_formats_provider_tooltip() -> None:
    cards = build_spotlight_cards(
        [
            {
                "company_name": "원익QnC",
                "company_code": "074600",
                "sector_name": "IT",
                "report_count": 3,
                "buy_count": 3,
                "hold_count": 0,
                "sell_count": 0,
                "nr_count": 0,
                "avg_target_price": 43667,
                "prev_close_price": 36850,
                "avg_upside_pct": 18.5,
                "provider_count": 2,
                "analyst_count": 2,
                "provider_details": [
                    {
                        "provider_name": "BNK투자증권",
                        "analyst_names": ["이민희"],
                    },
                    {
                        "provider_name": "유안타증권",
                        "analyst_names": ["백길현"],
                    },
                ],
                "spotlight_summaries": ["요약"],
            }
        ]
    )

    card = cards[0]
    assert "애널리스트" not in card["support_line"]
    assert card["provider_tooltip_text"] == "BNK투자증권 · 이민희\n유안타증권 · 백길현"


def test_build_sector_cards_formats_company_rows_with_metrics_and_summary() -> None:
    cards = build_sector_cards(
        [
            {
                "sector_name": "반도체/IT/장비",
                "report_count": 9,
                "avg_upside_pct": 16.7,
                "top_companies": [
                    {
                        "company_name": "원익QnC",
                        "report_count": 4,
                        "buy_count": 4,
                        "hold_count": 0,
                        "sell_count": 0,
                        "nr_count": 0,
                        "avg_target_price": 43000,
                        "prev_close_price": 36850,
                        "avg_upside_pct": 16.7,
                        "spotlight_summaries": [
                            "쿼츠·세정 Top Pick",
                            "OP +68%",
                        ],
                    }
                ],
            }
        ]
    )

    assert len(cards) == 1
    assert cards[0]["report_count_chip"] == "리포트 9건"
    assert len(cards[0]["company_rows"]) == 1
    row = cards[0]["company_rows"][0]
    assert row["opinion_badge_text"] == "BUY(4)"
    assert row["avg_target_price_text"] == "43,000원"
    assert row["prev_close_price_text"] == "36,850원"
    assert row["avg_upside_pct_text"] == "16.7%"
    assert row["summary_text"] == "쿼츠·세정 Top Pick · OP +68%"


def test_build_sector_cards_shortens_long_summary_lines() -> None:
    cards = build_sector_cards(
        [
            {
                "sector_name": "IT",
                "report_count": 1,
                "avg_upside_pct": 18.5,
                "top_companies": [
                    {
                        "company_name": "원익QnC",
                        "report_count": 3,
                        "buy_count": 3,
                        "hold_count": 0,
                        "sell_count": 0,
                        "nr_count": 0,
                        "avg_target_price": 43667,
                        "prev_close_price": 36850,
                        "avg_upside_pct": 18.5,
                        "spotlight_summaries": [
                            "1Q26 영업이익 253억원, 연간으로 999억원(68%YoY) 전망",
                            "목표주가 45,000원으로 상향조정, 투자의견 매수 유지",
                        ],
                    }
                ],
            }
        ]
    )

    row = cards[0]["company_rows"][0]
    assert row["summary_text"] == "1Q26 영업이익 253억원 · 목표주가 45,000원으로 상향조정"
