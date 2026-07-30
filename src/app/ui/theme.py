from __future__ import annotations

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QPalette
from PyQt5.QtWidgets import QApplication


# ── Color Palette ──────────────────────────────────────────────
# Professional blue (#2563EB) + amber accent (#D97706)
# Inspiration: Tailwind Slate + Blue + Amber — adapted for PyQt5/QSS

class Color:
    PRIMARY = "#2563EB"
    PRIMARY_HOVER = "#1D4ED8"
    PRIMARY_ACTIVE = "#1E40AF"
    PRIMARY_LIGHT = "#DBEAFE"
    SECONDARY = "#3B82F6"
    ACCENT = "#D97706"
    ACCENT_HOVER = "#B45309"
    DESTRUCTIVE = "#DC2626"
    SUCCESS = "#16A34A"

    BG = "#F8FAFC"
    SURFACE = "#FFFFFF"
    BORDER = "#E2E8F0"
    BORDER_FOCUS = "#2563EB"

    TEXT_PRIMARY = "#0F172A"
    TEXT_SECONDARY = "#475569"
    TEXT_MUTED = "#94A3B8"
    TEXT_ON_PRIMARY = "#FFFFFF"

    SCROLLBAR_HANDLE = "#CBD5E1"
    SCROLLBAR_HOVER = "#94A3B8"

    ROW_HOVER = "#F1F5F9"
    ROW_SELECTED = "#DBEAFE"
    ROW_ALT = "#FAFBFC"


# ── Tag Chip Colors ────────────────────────────────────────────
# Deterministic color assignment from tag name hash

TAG_COLORS: list[str] = [
    "#2563EB", "#D97706", "#16A34A", "#DC2626",
    "#7C3AED", "#DB2777", "#0891B2", "#CA8A04",
    "#059669", "#9333EA", "#EA580C", "#0284C7",
]


def tag_color(name: str) -> str:
    return TAG_COLORS[hash(name) % len(TAG_COLORS)]


# ── QSS Stylesheet ─────────────────────────────────────────────

