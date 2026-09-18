"""Deterministic verification of symbol->geometry bindings.

The hard part of reconstructing an antenna from a paper is deciding what each
symbol MEANS ("is S1 the outer hexagon edge?"). A proposal for that mapping may
come from a human, a heuristic, or an LLM - all of them fallible.

This module is the check that makes a fallible proposer safe. Antenna papers
over-specify their geometry: the same quantity is often derivable from other
listed quantities. Each such redundancy is an arithmetic identity that a
CORRECT binding must satisfy and an INCORRECT one will generally violate. So a
proposal is never trusted, only tested.

Nothing here is antenna-specific; templates supply the relations.
"""
import math
from enum import Enum
from typing import Callable, Dict, List, Optional
from pydantic import BaseModel, Field


class CheckOutcome(str, Enum):
    CONFIRMED = "CONFIRMED"
    REFUTED = "REFUTED"
    SKIPPED = "SKIPPED"  # required symbols absent from the table


def rounding_tolerance(stated: float, floor: float = 1e-9) -> float:
    """Tolerance implied by how precisely a value was printed.

    A paper printing "5.3" asserts the true value lies in [5.25, 5.35), so a
    prediction within 0.05 is consistent with it. Printing "4.76" is a much
    stronger claim (+/-0.005). This derives the tolerance from the evidence
    instead of hard-coding a fudge factor.
    """
    text = f"{stated!r}"
    if "e" in text.lower():
        return max(abs(stated) * 1e-6, floor)
    decimals = len(text.split(".")[1]) if "." in text else 0
    return max(0.5 * (10.0 ** -decimals), floor)


class Relation(BaseModel):
    """A checkable arithmetic identity predicting `target` from other symbols."""
    model_config = {"arbitrary_types_allowed": True}

    name: str
    target: str
    requires: List[str]
    description: str
    predict: Callable[[Dict[str, float]], float]


class CheckResult(BaseModel):
    name: str
    target: str
    description: str
    outcome: CheckOutcome
    predicted: Optional[float] = None
    stated: Optional[float] = None
    error: Optional[float] = None
    tolerance: Optional[float] = None
    missing: List[str] = Field(default_factory=list)

    def summary(self) -> str:
        if self.outcome is CheckOutcome.SKIPPED:
            return f"[SKIPPED] {self.name}: missing {', '.join(self.missing)}"
        return (
            f"[{self.outcome.value}] {self.name}: {self.description} | "
            f"predicted {self.predicted:.4f}, stated {self.stated}, "
            f"error {self.error:.4f} (tol {self.tolerance:.4f})"
        )


class VerificationReport(BaseModel):
    results: List[CheckResult] = Field(default_factory=list)

    @property
    def confirmed(self) -> List[CheckResult]:
        return [r for r in self.results if r.outcome is CheckOutcome.CONFIRMED]

    @property
    def refuted(self) -> List[CheckResult]:
        return [r for r in self.results if r.outcome is CheckOutcome.REFUTED]

    @property
    def skipped(self) -> List[CheckResult]:
        return [r for r in self.results if r.outcome is CheckOutcome.SKIPPED]

    @property
    def ok(self) -> bool:
        """A binding is acceptable only if nothing refutes it and something confirms it.

        Zero confirmations is NOT success: it means the parameter set carried no
        redundancy to test against, so the binding is unverified rather than
        verified, and callers must treat it as such.
        """
        return not self.refuted and bool(self.confirmed)

    def render(self) -> str:
        lines = [r.summary() for r in self.results]
        lines.append(
            f"--> {len(self.confirmed)} confirmed, {len(self.refuted)} refuted, "
            f"{len(self.skipped)} skipped"
        )
        return "\n".join(lines)


def verify(values: Dict[str, float], relations: List[Relation]) -> VerificationReport:
    """Test every relation against the paper's own numbers."""
    report = VerificationReport()

    for rel in relations:
        missing = [s for s in rel.requires if s not in values]
        if rel.target not in values:
            missing.append(rel.target)
        if missing:
            report.results.append(CheckResult(
                name=rel.name, target=rel.target, description=rel.description,
                outcome=CheckOutcome.SKIPPED, missing=sorted(set(missing)),
            ))
            continue

        stated = values[rel.target]
        try:
            predicted = float(rel.predict(values))
        except Exception as exc:  # a relation that cannot evaluate is not a pass
            report.results.append(CheckResult(
                name=rel.name, target=rel.target,
                description=f"{rel.description} (evaluation failed: {exc})",
                outcome=CheckOutcome.REFUTED, stated=stated,
            ))
            continue

        tol = rounding_tolerance(stated)
        err = abs(predicted - stated)
        if not math.isfinite(predicted):
            outcome = CheckOutcome.REFUTED
        else:
            outcome = CheckOutcome.CONFIRMED if err <= tol else CheckOutcome.REFUTED

        report.results.append(CheckResult(
            name=rel.name, target=rel.target, description=rel.description,
            outcome=outcome, predicted=predicted, stated=stated,
            error=err, tolerance=tol,
        ))

    return report
