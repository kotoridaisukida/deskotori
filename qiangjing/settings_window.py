"""设置刷新时间、大小，以及她靠哪一个角。"""

import math

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QKeySequence, QPainter, QPainterPath, QPen, QPixmap, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from qiangjing.config import INTERVAL_MAX, INTERVAL_MIN, SIZE_MAX, SIZE_MIN
from qiangjing.logic import CORNER_SHORT, screen_menu_label
from qiangjing.paths import SPRITE
from qiangjing.theme import AMBER, AMBER_SOFT, GREEN, GREEN_SOFT, LINE, MUTED, SETTINGS_QSS

PRESETS = (
    (3, "3秒"),
    (5, "5秒"),
    (10, "10秒"),
    (30, "30秒"),
    (60, "1分钟"),
)
SLIDER_STEPS = 1000


def seconds_to_slider(seconds: int) -> int:
    seconds = max(INTERVAL_MIN, min(INTERVAL_MAX, int(seconds)))
    return int(round(SLIDER_STEPS * math.log(seconds) / math.log(INTERVAL_MAX)))


def slider_to_seconds(value: int) -> int:
    value = max(0, min(SLIDER_STEPS, int(value)))
    if value <= 0:
        return INTERVAL_MIN
    seconds = int(round(math.exp(math.log(INTERVAL_MAX) * value / SLIDER_STEPS)))
    return max(INTERVAL_MIN, min(INTERVAL_MAX, seconds))


class DragHeader(QWidget):
    def __init__(self):
        super().__init__()
        self._dragging = False
        self._offset = None
        self.setCursor(Qt.CursorShape.OpenHandCursor)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._offset = event.globalPosition().toPoint() - self.window().frameGeometry().topLeft()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._dragging and self._offset is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.window().move(event.globalPosition().toPoint() - self._offset)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        self._dragging = False
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        super().mouseReleaseEvent(event)


