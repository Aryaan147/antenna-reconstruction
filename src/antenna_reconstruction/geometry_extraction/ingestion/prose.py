"""Recover dimensions stated in running text rather than in a table.

Three of the five sample papers publish no machine-readable parameter table;
they state dimensions in prose instead, in a small number of recurring forms:

    "fabricated on 76.8 X 57.8 mm2 FR-4 substrate"     <- role AFTER the numbers
    "The patch has dimension on 39.4X28.9mm2"          <- role BEFORE the numbers
    "L1 = 45 mm, L2 = 30 mm, W1 = L1"                  <- explicit assignments
    "microstrip line having width of 3.1mm"            <- a single named extent

This module reads only what is written. It never infers a dimension that the
text does not state, and where the text is ambiguous it records the ambiguity
instead of choosing.
"""
import re
from typing import Dict, List, Optional, Tuple
from pydantic import BaseModel, Field

NUM = r"[0-9]+(?:\.[0-9]+)?"

# "76.8 X 57.8 mm2", "45 × 45× 1.6 mm3", "39.4X28.9mm2"
DIM_PAIR_RE = re.compile(
    rf"({NUM})\s*[x×X]\s*({NUM})(?:\s*[x×X]\s*({NUM}))?\s*mm\s*[23]?",
)
# "L1 = 45 mm", "W = 1.2 mm"
ASSIGN_RE = re.compile(rf"\b([A-Za-z]{{1,3}}\s?[0-9]?)\s*=\s*({NUM})\s*mm\b")
# "W1 = L1"  (a symbolic alias, e.g. a square patch)
ALIAS_RE = re.compile(r"\b([A-Za-z]{1,3}\s?[0-9]?)\s*=\s*([A-Za-z]{1,3}\s?[0-9]?)\b(?!\s*=)")
# "width of 3.1mm", "thickness = 1.6 mm"
NAMED_EXTENT_RE = re.compile(rf"\b(width|length|height|thickness|radius|diameter)\b[^.]{{0,20}}?({NUM})\s*mm")
# A width that is explicitly the FEED's. An unqualified "width" must never be
# taken for one: "optimized by length and width in which, L=29.78mm" would
# otherwise bind a patch length as a feed width, silently and wrongly.
FEED_WIDTH_RE = re.compile(
    rf"(?:feed\s*-?\s*line|feedline|microstrip\s+line|feed)[^.]{{0,40}}?"
    rf"\bwidth\b[^.]{{0,15}}?({NUM})\s*mm",
    re.IGNORECASE,
)

ROLE_KEYWORDS = {
    "substrate": "substrate",
    "patch": "patch",
    "radiator": "patch",
    "ground": "ground",
    "feed": "feed",
    "microstrip line": "feed",
    "slot": "slot",
    # "The overall dimension of the antenna is 45 x 45 x 1.6 mm3" describes the
    # whole board, not a named part. Tagged so it cannot be mistaken for one.
    "overall dimension": "overall",
    "overall size": "overall",
}
# How far from the numbers a role word may sit and still be taken to describe them.
ROLE_WINDOW = 60


class DimensionPair(BaseModel):
    """An 'A x B' extent found in prose, with the role word nearest to it."""
    role: Optional[str] = None
    a: float
    b: float
    thickness: Optional[float] = None
    context: str = ""
    offset: int = 0


class ProseExtraction(BaseModel):
    values: Dict[str, float] = Field(default_factory=dict)
    aliases: Dict[str, str] = Field(default_factory=dict)
    # Symbols the text assigns more than one value: reported, never resolved.
    contested: Dict[str, List[float]] = Field(default_factory=dict)
    pairs: List[DimensionPair] = Field(default_factory=list)
    named_extents: Dict[str, float] = Field(default_factory=dict)
    feed_width: Optional[float] = None
    diagnostics: List[str] = Field(default_factory=list)


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text)


def _role_near(text: str, start: int, end: int) -> Optional[str]:
    """The role keyword closest to [start, end), searching both directions."""
    lo = max(0, start - ROLE_WINDOW)
    hi = min(len(text), end + ROLE_WINDOW)
    window = text[lo:hi].lower()

    best: Optional[Tuple[int, str]] = None
    for keyword, role in ROLE_KEYWORDS.items():
        for m in re.finditer(re.escape(keyword), window):
            k_start, k_end = m.start() + lo, m.end() + lo
            # Measure to the NEAREST EDGE of the keyword. Measuring from its
            # start would penalise long keywords that precede the numbers,
            # letting a distant "microstrip line" beat an adjacent "patch".
            if k_end <= start:
                distance = start - k_end
            elif k_start >= end:
                distance = k_start - end
            else:
                distance = 0
            if best is None or distance < best[0]:
                best = (distance, role)
    return best[1] if best else None


def _clean_symbol(raw: str) -> str:
    return re.sub(r"\s+", "", raw)


