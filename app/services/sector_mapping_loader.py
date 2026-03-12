from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import zipfile
import xml.etree.ElementTree as ET

NS = {
    "a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}


def normalize_company_code(value: str | None) -> str | None:
    if value is None:
        return None

    text = str(value).strip().upper()
    if text.startswith("A") and len(text) > 1:
        text = text[1:]
    return text or None


@lru_cache(maxsize=4)
def load_sector_mapping_from_xlsx(path_text: str) -> dict[str, str]:
    path = Path(path_text)
    if not path.exists():
        return {}

    with zipfile.ZipFile(path) as workbook_zip:
        shared_strings = _load_shared_strings(workbook_zip)
        sheet_path = _find_first_sheet_path(workbook_zip)
        if sheet_path is None:
            return {}

        root = ET.fromstring(workbook_zip.read(sheet_path))
        sheet_data = root.find("a:sheetData", NS)
        if sheet_data is None:
            return {}

        mapping: dict[str, str] = {}
        for row in list(sheet_data)[1:]:
            cells = _read_row_cells(row, shared_strings)
            company_code = normalize_company_code(cells.get("A"))
            sector_name = (cells.get("E") or "").strip()
            if company_code and sector_name:
                mapping[company_code] = sector_name
        return mapping


def _load_shared_strings(workbook_zip: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in workbook_zip.namelist():
        return []

    root = ET.fromstring(workbook_zip.read("xl/sharedStrings.xml"))
    values: list[str] = []
    for item in root.findall("a:si", NS):
        values.append("".join(node.text or "" for node in item.iterfind(".//a:t", NS)))
    return values


def _find_first_sheet_path(workbook_zip: zipfile.ZipFile) -> str | None:
    workbook = ET.fromstring(workbook_zip.read("xl/workbook.xml"))
    relationships = ET.fromstring(workbook_zip.read("xl/_rels/workbook.xml.rels"))
    relationship_map = {rel.attrib["Id"]: rel.attrib["Target"] for rel in relationships}
    sheets = workbook.find("a:sheets", NS)
    if sheets is None or len(sheets) == 0:
        return None

    first_sheet = sheets[0]
    relationship_id = first_sheet.attrib.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
    if not relationship_id:
        return None

    target = relationship_map.get(relationship_id)
    if not target:
        return None

    target = target.lstrip("/")
    if not target.startswith("xl/"):
        target = f"xl/{target}"
    return target


def _read_row_cells(row: ET.Element, shared_strings: list[str]) -> dict[str, str]:
    values: dict[str, str] = {}
    for cell in row.findall("a:c", NS):
        reference = cell.attrib.get("r", "")
        column = "".join(character for character in reference if character.isalpha())
        if not column:
            continue
        values[column] = _read_cell_value(cell, shared_strings)
    return values


def _read_cell_value(cell: ET.Element, shared_strings: list[str]) -> str:
    cell_type = cell.attrib.get("t")
    value = cell.find("a:v", NS)
    if value is not None:
        raw = value.text or ""
        if cell_type == "s" and raw.isdigit():
            return shared_strings[int(raw)]
        return raw

    inline_string = cell.find("a:is", NS)
    if inline_string is None:
        return ""
    return "".join(node.text or "" for node in inline_string.iterfind(".//a:t", NS))
