"""Quiet, native-inspired workspace styling."""
STYLE = """
* { font-family: 'Segoe UI'; font-size: 13px; color: #283344; }
QMainWindow, QWidget { background: #f6f7f9; }
QLabel { background: transparent; }
QLabel#brand { font-size: 19px; font-weight: 650; color: #182539; }
QLabel#heading { font-size: 16px; font-weight: 600; color: #182539; }
QLabel#panetab { font-size: 14px; font-weight: 600; }
QLabel#muted { color: #697586; }
QLabel#statvalue { color: #526173; }
QLabel#statusdot { color: #478565; }
QLabel#upstat, QLabel#downstat { color: #426b97; }
QFrame#topbar { background: #f6f7f9; border: none; }
QFrame#brandmark, QFrame#statusbar { background: transparent; border: none; }
QFrame#sidebar { background: #edf0f4; border: none; }
QFrame#panel { background: #ffffff; border: none; border-radius: 14px; }
QFrame#panel QWidget { background: transparent; }
QFrame#addressbar { background: #f3f5f8; border: none; border-radius: 8px; }
QPushButton { background: #ffffff; border: 1px solid #e1e5eb; border-radius: 7px; padding: 7px 12px; color: #38475a; }
QPushButton:hover { background: #e9eff8; border-color: #d6dfeb; }
QPushButton:pressed { background: #dce8f8; }
QPushButton:disabled { color: #9ba5b1; border-color: transparent; background: #f1f3f6; }
QPushButton:focus { border-color: #6695d2; }
QPushButton#primary { background: #397bd2; color: white; border: none; }
QPushButton#toolbtn, QPushButton#navbtn, QPushButton#linkbtn { border: none; background: transparent; }
QPushButton#toolbtn:hover, QPushButton#navbtn:hover, QPushButton#linkbtn:hover { background: #e8edf5; }
QPushButton#toolbtn:checked { background: #e5eefb; color: #245ca2; }
QFrame#sidebar QPushButton { background: transparent; border: none; text-align: left; padding: 10px 14px; border-radius: 8px; }
QFrame#sidebar QPushButton:hover { background: #e2e7ef; }
QFrame#sidebar QPushButton:checked { background: #dbe7f8; color: #245b9e; font-weight: 600; }
QPushButton#accounttab { background: transparent; border: none; font-weight: 600; padding: 6px; }
QPushButton#tinycancel { background: transparent; color: #a74848; border: none; }
QLineEdit, QSpinBox, QComboBox { background: #f3f5f8; color: #344154; border: 1px solid transparent; border-radius: 7px; padding: 8px 10px; selection-background-color: #dbe8fa; selection-color: #182c49; }
QLineEdit:focus, QSpinBox:focus, QComboBox:focus { border-color: #79a3da; }
QLineEdit[readOnly="true"] { color: #667587; }
QFrame#addressbar QLineEdit { background: transparent; border: none; }
QLineEdit#search { background: #e9edf2; border: none; border-radius: 9px; }
QTableWidget, QTreeWidget, QListWidget { background: transparent; border: none; outline: none; alternate-background-color: #fafbfd; }
QTableWidget::item, QTreeWidget::item { border: none; padding: 7px 8px; color: #344154; }
QTableWidget::item:selected, QTreeWidget::item:selected, QListWidget::item:selected { background: #e7effb; color: #214c84; }
QTreeWidget::branch { background: transparent; }
QTreeWidget#transfers::item { padding: 9px 6px; }
QHeaderView { background: transparent; }
QHeaderView::section { background: #ffffff; color: #758194; border: none; padding: 12px 8px; font-size: 12px; }
QTableCornerButton::section { background: white; border: none; }
QSplitter::handle { background: transparent; }
QSplitter::handle:hover { background: #dce5f0; border-radius: 3px; }
QScrollBar:vertical { background: transparent; width: 8px; }
QScrollBar:horizontal { background: transparent; height: 8px; }
QScrollBar::handle { background: #c6ced8; border-radius: 4px; min-height: 30px; min-width: 30px; }
QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; }
QScrollBar::add-page, QScrollBar::sub-page { background: transparent; }
QProgressBar { background: #eaf0f7; border: none; border-radius: 5px; min-height: 12px; max-height: 16px; text-align: center; color: #234c7c; font-size: 11px; }
QProgressBar::chunk { background: #7da7e2; border-radius: 5px; }
QProgressBar[state="done"]::chunk { background: #83b79b; }
QProgressBar[state="failed"]::chunk { background: #d99898; }
QCheckBox { spacing: 8px; background: transparent; color: #59687a; }
QCheckBox::indicator { width: 17px; height: 17px; border: 1px solid #bec9d7; border-radius: 5px; background: #ffffff; }
QCheckBox::indicator:checked { background: #4380cc; border-color: #4380cc; }
QSlider::groove:horizontal { height: 5px; background: #dfe6ef; border-radius: 2px; }
QSlider::sub-page:horizontal { background: #79a2d8; border-radius: 2px; }
QSlider::handle:horizontal { width: 18px; margin: -7px 0; background: #ffffff; border: 1px solid #b5c7de; border-radius: 9px; }
QMenu, QComboBox QAbstractItemView { background: #ffffff; border: 1px solid #e2e7ee; padding: 6px; }
QMenu::item { padding: 8px 24px; border-radius: 6px; }
QMenu::item:selected { background: #e7effb; }
QMenu::separator { height: 1px; background: #edf0f4; margin: 5px 10px; }
QToolTip { background: #ffffff; color: #344154; border: 1px solid #dce3ed; padding: 6px; }
QDialog { background: #f6f7f9; }
"""
