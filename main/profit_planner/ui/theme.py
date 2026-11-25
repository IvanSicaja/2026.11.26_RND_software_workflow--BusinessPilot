"""Dark theme: every colour of the user interface is defined here (one place to change the look)."""
from __future__ import annotations

from PySide6.QtGui import QColor, QPalette

# --- base surfaces -----------------------------------------------------------------
BG = "#16191E"            # window background
SURFACE = "#1E2228"       # tables, inputs, cards
SURFACE_ALT = "#23282F"   # alternating table rows
RAISED = "#2A3038"        # buttons, headers, toolbar
BORDER = "#3A424D"
INDICATOR = "#6B7685"     # border of unchecked check boxes / radio buttons
BORDER_SOFT = "#2E353E"

# --- text ------------------------------------------------------------------------------
TEXT = "#E6EAF0"
TEXT_MUTED = "#9AA5B4"
TEXT_DISABLED = "#5F6A78"

# --- accents -----------------------------------------------------------------------------
ACCENT = "#4C9AFF"
ACCENT_HOVER = "#6AACFF"
ACCENT_DIM = "#1F3A5C"     # selection background
ACCENT_TEXT = "#8CC2FF"    # titles

GOOD = "#5BD178"
BAD = "#FF6B6B"
WARN = "#F2C14E"
INFO = "#6AACFF"
PURPLE = "#C08BFF"

# --- cell / row highlight backgrounds (dark tints, light text stays readable) -----------
GOOD_BG = "#1C3A26"
BAD_BG = "#4A1F24"
WARN_BG = "#43391A"

# --- breakdown bar segments ----------------------------------------------------------------
SEGMENTS = {
    "Net to owner": "#3FB65F",
    "Taxes": "#A86BEB",
    "VAT": "#6B7685",
    "Production": "#3D82E0",
    "Shipping & customs": "#E07B2E",
    "Fees & returns": "#D4A72C",
    "Loss": "#E04848",
}



def _luminance(hex_value: str) -> float:
    c = QColor(hex_value)

    def ch(v: float) -> float:
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    return 0.2126 * ch(c.redF()) + 0.7152 * ch(c.greenF()) + 0.0722 * ch(c.blueF())


def contrast(fg: str, bg: str) -> float:
    """WCAG contrast ratio between two colours (4.5 or more = well readable)."""
    a, b = sorted((_luminance(fg), _luminance(bg)), reverse=True)
    return (a + 0.05) / (b + 0.05)


def text_on(bg_hex: str) -> str:
    """Dark or white text, whichever is more readable on the given background."""
    return max(("#0B1220", "#FFFFFF"), key=lambda fg: contrast(fg, bg_hex))


# line colours in the price breakdown table
LINE_COLORS = {"Tax": PURPLE, "Deduction": WARN, "Cost": INFO}


def qcolor(hex_value: str) -> QColor:
    return QColor(hex_value)


def palette() -> QPalette:
    p = QPalette()
    c = QColor
    for group in (QPalette.Active, QPalette.Inactive):
        p.setColor(group, QPalette.Window, c(BG))
        p.setColor(group, QPalette.WindowText, c(TEXT))
        p.setColor(group, QPalette.Base, c(SURFACE))
        p.setColor(group, QPalette.AlternateBase, c(SURFACE_ALT))
        p.setColor(group, QPalette.Text, c(TEXT))
        p.setColor(group, QPalette.Button, c(RAISED))
        p.setColor(group, QPalette.ButtonText, c(TEXT))
        p.setColor(group, QPalette.BrightText, c("#FFFFFF"))
        p.setColor(group, QPalette.Highlight, c(ACCENT_DIM))
        p.setColor(group, QPalette.HighlightedText, c("#FFFFFF"))
        p.setColor(group, QPalette.ToolTipBase, c("#252B33"))
        p.setColor(group, QPalette.ToolTipText, c(TEXT))
        p.setColor(group, QPalette.PlaceholderText, c(TEXT_DISABLED))
        p.setColor(group, QPalette.Link, c(ACCENT))
        p.setColor(group, QPalette.Light, c("#3A424D"))
        p.setColor(group, QPalette.Midlight, c("#30363F"))
        p.setColor(group, QPalette.Mid, c("#262B32"))
        p.setColor(group, QPalette.Dark, c("#101216"))
        p.setColor(group, QPalette.Shadow, c("#000000"))
    for role in (QPalette.WindowText, QPalette.Text, QPalette.ButtonText):
        p.setColor(QPalette.Disabled, role, c(TEXT_DISABLED))
    p.setColor(QPalette.Disabled, QPalette.Base, c(BG))
    p.setColor(QPalette.Disabled, QPalette.Button, c(SURFACE))
    p.setColor(QPalette.Disabled, QPalette.Highlight, c(BORDER))
    return p


