from dataclasses import dataclass
from typing import List, Optional


FAMILIARITY_LEVELS = ("不熟", "普通", "熟")
DEFAULT_FAMILIARITY = "普通"


@dataclass
class DrugCard:
    id: Optional[int]
    drug_name: str
    category: str = ""
    mechanism: str = ""
    key_points: str = ""
    side_effects: str = ""
    note: str = ""
    familiarity: str = DEFAULT_FAMILIARITY
    review_count: int = 0
    last_reviewed_at: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


@dataclass
class ExamItem:
    id: Optional[int]
    card_id: int
    item_name: str
    expected_answer: str
    points: int = 1
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


@dataclass
class ExamQuestion:
    card: DrugCard
    items: List[ExamItem]
