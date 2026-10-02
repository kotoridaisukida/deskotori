"""把小鸟、计时和设置接到一起。"""

import random
import signal
import sys

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QIcon, QPalette, QPixmap
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWidgets import QApplication, QMenu, QMessageBox, QSystemTrayIcon

from qiangjing.config import (
    INTERVAL_MAX,
    INTERVAL_MIN,
    SIZE_MAX,
    SIZE_MIN,
    ConfigStore,
)
from qiangjing.fonts import build_ui_font, load_fonts
from qiangjing.geometry import corner_position
from qiangjing.logic import describe_status, next_corner
from qiangjing.paths import FONTS, ICON, SPRITE
from qiangjing.pet import PetWindow
from qiangjing.settings_window import SettingsWindow
from qiangjing.theme import CREAM, GREEN, INK, MENU_QSS

SERVER_NAME = "qiangjing-niao"


class Controller:
    def __init__(self, app: QApplication, pixmap: QPixmap):
        self.app = app
        self.rng = random.Random()
        self.store = ConfigStore()
        self.first_run = not self.store.path.exists()
        self.config = self.store.load()
        if self.first_run:
            self.config = self.store.save(self.config)
        self.corner = self.rng.choice(("tl", "tr", "bl", "br"))
        self._started = False
        self._pending = self.corner
        self._again = False
        self._quitting = False
        self._hinted = False
        self._settings_placed = False
        self._placing = False
        self.tray = None
        self._tray_menu = None

        self.stay_timer = QTimer()
        self.stay_timer.setSingleShot(True)
        self.stay_timer.timeout.connect(self.jump_random)

        self.pet = PetWindow(pixmap)
        self.pet.resized.connect(self.place_pet)
        self.pet.set_display_width(self.config.size)
        self.pet.clicked.connect(self.show_settings)
        self.pet.customContextMenuRequested.connect(self._open_pet_menu)
        self.pet.leaveFinished.connect(self._after_leave)
        self.pet.enterFinished.connect(self._after_enter)

        self.settings = SettingsWindow(self)
        icon = load_app_icon(pixmap)
        app.setWindowIcon(icon)
        self.pet.setWindowIcon(icon)
        self.settings.setWindowIcon(icon)
        self._setup_tray(icon)

        self._server = QLocalServer()
        QLocalServer.removeServer(SERVER_NAME)
        if self._server.listen(SERVER_NAME):
            self._server.newConnection.connect(self._on_peer)
        app.aboutToQuit.connect(self._persist)

    def start(self) -> None:
        self._started = True
        self.pet.prepare_hidden()
        self.place_pet()
        self.pet.show()
        screen = self.app.primaryScreen()
        if screen is not None:
            screen.geometryChanged.connect(self.place_pet)
        self.pet.play_enter()
        if self.first_run or self.config.paused:
            self.show_settings()

    def area_tuple(self) -> tuple[int, int, int, int]:
        screen = self.app.primaryScreen()
        if screen is None:
            return (0, 0, 1280, 800)
        rect = screen.geometry()
        return (rect.x(), rect.y(), rect.width(), rect.height())

    def place_pet(self) -> None:
        if self._placing:
            return
        self._placing = True
        try:
            self.pet.set_corner(self.corner)
            if self.pet.width() <= 0 or self.pet.height() <= 0:
                return
            x, y = corner_position(
                self.corner,
                self.area_tuple(),
                self.pet.width(),
                self.pet.height(),
            )
            self.pet.move(x, y)
        finally:
            self._placing = False

    def status_parts(self) -> tuple[str, str]:
        if self.config.paused:
            phase = "idle"
            remaining = -1
        elif not self._started:
            phase = "waiting"
            remaining = -1
        elif self.pet.state != "idle":
            phase = "moving"
            remaining = -1
        else:
            phase = "idle"
            remaining = self.stay_timer.remainingTime()
        return describe_status(
            self.corner,
            paused=self.config.paused,
            phase=phase,
            remaining_ms=remaining,
        )

    def set_interval(self, seconds: int) -> None:
        seconds = max(INTERVAL_MIN, min(INTERVAL_MAX, int(seconds)))
        if seconds == self.config.interval_sec:
            return
        self.config.interval_sec = seconds
        self.config = self.store.save(self.config)
        if self._started and not self.config.paused and self.pet.state == "idle":
            self.stay_timer.start(seconds * 1000)
        self.settings.refresh_status()

    def set_size(self, size: int) -> None:
        size = max(SIZE_MIN, min(SIZE_MAX, int(size)))
        if size == self.config.size:
            return
        self.config.size = size
        self.config = self.store.save(self.config)
        self.pet.set_display_width(size)
        if self._started:
            self.place_pet()

    def toggle_pause(self) -> None:
        self.config.paused = not self.config.paused
        self.config = self.store.save(self.config)
        if self.config.paused:
            self.stay_timer.stop()
        elif self._started and self.pet.state == "idle":
            self.stay_timer.start(self.config.interval_sec * 1000)
        self.settings.refresh_status()

    def jump_random(self) -> None:
        self.jump_to(next_corner(self.corner, self.rng))

    def jump_to(self, corner: str) -> None:
        if corner not in ("tl", "tr", "bl", "br"):
            return
        self._pending = corner
        self.stay_timer.stop()
        state = self.pet.state
        if state == "idle":
            self.pet.play_leave()
        elif state == "enter":
            self._again = True

    def show_settings(self) -> None:
        if not self._settings_placed:
            self.settings.center_on_screen()
            self._settings_placed = True
        self.settings.show()
        self.settings.raise_()
        self.settings.activateWindow()

    def notify_settings_hidden(self) -> None:
        if self._hinted or self.tray is None or self._quitting:
            return
        self._hinted = True
        self.tray.showMessage(
            "抢镜鸟还在桌面上",
            "点她可以再打开设置。右键可以暂停或退出。",
            QSystemTrayIcon.MessageIcon.Information,
            4000,
        )

    def quit(self) -> None:
        self._quitting = True
        self.pet.allow_close = True
        self.settings.allow_close = True
        self._persist()
        self.app.quit()

    def _after_leave(self) -> None:
        self.corner = self._pending
        self.pet.prepare_hidden()
        self.place_pet()
        self.pet.play_enter()
        self.settings.refresh_status()

    def _after_enter(self) -> None:
        if self._again:
            self._again = False
            self.pet.play_leave()
            return
        if self._started and not self.config.paused:
            self.stay_timer.start(self.config.interval_sec * 1000)
        self.settings.refresh_status()

    def _open_pet_menu(self, pos) -> None:
        menu = self._make_menu()
        menu.exec(self.pet.mapToGlobal(pos))

    def _setup_tray(self, icon: QIcon) -> None:
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        self.tray = QSystemTrayIcon(icon)
        self.tray.setToolTip("抢镜鸟")
        self._tray_menu = self._make_menu()
        self.tray.setContextMenu(self._tray_menu)
        self.tray.activated.connect(self._tray_activated)
        self.tray.show()

    def _make_menu(self) -> QMenu:
        menu = QMenu()
        menu.setStyleSheet(MENU_QSS)
        menu.addAction("打开设置", self.show_settings)
        menu.addAction("现在就换", self.jump_random)
        pause_action = menu.addAction(self._pause_label(), self.toggle_pause)
        menu.addSeparator()
        menu.addAction("退出", self.quit)
        menu.aboutToShow.connect(lambda action=pause_action: action.setText(self._pause_label()))
        return menu

    def _pause_label(self) -> str:
        return "继续" if self.config.paused else "暂停"

    def _tray_activated(self, reason) -> None:
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self.show_settings()

    def _on_peer(self) -> None:
        sock = self._server.nextPendingConnection()
        if sock is None:
            return
        sock.readyRead.connect(lambda: self._read_peer(sock))
        if sock.bytesAvailable():
            self._read_peer(sock)

    def _read_peer(self, sock: QLocalSocket) -> None:
        sock.readAll()
        self.show_settings()
        sock.disconnectFromServer()

    def _persist(self) -> None:
        try:
            self.config = self.store.save(self.config)
        except OSError:
            pass


