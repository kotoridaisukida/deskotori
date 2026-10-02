"""贴在桌面上的透明小鸟。每个角转好，直角落在屏幕直角上。"""

from PySide6.QtCore import QEvent, QRectF, Qt, QTimer, QVariantAnimation, Signal
from PySide6.QtGui import QImage, QPainter, QPixmap
from PySide6.QtWidgets import QApplication, QWidget

from qiangjing.geometry import quarter_turns


class PetWindow(QWidget):
    clicked = Signal()
    leaveFinished = Signal()
    enterFinished = Signal()
    resized = Signal()

    def __init__(self, source: QPixmap):
        super().__init__()
        self.source = source
        self._corner = "bl"
        self._turns = 0
        self._face_w = 300
        self._face_h = 300
        self._opacity = 0.0
        self._scale = 1.0
        self._state = "idle"
        self._finish_ok = False
        self._armed = False
        self._cache_key = None
        self._face = QPixmap()
        self.allow_close = False

        self.setObjectName("petWindow")
        self.setWindowTitle("抢镜鸟")
        self.setAccessibleName("抢镜鸟")
        flags = (
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.NoDropShadowWindowHint
        )
        app = QApplication.instance()
        # 任务栏会占一条边。不绕过窗口管理器的话，上面两个角会被挤到工作区里，直角对不齐屏幕。
        if app is not None and app.platformName() == "xcb":
            flags |= Qt.WindowType.X11BypassWindowManagerHint
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setAutoFillBackground(False)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self.anim = QVariantAnimation(self)
        self.anim.valueChanged.connect(self._on_value)
        self.anim.finished.connect(self._on_finished)

    @property
    def state(self) -> str:
        return self._state

    @property
    def corner(self) -> str:
        return self._corner

    def set_display_width(self, width: int) -> None:
        aspect = self.source.height() / max(1, self.source.width())
        self._face_w = max(1, int(width))
        self._face_h = max(1, int(round(width * aspect)))
        self._cache_key = None
        self._rebuild_pixmaps()

    def set_corner(self, corner: str) -> None:
        turns = quarter_turns(corner)
        if corner != self._corner or turns != self._turns:
            self._corner = corner
            self._turns = turns
            self._cache_key = None
        self._rebuild_pixmaps()

    def prepare_hidden(self) -> None:
        self._opacity = 0.0
        self._scale = 0.72
        self.update()

    def play_enter(self) -> None:
        self._start_anim("enter", 280)

    def play_leave(self) -> None:
        self._start_anim("leave", 150)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._rebuild_pixmaps()

    def event(self, event) -> bool:
        if event.type() == QEvent.Type.DevicePixelRatioChange:
            self._cache_key = None
            QTimer.singleShot(0, self._rebuild_pixmaps)
        return super().event(event)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._armed = True
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if (
            event.button() == Qt.MouseButton.LeftButton
            and self._armed
            and self.rect().contains(event.position().toPoint())
        ):
            self.clicked.emit()
        self._armed = False
        super().mouseReleaseEvent(event)

    def closeEvent(self, event) -> None:
        if self.allow_close:
            event.accept()
        else:
            event.ignore()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
            painter.fillRect(self.rect(), Qt.GlobalColor.transparent)
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
            if self._face.isNull() or self._opacity <= 0.01:
                return
            painter.setOpacity(self._opacity)
            if abs(self._scale - 1.0) < 0.001:
                painter.drawPixmap(0, 0, self._face)
                return
            ax, ay = self._anchor()
            painter.translate(ax, ay)
            painter.scale(self._scale, self._scale)
            painter.translate(-ax, -ay)
            painter.drawPixmap(QRectF(self.rect()), self._face, QRectF(self._face.rect()))
        finally:
            painter.end()

    def _anchor(self) -> tuple[float, float]:
        width = float(self.width())
        height = float(self.height())
        if self._corner == "tr":
            return width, 0.0
        if self._corner == "bl":
            return 0.0, height
        if self._corner == "br":
            return width, height
        return 0.0, 0.0

    def _rebuild_pixmaps(self) -> None:
        if self.source.isNull():
            return
        dpr = self.devicePixelRatioF() or 1.0
        key = (self._face_w, self._face_h, self._turns, round(dpr, 2))
        if key == self._cache_key and not self._face.isNull():
            return
        width = max(1, int(round(self._face_w * dpr)))
        height = max(1, int(round(self._face_h * dpr)))
        scaled = self.source.scaled(
            width,
            height,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        scaled.setDevicePixelRatio(dpr)
        face = rotate_quarters(scaled, self._turns)
        face.setDevicePixelRatio(dpr)
        self._face = face
        self._cache_key = key
        logical_w = max(1, int(round(face.width() / dpr)))
        logical_h = max(1, int(round(face.height() / dpr)))
        if self.width() != logical_w or self.height() != logical_h:
            self.setFixedSize(logical_w, logical_h)
            self.resized.emit()
        self.update()

    def _start_anim(self, state: str, duration: int) -> None:
        self.anim.blockSignals(True)
        self.anim.stop()
        self.anim.blockSignals(False)
        self._state = state
        self.anim.setDuration(duration)
        self.anim.setStartValue(0.0)
        self.anim.setEndValue(1.0)
        self._finish_ok = True
        self.anim.start()

    def _on_value(self, value) -> None:
        t = float(value)
        if self._state == "enter":
            clamped = max(0.0, min(1.0, t))
            self._opacity = min(1.0, clamped * 1.35)
            self._scale = _enter_scale(clamped)
        elif self._state == "leave":
            clamped = max(0.0, min(1.0, t))
            self._opacity = 1.0 - clamped
            self._scale = 1.0 - 0.12 * clamped
        self.update()

    def _on_finished(self) -> None:
        if not self._finish_ok:
            return
        self._finish_ok = False
        if self._state == "leave":
            self._state = "between"
            self._opacity = 0.0
            self.leaveFinished.emit()
        elif self._state == "enter":
            self._state = "idle"
            self._scale = 1.0
            self._opacity = 1.0
            self.update()
            self.enterFinished.emit()


def rotate_quarters(src: QPixmap, turns: int) -> QPixmap:
    """顺时针转 0–3 个直角。输出尺寸正好包住画面，不留一圈透明边。"""
    turns &= 3
    if turns == 0 or src.isNull():
        return src
    image = src.toImage().convertToFormat(QImage.Format.Format_ARGB32_Premultiplied)
    width, height = image.width(), image.height()
    out_w, out_h = (width, height) if turns == 2 else (height, width)
    out = QImage(out_w, out_h, QImage.Format.Format_ARGB32_Premultiplied)
    out.fill(0)
    painter = QPainter(out)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, False)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
    if turns == 1:
        painter.translate(height, 0)
        painter.rotate(90)
    elif turns == 2:
        painter.translate(width, height)
        painter.rotate(180)
    else:
        painter.translate(0, width)
        painter.rotate(270)
    painter.drawImage(0, 0, image)
    painter.end()
    pixmap = QPixmap.fromImage(out)
    pixmap.setDevicePixelRatio(src.devicePixelRatio() or 1.0)
    return pixmap


def _enter_scale(t: float) -> float:
    u = max(0.0, min(1.0, t))
    u = 1 - (1 - u) ** 3
    return 0.72 + 0.28 * u
