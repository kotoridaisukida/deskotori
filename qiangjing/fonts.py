from pathlib import Path

from PySide6.QtGui import QFont, QFontDatabase


def load_fonts(fonts_dir: Path) -> tuple[str, str | None]:
    """Load bundled fonts. Returns the UI family and an optional display family."""
    ui_family = None
    display_family = None
    if fonts_dir.is_dir():
        for path in sorted(fonts_dir.iterdir()):
            if path.suffix.lower() not in {".ttf", ".otf", ".ttc"}:
                continue
            font_id = QFontDatabase.addApplicationFont(str(path))
            if font_id < 0:
                continue
            families = QFontDatabase.applicationFontFamilies(font_id)
            if not families:
                continue
            family = families[0]
            lowered = path.name.lower()
            if "zcool" in lowered or "kuaile" in lowered:
                display_family = family
            elif ui_family is None:
                ui_family = family
    if not ui_family:
        ui_family = "WenQuanYi Micro Hei"
    return ui_family, display_family


def build_ui_font(family: str) -> QFont:
    font = QFont(family)
    font.setPixelSize(14)
    font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
    return font
