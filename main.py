from __future__ import annotations

import html
import random
import sys
from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from database import DB_PATH, DrugCardDatabase
from models import DEFAULT_FAMILIARITY, FAMILIARITY_LEVELS, DrugCard, ExamItem, ExamQuestion


APP_TITLE = "藥物記憶卡"


def normalize_answer(value: str) -> str:
    return " ".join(value.strip().casefold().split())


class DrugCardDialog(QDialog):
    def __init__(self, parent: QWidget | None = None, card: DrugCard | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("編輯藥物" if card else "新增藥物")
        self.setMinimumWidth(560)
        self.card = card

        self.drug_name_input = QLineEdit()
        self.category_input = QLineEdit()
        self.mechanism_input = QTextEdit()
        self.key_points_input = QTextEdit()
        self.side_effects_input = QTextEdit()
        self.note_input = QTextEdit()
        self.familiarity_input = QComboBox()
        self.familiarity_input.addItems(FAMILIARITY_LEVELS)

        for text_edit in (
            self.mechanism_input,
            self.key_points_input,
            self.side_effects_input,
            self.note_input,
        ):
            text_edit.setMinimumHeight(80)
            text_edit.setAcceptRichText(False)

        form = QFormLayout()
        form.addRow("drug_name", self.drug_name_input)
        form.addRow("category", self.category_input)
        form.addRow("mechanism", self.mechanism_input)
        form.addRow("key_points", self.key_points_input)
        form.addRow("side_effects", self.side_effects_input)
        form.addRow("note", self.note_input)
        form.addRow("familiarity", self.familiarity_input)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

        if card:
            self._load_card(card)

    def _load_card(self, card: DrugCard) -> None:
        self.drug_name_input.setText(card.drug_name)
        self.category_input.setText(card.category)
        self.mechanism_input.setPlainText(card.mechanism)
        self.key_points_input.setPlainText(card.key_points)
        self.side_effects_input.setPlainText(card.side_effects)
        self.note_input.setPlainText(card.note)
        self.familiarity_input.setCurrentText(card.familiarity or DEFAULT_FAMILIARITY)

    def get_card(self) -> DrugCard:
        return DrugCard(
            id=self.card.id if self.card else None,
            drug_name=self.drug_name_input.text(),
            category=self.category_input.text(),
            mechanism=self.mechanism_input.toPlainText(),
            key_points=self.key_points_input.toPlainText(),
            side_effects=self.side_effects_input.toPlainText(),
            note=self.note_input.toPlainText(),
            familiarity=self.familiarity_input.currentText(),
            review_count=self.card.review_count if self.card else 0,
            last_reviewed_at=self.card.last_reviewed_at if self.card else None,
        )

    def accept(self) -> None:
        if not self.drug_name_input.text().strip():
            QMessageBox.warning(self, "欄位不足", "drug_name 為必填欄位。")
            self.drug_name_input.setFocus()
            return
        super().accept()


class ExamItemDialog(QDialog):
    def __init__(
        self,
        parent: QWidget | None,
        card_id: int,
        item: ExamItem | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("編輯考試項目" if item else "新增考試項目")
        self.setMinimumWidth(520)
        self.card_id = card_id
        self.item = item

        self.item_name_input = QLineEdit()
        self.expected_answer_input = QTextEdit()
        self.expected_answer_input.setAcceptRichText(False)
        self.expected_answer_input.setMinimumHeight(100)
        self.points_input = QSpinBox()
        self.points_input.setRange(1, 999)
        self.points_input.setValue(1)

        form = QFormLayout()
        form.addRow("項目名稱 item_name", self.item_name_input)
        form.addRow("標準答案 expected_answer", self.expected_answer_input)
        form.addRow("分數 points", self.points_input)

        hint = QLabel("考試時答案需要和標準答案一致才會得分；只忽略大小寫、前後空白與連續空白。")
        hint.setWordWrap(True)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(hint)
        layout.addLayout(form)
        layout.addWidget(buttons)

        if item:
            self.item_name_input.setText(item.item_name)
            self.expected_answer_input.setPlainText(item.expected_answer)
            self.points_input.setValue(max(1, item.points))

    def get_item(self) -> ExamItem:
        return ExamItem(
            id=self.item.id if self.item else None,
            card_id=self.card_id,
            item_name=self.item_name_input.text(),
            expected_answer=self.expected_answer_input.toPlainText(),
            points=self.points_input.value(),
        )

    def accept(self) -> None:
        if not self.item_name_input.text().strip():
            QMessageBox.warning(self, "欄位不足", "項目名稱為必填。")
            self.item_name_input.setFocus()
            return
        if not self.expected_answer_input.toPlainText().strip():
            QMessageBox.warning(self, "欄位不足", "標準答案為必填。")
            self.expected_answer_input.setFocus()
            return
        super().accept()


class ExamItemManagerDialog(QDialog):
    def __init__(self, parent: "MainWindow") -> None:
        super().__init__(parent)
        self.main_window = parent
        self.db = parent.db
        self.cards: list[DrugCard] = []
        self.items: list[ExamItem] = []

        self.setWindowTitle("考試項目管理")
        self.resize(720, 520)

        self.card_combo = QComboBox()
        self.card_combo.currentIndexChanged.connect(self.reload_items)

        self.item_list = QListWidget()

        add_button = QPushButton("新增項目")
        edit_button = QPushButton("編輯項目")
        delete_button = QPushButton("刪除項目")
        close_button = QPushButton("關閉")

        add_button.clicked.connect(self.add_item)
        edit_button.clicked.connect(self.edit_item)
        delete_button.clicked.connect(self.delete_item)
        close_button.clicked.connect(self.accept)

        hint = QLabel("提示：考試採嚴格比對，不做同義詞、關鍵字或模糊判斷。")
        hint.setWordWrap(True)

        button_layout = QHBoxLayout()
        button_layout.addWidget(add_button)
        button_layout.addWidget(edit_button)
        button_layout.addWidget(delete_button)
        button_layout.addStretch()
        button_layout.addWidget(close_button)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("選擇藥物卡片"))
        layout.addWidget(self.card_combo)
        layout.addWidget(hint)
        layout.addWidget(self.item_list, 1)
        layout.addLayout(button_layout)

        self.reload_cards()

    def reload_cards(self) -> None:
        current_id = self.card_combo.currentData()
        self.cards = self.db.list_cards()
        self.card_combo.blockSignals(True)
        self.card_combo.clear()
        for card in self.cards:
            label = f"{card.drug_name}（{card.category or '未分類'}）"
            self.card_combo.addItem(label, card.id)
        index = self.card_combo.findData(current_id)
        self.card_combo.setCurrentIndex(index if index >= 0 else 0)
        self.card_combo.blockSignals(False)
        self.reload_items()

    def current_card_id(self) -> int | None:
        card_id = self.card_combo.currentData()
        return int(card_id) if card_id is not None else None

    def current_item(self) -> ExamItem | None:
        selected = self.item_list.currentItem()
        if not selected:
            return None
        item_id = selected.data(Qt.UserRole)
        return next((item for item in self.items if item.id == item_id), None)

    def reload_items(self) -> None:
        self.item_list.clear()
        card_id = self.current_card_id()
        if card_id is None:
            self.items = []
            self.item_list.addItem("目前沒有藥物卡片。請先新增藥物。")
            return

        self.items = self.db.list_exam_items(card_id)
        if not self.items:
            self.item_list.addItem("此藥物尚未設定考試項目。")
            return

        for item in self.items:
            list_item = QListWidgetItem(
                f"{item.item_name} | {item.points} 分 | 標準答案：{item.expected_answer}"
            )
            list_item.setData(Qt.UserRole, item.id)
            self.item_list.addItem(list_item)

    def add_item(self) -> None:
        card_id = self.current_card_id()
        if card_id is None:
            QMessageBox.information(self, "沒有卡片", "請先新增藥物卡片。")
            return
        dialog = ExamItemDialog(self, card_id)
        if dialog.exec() != QDialog.Accepted:
            return
        self.db.add_exam_item(dialog.get_item())
        self.reload_items()

    def edit_item(self) -> None:
        item = self.current_item()
        if not item:
            QMessageBox.information(self, "沒有項目", "請先選擇一個考試項目。")
            return
        dialog = ExamItemDialog(self, item.card_id, item)
        if dialog.exec() != QDialog.Accepted:
            return
        self.db.update_exam_item(dialog.get_item())
        self.reload_items()

    def delete_item(self) -> None:
        item = self.current_item()
        if not item or item.id is None:
            QMessageBox.information(self, "沒有項目", "請先選擇一個考試項目。")
            return
        reply = QMessageBox.question(
            self,
            "刪除確認",
            f"確定要刪除「{item.item_name}」嗎？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        self.db.delete_exam_item(item.id)
        self.reload_items()


class SettingsDialog(QDialog):
    def __init__(self, parent: "MainWindow") -> None:
        super().__init__(parent)
        self.main_window = parent
        self.setWindowTitle("設定")
        self.setMinimumWidth(380)

        add_button = QPushButton("新增藥物")
        edit_button = QPushButton("編輯目前卡片")
        delete_button = QPushButton("刪除目前卡片")
        exam_items_button = QPushButton("考試項目管理")
        database_help_button = QPushButton("資料庫說明")
        import_button = QPushButton("匯入 CSV")
        export_button = QPushButton("匯出 CSV")
        export_xlsx_button = QPushButton("匯出 Excel .xlsx")
        close_button = QPushButton("關閉")

        add_button.clicked.connect(self.main_window.add_card)
        edit_button.clicked.connect(self.main_window.edit_card)
        delete_button.clicked.connect(self.main_window.delete_card)
        exam_items_button.clicked.connect(self.main_window.open_exam_item_manager)
        database_help_button.clicked.connect(self.main_window.show_database_help)
        import_button.clicked.connect(self.main_window.import_csv)
        export_button.clicked.connect(self.main_window.export_csv)
        export_xlsx_button.clicked.connect(self.main_window.export_xlsx)
        close_button.clicked.connect(self.accept)

        layout = QVBoxLayout(self)
        csv_hint = QLabel(
            "若直接開啟 CSV 看到中文亂碼，請使用本軟體的 UTF-8 BOM 匯出，"
            "或改用 Excel 的資料匯入功能選擇 UTF-8 編碼。"
        )
        csv_hint.setWordWrap(True)

        layout.addWidget(add_button)
        layout.addWidget(edit_button)
        layout.addWidget(delete_button)
        layout.addSpacing(12)
        layout.addWidget(exam_items_button)
        layout.addWidget(database_help_button)
        layout.addSpacing(12)
        layout.addWidget(csv_hint)
        layout.addWidget(import_button)
        layout.addWidget(export_button)
        layout.addWidget(export_xlsx_button)
        layout.addStretch()
        layout.addWidget(close_button)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.db = DrugCardDatabase()
        self.cards: list[DrugCard] = []
        self.current_index = 0
        self.is_back_visible = False
        self._updating_familiarity_buttons = False

        self.exam_questions: list[ExamQuestion] = []
        self.exam_current_index = 0
        self.exam_started_at = ""
        self.exam_result_items: list[dict[str, object]] = []
        self.exam_current_checked = False
        self.exam_answer_inputs: dict[int, QTextEdit] = {}
        self.exam_last_scope = "all"
        self.exam_last_category = ""
        self.exam_last_count: int | None = None

        self.setWindowTitle(APP_TITLE)
        self.resize(1040, 760)
        self.setMinimumSize(900, 660)
        self._build_ui()
        self._build_menu()
        self.reload_categories()
        self.refresh_cards()

    def _build_menu(self) -> None:
        settings_action = QAction("設定", self)
        settings_action.triggered.connect(self.open_settings)

        exit_action = QAction("離開", self)
        exit_action.triggered.connect(self.close)

        menu = self.menuBar().addMenu("檔案")
        menu.addAction(settings_action)
        menu.addSeparator()
        menu.addAction(exit_action)

    def _build_ui(self) -> None:
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        self.review_page = QWidget()
        self.exam_page = QWidget()
        self.tabs.addTab(self.review_page, "複習模式")
        self.tabs.addTab(self.exam_page, "考試模式")

        self._build_review_page()
        self._build_exam_page()

        self.setStyleSheet(
            """
            QWidget {
                font-family: "Microsoft JhengHei UI", "Segoe UI", sans-serif;
                font-size: 14px;
            }
            QMainWindow, QTabWidget::pane {
                background: #f4f6f8;
            }
            QFrame#cardFrame, QFrame#examPanel, QFrame#examQuestionPanel, QFrame#examSummaryPanel {
                background: #ffffff;
                border: 1px solid #d6dce3;
                border-radius: 8px;
            }
            QLabel#titleLabel, QLabel#examDrugLabel {
                color: #15202b;
                font-size: 34px;
                font-weight: 700;
            }
            QLabel#detailLabel, QLabel#examResultLabel, QLabel#examSummaryLabel {
                color: #273444;
                font-size: 16px;
            }
            QPushButton {
                background: #ffffff;
                border: 1px solid #b8c2cc;
                border-radius: 6px;
                padding: 9px 16px;
            }
            QPushButton:hover {
                background: #eef4fb;
                border-color: #7aa7d9;
            }
            QPushButton:disabled {
                color: #9aa5b1;
                background: #eef0f2;
            }
            QLineEdit, QComboBox, QSpinBox, QTextEdit {
                background: #ffffff;
                border: 1px solid #b8c2cc;
                border-radius: 6px;
                padding: 7px 10px;
            }
            """
        )

    def _build_review_page(self) -> None:
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜尋 drug_name")
        self.search_input.textChanged.connect(self.apply_filters)

        self.category_combo = QComboBox()
        self.category_combo.currentIndexChanged.connect(self.apply_filters)

        self.unfamiliar_only_checkbox = QCheckBox("只複習不熟")
        self.unfamiliar_only_checkbox.toggled.connect(self.apply_filters)

        self.settings_button = QPushButton("設定")
        self.settings_button.clicked.connect(self.open_settings)

        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("搜尋"))
        filter_layout.addWidget(self.search_input, 2)
        filter_layout.addWidget(QLabel("分類"))
        filter_layout.addWidget(self.category_combo, 1)
        filter_layout.addWidget(self.unfamiliar_only_checkbox)
        filter_layout.addStretch()
        filter_layout.addWidget(self.settings_button)

        self.card_frame = QFrame()
        self.card_frame.setObjectName("cardFrame")
        self.card_frame.setFrameShape(QFrame.StyledPanel)
        self.card_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.title_label = QLabel()
        self.title_label.setObjectName("titleLabel")
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setWordWrap(True)

        self.detail_label = QLabel()
        self.detail_label.setObjectName("detailLabel")
        self.detail_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.detail_label.setWordWrap(True)
        self.detail_label.setTextFormat(Qt.RichText)
        self.detail_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.detail_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)

        self.detail_scroll = QScrollArea()
        self.detail_scroll.setWidgetResizable(True)
        self.detail_scroll.setFrameShape(QFrame.NoFrame)
        self.detail_scroll.setWidget(self.detail_label)

        card_layout = QVBoxLayout(self.card_frame)
        card_layout.setContentsMargins(36, 32, 36, 32)
        card_layout.setSpacing(20)
        card_layout.addWidget(self.title_label)
        card_layout.addWidget(self.detail_scroll, 1)

        self.counter_label = QLabel()
        self.counter_label.setAlignment(Qt.AlignCenter)

        self.review_meta_label = QLabel()
        self.review_meta_label.setAlignment(Qt.AlignCenter)

        self.prev_button = QPushButton("上一張")
        self.flip_button = QPushButton("翻面")
        self.next_button = QPushButton("下一張")
        self.random_button = QPushButton("隨機抽卡")

        self.prev_button.clicked.connect(self.previous_card)
        self.flip_button.clicked.connect(self.flip_card)
        self.next_button.clicked.connect(self.next_card)
        self.random_button.clicked.connect(self.random_card)

        nav_layout = QHBoxLayout()
        nav_layout.addWidget(self.prev_button)
        nav_layout.addWidget(self.flip_button)
        nav_layout.addWidget(self.next_button)
        nav_layout.addWidget(self.random_button)

        self.familiarity_widget = QWidget()
        self.familiarity_group = QButtonGroup(self)
        self.familiarity_buttons: dict[str, QRadioButton] = {}
        familiarity_layout = QHBoxLayout(self.familiarity_widget)
        familiarity_layout.setContentsMargins(0, 0, 0, 0)
        familiarity_layout.addStretch()
        familiarity_layout.addWidget(QLabel("熟悉度"))
        for level in FAMILIARITY_LEVELS:
            button = QRadioButton(level)
            self.familiarity_group.addButton(button)
            self.familiarity_buttons[level] = button
            familiarity_layout.addWidget(button)
        familiarity_layout.addStretch()
        self.familiarity_group.buttonClicked.connect(self.mark_current_familiarity)

        layout = QVBoxLayout(self.review_page)
        layout.setContentsMargins(24, 18, 24, 24)
        layout.setSpacing(14)
        layout.addLayout(filter_layout)
        layout.addWidget(self.card_frame, 1)
        layout.addWidget(self.counter_label)
        layout.addWidget(self.review_meta_label)
        layout.addWidget(self.familiarity_widget)
        layout.addLayout(nav_layout)

    def _build_exam_page(self) -> None:
        self.exam_setup_panel = QFrame()
        self.exam_setup_panel.setObjectName("examPanel")
        setup_layout = QVBoxLayout(self.exam_setup_panel)
        setup_layout.setContentsMargins(24, 24, 24, 24)
        setup_layout.setSpacing(14)

        self.exam_scope_combo = QComboBox()
        self.exam_scope_combo.addItem("全部卡片", "all")
        self.exam_scope_combo.addItem("指定分類", "category")
        self.exam_scope_combo.addItem("只考不熟", "unfamiliar")
        self.exam_scope_combo.currentIndexChanged.connect(self.update_exam_scope_controls)

        self.exam_category_combo = QComboBox()

        self.exam_count_combo = QComboBox()
        self.exam_count_combo.addItem("全部", None)
        self.exam_count_combo.addItem("10 題", 10)
        self.exam_count_combo.addItem("20 題", 20)
        self.exam_count_combo.addItem("自訂數量", "custom")
        self.exam_count_combo.currentIndexChanged.connect(self.update_exam_count_controls)

        self.exam_custom_count_spin = QSpinBox()
        self.exam_custom_count_spin.setRange(1, 9999)
        self.exam_custom_count_spin.setValue(10)

        self.start_exam_button = QPushButton("開始考試")
        self.start_exam_button.clicked.connect(self.start_exam)

        setup_form = QFormLayout()
        setup_form.addRow("考試範圍", self.exam_scope_combo)
        setup_form.addRow("分類", self.exam_category_combo)
        setup_form.addRow("題目數量", self.exam_count_combo)
        setup_form.addRow("自訂題數", self.exam_custom_count_spin)

        self.exam_setup_hint = QLabel("請先到設定 > 考試項目管理，為卡片設定標準答案。")
        self.exam_setup_hint.setWordWrap(True)

        setup_layout.addLayout(setup_form)
        setup_layout.addWidget(self.exam_setup_hint)
        setup_layout.addWidget(self.start_exam_button, alignment=Qt.AlignRight)

        self.exam_question_panel = QFrame()
        self.exam_question_panel.setObjectName("examQuestionPanel")
        question_layout = QVBoxLayout(self.exam_question_panel)
        question_layout.setContentsMargins(24, 24, 24, 24)
        question_layout.setSpacing(14)

        self.exam_progress_label = QLabel()
        self.exam_progress_label.setAlignment(Qt.AlignCenter)

        self.exam_drug_label = QLabel()
        self.exam_drug_label.setObjectName("examDrugLabel")
        self.exam_drug_label.setAlignment(Qt.AlignCenter)
        self.exam_drug_label.setWordWrap(True)

        self.exam_answers_widget = QWidget()
        self.exam_answers_layout = QFormLayout(self.exam_answers_widget)

        self.exam_answers_scroll = QScrollArea()
        self.exam_answers_scroll.setWidgetResizable(True)
        self.exam_answers_scroll.setFrameShape(QFrame.NoFrame)
        self.exam_answers_scroll.setWidget(self.exam_answers_widget)

        self.confirm_answer_button = QPushButton("確認答案")
        self.next_question_button = QPushButton("下一題")
        self.next_question_button.setEnabled(False)
        self.confirm_answer_button.clicked.connect(self.confirm_exam_answer)
        self.next_question_button.clicked.connect(self.next_exam_question)

        self.exam_result_label = QLabel()
        self.exam_result_label.setObjectName("examResultLabel")
        self.exam_result_label.setTextFormat(Qt.RichText)
        self.exam_result_label.setWordWrap(True)
        self.exam_result_label.setTextInteractionFlags(Qt.TextSelectableByMouse)

        self.exam_result_scroll = QScrollArea()
        self.exam_result_scroll.setWidgetResizable(True)
        self.exam_result_scroll.setFrameShape(QFrame.NoFrame)
        self.exam_result_scroll.setWidget(self.exam_result_label)

        question_button_layout = QHBoxLayout()
        question_button_layout.addStretch()
        question_button_layout.addWidget(self.confirm_answer_button)
        question_button_layout.addWidget(self.next_question_button)

        question_layout.addWidget(self.exam_progress_label)
        question_layout.addWidget(self.exam_drug_label)
        question_layout.addWidget(self.exam_answers_scroll, 2)
        question_layout.addLayout(question_button_layout)
        question_layout.addWidget(self.exam_result_scroll, 2)

        self.exam_summary_panel = QFrame()
        self.exam_summary_panel.setObjectName("examSummaryPanel")
        summary_layout = QVBoxLayout(self.exam_summary_panel)
        summary_layout.setContentsMargins(24, 24, 24, 24)
        summary_layout.setSpacing(14)

        self.exam_summary_label = QLabel()
        self.exam_summary_label.setObjectName("examSummaryLabel")
        self.exam_summary_label.setTextFormat(Qt.RichText)
        self.exam_summary_label.setWordWrap(True)
        self.exam_summary_label.setTextInteractionFlags(Qt.TextSelectableByMouse)

        self.retry_exam_button = QPushButton("重新考一次")
        self.retry_exam_button.clicked.connect(self.retry_exam)

        summary_layout.addWidget(self.exam_summary_label, 1)
        summary_layout.addWidget(self.retry_exam_button, alignment=Qt.AlignRight)

        layout = QVBoxLayout(self.exam_page)
        layout.setContentsMargins(24, 18, 24, 24)
        layout.setSpacing(14)
        layout.addWidget(self.exam_setup_panel)
        layout.addWidget(self.exam_question_panel, 1)
        layout.addWidget(self.exam_summary_panel, 1)

        self.exam_question_panel.setVisible(False)
        self.exam_summary_panel.setVisible(False)
        self.update_exam_scope_controls()
        self.update_exam_count_controls()

    def open_settings(self) -> None:
        SettingsDialog(self).exec()

    def open_exam_item_manager(self) -> None:
        ExamItemManagerDialog(self).exec()

    def show_database_help(self) -> None:
        QMessageBox.information(
            self,
            "資料庫說明",
            "目前資料會儲存在軟體資料夾底下的 data\\drug_cards.db。\n\n"
            f"目前使用的資料庫：\n{DB_PATH}\n\n"
            "一般使用者建議用軟體內的設定功能新增、編輯、刪除資料，"
            "或使用 CSV 匯入 / 匯出大量編輯。\n\n"
            "備份資料：關閉軟體後，複製 data\\drug_cards.db 到安全位置。\n\n"
            "更換資料庫：關閉軟體後，用另一個 drug_cards.db 覆蓋 data\\drug_cards.db，"
            "再重新開啟軟體。",
        )

    def reload_categories(self) -> None:
        current_category = self.category_combo.currentData() or ""
        self.category_combo.blockSignals(True)
        self.category_combo.clear()
        self.category_combo.addItem("全部分類", "")
        for category in self.db.list_categories():
            self.category_combo.addItem(category, category)
        index = self.category_combo.findData(current_category)
        self.category_combo.setCurrentIndex(index if index >= 0 else 0)
        self.category_combo.blockSignals(False)

        current_exam_category = self.exam_category_combo.currentData() or ""
        self.exam_category_combo.blockSignals(True)
        self.exam_category_combo.clear()
        for category in self.db.list_categories():
            self.exam_category_combo.addItem(category, category)
        exam_index = self.exam_category_combo.findData(current_exam_category)
        self.exam_category_combo.setCurrentIndex(exam_index if exam_index >= 0 else 0)
        self.exam_category_combo.blockSignals(False)

    def update_exam_scope_controls(self) -> None:
        is_category_mode = self.exam_scope_combo.currentData() == "category"
        self.exam_category_combo.setEnabled(is_category_mode)

    def update_exam_count_controls(self) -> None:
        self.exam_custom_count_spin.setEnabled(self.exam_count_combo.currentData() == "custom")

    def apply_filters(self) -> None:
        self.current_index = 0
        self.is_back_visible = False
        self.refresh_cards()

    def refresh_cards(
        self,
        keep_current_id: int | None = None,
        reset_side: bool = True,
    ) -> None:
        self.cards = self.db.list_cards(
            search_text=self.search_input.text(),
            category=self.category_combo.currentData() or "",
            unfamiliar_only=self.unfamiliar_only_checkbox.isChecked(),
        )
        if not self.cards:
            self.current_index = 0
            self.is_back_visible = False
            self._render_empty_state()
            return

        if keep_current_id is not None:
            ids = [card.id for card in self.cards]
            self.current_index = ids.index(keep_current_id) if keep_current_id in ids else 0
        else:
            self.current_index = min(self.current_index, len(self.cards) - 1)

        if reset_side:
            self.is_back_visible = False
        self.render_card()

    def _render_empty_state(self) -> None:
        total_count = self.db.count_cards()
        self.title_label.setText("沒有可顯示的藥物卡")
        if total_count == 0:
            self.detail_label.setText("目前資料庫是空的。請到設定新增藥物或匯入 CSV。")
        else:
            self.detail_label.setText("目前搜尋、分類或只複習不熟條件下沒有符合的卡片。")
        self.detail_scroll.setVisible(True)
        self.counter_label.setText(f"進度：0 / 0　|　資料庫總卡片數：{total_count}")
        self.review_meta_label.setText("")
        self.familiarity_widget.setVisible(False)
        self._set_card_buttons_enabled(False)
        self._sync_familiarity_buttons(None)

    def _set_card_buttons_enabled(self, enabled: bool) -> None:
        for button in (
            self.prev_button,
            self.flip_button,
            self.next_button,
            self.random_button,
        ):
            button.setEnabled(enabled)
        for button in self.familiarity_buttons.values():
            button.setEnabled(enabled)

    def current_card(self) -> DrugCard | None:
        if not self.cards:
            return None
        return self.cards[self.current_index]

    def render_card(self) -> None:
        card = self.current_card()
        if not card:
            self._render_empty_state()
            return

        self._set_card_buttons_enabled(True)
        total_count = self.db.count_cards()
        self.counter_label.setText(
            f"進度：{self.current_index + 1} / {len(self.cards)}　|　資料庫總卡片數：{total_count}"
        )
        last_reviewed = card.last_reviewed_at or "尚未複習"
        self._sync_familiarity_buttons(card)

        if self.is_back_visible:
            self.title_label.setText(card.drug_name)
            self.detail_label.setText(self._format_back_html(card))
            self.detail_scroll.setVisible(True)
            self.review_meta_label.setText(
                f"熟悉度：{card.familiarity}　|　複習次數：{card.review_count}　|　最後複習：{last_reviewed}"
            )
            self.familiarity_widget.setVisible(True)
            self.flip_button.setText("顯示正面")
        else:
            self.title_label.setText(card.drug_name)
            self.detail_label.setText("")
            self.detail_scroll.setVisible(False)
            self.review_meta_label.setText(
                f"複習次數：{card.review_count}　|　最後複習：{last_reviewed}"
            )
            self.familiarity_widget.setVisible(False)
            self.flip_button.setText("翻面")

    def _sync_familiarity_buttons(self, card: DrugCard | None) -> None:
        self._updating_familiarity_buttons = True
        self.familiarity_group.setExclusive(False)
        for level, button in self.familiarity_buttons.items():
            button.setChecked(bool(card and card.familiarity == level))
        self.familiarity_group.setExclusive(True)
        self._updating_familiarity_buttons = False

    def _format_back_html(self, card: DrugCard) -> str:
        fields = (
            ("分類", card.category),
            ("藥物的機制", card.mechanism),
            ("考點", card.key_points),
            ("副作用", card.side_effects),
            ("備註", card.note),
        )
        sections = []
        for index, (label, value) in enumerate(fields):
            top_border = "border-top: 1px solid #d6dce3;" if index else ""
            escaped_value = html.escape(value.strip() or "-").replace("\n", "<br>")
            sections.append(
                f"""
                <div style="{top_border} padding-top: 12px; margin-top: 12px;">
                    <div style="font-weight: 700; color: #15202b; margin-bottom: 6px;">{label}</div>
                    <div style="line-height: 1.6;">{escaped_value}</div>
                </div>
                """
            )
        return "<div>" + "".join(sections) + "</div>"

    def previous_card(self) -> None:
        if not self.cards:
            return
        self.current_index = (self.current_index - 1) % len(self.cards)
        self.is_back_visible = False
        self.render_card()

    def next_card(self) -> None:
        if not self.cards:
            return
        self.current_index = (self.current_index + 1) % len(self.cards)
        self.is_back_visible = False
        self.render_card()

    def random_card(self) -> None:
        if not self.cards:
            return
        if len(self.cards) == 1:
            self.current_index = 0
        else:
            choices = [index for index in range(len(self.cards)) if index != self.current_index]
            self.current_index = random.choice(choices)
        self.is_back_visible = False
        self.render_card()

    def flip_card(self) -> None:
        if not self.cards:
            return

        card = self.current_card()
        if not self.is_back_visible and card and card.id is not None:
            self.is_back_visible = True
            self.db.record_review(card.id)
            self.refresh_cards(keep_current_id=card.id, reset_side=False)
            return

        self.is_back_visible = False
        self.render_card()

    def mark_current_familiarity(self, _button=None) -> None:
        if self._updating_familiarity_buttons:
            return
        card = self.current_card()
        checked_button = self.familiarity_group.checkedButton()
        if not card or card.id is None or not checked_button:
            return

        self.db.mark_familiarity(card.id, checked_button.text())
        self.refresh_cards(keep_current_id=card.id, reset_side=False)

    def add_card(self) -> None:
        dialog = DrugCardDialog(self)
        if dialog.exec() != QDialog.Accepted:
            return

        card = dialog.get_card()
        new_id = self.db.add_card(card)
        self.reload_categories()
        self.refresh_cards(keep_current_id=new_id)

    def edit_card(self) -> None:
        card = self.current_card()
        if not card:
            QMessageBox.information(self, "沒有卡片", "目前沒有可編輯的卡片。")
            return

        dialog = DrugCardDialog(self, card)
        if dialog.exec() != QDialog.Accepted:
            return

        updated_card = dialog.get_card()
        self.db.update_card(updated_card)
        self.reload_categories()
        self.refresh_cards(keep_current_id=updated_card.id)

    def delete_card(self) -> None:
        card = self.current_card()
        if not card or card.id is None:
            QMessageBox.information(self, "沒有卡片", "目前沒有可刪除的卡片。")
            return

        reply = QMessageBox.question(
            self,
            "刪除確認",
            f"確定要刪除「{card.drug_name}」嗎？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        self.db.delete_card(card.id)
        self.current_index = max(0, self.current_index - 1)
        self.reload_categories()
        self.refresh_cards()

    def import_csv(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "選擇 CSV 檔案",
            "",
            "CSV Files (*.csv);;All Files (*)",
        )
        if not path:
            return

        try:
            imported_count, encoding = self.db.import_csv(path)
        except Exception as exc:
            QMessageBox.critical(self, "匯入失敗", f"CSV 匯入失敗：\n{exc}")
            return

        self.reload_categories()
        self.refresh_cards()
        QMessageBox.information(
            self,
            "匯入完成",
            f"已使用 {encoding} 匯入 {imported_count} 張卡片。",
        )

    def export_csv(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "匯出 CSV 檔案",
            "drug_cards_export.csv",
            "CSV Files (*.csv);;All Files (*)",
        )
        if not path:
            return
        if not path.lower().endswith(".csv"):
            path = f"{path}.csv"

        try:
            exported_count = self.db.export_csv(path)
        except Exception as exc:
            QMessageBox.critical(self, "匯出失敗", f"CSV 匯出失敗：\n{exc}")
            return

        QMessageBox.information(
            self,
            "匯出完成",
            f"已匯出 {exported_count} 張卡片。\n已用 UTF-8 BOM 格式匯出，建議用 Excel 開啟。",
        )

    def export_xlsx(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "匯出 Excel 檔案",
            "drug_cards_export.xlsx",
            "Excel Files (*.xlsx);;All Files (*)",
        )
        if not path:
            return
        if not path.lower().endswith(".xlsx"):
            path = f"{path}.xlsx"

        try:
            exported_count = self.db.export_xlsx(path)
        except Exception as exc:
            QMessageBox.critical(self, "匯出失敗", f"Excel 匯出失敗：\n{exc}")
            return

        QMessageBox.information(
            self,
            "匯出完成",
            f"已匯出 {exported_count} 張卡片。\n已匯出 Excel 檔案，建議優先使用此格式避免中文亂碼。",
        )

    def _clear_exam_answer_form(self) -> None:
        while self.exam_answers_layout.count():
            item = self.exam_answers_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.exam_answer_inputs.clear()

    def _exam_count_limit(self) -> int | None:
        value = self.exam_count_combo.currentData()
        if value == "custom":
            return self.exam_custom_count_spin.value()
        return int(value) if value else None

    def start_exam(self) -> None:
        scope = self.exam_scope_combo.currentData()
        category = self.exam_category_combo.currentData() or ""
        count_limit = self._exam_count_limit()
        self._start_exam_with_options(scope, category, count_limit)

    def retry_exam(self) -> None:
        self._start_exam_with_options(
            self.exam_last_scope,
            self.exam_last_category,
            self.exam_last_count,
        )

    def _start_exam_with_options(
        self,
        scope: str,
        category: str,
        count_limit: int | None,
    ) -> None:
        if scope == "category" and not category:
            QMessageBox.information(self, "沒有分類", "目前沒有可選擇的分類。")
            return

        cards = self.db.list_cards(
            category=category if scope == "category" else "",
            unfamiliar_only=scope == "unfamiliar",
        )
        if not cards:
            QMessageBox.information(self, "沒有卡片", "目前考試範圍內沒有卡片。")
            return

        questions: list[ExamQuestion] = []
        for card in cards:
            if card.id is None:
                continue
            items = self.db.list_exam_items(card.id)
            if items:
                questions.append(ExamQuestion(card=card, items=items))

        if not questions:
            QMessageBox.information(
                self,
                "沒有可考項目",
                "目前考試範圍內沒有已設定 exam_items 的卡片，請到設定 > 考試項目管理新增。",
            )
            return

        random.shuffle(questions)
        if count_limit is not None:
            questions = questions[:count_limit]

        self.exam_questions = questions
        self.exam_current_index = 0
        self.exam_started_at = datetime.now().isoformat(timespec="seconds")
        self.exam_result_items = []
        self.exam_current_checked = False
        self.exam_last_scope = scope
        self.exam_last_category = category
        self.exam_last_count = count_limit

        self.exam_setup_panel.setVisible(False)
        self.exam_summary_panel.setVisible(False)
        self.exam_question_panel.setVisible(True)
        self.render_exam_question()

    def render_exam_question(self) -> None:
        question = self.exam_questions[self.exam_current_index]
        self.exam_current_checked = False
        self.exam_progress_label.setText(
            f"題號：{self.exam_current_index + 1} / {len(self.exam_questions)}"
        )
        self.exam_drug_label.setText(question.card.drug_name)
        self.exam_result_label.setText("")
        self.confirm_answer_button.setEnabled(True)
        self.next_question_button.setEnabled(False)
        self.next_question_button.setText(
            "完成考試" if self.exam_current_index == len(self.exam_questions) - 1 else "下一題"
        )

        self._clear_exam_answer_form()
        for item in question.items:
            answer_input = QTextEdit()
            answer_input.setAcceptRichText(False)
            answer_input.setMinimumHeight(70)
            answer_input.setPlaceholderText("請輸入答案")
            self.exam_answer_inputs[item.id or -1] = answer_input
            self.exam_answers_layout.addRow(f"{item.item_name}（{item.points} 分）", answer_input)

    def confirm_exam_answer(self) -> None:
        if self.exam_current_checked:
            return

        question = self.exam_questions[self.exam_current_index]
        question_score = 0
        question_max_score = 0
        rows = []

        for item in question.items:
            input_widget = self.exam_answer_inputs.get(item.id or -1)
            user_answer = input_widget.toPlainText() if input_widget else ""
            is_correct = normalize_answer(user_answer) == normalize_answer(item.expected_answer)
            score = item.points if is_correct else 0
            question_score += score
            question_max_score += item.points
            self.exam_result_items.append(
                {
                    "card_id": question.card.id,
                    "drug_name": question.card.drug_name,
                    "item_name": item.item_name,
                    "user_answer": user_answer,
                    "expected_answer": item.expected_answer,
                    "is_correct": is_correct,
                    "score": score,
                    "max_score": item.points,
                }
            )
            rows.append(
                self._format_exam_result_row(item, user_answer, is_correct, score)
            )

        self.exam_result_label.setText(
            f"<div style='font-weight: 700; margin-bottom: 8px;'>本題得分："
            f"{question_score} / {question_max_score}</div>"
            + "".join(rows)
        )
        self.exam_current_checked = True
        self.confirm_answer_button.setEnabled(False)
        self.next_question_button.setEnabled(True)

    def _format_exam_result_row(
        self,
        item: ExamItem,
        user_answer: str,
        is_correct: bool,
        score: int,
    ) -> str:
        status = "答對" if is_correct else "答錯"
        color = "#1b7f45" if is_correct else "#b42318"
        return (
            "<div style='border-top: 1px solid #d6dce3; padding-top: 10px; margin-top: 10px;'>"
            f"<div style='font-weight: 700; color: {color};'>{html.escape(item.item_name)}：{status}"
            f"（{score} / {item.points} 分）</div>"
            f"<div>你的答案：{html.escape(user_answer.strip() or '(空答案)')}</div>"
            f"<div>標準答案：{html.escape(item.expected_answer)}</div>"
            "</div>"
        )

    def next_exam_question(self) -> None:
        if not self.exam_current_checked:
            QMessageBox.information(self, "尚未確認", "請先按下確認答案。")
            return

        if self.exam_current_index < len(self.exam_questions) - 1:
            self.exam_current_index += 1
            self.render_exam_question()
            return

        self.finish_exam()

    def finish_exam(self) -> None:
        total_score = sum(int(item["score"]) for item in self.exam_result_items)
        max_score = sum(int(item["max_score"]) for item in self.exam_result_items)
        accuracy = total_score / max_score if max_score else 0
        mode = self.exam_scope_combo.currentText()
        category = self.exam_last_category if self.exam_last_scope == "category" else ""
        self.db.save_exam_result(
            started_at=self.exam_started_at,
            total_score=total_score,
            max_score=max_score,
            accuracy=accuracy,
            mode=mode,
            category=category,
            result_items=self.exam_result_items,
        )
        self.reload_categories()
        self.refresh_cards(reset_side=False)

        wrong_items = [item for item in self.exam_result_items if not item["is_correct"]]
        wrong_html = ""
        if wrong_items:
            wrong_html = "<div style='font-weight: 700; margin-top: 16px;'>錯題列表</div>"
            for item in wrong_items:
                wrong_html += (
                    "<div style='border-top: 1px solid #d6dce3; padding-top: 8px; margin-top: 8px;'>"
                    f"<div>{html.escape(str(item['drug_name']))} - {html.escape(str(item['item_name']))}</div>"
                    f"<div>你的答案：{html.escape(str(item['user_answer']).strip() or '(空答案)')}</div>"
                    f"<div>標準答案：{html.escape(str(item['expected_answer']))}</div>"
                    "</div>"
                )
        else:
            wrong_html = "<div style='margin-top: 16px;'>本次沒有錯題。</div>"

        self.exam_summary_label.setText(
            f"<div style='font-size: 22px; font-weight: 700;'>考試完成</div>"
            f"<div style='margin-top: 10px;'>總分：{total_score}</div>"
            f"<div>滿分：{max_score}</div>"
            f"<div>正確率：{accuracy:.1%}</div>"
            f"{wrong_html}"
        )
        self.exam_question_panel.setVisible(False)
        self.exam_summary_panel.setVisible(True)
        self.exam_setup_panel.setVisible(True)

    def keyPressEvent(self, event) -> None:
        focus_widget = QApplication.focusWidget()
        if isinstance(focus_widget, (QLineEdit, QTextEdit)):
            super().keyPressEvent(event)
            return

        if self.tabs.currentWidget() == self.review_page:
            if event.key() == Qt.Key_Space:
                self.flip_card()
                event.accept()
            elif event.key() == Qt.Key_Right:
                self.next_card()
                event.accept()
            elif event.key() == Qt.Key_Left:
                self.previous_card()
                event.accept()
            else:
                super().keyPressEvent(event)
            return

        super().keyPressEvent(event)


def main() -> int:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
