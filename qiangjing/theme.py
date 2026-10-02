INK = "#3A2A22"
MUTED = "#7A6458"
CREAM = "#FFF9F4"
LINE = "#EADCCE"
GREEN = "#1F8A40"
GREEN_DARK = "#176B32"
GREEN_SOFT = "#E7F6EC"
AMBER = "#B5732A"
AMBER_SOFT = "#FFF1DE"
QUIT = "#8A7064"
QUIT_HOVER = "#A33B32"

SETTINGS_QSS = f"""
QFrame#card {{
    background: {CREAM};
    border: 1px solid {LINE};
    border-radius: 22px;
}}
QLabel {{
    background: transparent;
    color: {INK};
}}
QLabel#title {{
    font-size: 26px;
    color: {INK};
}}
QLabel#subtitle, QLabel#hint {{
    color: {MUTED};
    font-size: 12px;
}}
QLabel#section {{
    color: {INK};
    font-size: 13px;
}}
QLabel#value {{
    color: {GREEN};
    font-size: 13px;
}}
QPushButton#close {{
    background: #F3E6D8;
    color: {INK};
    border: none;
    border-radius: 14px;
    font-size: 16px;
}}
QPushButton#close:hover {{
    background: #E7D3C2;
}}
QPushButton#primary {{
    background: {GREEN};
    color: white;
    border: none;
    border-radius: 12px;
    padding: 8px 14px;
    font-size: 14px;
    min-height: 36px;
}}
QPushButton#primary:hover {{
    background: {GREEN_DARK};
}}
QPushButton#primary:pressed {{
    background: #125828;
}}
QPushButton#secondary {{
    background: white;
    color: {INK};
    border: 1px solid {LINE};
    border-radius: 12px;
    padding: 8px 14px;
    font-size: 14px;
    min-height: 36px;
}}
QPushButton#secondary:hover {{
    background: #FFF3E8;
}}
QPushButton#quit {{
    background: transparent;
    color: {QUIT};
    border: none;
    padding: 4px 8px;
    font-size: 12px;
}}
QPushButton#quit:hover {{
    color: {QUIT_HOVER};
}}
QPushButton#preset {{
    background: white;
    color: #5C463C;
    border: 1px solid {LINE};
    border-radius: 15px;
    padding: 4px 8px;
    font-size: 12px;
    min-height: 28px;
}}
QPushButton#preset:hover {{
    border-color: {GREEN};
}}
QPushButton#preset:checked {{
    background: {GREEN};
    color: white;
    border-color: {GREEN};
}}
QPushButton#preset:checked:hover {{
    background: {GREEN_DARK};
}}
QSpinBox {{
    background: white;
    color: {INK};
    border: 1px solid {LINE};
    border-radius: 10px;
    padding: 2px 10px;
    font-size: 16px;
    min-height: 32px;
}}
QSpinBox::up-button, QSpinBox::down-button {{
    width: 0;
    height: 0;
    border: none;
}}
QSlider::groove:horizontal {{
    height: 6px;
    background: #EFE2D4;
    border-radius: 3px;
}}
QSlider::sub-page:horizontal {{
    background: {GREEN};
    border-radius: 3px;
}}
QSlider::handle:horizontal {{
    width: 18px;
    height: 18px;
    margin: -7px 0;
    border-radius: 9px;
    background: white;
    border: 2px solid {GREEN};
}}
"""

MENU_QSS = f"""
QMenu {{
    background: {CREAM};
    color: {INK};
    border: 1px solid {LINE};
    border-radius: 10px;
    padding: 6px;
}}
QMenu::item {{
    padding: 6px 18px;
    border-radius: 6px;
    background: transparent;
}}
QMenu::item:selected {{
    background: {GREEN_SOFT};
    color: {GREEN};
}}
QMenu::separator {{
    height: 1px;
    background: {LINE};
    margin: 4px 8px;
}}
"""
