"""Quantities a paper implies rather than prints.

Some dimensions are never written as a number. The array paper says only
"Distance between patches is kept as lambda/2" - but it also states its centre
frequency, and a wavelength follows from that by definition. Recovering such a
value is arithmetic on stated facts, not a guess, so it belongs here.

Every derived value carries the formula and the inputs it came from, so it can
be audited and told apart from a value the paper actually printed. Nothing here
invents a missing measurement: if the inputs are absent or contradictory, the
quantity is simply not derived.
"""
import math
import re
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

C_MM_PER_S = 299_792_458.0 * 1000.0

NUM = r"[0-9]+(?:\.[0-9]+)?"
FREQ_RE = re.compile(rf"({NUM})\s*(G|M|k)?Hz", re.IGNORECASE)
CENTRE_FREQ_RE = re.compile(
    rf"(?:cent(?:re|er)\s+frequency|operat\w+\s+at|designed\s+(?:at|for))[^.]{{0,40}}?({NUM})\s*(G|M|k)?Hz",
    re.IGNORECASE,
)
# Also catch "... at 2.4 GHz centre frequency", where the qualifier trails.
TRAILING_CENTRE_RE = re.compile(
    rf"({NUM})\s*(G|M|k)?Hz\s+cent(?:re|er)\s+frequency", re.IGNORECASE
)
EPSILON_RE = re.compile(
    rf"dielectric\s+constant[^.]{{0,30}}?({NUM})", re.IGNORECASE
)
# "4x2 array", and also "4x2 patch array" / "4 x 2 microstrip patch array".
ARRAY_RE = re.compile(
    r"\b([1-9])\s*[x×]\s*([1-9])(?:\s+[A-Za-z]+){0,2}\s+array", re.IGNORECASE
)
# "Distance between patches is kept as lambda/2"
SPACING_RE = re.compile(
    r"distance\s+between\s+(?:patches|elements)[^.]{0,40}?"
    r"(?:λ|lambda)\s*/\s*([2-9])",
    re.IGNORECASE,
)

MULTIPLIER = {"g": 1e9, "m": 1e6, "k": 1e3, None: 1.0, "": 1.0}


class DerivedQuantity(BaseModel):
    """One value computed from stated facts, with its full derivation."""
    symbol: str
    value: float
    unit: str
    formula: str
    inputs: Dict[str, float] = Field(default_factory=dict)
    source: str = ""

    def summary(self) -> str:
        args = ", ".join(f"{k}={v:g}" for k, v in self.inputs.items())
        return f"{self.symbol} = {self.value:.4f} {self.unit}  [{self.formula}; {args}]"


class PhysicsExtraction(BaseModel):
    frequency_hz: Optional[float] = None
    epsilon_r: Optional[float] = None
    array_nx: Optional[int] = None
    array_ny: Optional[int] = None
    spacing_divisor: Optional[int] = None
    derived: List[DerivedQuantity] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)
    diagnostics: List[str] = Field(default_factory=list)


def _to_hz(value: str, prefix: Optional[str]) -> float:
    return float(value) * MULTIPLIER[(prefix or "").lower()]


def _pick_frequency(text: str, out: PhysicsExtraction) -> Optional[float]:
    """The design frequency, or nothing.

    Papers quote many frequencies - resonances, bands, values from cited work.
    A qualified "centre frequency" wins. Failing that, the frequency is only
    taken when every mention agrees, because choosing among several would be a
    guess about which band the design targets.
    """
    for pattern in (CENTRE_FREQ_RE, TRAILING_CENTRE_RE):
        m = pattern.search(text)
        if m:
            return _to_hz(m.group(1), m.group(2))

    found = {_to_hz(m.group(1), m.group(2)) for m in FREQ_RE.finditer(text)}
    found = {f for f in found if 1e8 <= f <= 1e12}  # plausible antenna range
    if len(found) == 1:
        return found.pop()
    if len(found) > 1:
        out.diagnostics.append(
            f"{len(found)} different frequencies are quoted "
            f"({sorted(f / 1e9 for f in found)} GHz) and none is marked as the "
            "centre frequency, so no wavelength is derived"
        )
    return None


def extract_physics(text: str) -> PhysicsExtraction:
    out = PhysicsExtraction()
    flat = re.sub(r"\s+", " ", text)

    out.frequency_hz = _pick_frequency(flat, out)

    eps = {float(m.group(1)) for m in EPSILON_RE.finditer(flat)}
    eps = {e for e in eps if 1.0 <= e <= 20.0}
    if len(eps) == 1:
        out.epsilon_r = eps.pop()
    elif len(eps) > 1:
        out.diagnostics.append(
            f"conflicting dielectric constants {sorted(eps)}; none used"
        )

    m = ARRAY_RE.search(flat)
    if m:
        out.array_nx, out.array_ny = int(m.group(1)), int(m.group(2))

    m = SPACING_RE.search(flat)
    if m:
        out.spacing_divisor = int(m.group(1))

    _derive(out)
    return out


def _derive(out: PhysicsExtraction) -> None:
    if out.frequency_hz is None:
        return

    lam = C_MM_PER_S / out.frequency_hz
    out.derived.append(DerivedQuantity(
        symbol="LAMBDA0", value=lam, unit="mm",
        formula="lambda0 = c / f",
        inputs={"f_GHz": out.frequency_hz / 1e9},
        source="stated centre frequency",
    ))

    if out.epsilon_r is not None:
        # Upper bound on guided wavelength: the true value needs the effective
        # permittivity, which depends on trace width. Recorded, never used as a
        # dimension, because a bound is not a measurement.
        lam_g = lam / math.sqrt(out.epsilon_r)
        out.derived.append(DerivedQuantity(
            symbol="LAMBDA_G_MIN", value=lam_g, unit="mm",
            formula="lambda_g = lambda0 / sqrt(eps_r)  (lower bound)",
            inputs={"lambda0": lam, "eps_r": out.epsilon_r},
            source="stated dielectric constant",
        ))

    if out.spacing_divisor is not None:
        spacing = lam / out.spacing_divisor
        out.assumptions.append(
            f"'lambda/{out.spacing_divisor}' spacing is read as free-space "
            "lambda0, the usual convention for array element spacing; the "
            "guided wavelength would give a smaller figure"
        )
        for symbol in ("DX", "DY"):
            out.derived.append(DerivedQuantity(
                symbol=symbol, value=spacing, unit="mm",
                formula=f"lambda0 / {out.spacing_divisor}",
                inputs={"lambda0": lam},
                source="stated element spacing rule",
            ))


def derived_symbols(out: PhysicsExtraction) -> Dict[str, float]:
    """The derived quantities that templates can consume as symbols."""
    values: Dict[str, float] = {q.symbol: q.value for q in out.derived}
    values.pop("LAMBDA0", None)
    values.pop("LAMBDA_G_MIN", None)
    if out.array_nx is not None and out.array_ny is not None:
        values["NX"] = float(out.array_nx)
        values["NY"] = float(out.array_ny)
    return values
