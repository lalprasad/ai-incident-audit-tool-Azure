from __future__ import annotations

import json
from pathlib import Path

from app.models.criteria import AuditCriteria


def load_criteria(path: Path) -> AuditCriteria:
    data = json.loads(path.read_text(encoding="utf-8"))
    return AuditCriteria.model_validate(data)