def load_app_icon(fallback: QPixmap | None = None) -> QIcon:
    """窗口、托盘和任务栏都用抢镜鸟的头像。"""
    icon = QIcon()
    if ICON.exists():
        base = QPixmap(str(ICON))
        if not base.isNull():
            for size in (16, 20, 24, 32, 48, 64, 128, 256):
                icon.addPixmap(
                    base.scaled(
                        size,
                        size,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                )
    if icon.isNull() and fallback is not None and not fallback.isNull():
        icon.addPixmap(
            fallback.scaled(
                128,
                128,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )
    return icon


def set_windows_app_id() -> None:
    """让任务栏把这个进程认成抢镜鸟，并显示小鸟图标。"""
    if sys.platform != "win32":
        return
    import ctypes

    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("qiangjing.niao.pet")


def ensure_primary() -> bool:
    sock = QLocalSocket()
    sock.connectToServer(SERVER_NAME)
    if sock.waitForConnected(250):
        sock.write(b"show")
        sock.flush()
        sock.waitForBytesWritten(250)
        sock.disconnectFromServer()
        return False
    return True


def apply_theme(app: QApplication) -> None:
    ui_family, display_family = load_fonts(FONTS)
    app.setFont(build_ui_font(ui_family))
    app.setProperty("displayFamily", display_family or "")
    palette = app.palette()
    palette.setColor(QPalette.ColorRole.Window, QColor(CREAM))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(INK))
    palette.setColor(QPalette.ColorRole.Base, QColor("#FFFFFF"))
    palette.setColor(QPalette.ColorRole.Text, QColor(INK))
    palette.setColor(QPalette.ColorRole.Button, QColor(CREAM))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(INK))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(GREEN))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#FFFFFF"))
    app.setPalette(palette)


def run() -> int:
    set_windows_app_id()
    app = QApplication(sys.argv)
    app.setApplicationName("抢镜鸟")
    app.setWindowIcon(load_app_icon())
    app.setOrganizationName("qiangjing-niao")
    app.setQuitOnLastWindowClosed(False)
    app.setStyle("Fusion")
    apply_theme(app)

    if not SPRITE.exists():
        QMessageBox.critical(None, "抢镜鸟", f"找不到小鸟图片：\n{SPRITE}")
        return 1
    pixmap = QPixmap(str(SPRITE))
    if pixmap.isNull():
        QMessageBox.critical(None, "抢镜鸟", f"图片打不开：\n{SPRITE}")
        return 1
    if not ensure_primary():
        return 0

    controller = Controller(app, pixmap)
    controller.start()

    def _stop(*_args) -> None:
        controller.quit()

    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)
    wake = QTimer()
    wake.start(400)
    wake.timeout.connect(lambda: None)
    return app.exec()
