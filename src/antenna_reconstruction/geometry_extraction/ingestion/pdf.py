"""PDF ingestion that preserves table structure.

pypdf flattens tables into unordered text, which destroys the symbol->value
association that parameter tables carry (the single richest source of
authoritative dimensions in an antenna paper). pdfplumber keeps the cell
grid, so a "Parameters | Dimensions (mm)" table survives as real key/value
pairs.
"""
import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

# A symbol like W, L, S1, H_1, F_W, GL. Deliberately narrow: parameter symbols
# in these papers are 1-3 chars plus an optional digit/letter subscript.
SYMBOL_RE = re.compile(r"^([A-Za-z]{1,3})[\s_]*([0-9]{1,2}|[A-Za-z])?$")
NUMBER_RE = re.compile(r"^[-+]?[0-9]*\.?[0-9]+$")
UNIT_IN_HEADER_RE = re.compile(r"\((m?m)m?\s*\)|\b(mm|cm|m)\b", re.IGNORECASE)


class RawTable(BaseModel):
    page: int
    index: int
    rows: List[List[Optional[str]]] = Field(default_factory=list)


class ParameterTable(BaseModel):
    """A table parsed into authoritative symbol -> value pairs."""
    page: int
    index: int
    unit: str = "mm"
    # Set when the table describes several design variants (one per row); the
    # label identifies which variant these values belong to.
    variant: Optional[str] = None
    values: Dict[str, float] = Field(default_factory=dict)
    # Where each symbol came from, for provenance.
    provenance: Dict[str, Dict[str, Any]] = Field(default_factory=dict)


class PdfDocument(BaseModel):
    source_id: str
    text: str = ""
    tables: List[RawTable] = Field(default_factory=list)
    parameter_tables: List[ParameterTable] = Field(default_factory=list)

    def merged_parameters(self) -> Dict[str, float]:
        """All parameter tables merged. Earlier tables win on conflict."""
        merged: Dict[str, float] = {}
        for pt in self.parameter_tables:
            for k, v in pt.values.items():
                merged.setdefault(k, v)
        return merged


def _clean(cell: Optional[str]) -> str:
    if cell is None:
        return ""
    return re.sub(r"\s+", " ", cell).strip()


def normalize_symbol(raw: str) -> Optional[str]:
    """'S 1' / 'S_1' / 'F W' -> 'S1' / 'FW'. Returns None if not a symbol."""
    s = _clean(raw)
    if not s or len(s) > 6:
        return None
    m = SYMBOL_RE.match(s)
    if not m:
        return None
    head, sub = m.group(1), m.group(2) or ""
    return f"{head}{sub}"


def _parse_number(raw: str) -> Optional[float]:
    s = _clean(raw)
    # Tolerate a trailing unit inside the value cell, e.g. "6.5 mm".
    s = re.sub(r"\s*(mm|cm|m)\s*$", "", s, flags=re.IGNORECASE)
    if not NUMBER_RE.match(s):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _detect_unit(rows: List[List[Optional[str]]]) -> str:
    for row in rows[:3]:
        for cell in row:
            m = UNIT_IN_HEADER_RE.search(_clean(cell))
            if m:
                found = (m.group(1) or m.group(2) or "").lower()
                if found in {"mm", "cm", "m"}:
                    return found
    return "mm"