class Avatar(QWidget):
    def __init__(self, pixmap: QPixmap, size: int = 58):
        super().__init__()
        self.pixmap = pixmap
        self.setFixedSize(size, size)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

    def paintEvent(self, event) -> None:
        if self.pixmap.isNull():
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        rect = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        path = QPainterPath()
        path.addRoundedRect(rect, 16, 16)
        painter.setClipPath(path)
        painter.drawPixmap(self.rect(), self.pixmap)
        painter.setClipping(False)
        painter.setPen(QPen(QColor(GREEN), 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(rect, 16, 16)
        painter.end()


class CornerMap(QWidget):
    cornerPicked = Signal(str)

    def __init__(self):
        super().__init__()
        self.current = "tl"
        self._hover = None
        self.setMouseTracking(True)
        self.setFixedHeight(126)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAccessibleName("四个角")

    def set_current(self, corner: str) -> None:
        if corner != self.current:
            self.current = corner
            self.update()

    def _zones(self) -> dict[str, QRectF]:
        rect = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        gap = 8
        width = (rect.width() - gap) / 2
        height = (rect.height() - gap) / 2
        return {
            "tl": QRectF(rect.left(), rect.top(), width, height),
            "tr": QRectF(rect.left() + width + gap, rect.top(), width, height),
            "bl": QRectF(rect.left(), rect.top() + height + gap, width, height),
            "br": QRectF(rect.left() + width + gap, rect.top() + height + gap, width, height),
        }

    def _hit(self, pos) -> str | None:
        point = QPointF(pos)
        for name, zone in self._zones().items():
            if zone.contains(point):
                return name
        return None

    def mouseMoveEvent(self, event) -> None:
        hover = self._hit(event.position())
        if hover != self._hover:
            self._hover = hover
            self.update()

    def leaveEvent(self, event) -> None:
        self._hover = None
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            name = self._hit(event.position())
            if name:
                self.cornerPicked.emit(name)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setFont(self.font())
        for name, zone in self._zones().items():
            active = name == self.current
            hover = name == self._hover and not active
            if active:
                fill = QColor(GREEN_SOFT)
                border = QColor(GREEN)
                text = QColor(GREEN)
            elif hover:
                fill = QColor("#FFF3E8")
                border = QColor(GREEN)
                text = QColor("#5C463C")
            else:
                fill = QColor("#FFFFFF")
                border = QColor(LINE)
                text = QColor(MUTED)
            painter.setPen(QPen(border, 1.4 if active else 1))
            painter.setBrush(fill)
            painter.drawRoundedRect(zone, 14, 14)
            painter.setPen(text)
            painter.drawText(zone, Qt.AlignmentFlag.AlignCenter, CORNER_SHORT[name])
        painter.end()


class SettingsWindow(QWidget):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.allow_close = False
        self._status_style = ""
        self._pending_size = None
        self.setObjectName("settingsWindow")
        self.setWindowTitle("抢镜鸟")
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
        self.setFixedWidth(448)
        self._build()
        self.setStyleSheet(SETTINGS_QSS)
        self._apply_display_font()
        self._apply_config_to_controls()
        self._connect()
        self.clock = QTimer(self)
        self.clock.setInterval(200)
        self.clock.timeout.connect(self.refresh_status)
        self._escape = QShortcut(QKeySequence(Qt.Key.Key_Escape), self)
        self._escape.activated.connect(self.close)
        self._size_timer = QTimer(self)
        self._size_timer.setSingleShot(True)
        self._size_timer.setInterval(40)
        self._size_timer.timeout.connect(self._flush_size)

    def _build(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(18, 18, 18, 18)

        card = QFrame()
        card.setObjectName("card")
        card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        card.setFrameShape(QFrame.Shape.NoFrame)
        outer.addWidget(card)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)

        header = DragHeader()
        header_row = QHBoxLayout(header)
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.setSpacing(12)
        avatar = Avatar(QPixmap(str(SPRITE)))
        header_row.addWidget(avatar, 0, Qt.AlignmentFlag.AlignVCenter)

        titles = QVBoxLayout()
        titles.setSpacing(2)
        self.title = QLabel("抢镜鸟")
        self.title.setObjectName("title")
        self.title.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        titles.addWidget(self.title)
        header_row.addLayout(titles, 1)

        close = QPushButton("×")
        close.setObjectName("close")
        close.setFixedSize(28, 28)
        close.setCursor(Qt.CursorShape.ArrowCursor)
        close.setAccessibleName("关闭设置")
        close.clicked.connect(self.close)
        header_row.addWidget(close, 0, Qt.AlignmentFlag.AlignTop)
        layout.addWidget(header)

        self.map = CornerMap()
        layout.addWidget(self.map)

        self.screen_row = QHBoxLayout()
        self.screen_row.setSpacing(6)
        self.screen_group = QButtonGroup(self)
        self.screen_group.setExclusive(True)
        self.screen_buttons: dict[str, QPushButton] = {}
        layout.addLayout(self.screen_row)

        time_row = QHBoxLayout()
        time_label = QLabel("刷新时间")
        time_label.setObjectName("section")
        self.spin = QSpinBox()
        self.spin.setObjectName("intervalSpin")
        self.spin.setRange(INTERVAL_MIN, INTERVAL_MAX)
        self.spin.setSuffix(" 秒")
        self.spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.spin.setFixedWidth(112)
        self.spin.setKeyboardTracking(False)
        self.spin.setAccessibleName("刷新时间")
        time_row.addWidget(time_label)
        time_row.addStretch(1)
        time_row.addWidget(self.spin)
        layout.addLayout(time_row)

        self.interval_slider = QSlider(Qt.Orientation.Horizontal)
        self.interval_slider.setRange(0, SLIDER_STEPS)
        self.interval_slider.setSingleStep(8)
        self.interval_slider.setPageStep(40)
        self.interval_slider.setMinimumHeight(22)
        layout.addWidget(self.interval_slider)

        presets = QHBoxLayout()
        presets.setSpacing(6)
        self.preset_group = QButtonGroup(self)
        self.preset_group.setExclusive(True)
        self.preset_buttons = {}
        for seconds, label in PRESETS:
            button = QPushButton(label)
            button.setObjectName("preset")
            button.setCheckable(True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            self.preset_group.addButton(button, seconds)
            self.preset_buttons[seconds] = button
            presets.addWidget(button, 1)
        layout.addLayout(presets)

        self.status = QLabel("准备出发")
        self.status.setObjectName("status")
        self.status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status)

        self.size_slider = QSlider(Qt.Orientation.Horizontal)
        self.size_slider.setObjectName("sizeSlider")
        self.size_slider.setRange(SIZE_MIN, SIZE_MAX)
        self.size_slider.setMinimumHeight(22)
        self.size_value = QLabel("300 px")
        self.size_value.setObjectName("value")
        layout.addLayout(self._slider_column("形象大小", self.size_slider, self.size_value))

        buttons = QHBoxLayout()
        buttons.setSpacing(10)
        self.jump_btn = QPushButton("现在就换")
        self.jump_btn.setObjectName("primary")
        self.jump_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.pause_btn = QPushButton("暂停")
        self.pause_btn.setObjectName("secondary")
        self.pause_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        buttons.addWidget(self.jump_btn, 1)
        buttons.addWidget(self.pause_btn, 1)
        layout.addLayout(buttons)

        footer = QHBoxLayout()
        self.quit_btn = QPushButton("退出")
        self.quit_btn.setObjectName("quit")
        self.quit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        footer.addStretch(1)
        footer.addWidget(self.quit_btn)
        layout.addLayout(footer)

    def _slider_column(self, title: str, slider: QSlider, value: QLabel) -> QVBoxLayout:
        column = QVBoxLayout()
        column.setSpacing(4)
        top = QHBoxLayout()
        label = QLabel(title)
        label.setObjectName("section")
        value.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        top.addWidget(label)
        top.addStretch(1)
        top.addWidget(value)
        column.addLayout(top)
        column.addWidget(slider)
        return column

    def _apply_display_font(self) -> None:
        app = QApplication.instance()
        if app is None:
            return
        family = app.property("displayFamily")
        if not family:
            return
        from PySide6.QtGui import QFont

        font = QFont(str(family))
        font.setPixelSize(26)
        self.title.setFont(font)

    def _apply_config_to_controls(self) -> None:
        config = self.controller.config
        self.spin.setValue(config.interval_sec)
        self.interval_slider.setValue(seconds_to_slider(config.interval_sec))
        self.size_slider.setValue(config.size)
        self.size_value.setText(f"{config.size} px")
        self._sync_presets(config.interval_sec)
        self.refresh_status()

    def _connect(self) -> None:
        self.spin.valueChanged.connect(self._on_spin)
        self.interval_slider.valueChanged.connect(self._on_interval_slider)
        self.preset_group.idClicked.connect(self._on_preset)
        self.size_slider.valueChanged.connect(self._on_size)
        self.jump_btn.clicked.connect(self.controller.jump_random)
        self.pause_btn.clicked.connect(self.controller.toggle_pause)
        self.quit_btn.clicked.connect(self.controller.quit)
        self.map.cornerPicked.connect(self.controller.jump_to)

    def _on_spin(self, value: int) -> None:
        self.interval_slider.blockSignals(True)
        self.interval_slider.setValue(seconds_to_slider(value))
        self.interval_slider.blockSignals(False)
        self._sync_presets(value)
        self.controller.set_interval(value)

    def _on_interval_slider(self, value: int) -> None:
        seconds = slider_to_seconds(value)
        self.spin.blockSignals(True)
        self.spin.setValue(seconds)
        self.spin.blockSignals(False)
        self._sync_presets(seconds)
        self.controller.set_interval(seconds)

    def _on_preset(self, seconds: int) -> None:
        self.spin.setValue(seconds)

    def _on_size(self, value: int) -> None:
        self.size_value.setText(f"{value} px")
        self._pending_size = value
        self._size_timer.start()

    def _flush_size(self) -> None:
        if self._pending_size is not None:
            self.controller.set_size(self._pending_size)

    def _sync_presets(self, seconds: int) -> None:
        self.preset_group.blockSignals(True)
        self.preset_group.setExclusive(False)
        for preset, button in self.preset_buttons.items():
            button.blockSignals(True)
            button.setChecked(preset == seconds)
            button.blockSignals(False)
        self.preset_group.setExclusive(True)
        self.preset_group.blockSignals(False)

    def _sync_screens(self) -> None:
        screens = list(QApplication.screens())
        names = [screen.name() for screen in screens]
        if names != getattr(self, "_screen_names", None):
            self._screen_names = names
            for button in self.screen_buttons.values():
                self.screen_group.removeButton(button)
            while self.screen_row.count():
                item = self.screen_row.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()
            self.screen_buttons.clear()
            if len(screens) > 1:
                label = QLabel("屏幕")
                label.setObjectName("section")
                self.screen_row.addWidget(label)
                primary = QApplication.primaryScreen()
                for index, screen in enumerate(screens):
                    name = screen.name()
                    button = QPushButton(
                        screen_menu_label(
                            name,
                            is_primary=screen is primary,
                            index=index,
                        )
                    )
                    button.setObjectName("preset")
                    button.setCheckable(True)
                    button.setCursor(Qt.CursorShape.PointingHandCursor)
                    button.clicked.connect(
                        lambda _checked=False, picked=name: self.controller.use_screen(picked)
                    )
                    self.screen_group.addButton(button)
                    self.screen_buttons[name] = button
                    self.screen_row.addWidget(button, 1)
        current = self.controller.current_screen()
        current_name = current.name() if current is not None else ""
        for name, button in self.screen_buttons.items():
            button.blockSignals(True)
            button.setChecked(name == current_name)
            button.blockSignals(False)

    def refresh_status(self) -> None:
        self._sync_screens()
        text, tone = self.controller.status_parts()
        if tone == "amber":
            style = (
                f"color: {AMBER}; background: {AMBER_SOFT}; "
                "border-radius: 10px; padding: 6px 10px; font-size: 13px;"
            )
        else:
            style = (
                f"color: {GREEN}; background: {GREEN_SOFT}; "
                "border-radius: 10px; padding: 6px 10px; font-size: 13px;"
            )
        if style != self._status_style:
            self._status_style = style
            self.status.setStyleSheet(style)
        self.status.setText(text)
        self.pause_btn.setText("继续" if self.controller.config.paused else "暂停")
        self.map.set_current(self.controller.corner)

    def center_on_screen(self) -> None:
        self.adjustSize()
        screen = self.controller.current_screen()
        if screen is None:
            return
        area = screen.availableGeometry()
        frame = self.frameGeometry()
        frame.moveCenter(area.center())
        if frame.top() < area.top():
            frame.moveTop(area.top() + 8)
        self.move(frame.topLeft())

    def showEvent(self, event) -> None:
        self.clock.start()
        self.refresh_status()
        super().showEvent(event)

    def hideEvent(self, event) -> None:
        self.clock.stop()
        super().hideEvent(event)

    def closeEvent(self, event) -> None:
        if self.allow_close:
            event.accept()
            return
        event.ignore()
        was_visible = self.isVisible()
        self.hide()
        if was_visible:
            self.controller.notify_settings_hidden()