def extract_prose_parameters(text: str) -> ProseExtraction:
    out = ProseExtraction()
    flat = _normalize(text)

    for m in DIM_PAIR_RE.finditer(flat):
        a, b, third = m.group(1), m.group(2), m.group(3)
        pair = DimensionPair(
            role=_role_near(flat, m.start(), m.end()),
            a=float(a), b=float(b),
            thickness=float(third) if third else None,
            context=flat[max(0, m.start() - 40):m.end() + 40],
            offset=m.start(),
        )
        out.pairs.append(pair)

    # Collect every stated value per symbol first. Papers that present several
    # design variants assign the same symbol repeatedly with different values,
    # and picking one of them would be a silent guess about which design the
    # reader wants, so contested symbols are dropped instead.
    seen: Dict[str, List[float]] = {}
    for m in ASSIGN_RE.finditer(flat):
        seen.setdefault(_clean_symbol(m.group(1)), []).append(float(m.group(2)))

    for sym, found in seen.items():
        distinct = sorted(set(found))
        if len(distinct) > 1:
            out.contested[sym] = distinct
            out.diagnostics.append(
                f"{sym} is assigned {len(distinct)} different values in prose "
                f"({distinct}); the paper states several design variants, so "
                f"{sym} is dropped rather than guessed"
            )
            continue
        out.values[sym] = distinct[0]

    for m in ALIAS_RE.finditer(flat):
        lhs, rhs = _clean_symbol(m.group(1)), _clean_symbol(m.group(2))
        if lhs == rhs or rhs.lower() in {"mm", "cm"}:
            continue
        out.aliases.setdefault(lhs, rhs)

    for m in NAMED_EXTENT_RE.finditer(flat):
        out.named_extents.setdefault(m.group(1).lower(), float(m.group(2)))

    widths = {float(m.group(1)) for m in FEED_WIDTH_RE.finditer(flat)}
    if len(widths) == 1:
        out.feed_width = widths.pop()
    elif len(widths) > 1:
        out.diagnostics.append(
            f"several feed widths stated in prose ({sorted(widths)}); none used"
        )

    return out


def check_alias_consistency(extraction: ProseExtraction) -> None:
    """An alias that contradicts a direct assignment marks the symbol contested.

    "W1 = L1" and "W1 = 40 mm" with "L1 = 45 mm" cannot both describe one
    design. Rather than preferring either statement, the symbol is dropped.
    """
    for lhs, rhs in extraction.aliases.items():
        if lhs in extraction.values and rhs in extraction.values:
            direct, via_alias = extraction.values[lhs], extraction.values[rhs]
            if direct != via_alias:
                extraction.contested[lhs] = sorted({direct, via_alias})
                extraction.values.pop(lhs, None)
                extraction.diagnostics.append(
                    f"{lhs} is stated directly as {direct} but aliased to "
                    f"{rhs} = {via_alias}; the two disagree, so {lhs} is dropped"
                )


def resolve_aliases(extraction: ProseExtraction) -> Dict[str, float]:
    """Apply 'W1 = L1' style aliases to fill in symbols stated only by reference."""
    values = dict(extraction.values)
    for _ in range(len(extraction.aliases) + 1):
        changed = False
        for lhs, rhs in extraction.aliases.items():
            if lhs in extraction.contested or rhs in extraction.contested:
                continue
            if lhs not in values and rhs in values:
                values[lhs] = values[rhs]
                changed = True
        if not changed:
            break
    return values


def to_template_symbols(extraction: ProseExtraction) -> Dict[str, float]:
    """Map prose findings onto the symbol names templates expect.

    Only unambiguous findings are mapped. A role with several differing
    extents is left out and recorded as a diagnostic, because choosing between
    competing design variants is not this module's decision to make.
    """
    check_alias_consistency(extraction)
    values = resolve_aliases(extraction)

    by_role: Dict[str, List[DimensionPair]] = {}
    for pair in extraction.pairs:
        if pair.role:
            by_role.setdefault(pair.role, []).append(pair)

    def unique_pair(role: str) -> Optional[DimensionPair]:
        found = by_role.get(role, [])
        if not found:
            return None
        distinct = {(p.a, p.b) for p in found}
        if len(distinct) > 1:
            extraction.diagnostics.append(
                f"{role}: {len(distinct)} different extents stated in prose "
                f"({sorted(distinct)}); refusing to choose between design variants"
            )
            return None
        return found[0]

    substrate = unique_pair("substrate")
    if substrate is not None:
        values.setdefault("SW", substrate.a)
        values.setdefault("SL", substrate.b)
        if substrate.thickness is not None:
            values.setdefault("ST", substrate.thickness)

    patch = unique_pair("patch")
    if patch is not None:
        values.setdefault("W", patch.a)
        values.setdefault("L", patch.b)

    if extraction.feed_width is not None:
        values.setdefault("FW", extraction.feed_width)

    return values
