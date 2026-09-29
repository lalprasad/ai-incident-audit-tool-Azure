from __future__ import annotations

from pydantic import BaseModel, Field


class NamedCount(BaseModel):
    label: str
    count: int


class MeasureAverage(BaseModel):
    measure_id: str
    measure_name: str
    average: float


class ScoreBucket(BaseModel):
    score: float
    count: int


class TrendPoint(BaseModel):
    date: str
    average_percentage: float
    tickets: int


class GapCount(BaseModel):
    text: str
    count: int


class DashboardSummary(BaseModel):
    total_tickets: int
    average_score: float
    average_percentage: float
    maximum_score: float
    classifications: list[NamedCount]
    human_review_count: int
    measure_averages: list[MeasureAverage]
    score_distribution: list[ScoreBucket]
    quality_distribution: list[NamedCount]
    common_gaps: list[GapCount]
    score_trend: list[TrendPoint]
    executive_summary: str
    criteria_version: str
    totals_computed_by: str = "scoring_engine"
    empty: bool = False
    review_reason_counts: list[NamedCount] = Field(default_factory=list)