def parse_parameter_table(table: RawTable) -> Optional[ParameterTable]:
    """Parse a raw table into symbol->value pairs, or None if it isn't one.

    Accepts the common layouts: a 2-column (symbol, value) table, and wider
    tables where a (symbol, value) pair sits in adjacent columns.
    """
    unit = _detect_unit(table.rows)
    values: Dict[str, float] = {}
    provenance: Dict[str, Dict[str, Any]] = {}

    for r_idx, row in enumerate(table.rows):
        cells = [_clean(c) for c in row]
        for c_idx in range(len(cells) - 1):
            sym = normalize_symbol(cells[c_idx])
            if sym is None:
                continue
            val = _parse_number(cells[c_idx + 1])
            if val is None:
                continue
            if sym in values:
                continue  # first occurrence wins; conflicts surface downstream
            values[sym] = val
            provenance[sym] = {
                "page": table.page,
                "table_index": table.index,
                "row": r_idx,
                "column": c_idx,
            }

    # A geometry parameter table needs a meaningful number of pairs; below this
    # we are almost certainly reading a results/comparison table by accident.
    if len(values) < 3:
        return None

    return ParameterTable(
        page=table.page, index=table.index, unit=unit,
        values=values, provenance=provenance,
    )


# A column header that names a length parameter, e.g. "Patch width W (mm)",
# "L(mm)". The length unit is what distinguishes a geometry column from a
# results column such as "S11 (dB)" or "Gain (dB)".
LENGTH_HEADER_RE = re.compile(r"^(.*?)[\s(]*\((mm|cm|m)\)\s*$", re.IGNORECASE)


def parse_header_symbol(cell: str) -> Optional[tuple]:
    """'Patch width W (mm)' -> ('W', 'mm'). None if not a length column."""
    s = _clean(cell)
    m = LENGTH_HEADER_RE.match(s)
    if not m:
        return None
    prefix, unit = m.group(1).strip(), m.group(2).lower()
    if not prefix:
        return None
    # The symbol is the final standalone token before the unit.
    token = prefix.split()[-1]
    sym = normalize_symbol(token)
    if sym is None:
        return None
    return sym, unit


def parse_header_oriented_table(table: RawTable) -> List[ParameterTable]:
    """Parse tables whose COLUMN HEADERS name parameters and whose rows are
    design variants. Emits one ParameterTable per variant row - never collapses
    them, because picking one variant silently would be a guess.
    """
    if not table.rows or len(table.rows) < 2:
        return []

    header = [_clean(c) for c in table.rows[0]]
    columns: Dict[int, tuple] = {}
    for c_idx, cell in enumerate(header):
        parsed = parse_header_symbol(cell)
        if parsed is not None:
            columns[c_idx] = parsed
    if len(columns) < 2:
        return []

    out: List[ParameterTable] = []
    for r_idx, row in enumerate(table.rows[1:], start=1):
        cells = [_clean(c) for c in row]
        values: Dict[str, float] = {}
        provenance: Dict[str, Dict[str, Any]] = {}
        unit = "mm"
        for c_idx, (sym, col_unit) in columns.items():
            if c_idx >= len(cells):
                continue
            val = _parse_number(cells[c_idx])
            if val is None:
                continue
            values[sym] = val
            unit = col_unit
            provenance[sym] = {
                "page": table.page, "table_index": table.index,
                "row": r_idx, "column": c_idx,
            }
        if len(values) < 2:
            continue
        label = next((c for c in cells if c and _parse_number(c) is None), None)
        out.append(ParameterTable(
            page=table.page, index=table.index, unit=unit,
            variant=label, values=values, provenance=provenance,
        ))
    return out


def extract_pdf(path: str, source_id: Optional[str] = None) -> PdfDocument:
    import pdfplumber

    sid = source_id or path.rsplit("/", 1)[-1].replace(".pdf", "")
    doc = PdfDocument(source_id=sid)
    text_parts: List[str] = []

    with pdfplumber.open(path) as pdf:
        for p_idx, page in enumerate(pdf.pages, start=1):
            text_parts.append(page.extract_text() or "")
            for t_idx, raw in enumerate(page.extract_tables() or []):
                table = RawTable(page=p_idx, index=t_idx, rows=raw)
                doc.tables.append(table)
                parsed = parse_parameter_table(table)
                if parsed is not None:
                    doc.parameter_tables.append(parsed)
                else:
                    doc.parameter_tables.extend(parse_header_oriented_table(table))

    doc.text = "\n".join(text_parts)
    return doc
