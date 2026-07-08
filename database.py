from __future__ import annotations

import csv
import shutil
import sqlite3
import sys
from datetime import datetime
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from models import DEFAULT_FAMILIARITY, FAMILIARITY_LEVELS, DrugCard, ExamItem


def app_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def resolve_database_path() -> Path:
    base_dir = app_base_dir()
    data_dir = base_dir / "data"
    data_db = data_dir / "drug_cards.db"
    legacy_db = base_dir / "drug_cards.db"

    data_dir.mkdir(parents=True, exist_ok=True)
    if not data_db.exists() and legacy_db.exists():
        shutil.copy2(legacy_db, data_db)
    return data_db


DB_PATH = resolve_database_path()
TABLE_NAME = "cards"
LEGACY_TABLE_NAME = "drug_cards"
EXAM_ITEMS_TABLE = "exam_items"
EXAM_RESULTS_TABLE = "exam_results"
EXAM_RESULT_ITEMS_TABLE = "exam_result_items"
CSV_IMPORT_ENCODINGS = ("utf-8-sig", "utf-8", "cp950", "big5", "gb18030")
CARD_EXPORT_FIELDNAMES = [
    "id",
    "drug_name",
    "category",
    "mechanism",
    "key_points",
    "side_effects",
    "note",
    "familiarity",
    "review_count",
    "last_reviewed_at",
    "created_at",
    "updated_at",
]


