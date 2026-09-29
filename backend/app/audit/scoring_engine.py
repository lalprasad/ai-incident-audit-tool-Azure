from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

from app.models.criteria import AuditCriteria
from app.utils.errors import ScoringError


@dataclass(frozen=True)
class MeasureContribution:
    measure_id: str
    score: int
    weight: float
    weighted_score: float


@dataclass(frozen=True)
class ScoreComputation:
    total_score: float
    maximum_score: float
    percentage: float
    classification: str
    contributions: list[MeasureContribution]


class ScoringEngine:
    """Owns totals, percentage, and classification. The model does not."""

    def __init__(self, criteria: AuditCriteria) -> None:
        self._criteria = criteria

    def validate_measure_score(self, measure_id: str, score: int) -> None:
        if isinstance(score, bool) or not isinstance(score, int):
            raise ScoringError(f"Score for {measure_id} must be an integer")
        measure = self._criteria.measure(measure_id)
        if score < measure.min_score or score > measure.max_score:
            raise ScoringError(
                f"Score {score} for {measure_id} is outside {measure.min_score}-{measure.max_score}"
            )

    def classify(self, percentage: float) -> str:
        for band in self._criteria.classification:
            if band.min_inclusive <= percentage <= band.max_inclusive:
                return band.label
        raise ScoringError(f"Percentage {percentage} does not fall in a classification band")

    def compute(self, scores: dict[str, int]) -> ScoreComputation:
        expected = self._criteria.measure_ids()
        missing = [measure_id for measure_id in expected if measure_id not in scores]
        if missing:
            raise ScoringError(f"Missing measure scores: {', '.join(missing)}")

        contributions: list[MeasureContribution] = []
        total = Decimal("0")
        maximum = Decimal("0")
        for measure_id in expected:
            self.validate_measure_score(measure_id, scores[measure_id])
            measure = self._criteria.measure(measure_id)
            weight = Decimal(str(measure.weight))
            weighted = Decimal(scores[measure_id]) * weight
            total += weighted
            maximum += Decimal(measure.max_score) * weight
            contributions.append(
                MeasureContribution(
                    measure_id=measure_id,
                    score=scores[measure_id],
                    weight=float(weight),
                    weighted_score=float(weighted),
                )
            )
        if maximum == 0:
            raise ScoringError("Maximum score is zero")
        percentage = float(
            (total / maximum * Decimal(100)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        )
        return ScoreComputation(
            total_score=float(total),
            maximum_score=float(maximum),
            percentage=percentage,
            classification=self.classify(percentage),
            contributions=contributions,
        )
