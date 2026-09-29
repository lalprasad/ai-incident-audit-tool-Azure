from __future__ import annotations

from pydantic import BaseModel, Field


class ScoreLevel(BaseModel):
    score: int
    label: str
    system_defined_extension: bool = False
    guidance: str


class MeasureDefinition(BaseModel):
    id: str
    name: str
    weight: float = 1
    min_score: int = 1
    max_score: int = 5
    description: str
    levels: list[ScoreLevel]


class ClassificationBand(BaseModel):
    min_inclusive: float
    max_inclusive: float
    label: str


class ConfidenceBand(BaseModel):
    min_inclusive: float
    label: str


class TimelinessGuidance(BaseModel):
    priority_first_update_hours: dict[str, float]
    penalize_when_first_update_and_longest_gap_exceed: bool = True


class AuditMessages(BaseModel):
    root_cause_missing: str
    ownership_missing: str
    updates_missing: str
    resolution_missing: str
    conflict: str
    symptom_not_cause: str


class AuditCriteria(BaseModel):
    version: str
    prompt_version: str
    measures: list[MeasureDefinition]
    classification: list[ClassificationBand]
    confidence_bands: list[ConfidenceBand]
    timeliness: TimelinessGuidance
    messages: AuditMessages

    def measure(self, measure_id: str) -> MeasureDefinition:
        for item in self.measures:
            if item.id == measure_id:
                return item
        raise KeyError(measure_id)

    def level(self, measure_id: str, score: int) -> ScoreLevel:
        for level in self.measure(measure_id).levels:
            if level.score == score:
                return level
        raise KeyError((measure_id, score))

    def measure_ids(self) -> list[str]:
        return [item.id for item in self.measures]

    def confidence_label(self, value: float) -> str:
        bands = sorted(self.confidence_bands, key=lambda band: band.min_inclusive, reverse=True)
        for band in bands:
            if value >= band.min_inclusive:
                return band.label
        return "Requires human review"


class CriteriaDocument(BaseModel):
    """Public rubric payload for the UI."""

    version: str
    prompt_version: str
    measures: list[MeasureDefinition]
    classification: list[ClassificationBand]
    confidence_bands: list[ConfidenceBand] = Field(default_factory=list)
