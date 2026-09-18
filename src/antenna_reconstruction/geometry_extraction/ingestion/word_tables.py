"""Rebuild parameter tables from word positions when the cell grid fails.

pdfplumber's grid detection can return only part of a table. On one paper it
found the right-hand half of a four-column
"Parameter | Value | Parameter | Value" layout, leaving the left Value column
paired with the right Parameter column - so every symbol received another
symbol's number, silently.

Reading the words and their coordinates avoids that: the header's own x
positions define the columns, so a value can only ever pair with the symbol
printed beside it. Typeset subscripts, which sit on their own baseline a few
points lower ("L" above "SII" meaning L_SII), are folded back in.
"""
import re
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field

PARAM_HEADER_RE = re.compile(r"^param(eter)?s?$", re.IGNORECASE)
VALUE_HEADER_RE = re.compile(
    r"^(value|dimension|size)s?\s*\(?\s*(mm|cm|m)\s*\)?$", re.IGNORECASE
)
LINE_TOLERANCE = 3.0      # words within this vertical span are one line
SUBSCRIPT_GAP = 8.0       # a line this close below another is its subscripts


class WordTable(BaseModel):
    page: int
    unit: str = "mm"
    values: Dict[str, float] = Field(default_factory=dict)
    provenance: Dict[str, Dict[str, Any]] = Field(default_factory=dict)


def _group_lines(words: List[dict]) -> List[List[dict]]:
    lines: List[List[dict]] = []
    for w in sorted(words, key=lambda w: (w["top"], w["x0"])):
        if lines and abs(w["top"] - lines[-1][0]["top"]) <= LINE_TOLERANCE:
            lines[-1].append(w)
        else:
            lines.append([w])
    return [sorted(line, key=lambda w: w["x0"]) for line in lines]


def _fold_subscripts(lines: List[List[dict]]) -> List[List[dict]]:
    """Merge a subscript line into the line it belongs to."""
    out: List[List[dict]] = []
    for line in lines:
        if out and 0 < line[0]["top"] - out[-1][0]["top"] <= SUBSCRIPT_GAP \
                and len(line) <= len(out[-1]):
            out[-1] = sorted(out[-1] + line, key=lambda w: w["x0"])
        else:
            out.append(list(line))
    return out


def _header_columns(line: List[dict]) -> Optional[List[Tuple[float, str]]]:
    """Column anchors from a header line, as (x0, 'param'|'value')."""
    columns: List[Tuple[float, str]] = []
    for w in line:
        text = w["text"].strip()
        if PARAM_HEADER_RE.match(text):
            columns.append((w["x0"], "param"))
        elif VALUE_HEADER_RE.match(text.replace(" ", "")):
            columns.append((w["x0"], "value"))
    # Needs at least one complete pair, and the kinds must alternate.
    if len(columns) < 2 or not any(k == "param" for _, k in columns) \
            or not any(k == "value" for _, k in columns):
        return None
    return columns


def _assign(line: List[dict],
            anchors: List[Tuple[float, str]]) -> List[List[str]]:
    """Each line's words, bucketed into the column whose anchor is nearest.

    Words are kept separate rather than concatenated so a symbol's base and its
    subscript stay distinguishable: joining first and re-parsing splits "LSIII"
    into the wrong pieces.
    """
    cells: List[List[str]] = [[] for _ in anchors]
    for w in line:
        idx = min(range(len(anchors)), key=lambda i: abs(anchors[i][0] - w["x0"]))
        text = w["text"].strip()
        if text:
            cells[idx].append(text)
    return cells


def _symbol_from(parts: List[str]) -> Optional[str]:
    """'L' + 'SIII' -> 'L_SIII'. The first word is the base, the rest subscript."""
    if not parts:
        return None
    base = parts[0]
    if not re.fullmatch(r"[A-Za-z]{1,3}", base):
        return None
    sub = "".join(parts[1:])
    if sub and not re.fullmatch(r"[A-Za-z0-9]{1,5}", sub):
        return None
    return f"{base}_{sub}" if sub else base


def _unit_of(line: List[dict]) -> str:
    for w in line:
        m = re.search(r"\b(mm|cm|m)\b", w["text"], re.IGNORECASE)
        if m:
            return m.group(1).lower()
    return "mm"


def parse_word_tables(page, page_number: int) -> List[WordTable]:
    """Every 'Parameter | Value' block on a page, read from word positions."""
    from .pdf import _parse_number

    try:
        words = page.extract_words()
    except Exception:
        return []

    lines = _fold_subscripts(_group_lines(words))
    tables: List[WordTable] = []

    for i, line in enumerate(lines):
        anchors = _header_columns(line)
        if anchors is None:
            continue

        table = WordTable(page=page_number, unit=_unit_of(line))
        for r_idx, row in enumerate(lines[i + 1:], start=1):
            cells = _assign(row, anchors)
            hits = 0
            for c_idx, (_, kind) in enumerate(anchors):
                if kind != "param" or c_idx + 1 >= len(anchors):
                    continue
                if anchors[c_idx + 1][1] != "value":
                    continue
                sym = _symbol_from(cells[c_idx])
                val = _parse_number("".join(cells[c_idx + 1]))
                if sym is None or val is None:
                    continue
                hits += 1
                if sym not in table.values:
                    table.values[sym] = val
                    table.provenance[sym] = {
                        "page": page_number, "row": r_idx, "column": c_idx,
                        "method": "word-grid",
                    }
            if hits == 0 and table.values:
                break  # the block has ended
        if len(table.values) >= 3:
            tables.append(table)

    return tables
