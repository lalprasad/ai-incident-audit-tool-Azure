from decimal import Decimal

import pytest

from app.audit.scoring_engine import ScoringEngine
from app.models.criteria import AuditCriteria
from app.utils.errors import ScoringError


def test_equal_weights_and_classification(criteria: AuditCriteria) -> None:
    engine = ScoringEngine(criteria)
    excellent = engine.compute(
        {"user_engagement": 5, "issue_diagnosis": 5, "solutioning": 5}
    )
    assert excellent.total_score == 15
    assert excellent.maximum_score == 15
    assert excellent.percentage == 100
    assert excellent.classification == "Excellent"

    good = engine.compute({"user_engagement": 4, "issue_diagnosis": 4, "solutioning": 4})
    assert good.percentage == 80
    assert good.classification == "Good"

    fair = engine.compute({"user_engagement": 3, "issue_diagnosis": 3, "solutioning": 3})
    assert fair.percentage == 60
    assert fair.classification == "Fair"

    poor = engine.compute({"user_engagement": 1, "issue_diagnosis": 1, "solutioning": 1})
    assert poor.total_score == 3
    assert poor.percentage == 20
    assert poor.classification == "Needs Improvement"


def test_classification_boundaries(criteria: AuditCriteria) -> None:
    engine = ScoringEngine(criteria)
    assert engine.classify(100) == "Excellent"
    assert engine.classify(90) == "Excellent"
    assert engine.classify(89.99) == "Good"
    assert engine.classify(75) == "Good"
    assert engine.classify(74.99) == "Fair"
    assert engine.classify(60) == "Fair"
    assert engine.classify(59.99) == "Needs Improvement"
    assert engine.classify(0) == "Needs Improvement"


def test_custom_weights_change_the_maximum(criteria: AuditCriteria) -> None:
    weighted = criteria.model_copy(
        update={
            "measures": [
                criteria.measures[0].model_copy(update={"weight": 2}),
                criteria.measures[1],
                criteria.measures[2],
            ]
        }
    )
    engine = ScoringEngine(weighted)
    result = engine.compute({"user_engagement": 5, "issue_diagnosis": 3, "solutioning": 1})
    assert result.maximum_score == 20
    assert result.total_score == 14
    assert result.percentage == 70
    assert result.classification == "Fair"


def test_out_of_range_and_non_integer_scores_are_rejected(criteria: AuditCriteria) -> None:
    engine = ScoringEngine(criteria)
    with pytest.raises(ScoringError):
        engine.validate_measure_score("user_engagement", 0)
    with pytest.raises(ScoringError):
        engine.validate_measure_score("user_engagement", 6)
    with pytest.raises(ScoringError):
        engine.validate_measure_score("solutioning", True)  # type: ignore[arg-type]
    with pytest.raises(ScoringError):
        engine.compute({"user_engagement": 5, "issue_diagnosis": 5})


def test_percentage_rounding_uses_half_up(criteria: AuditCriteria) -> None:
    engine = ScoringEngine(criteria)
    result = engine.compute({"user_engagement": 4, "issue_diagnosis": 2, "solutioning": 4})
    assert result.total_score == 10
    assert result.percentage == float(Decimal("66.67"))
    assert result.classification == "Fair"
