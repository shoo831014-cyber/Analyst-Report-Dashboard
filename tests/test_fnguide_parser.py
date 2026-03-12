from app.collectors.fnguide.parser_requests import parse_report_rows


HTML_FIXTURE = """
<table id="rptSmrSummary">
  <tbody>
    <tr data-rpt_id="1078052" data-cmp_cd="251270">
      <td class="c clf">2026/03/06</td>
      <td class="l nopre">
        <dl class="um_tdinsm">
          <dt>
            <a href="javascript:;" class="snapshotLink">
              넷마블 <span class="txt1">251270</span>
            </a>
            <span class="txt2"> - Biggest beneficiary of fee cuts</span>
          </dt>
        </dl>
      </td>
      <td class="c nopre2"><span class="gpbox">BUY</span></td>
      <td class="r nopre2"><span class="gpbox">85,000</span></td>
      <td class="r">54,000</td>
      <td class="cle c nopre2">
        <span class="gpbox">미래에셋증권<br />임희석</span>
      </td>
    </tr>
  </tbody>
</table>
"""

JSON_FIXTURE = """
{
  "dataset": {
    "data": [
      {
        "DT": "2026/03/06",
        "CMP_CD": "251270",
        "RPT_ID": 1078052,
        "RPT_TITLE": "Biggest beneficiary of fee cuts",
        "COMMENT": "▶ Google announces Play Store fee cuts\\r\\n▶ Netmarble stands to benefit the most from fee cuts",
        "CMP_NM_KOR": "넷마블",
        "BRK_NM_KOR": "미래에셋증권",
        "ANL_NM_KOR": "임희석",
        "RECOMM_NM": "BUY",
        "TARGET_PRC": "85,000",
        "CLOSE_PRC": "54,000"
      }
    ]
  }
}
"""


def test_parse_report_rows_from_html_fixture() -> None:
    rows = parse_report_rows(HTML_FIXTURE)

    assert len(rows) == 1
    row = rows[0]
    assert row["company_code"] == "251270"
    assert row["company_name"] == "넷마블"
    assert row["report_title"] == "Biggest beneficiary of fee cuts"
    assert row["provider_name"] == "미래에셋증권"
    assert row["analyst_name"] == "임희석"
    assert row["opinion_raw"] == "BUY"
    assert row["target_price_raw"] == "85,000"
    assert row["summary_lines"] == []


def test_parse_report_rows_from_json_fixture() -> None:
    rows = parse_report_rows(JSON_FIXTURE)

    assert len(rows) == 1
    row = rows[0]
    assert row["company_code"] == "251270"
    assert row["company_name"] == "넷마블"
    assert row["report_title"] == "Biggest beneficiary of fee cuts"
    assert row["summary_lines"] == [
        "Google announces Play Store fee cuts",
        "Netmarble stands to benefit the most from fee cuts",
    ]
    assert row["source_url"] is not None
