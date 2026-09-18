"""DriveDesk's light workspace: clear surfaces, restrained chrome, strong actions."""
STYLE = """
* { font-family: 'Segoe UI'; font-size: 13px; color: #243247; }
QMainWindow, QWidget { background: #f2f5f9; }
QLabel { background: transparent; }
QLabel#brand { font-size: 20px; font-weight: 700; color: #172a46; }
QLabel#heading { font-size: 15px; font-weight: 700; color: #182b45; }
QLabel#panetab { font-size: 15px; font-weight: 700; color: #182b45; }
QLabel#muted { color: #60718a; }
QLabel#sectionLabel { color: #687990; font-size: 11px; font-weight: 700; padding: 0 12px 6px 12px; }
QLabel#statvalue { color: #526173; }
QLabel#statusdot { color: #478565; }
QLabel#upstat, QLabel#downstat { color: #426b97; }
QFrame#topbar { background: #ffffff; border: none; border-bottom: 1px solid #dce4ee; }
QFrame#brandmark, QFrame#statusbar { background: transparent; border: none; }
QFrame#sidebar { background: #eaf0f7; border: none; border-right: 1px solid #d8e1ec; }
QFrame#panel { background: #ffffff; border: 1px solid #dce4ee; border-radius: 12px; }
QFrame#panel QWidget { background: transparent; }
QFrame#addressbar { background: #f5f7fa; border: 1px solid #e3e9f1; border-radius: 8px; }
QPushButton { background: #ffffff; border: 1px solid #cfd9e6; border-radius: 8px; padding: 8px 13px; color: #284365; font-weight: 600; }
QPushButton:hover { background: #f2f7ff; border-color: #a9c4e8; }
QPushButton:pressed { background: #e3edfa; }
QPushButton:disabled { color: #9ba5b1; border-color: transparent; background: #f1f3f6; }
QPushButton:focus { border-color: #6695d2; }
QPushButton#primary { background: #1769c2; color: white; border: 1px solid #1769c2; }
QPushButton#primary:hover { background: #0e59ab; border-color: #0e59ab; }
QPushButton#primary:pressed { background: #08498e; }
QFrame#panel QPushButton#primary { background: #1769c2; color: #ffffff; border: 1px solid #1769c2; }
QFrame#panel QPushButton#primary:hover { background: #0e59ab; border-color: #0e59ab; }
QPushButton#secondaryAction { background: #eaf3ff; border-color: #bad2ee; color: #175b9e; }
QFrame#panel QPushButton#secondaryAction { background: #eaf3ff; border: 1px solid #bad2ee; color: #175b9e; }
QPushButton#toolbtn, QPushButton#navbtn, QPushButton#linkbtn { border: none; background: transparent; }
QPushButton#toolbtn:hover, QPushButton#navbtn:hover, QPushButton#linkbtn:hover { background: #e8edf5; }
QPushButton#toolbtn:checked { background: #e5eefb; color: #245ca2; }
QFrame#sidebar QPushButton { background: transparent; border: none; text-align: left; padding: 11px 13px; border-radius: 8px; color: #354a64; font-weight: 500; }
QFrame#sidebar QPushButton:hover { background: #dfe9f5; }
QFrame#sidebar QPushButton:checked { background: #d4e6fb; color: #15599f; font-weight: 700; }
QPushButton#accounttab { background: transparent; border: none; font-weight: 600; padding: 6px; }
QPushButton#tinycancel { background: transparent; color: #a74848; border: none; }
QLineEdit, QSpinBox, QComboBox { background: #ffffff; color: #243247; border: 1px solid #cfd9e6; border-radius: 8px; padding: 8px 10px; selection-background-color: #dbe8fa; selection-color: #182c49; }
QLineEdit:focus, QSpinBox:focus, QComboBox:focus { border-color: #79a3da; }
QLineEdit[readOnly="true"] { color: #667587; }
QFrame#addressbar QLineEdit { background: transparent; border: none; }
QLineEdit#search { background: #f5f7fa; border: 1px solid #dce4ee; border-radius: 9px; }
QTableWidget, QTreeWidget, QListWidget { background: transparent; border: none; outline: none; alternate-background-color: #f7faff; }
QTableWidget::item, QTreeWidget::item { border: none; padding: 8px 9px; color: #293b53; }
QTableWidget::item:selected, QTreeWidget::item:selected, QListWidget::item:selected { background: #dcecff; color: #14518f; }
QTreeWidget::branch { background: transparent; }
QTreeWidget#transfers::item { padding: 9px 6px; }
QHeaderView { background: transparent; }
QHeaderView::section { background: #f8fafc; color: #526782; border: none; border-bottom: 1px solid #e4eaf2; padding: 11px 9px; font-size: 12px; font-weight: 600; }
QTableCornerButton::section { background: white; border: none; }
QSplitter::handle { background: transparent; }
QSplitter::handle:hover { background: #cbdbea; border-radius: 3px; }
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
QMenu, QComboBox QAbstractItemView { background: #ffffff; border: 1px solid #d5e0eb; padding: 6px; }
QMenu::item { padding: 8px 24px; border-radius: 6px; }
QMenu::item:selected { background: #e7effb; }
QMenu::separator { height: 1px; background: #edf0f4; margin: 5px 10px; }
QToolTip { background: #ffffff; color: #344154; border: 1px solid #dce3ed; padding: 6px; }
QDialog { background: #f2f5f9; }
"""
