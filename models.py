from dataclasses import dataclass


FAMILIARITY_LEVELS = ("不熟", "普通", "熟")
DEFAULT_FAMILIARITY = "普通"


@dataclass
class DrugCard:
    id: int | None
    drug_name: str
    category: str = ""
    mechanism: str = ""
    key_points: str = ""
    side_effects: str = ""
    note: str = ""
    familiarity: str = DEFAULT_FAMILIARITY
    review_count: int = 0
    last_reviewed_at: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


@dataclass
class ExamItem:
    id: int | None
    card_id: int
    item_name: str
    expected_answer: str
    points: int = 1
    created_at: str | None = None
    updated_at: str | None = None


@dataclass
class ExamQuestion:
    card: DrugCard
    items: list[ExamItem]