class DrugCardDatabase:
    def __init__(self, db_path: Path | str = DB_PATH) -> None:
        self.db_path = Path(db_path)
        self.initialize()

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def initialize(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as conn:
            conn.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    drug_name TEXT NOT NULL,
                    category TEXT NOT NULL DEFAULT '',
                    mechanism TEXT NOT NULL DEFAULT '',
                    key_points TEXT NOT NULL DEFAULT '',
                    side_effects TEXT NOT NULL DEFAULT '',
                    note TEXT NOT NULL DEFAULT '',
                    familiarity TEXT NOT NULL DEFAULT '{DEFAULT_FAMILIARITY}',
                    review_count INTEGER NOT NULL DEFAULT 0,
                    last_reviewed_at TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            self._ensure_columns(conn)
            self._migrate_legacy_table(conn)
            self._ensure_exam_tables(conn)

    def _ensure_columns(self, conn: sqlite3.Connection) -> None:
        existing_columns = {
            row["name"] for row in conn.execute(f"PRAGMA table_info({TABLE_NAME})").fetchall()
        }
        columns_to_add = {
            "familiarity": f"TEXT NOT NULL DEFAULT '{DEFAULT_FAMILIARITY}'",
            "review_count": "INTEGER NOT NULL DEFAULT 0",
            "last_reviewed_at": "TEXT",
            "created_at": "TEXT NOT NULL DEFAULT ''",
            "updated_at": "TEXT NOT NULL DEFAULT ''",
        }
        for column_name, column_definition in columns_to_add.items():
            if column_name not in existing_columns:
                conn.execute(
                    f"ALTER TABLE {TABLE_NAME} ADD COLUMN {column_name} {column_definition}"
                )

    def _migrate_legacy_table(self, conn: sqlite3.Connection) -> None:
        legacy_exists = conn.execute(
            """
            SELECT 1
            FROM sqlite_master
            WHERE type = 'table' AND name = ?
            """,
            (LEGACY_TABLE_NAME,),
        ).fetchone()
        if not legacy_exists:
            return

        current_count = conn.execute(f"SELECT COUNT(*) FROM {TABLE_NAME}").fetchone()[0]
        if current_count:
            return

        conn.execute(
            f"""
            INSERT INTO {TABLE_NAME} (
                id, drug_name, category, mechanism, key_points, side_effects, note
            )
            SELECT id, drug_name, category, mechanism, key_points, side_effects, note
            FROM {LEGACY_TABLE_NAME}
            """
        )

    def _ensure_exam_tables(self, conn: sqlite3.Connection) -> None:
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {EXAM_ITEMS_TABLE} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                card_id INTEGER NOT NULL,
                item_name TEXT NOT NULL,
                expected_answer TEXT NOT NULL,
                points INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(card_id) REFERENCES {TABLE_NAME}(id) ON DELETE CASCADE
            )
            """
        )
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {EXAM_RESULTS_TABLE} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at TEXT NOT NULL,
                finished_at TEXT NOT NULL,
                total_score INTEGER NOT NULL,
                max_score INTEGER NOT NULL,
                accuracy REAL NOT NULL,
                mode TEXT NOT NULL,
                category TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {EXAM_RESULT_ITEMS_TABLE} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                result_id INTEGER NOT NULL,
                card_id INTEGER NOT NULL,
                item_name TEXT NOT NULL,
                user_answer TEXT NOT NULL,
                expected_answer TEXT NOT NULL,
                is_correct INTEGER NOT NULL,
                score INTEGER NOT NULL,
                max_score INTEGER NOT NULL,
                FOREIGN KEY(result_id) REFERENCES {EXAM_RESULTS_TABLE}(id) ON DELETE CASCADE,
                FOREIGN KEY(card_id) REFERENCES {TABLE_NAME}(id)
            )
            """
        )

    def list_cards(
        self,
        search_text: str = "",
        category: str = "",
        unfamiliar_only: bool = False,
    ) -> list[DrugCard]:
        clauses: list[str] = []
        params: list[str] = []

        if search_text.strip():
            clauses.append("drug_name LIKE ?")
            params.append(f"%{search_text.strip()}%")

        if category.strip():
            clauses.append("category = ?")
            params.append(category.strip())

        if unfamiliar_only:
            clauses.append("familiarity = ?")
            params.append("不熟")

        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with self.connect() as conn:
            rows = conn.execute(
                f"""
                SELECT id, drug_name, category, mechanism, key_points, side_effects, note,
                       familiarity, review_count, last_reviewed_at, created_at, updated_at
                FROM {TABLE_NAME}
                {where_sql}
                ORDER BY id ASC
                """,
                params,
            ).fetchall()
        return [self._row_to_card(row) for row in rows]

    def list_categories(self) -> list[str]:
        with self.connect() as conn:
            rows = conn.execute(
                f"""
                SELECT DISTINCT category
                FROM {TABLE_NAME}
                WHERE TRIM(category) != ''
                ORDER BY category COLLATE NOCASE
                """
            ).fetchall()
        return [row["category"] for row in rows]

    def count_cards(self) -> int:
        with self.connect() as conn:
            return int(conn.execute(f"SELECT COUNT(*) FROM {TABLE_NAME}").fetchone()[0])

    def add_card(self, card: DrugCard) -> int:
        with self.connect() as conn:
            cursor = conn.execute(
                f"""
                INSERT INTO {TABLE_NAME} (
                    drug_name, category, mechanism, key_points, side_effects, note,
                    familiarity, review_count, last_reviewed_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                self._card_values(card, include_review=True),
            )
            return int(cursor.lastrowid)

    def update_card(self, card: DrugCard) -> None:
        if card.id is None:
            raise ValueError("Cannot update a drug card without an id.")

        with self.connect() as conn:
            conn.execute(
                f"""
                UPDATE {TABLE_NAME}
                SET drug_name = ?,
                    category = ?,
                    mechanism = ?,
                    key_points = ?,
                    side_effects = ?,
                    note = ?,
                    familiarity = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (
                    card.drug_name.strip(),
                    card.category.strip(),
                    card.mechanism.strip(),
                    card.key_points.strip(),
                    card.side_effects.strip(),
                    card.note.strip(),
                    self._normal_familiarity(card.familiarity),
                    card.id,
                ),
            )

    def mark_familiarity(self, card_id: int, familiarity: str) -> None:
        with self.connect() as conn:
            conn.execute(
                f"""
                UPDATE {TABLE_NAME}
                SET familiarity = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (self._normal_familiarity(familiarity), card_id),
            )

    def record_review(self, card_id: int) -> None:
        with self.connect() as conn:
            conn.execute(
                f"""
                UPDATE {TABLE_NAME}
                SET
                    review_count = review_count + 1,
                    last_reviewed_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (card_id,),
            )

    def delete_card(self, card_id: int) -> None:
        with self.connect() as conn:
            conn.execute(f"DELETE FROM {EXAM_ITEMS_TABLE} WHERE card_id = ?", (card_id,))
            conn.execute(f"DELETE FROM {TABLE_NAME} WHERE id = ?", (card_id,))

    def list_exam_items(self, card_id: int) -> list[ExamItem]:
        with self.connect() as conn:
            rows = conn.execute(
                f"""
                SELECT id, card_id, item_name, expected_answer, points, created_at, updated_at
                FROM {EXAM_ITEMS_TABLE}
                WHERE card_id = ?
                ORDER BY id ASC
                """,
                (card_id,),
            ).fetchall()
        return [self._row_to_exam_item(row) for row in rows]

    def add_exam_item(self, item: ExamItem) -> int:
        with self.connect() as conn:
            cursor = conn.execute(
                f"""
                INSERT INTO {EXAM_ITEMS_TABLE} (
                    card_id, item_name, expected_answer, points
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    item.card_id,
                    item.item_name.strip(),
                    item.expected_answer.strip(),
                    max(1, int(item.points or 1)),
                ),
            )
            return int(cursor.lastrowid)

    def update_exam_item(self, item: ExamItem) -> None:
        if item.id is None:
            raise ValueError("Cannot update an exam item without an id.")

        with self.connect() as conn:
            conn.execute(
                f"""
                UPDATE {EXAM_ITEMS_TABLE}
                SET item_name = ?,
                    expected_answer = ?,
                    points = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (
                    item.item_name.strip(),
                    item.expected_answer.strip(),
                    max(1, int(item.points or 1)),
                    item.id,
                ),
            )

    def delete_exam_item(self, item_id: int) -> None:
        with self.connect() as conn:
            conn.execute(f"DELETE FROM {EXAM_ITEMS_TABLE} WHERE id = ?", (item_id,))

    def save_exam_result(
        self,
        *,
        started_at: str,
        total_score: int,
        max_score: int,
        accuracy: float,
        mode: str,
        category: str,
        result_items: list[dict[str, object]],
    ) -> int:
        finished_at = datetime.now().isoformat(timespec="seconds")
        with self.connect() as conn:
            cursor = conn.execute(
                f"""
                INSERT INTO {EXAM_RESULTS_TABLE} (
                    started_at, finished_at, total_score, max_score, accuracy, mode, category
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (started_at, finished_at, total_score, max_score, accuracy, mode, category),
            )
            result_id = int(cursor.lastrowid)

            per_card: dict[int, dict[str, int]] = {}
            for item in result_items:
                card_id = int(item["card_id"])
                score = int(item["score"])
                item_max_score = int(item["max_score"])
                conn.execute(
                    f"""
                    INSERT INTO {EXAM_RESULT_ITEMS_TABLE} (
                        result_id, card_id, item_name, user_answer, expected_answer,
                        is_correct, score, max_score
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        result_id,
                        card_id,
                        str(item["item_name"]),
                        str(item["user_answer"]),
                        str(item["expected_answer"]),
                        1 if bool(item["is_correct"]) else 0,
                        score,
                        item_max_score,
                    ),
                )
                per_card.setdefault(card_id, {"score": 0, "max_score": 0})
                per_card[card_id]["score"] += score
                per_card[card_id]["max_score"] += item_max_score

            for card_id, scores in per_card.items():
                card_accuracy = (
                    scores["score"] / scores["max_score"] if scores["max_score"] else 0
                )
                conn.execute(
                    f"""
                    UPDATE {TABLE_NAME}
                    SET familiarity = ?,
                        review_count = review_count + 1,
                        last_reviewed_at = CURRENT_TIMESTAMP,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (self._familiarity_from_accuracy(card_accuracy), card_id),
                )
            return result_id

    def import_csv(self, csv_path: Path | str) -> tuple[int, str]:
        csv_file = Path(csv_path)
        last_error: Exception | None = None

        for encoding in CSV_IMPORT_ENCODINGS:
            try:
                rows = self._read_csv_rows(csv_file, encoding)
            except UnicodeDecodeError as exc:
                last_error = exc
                continue
            except csv.Error as exc:
                last_error = exc
                continue
            except ValueError as exc:
                last_error = exc
                continue

            imported_count = self._import_csv_rows(rows)
            return imported_count, encoding

        raise UnicodeError(
            "無法讀取 CSV 編碼。已嘗試："
            + ", ".join(CSV_IMPORT_ENCODINGS)
            + (
                f"\n最後錯誤：{last_error}"
                if last_error
                else "\n請確認檔案是有效的 CSV。"
            )
        )

    def _read_csv_rows(self, csv_path: Path, encoding: str) -> list[dict[str, str]]:
        with csv_path.open("r", encoding=encoding, newline="") as file:
            reader = csv.DictReader(file)
            if not self._csv_fieldnames_are_reasonable(reader.fieldnames):
                raise ValueError(
                    "CSV 欄位名稱不符合格式，至少需要 drug_name 欄位。"
                )
            return [
                {
                    str(key): self._csv_text(value)
                    for key, value in row.items()
                    if key is not None
                }
                for row in reader
            ]

    def _import_csv_rows(self, rows: list[dict[str, str]]) -> int:
        imported_count = 0
        with self.connect() as conn:
            for row in rows:
                card = DrugCard(
                    id=None,
                    drug_name=self._csv_text(row.get("drug_name")).strip(),
                    category=self._csv_text(row.get("category")),
                    mechanism=self._csv_text(row.get("mechanism")),
                    key_points=self._csv_text(row.get("key_points")),
                    side_effects=self._csv_text(row.get("side_effects")),
                    note=self._csv_text(row.get("note")),
                    familiarity=self._csv_text(row.get("familiarity")) or DEFAULT_FAMILIARITY,
                )
                if not card.drug_name:
                    continue
                conn.execute(
                    f"""
                    INSERT INTO {TABLE_NAME} (
                        drug_name, category, mechanism, key_points, side_effects,
                        note, familiarity, review_count, last_reviewed_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    self._card_values(card, include_review=True),
                )
                imported_count += 1
        return imported_count

    def export_csv(self, csv_path: Path | str) -> int:
        cards = self.list_cards()
        with Path(csv_path).open("w", encoding="utf-8-sig", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=CARD_EXPORT_FIELDNAMES)
            writer.writeheader()
            for card in cards:
                writer.writerow(
                    {field: self._csv_text(getattr(card, field)) for field in CARD_EXPORT_FIELDNAMES}
                )
        return len(cards)

    def export_xlsx(self, xlsx_path: Path | str) -> int:
        try:
            from openpyxl import Workbook
        except ImportError as exc:
            raise RuntimeError(
                "缺少 openpyxl 套件，無法匯出 Excel 檔案。請重新安裝 requirements.txt。"
            ) from exc

        cards = self.list_cards()
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Drug Cards"
        sheet.append(CARD_EXPORT_FIELDNAMES)
        for card in cards:
            sheet.append(
                [self._csv_text(getattr(card, field)) for field in CARD_EXPORT_FIELDNAMES]
            )

        for column_cells in sheet.columns:
            max_length = max(len(str(cell.value or "")) for cell in column_cells)
            sheet.column_dimensions[column_cells[0].column_letter].width = min(
                max(max_length + 2, 12),
                48,
            )

        workbook.save(xlsx_path)
        return len(cards)

    def _card_values(self, card: DrugCard, include_review: bool) -> tuple[object, ...]:
        values: list[object] = [
            card.drug_name.strip(),
            card.category.strip(),
            card.mechanism.strip(),
            card.key_points.strip(),
            card.side_effects.strip(),
            card.note.strip(),
            self._normal_familiarity(card.familiarity),
        ]
        if include_review:
            values.extend(
                [
                    int(card.review_count or 0),
                    card.last_reviewed_at,
                ]
            )
        return tuple(values)

    @staticmethod
    def _csv_text(value: object) -> str:
        if value is None:
            return ""
        if isinstance(value, bytes):
            return value.decode("utf-8", errors="replace")
        return str(value)

    @staticmethod
    def _csv_fieldnames_are_reasonable(fieldnames: list[str] | None) -> bool:
        if not fieldnames:
            return False
        normalized = {str(field).strip().lstrip("\ufeff") for field in fieldnames}
        return "drug_name" in normalized

    @staticmethod
    def _normal_familiarity(value: str) -> str:
        return value if value in FAMILIARITY_LEVELS else DEFAULT_FAMILIARITY

    @staticmethod
    def _familiarity_from_accuracy(accuracy: float) -> str:
        if accuracy >= 0.8:
            return "熟"
        if accuracy >= 0.5:
            return "普通"
        return "不熟"

    @staticmethod
    def _row_to_card(row: sqlite3.Row) -> DrugCard:
        return DrugCard(
            id=row["id"],
            drug_name=row["drug_name"],
            category=row["category"],
            mechanism=row["mechanism"],
            key_points=row["key_points"],
            side_effects=row["side_effects"],
            note=row["note"],
            familiarity=row["familiarity"],
            review_count=row["review_count"],
            last_reviewed_at=row["last_reviewed_at"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    @staticmethod
    def _row_to_exam_item(row: sqlite3.Row) -> ExamItem:
        return ExamItem(
            id=row["id"],
            card_id=row["card_id"],
            item_name=row["item_name"],
            expected_answer=row["expected_answer"],
            points=row["points"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
