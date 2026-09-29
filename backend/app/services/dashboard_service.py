from __future__ import annotations

from collections import Counter
from statistics import mean

from app.models.audit import AuditRecord
from app.models.criteria import AuditCriteria
from app.models.dashboard import (
    DashboardSummary,
    GapCount,
    MeasureAverage,
    NamedCount,
    ScoreBucket,
    TrendPoint,
)


def latest_audits(audits: list[AuditRecord]) -> list[AuditRecord]:
    chosen: dict[str, AuditRecord] = {}
    for audit in audits:
        current = chosen.get(audit.ticket_id)
        if current is None or (audit.audit_version, audit.audited_at) >= (
            current.audit_version,
            current.audited_at,
        ):
            chosen[audit.ticket_id] = audit
    return sorted(chosen.values(), key=lambda audit: audit.ticket.opened_at or audit.audited_at)


def build_summary(audits: list[AuditRecord], criteria: AuditCriteria) -> DashboardSummary:
    latest = latest_audits(audits)
    labels = [band.label for band in criteria.classification]
    if not latest:
        return DashboardSummary(
            total_tickets=0,
            average_score=0,
            average_percentage=0,
            maximum_score=float(sum(item.max_score * item.weight for item in criteria.measures)),
            classifications=[NamedCount(label=label, count=0) for label in labels],
            human_review_count=0,
            measure_averages=[
                MeasureAverage(measure_id=item.id, measure_name=item.name, average=0)
                for item in criteria.measures
            ],
            score_distribution=[],
            quality_distribution=[NamedCount(label=label, count=0) for label in labels],
            common_gaps=[],
            score_trend=[],
            executive_summary="No tickets have been audited yet.",
            criteria_version=criteria.version,
            empty=True,
        )

    class_counts = Counter(audit.classification for audit in latest)
    classifications = [NamedCount(label=label, count=class_counts.get(label, 0)) for label in labels]
    measure_averages = []
    for definition in criteria.measures:
        values = [
            measure.final_score
            for audit in latest
            for measure in audit.measures
            if measure.measure_id == definition.id
        ]
        measure_averages.append(
            MeasureAverage(
                measure_id=definition.id,
                measure_name=definition.name,
                average=round(mean(values), 2) if values else 0,
            )
        )
    score_counts = Counter(audit.overall_score for audit in latest)
    distribution = [
        ScoreBucket(score=score, count=score_counts[score]) for score in sorted(score_counts)
    ]
    gap_counts = Counter(gap for audit in latest for gap in audit.overall_gaps)
    common_gaps = [
        GapCount(text=text, count=count) for text, count in gap_counts.most_common(6)
    ]
    reason_counts = Counter(reason for audit in latest for reason in audit.review_reasons)
    trend = _trend(latest)
    average_score = round(mean(audit.overall_score for audit in latest), 2)
    average_percentage = round(mean(audit.percentage for audit in latest), 2)
    human_review = sum(1 for audit in latest if audit.human_review_required)
    weakest = min(measure_averages, key=lambda item: item.average)
    summary = _executive_summary(
        total=len(latest),
        average_score=average_score,
        average_percentage=average_percentage,
        maximum=latest[0].maximum_score,
        classifications=classifications,
        human_review=human_review,
        weakest=weakest,
        top_gap=common_gaps[0].text if common_gaps else None,
    )
    return DashboardSummary(
        total_tickets=len(latest),
        average_score=average_score,
        average_percentage=average_percentage,
        maximum_score=latest[0].maximum_score,
        classifications=classifications,
        human_review_count=human_review,
        measure_averages=measure_averages,
        score_distribution=distribution,
        quality_distribution=classifications,
        common_gaps=common_gaps,
        score_trend=trend,
        executive_summary=summary,
        criteria_version=criteria.version,
        review_reason_counts=[
            NamedCount(label=label, count=reason_counts[label])
            for label in reason_counts
        ],
    )


def _trend(audits: list[AuditRecord]) -> list[TrendPoint]:
    grouped: dict[str, list[float]] = {}
    for audit in audits:
        moment = audit.ticket.opened_at or audit.audited_at
        key = moment.date().isoformat()
        grouped.setdefault(key, []).append(audit.percentage)
    points = [
        TrendPoint(
            date=day,
            average_percentage=round(mean(values), 2),
            tickets=len(values),
        )
        for day, values in grouped.items()
    ]
    points.sort(key=lambda point: point.date)
    return points


def _executive_summary(
    *,
    total: int,
    average_score: float,
    average_percentage: float,
    maximum: float,
    classifications: list[NamedCount],
    human_review: int,
    weakest: MeasureAverage,
    top_gap: str | None,
) -> str:
    mix = ", ".join(f"{item.count} {item.label}" for item in classifications)
    gap = f' The most common gap is "{top_gap}".' if top_gap else ""
    return (
        f"Audited {total} tickets. Average quality is {average_percentage}% "
        f"({average_score} of {maximum:g}). Distribution: {mix}. "
        f"{human_review} require human review. The weakest measure is {weakest.measure_name} "
        f"(average {weakest.average} of 5).{gap}"
    )