QSS = f"""
QMainWindow {{
    background: {Color.BG};
}}

/* ── LineEdit ──────────────────────────────────────────────── */
QLineEdit {{
    border: 1px solid {Color.BORDER};
    border-radius: 6px;
    padding: 7px 12px;
    background: {Color.SURFACE};
    color: {Color.TEXT_PRIMARY};
    font-size: 13px;
}}
QLineEdit:focus {{
    border-color: {Color.BORDER_FOCUS};
}}
QLineEdit::placeholder {{
    color: {Color.TEXT_MUTED};
}}

/* ── PushButton ────────────────────────────────────────────── */
QPushButton {{
    background: {Color.PRIMARY};
    color: {Color.TEXT_ON_PRIMARY};
    border: none;
    border-radius: 6px;
    padding: 7px 16px;
    font-size: 13px;
}}
QPushButton:hover {{
    background: {Color.PRIMARY_HOVER};
}}
QPushButton:pressed {{
    background: {Color.PRIMARY_ACTIVE};
}}
QPushButton:disabled {{
    background: {Color.BORDER};
    color: {Color.TEXT_MUTED};
}}
QPushButton[flat="true"] {{
    background: transparent;
    color: {Color.TEXT_SECONDARY};
    border: 1px solid {Color.BORDER};
}}
QPushButton[flat="true"]:hover {{
    background: {Color.ROW_HOVER};
    border-color: {Color.BORDER_FOCUS};
}}

/* ── ComboBox ──────────────────────────────────────────────── */
QComboBox {{
    border: 1px solid {Color.BORDER};
    border-radius: 6px;
    padding: 6px 12px;
    background: {Color.SURFACE};
    color: {Color.TEXT_PRIMARY};
    font-size: 13px;
    min-width: 100px;
}}
QComboBox:hover {{
    border-color: {Color.BORDER_FOCUS};
}}
QComboBox::drop-down {{
    border: none;
    padding-right: 8px;
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 20px;
}}
QComboBox::down-arrow {{
    width: 10px;
    height: 10px;
}}
QComboBox QAbstractItemView {{
    border: 1px solid {Color.BORDER};
    border-radius: 6px;
    background: {Color.SURFACE};
    selection-background-color: {Color.ROW_SELECTED};
    selection-color: {Color.PRIMARY_ACTIVE};
    padding: 4px;
    outline: none;
}}
QComboBox QAbstractItemView::item {{
    padding: 6px 12px;
    border-radius: 4px;
}}
QComboBox QAbstractItemView::item:hover {{
    background: {Color.ROW_HOVER};
}}

/* ── TreeWidget (Tag tree) ─────────────────────────────────── */
QTreeWidget {{
    background: {Color.SURFACE};
    border: 1px solid {Color.BORDER};
    border-radius: 8px;
    outline: none;
    padding: 4px 0;
}}
QTreeWidget::item {{
    padding: 6px 10px;
    border-radius: 4px;
    margin: 1px 4px;
    color: {Color.TEXT_PRIMARY};
}}
QTreeWidget::item:hover {{
    background: {Color.ROW_HOVER};
}}
QTreeWidget::item:selected {{
    background: {Color.ROW_SELECTED};
    color: {Color.PRIMARY};
}}
QTreeWidget::branch {{
    background: transparent;
}}

/* ── ListWidget (File list) ────────────────────────────────── */
QListWidget {{
    background: {Color.SURFACE};
    border: 1px solid {Color.BORDER};
    border-radius: 8px;
    outline: none;
    padding: 4px 0;
}}
QListWidget::item {{
    padding: 8px 12px;
    border-radius: 4px;
    margin: 1px 4px;
    color: {Color.TEXT_PRIMARY};
    font-size: 13px;
}}
QListWidget::item:hover {{
    background: {Color.ROW_HOVER};
}}
QListWidget::item:selected {{
    background: {Color.ROW_SELECTED};
    color: {Color.PRIMARY};
}}
QListWidget::item:alternate {{
    background: {Color.ROW_ALT};
}}

/* ── TabWidget ─────────────────────────────────────────────── */
QTabWidget::pane {{
    border: 1px solid {Color.BORDER};
    border-radius: 8px;
    background: {Color.SURFACE};
    top: -1px;
    padding: 8px;
}}
QTabBar::tab {{
    padding: 8px 18px;
    border: 1px solid transparent;
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    background: transparent;
    color: {Color.TEXT_SECONDARY};
    font-size: 13px;
    margin-right: 2px;
}}
QTabBar::tab:selected {{
    background: {Color.SURFACE};
    border-color: {Color.BORDER};
    color: {Color.PRIMARY};
    font-weight: 600;
}}
QTabBar::tab:hover:!selected {{
    background: {Color.ROW_HOVER};
    color: {Color.TEXT_PRIMARY};
}}

/* ── Splitter ──────────────────────────────────────────────── */
QSplitter::handle {{
    background: {Color.BORDER};
    width: 2px;
    margin: 4px 0;
}}
QSplitter::handle:hover {{
    background: {Color.PRIMARY};
}}
QSplitter::handle:horizontal {{
    width: 2px;
    margin: 4px 0;
}}

/* ── ScrollBar ─────────────────────────────────────────────── */
QScrollBar:vertical {{
    background: transparent;
    width: 8px;
    margin: 2px 2px 2px 0;
}}
QScrollBar::handle:vertical {{
    background: {Color.SCROLLBAR_HANDLE};
    border-radius: 4px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{
    background: {Color.SCROLLBAR_HOVER};
}}
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {{
    height: 0;
    border: none;
}}
QScrollBar:horizontal {{
    background: transparent;
    height: 8px;
    margin: 0 2px 2px 2px;
}}
QScrollBar::handle:horizontal {{
    background: {Color.SCROLLBAR_HANDLE};
    border-radius: 4px;
    min-width: 30px;
}}
QScrollBar::handle:horizontal:hover {{
    background: {Color.SCROLLBAR_HOVER};
}}
QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal {{
    width: 0;
    border: none;
}}

/* ── ProgressBar ───────────────────────────────────────────── */
QProgressBar {{
    border: none;
    border-radius: 4px;
    text-align: center;
    background: {Color.BORDER};
    font-size: 11px;
    color: {Color.TEXT_SECONDARY};
}}
QProgressBar::chunk {{
    background: {Color.PRIMARY};
    border-radius: 4px;
}}

/* ── StatusBar ─────────────────────────────────────────────── */
QStatusBar {{
    background: {Color.SURFACE};
    border-top: 1px solid {Color.BORDER};
    color: {Color.TEXT_SECONDARY};
    font-size: 12px;
    padding: 2px 8px;
}}
QStatusBar::item {{
    border: none;
}}

/* ── TextEdit ──────────────────────────────────────────────── */
QTextEdit {{
    border: 1px solid {Color.BORDER};
    border-radius: 6px;
    background: {Color.SURFACE};
    padding: 8px;
    color: {Color.TEXT_PRIMARY};
    font-size: 13px;
}}
QTextEdit:focus {{
    border-color: {Color.BORDER_FOCUS};
}}

/* ── MenuBar ───────────────────────────────────────────────── */
QMenuBar {{
    background: {Color.SURFACE};
    border-bottom: 1px solid {Color.BORDER};
    padding: 2px 0;
    font-size: 13px;
}}
QMenuBar::item {{
    padding: 5px 12px;
    border-radius: 4px;
    color: {Color.TEXT_SECONDARY};
}}
QMenuBar::item:selected {{
    background: {Color.ROW_HOVER};
    color: {Color.TEXT_PRIMARY};
}}
QMenu {{
    background: {Color.SURFACE};
    border: 1px solid {Color.BORDER};
    border-radius: 8px;
    padding: 4px;
    font-size: 13px;
}}
QMenu::item {{
    padding: 7px 32px 7px 14px;
    border-radius: 4px;
    color: {Color.TEXT_PRIMARY};
}}
QMenu::item:selected {{
    background: {Color.ROW_SELECTED};
    color: {Color.PRIMARY};
}}
QMenu::separator {{
    height: 1px;
    background: {Color.BORDER};
    margin: 4px 8px;
}}

/* ── Dialog ────────────────────────────────────────────────── */
QDialog {{
    background: {Color.SURFACE};
}}

/* ── QGroupBox / QLabel ────────────────────────────────────── */
QLabel {{
    color: {Color.TEXT_SECONDARY};
    font-size: 13px;
}}
QLabel[heading="true"] {{
    color: {Color.TEXT_PRIMARY};
    font-size: 15px;
    font-weight: 600;
}}

/* ── QDateTimeEdit ─────────────────────────────────────────── */
QDateTimeEdit {{
    border: 1px solid {Color.BORDER};
    border-radius: 6px;
    padding: 6px 10px;
    background: {Color.SURFACE};
    color: {Color.TEXT_PRIMARY};
}}
QDateTimeEdit:focus {{
    border-color: {Color.BORDER_FOCUS};
}}

/* ── QScrollArea ───────────────────────────────────────────── */
QScrollArea {{
    border: none;
    background: transparent;
}}
"""


def setup_theme(app: QApplication) -> None:
    app.setStyleSheet(QSS)