STYLE = f"""
QWidget {{ font-size: 10pt; color: {TEXT}; }}
QMainWindow, QDialog {{ background: {BG}; }}
QToolTip {{ background: #252B33; color: {TEXT}; border: 1px solid {ACCENT}; padding: 8px; border-radius: 4px; }}

QToolBar {{ spacing: 4px; padding: 4px; border: none; border-bottom: 1px solid {BORDER}; background: {RAISED}; }}
QToolBar QToolButton {{ padding: 5px 10px; border-radius: 4px; color: {TEXT}; }}
QToolBar QToolButton:hover {{ background: {ACCENT_DIM}; }}
QToolBar QToolButton:pressed {{ background: {ACCENT}; }}
QToolBar::separator {{ background: {BORDER}; width: 1px; margin: 4px 6px; }}

QTabWidget::pane {{ border: none; }}
QTabBar::tab {{ padding: 8px 16px; border: none; color: {TEXT_MUTED}; background: transparent; }}
QTabBar::tab:selected {{ color: {ACCENT_TEXT}; border-bottom: 3px solid {ACCENT}; font-weight: bold; }}
QTabBar::tab:hover {{ color: {TEXT}; background: {SURFACE}; }}

QLabel {{ background: transparent; }}
QLabel#pageTitle {{ font-size: 15pt; font-weight: bold; color: {ACCENT_TEXT}; }}
QLabel#sectionTitle {{ font-size: 11pt; color: {ACCENT_TEXT}; }}
QLabel#hint {{ color: {TEXT_MUTED}; }}

QPushButton {{ padding: 5px 12px; border: 1px solid {BORDER}; border-radius: 4px; background: {RAISED}; color: {TEXT}; }}
QPushButton:hover {{ background: #343B45; border-color: {ACCENT}; }}
QPushButton:pressed {{ background: {ACCENT_DIM}; }}
QPushButton:disabled {{ color: {TEXT_DISABLED}; border-color: {BORDER_SOFT}; background: {SURFACE}; }}
QPushButton#primaryButton {{ background: {ACCENT}; color: #0B1220; border-color: {ACCENT}; font-weight: bold; padding: 8px; }}
QPushButton#primaryButton:hover {{ background: {ACCENT_HOVER}; }}
QPushButton#dangerButton:hover {{ background: {BAD_BG}; border-color: {BAD}; }}
QPushButton:flat {{ border: none; background: transparent; }}

QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {{ background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 4px;
    padding: 3px 6px; color: {TEXT}; selection-background-color: {ACCENT_DIM}; }}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {{ border-color: {ACCENT}; }}
QLineEdit:disabled, QComboBox:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled {{ color: {TEXT_DISABLED}; background: {BG}; }}
QComboBox QAbstractItemView {{ background: {SURFACE}; color: {TEXT}; border: 1px solid {BORDER};
    selection-background-color: {ACCENT_DIM}; }}

QTableView, QTableWidget, QListWidget {{ background: {SURFACE}; alternate-background-color: {SURFACE_ALT};
    gridline-color: {BORDER_SOFT}; border: 1px solid {BORDER_SOFT}; selection-background-color: {ACCENT_DIM};
    selection-color: #FFFFFF; }}
QTableView QLineEdit {{ border-radius: 0; padding: 0 4px; }}
QTableCornerButton::section {{ background: {RAISED}; border: none; }}
QHeaderView::section {{ background: {RAISED}; padding: 4px; border: none; border-right: 1px solid {BORDER_SOFT};
    border-bottom: 1px solid {BORDER}; font-weight: bold; color: {TEXT}; }}
QHeaderView::section:hover {{ background: #343B45; }}

QFrame#kpiCard {{ background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 6px; }}
QLabel#kpiTitle {{ color: {TEXT_MUTED}; font-size: 9pt; }}
QLabel#kpiValue {{ font-size: 15pt; font-weight: bold; color: {TEXT}; }}
QLabel#kpiValue[state="good"] {{ color: {GOOD}; }}
QLabel#kpiValue[state="bad"] {{ color: {BAD}; }}
QLabel#kpiSub {{ color: {TEXT_MUTED}; font-size: 9pt; }}

QGroupBox {{ font-weight: bold; border: 1px solid {BORDER}; border-radius: 6px; margin-top: 10px; padding-top: 8px; }}
QGroupBox::title {{ subcontrol-origin: margin; left: 8px; padding: 0 4px; color: {ACCENT_TEXT}; }}

QCheckBox, QRadioButton {{ background: transparent; spacing: 6px; }}
QCheckBox::indicator, QRadioButton::indicator {{ width: 15px; height: 15px; border: 1px solid {INDICATOR}; background: {SURFACE}; }}
QCheckBox::indicator {{ border-radius: 3px; }}
QRadioButton::indicator {{ border-radius: 8px; }}
QCheckBox::indicator:checked, QRadioButton::indicator:checked {{ background: {ACCENT}; border-color: {ACCENT}; }}
QCheckBox::indicator:hover, QRadioButton::indicator:hover {{ border-color: {ACCENT}; }}
QListWidget::indicator {{ width: 15px; height: 15px; border: 1px solid {INDICATOR}; background: {SURFACE}; border-radius: 3px; }}
QListWidget::indicator:checked {{ background: {ACCENT}; border-color: {ACCENT}; }}

QSplitter::handle {{ background: {BG}; }}
QSplitter::handle:hover {{ background: {ACCENT_DIM}; }}
QStatusBar {{ background: {RAISED}; border-top: 1px solid {BORDER}; }}
QStatusBar::item {{ border: none; }}
QMenu {{ background: {SURFACE}; border: 1px solid {BORDER}; }}
QMenu::item:selected {{ background: {ACCENT_DIM}; }}
QMessageBox, QInputDialog {{ background: {BG}; }}

QScrollBar:vertical {{ background: {BG}; width: 12px; margin: 0; }}
QScrollBar:horizontal {{ background: {BG}; height: 12px; margin: 0; }}
QScrollBar::handle {{ background: {BORDER}; border-radius: 5px; min-height: 24px; min-width: 24px; margin: 2px; }}
QScrollBar::handle:hover {{ background: #4D5764; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: none; }}
"""
