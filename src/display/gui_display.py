# -*- coding: utf-8 -*-
"""
Mô-đun hiển thị GUI - sử dụng QML.
"""

import asyncio
import os
import signal
from abc import ABCMeta
from pathlib import Path
from typing import Callable, Optional

from PyQt5.QtCore import QObject, Qt, QTimer, QUrl
from PyQt5.QtGui import QCursor, QFont
from PyQt5.QtQuickWidgets import QQuickWidget
from PyQt5.QtWidgets import QApplication, QVBoxLayout, QWidget

from src.display.base_display import BaseDisplay
from src.display.gui_display_model import GuiDisplayModel
from src.utils.resource_finder import find_assets_dir


# Tạo metaclass tương thích
class CombinedMeta(type(QObject), ABCMeta):
    pass


class GuiDisplay(BaseDisplay, QObject, metaclass=CombinedMeta):
    """Lớp hiển thị GUI - giao diện hiện đại dựa trên QML"""

    # Định nghĩa hằng số
    EMOTION_EXTENSIONS = (".gif", ".png", ".jpg", ".jpeg", ".webp")
    DEFAULT_WINDOW_SIZE = (1024, 768)
    DEFAULT_FONT_SIZE = 12
    QUIT_TIMEOUT_MS = 3000

    def __init__(self):
        super().__init__()
        QObject.__init__(self)

        # Thành phần Qt
        self.app = None
        self.root = None
        self.qml_widget = None
        self.system_tray = None

        # Mô hình dữ liệu
        self.display_model = GuiDisplayModel()

        # Quản lý biểu cảm
        self._emotion_cache = {}
        self._last_emotion_name = None

        # Quản lý trạng thái
        self.auto_mode = False
        self._running = True
        self.current_status = ""
        self.is_connected = True

        # Trạng thái kéo cửa sổ
        self._dragging = False
        self._drag_position = None

        # Bản đồ hàm callback
        self._callbacks = {
            "button_press": None,
            "button_release": None,
            "mode": None,
            "auto": None,
            "abort": None,
            "send_text": None,
        }

    # =========================================================================
    # API công cộng - Callback và cập nhật
    # =========================================================================

    async def set_callbacks(
        self,
        press_callback: Optional[Callable] = None,
        release_callback: Optional[Callable] = None,
        mode_callback: Optional[Callable] = None,
        auto_callback: Optional[Callable] = None,
        abort_callback: Optional[Callable] = None,
        send_text_callback: Optional[Callable] = None,
    ):
        """
        Thiết lập các hàm callback.
        """
        self._callbacks.update(
            {
                "button_press": press_callback,
                "button_release": release_callback,
                "mode": mode_callback,
                "auto": auto_callback,
                "abort": abort_callback,
                "send_text": send_text_callback,
            }
        )

    async def update_status(self, status: str, connected: bool):
        """
        Cập nhật văn bản trạng thái và xử lý logic liên quan.
        """
        self.display_model.update_status(status, connected)

        # Theo dõi sự thay đổi trạng thái
        status_changed = status != self.current_status
        connected_changed = bool(connected) != self.is_connected

        if status_changed:
            self.current_status = status
        if connected_changed:
            self.is_connected = bool(connected)

        # Cập nhật khay hệ thống
        if (status_changed or connected_changed) and self.system_tray:
            self.system_tray.update_status(status, self.is_connected)

    async def update_text(self, text: str):
        """
        Cập nhật văn bản TTS.
        """
        self.display_model.update_text(text)

    async def update_emotion(self, emotion_name: str):
        """
        Cập nhật biểu cảm hiển thị.
        """
        if emotion_name == self._last_emotion_name:
            return

        self._last_emotion_name = emotion_name
        asset_path = self._get_emotion_asset_path(emotion_name)

        # Chuyển đường dẫn file cục bộ thành URL có thể sử dụng trong QML (file:///...),
        # Không phải file (như ký tự emoji) giữ nguyên.
        def to_qml_url(p: str) -> str:
            if not p:
                return ""
            if p.startswith(("qrc:/", "file:")):
                return p
            # Chỉ chuyển thành URL file khi đường dẫn tồn tại, tránh nhầm emoji thành đường dẫn
            try:
                if os.path.exists(p):
                    return QUrl.fromLocalFile(p).toString()
            except Exception:
                pass
            return p

        url_or_text = to_qml_url(asset_path)
        self.display_model.update_emotion(url_or_text)

    async def update_button_status(self, text: str):
        """
        Cập nhật trạng thái nút.
        """
        if self.auto_mode:
            self.display_model.update_button_text(text)

    async def toggle_mode(self):
        """
        Chuyển đổi chế độ đối thoại.
        """
        if self._callbacks["mode"]:
            self._on_mode_button_click()
            self.logger.debug("Đã chuyển chế độ đối thoại thông qua phím tắt")

    async def toggle_window_visibility(self):
        """
        Chuyển đổi khả năng hiển thị của cửa sổ.
        """
        if not self.root:
            return

        if self.root.isVisible():
            self.logger.debug("Đã ẩn cửa sổ thông qua phím tắt")
            self.root.hide()
        else:
            self.logger.debug("Đã hiển thị cửa sổ thông qua phím tắt")
            self._show_main_window()

    async def close(self):
        """
        Xử lý đóng cửa sổ.
        """
        self._running = False
        if self.system_tray:
            self.system_tray.hide()
        if self.root:
            self.root.close()

    # =========================================================================
    # Quy trình khởi động
    # =========================================================================

    async def start(self):
        """
        Khởi động GUI.
        """
        try:
            self._configure_environment()
            self._create_main_window()
            self._load_qml()
            self._setup_interactions()
            await self._finalize_startup()
        except Exception as e:
            self.logger.error(f"Khởi động GUI thất bại: {e}", exc_info=True)
            raise

    def _configure_environment(self):
        """
        Cấu hình môi trường.
        """
        os.environ.setdefault("QT_LOGGING_RULES", "qt.qpa.fonts.debug=false")

        self.app = QApplication.instance()
        if self.app is None:
            raise RuntimeError("QApplication không tìm thấy, hãy đảm bảo chạy trong môi trường qasync")

        self.app.setQuitOnLastWindowClosed(False)
        self.app.setFont(QFont("Tahoma, Arial", self.DEFAULT_FONT_SIZE))

        self._setup_signal_handlers()
        self._setup_activation_handler()

    def _create_main_window(self):
        """
        Tạo cửa sổ chính.
        """
        self.root = QWidget()
        self.root.setWindowTitle("")
        self.root.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)

        # Tính kích thước cửa sổ dựa trên cấu hình
        window_size, is_fullscreen = self._calculate_window_size()
        self.root.resize(*window_size)

        # Lưu trạng thái toàn màn hình, sử dụng khi hiển thị
        self._is_fullscreen = is_fullscreen

        self.root.closeEvent = self._closeEvent

    def _calculate_window_size(self) -> tuple:
        """
        Tính kích thước cửa sổ dựa trên cấu hình, trả về (rộng, cao, có toàn màn hình hay không)
        """
        try:
            from src.utils.config_manager import ConfigManager

            config_manager = ConfigManager.get_instance()
            window_size_mode = config_manager.get_config(
                "SYSTEM_OPTIONS.WINDOW_SIZE_MODE", "default"
            )

            # Lấy kích thước màn hình (khu vực khả dụng, loại trừ thanh tác vụ, v.v.)
            desktop = QApplication.desktop()
            screen_rect = desktop.availableGeometry()
            screen_width = screen_rect.width()
            screen_height = screen_rect.height()

            # Tính kích thước cửa sổ dựa trên chế độ
            if window_size_mode == "default":
                # Mặc định sử dụng 50%
                width = int(screen_width * 0.5)
                height = int(screen_height * 0.5)
                is_fullscreen = False
            elif window_size_mode == "screen_75":
                width = int(screen_width * 0.75)
                height = int(screen_height * 0.75)
                is_fullscreen = False
            elif window_size_mode == "screen_100":
                # 100% sử dụng chế độ toàn màn hình thực sự
                width = screen_width
                height = screen_height
                is_fullscreen = True
            else:
                # Chế độ không xác định sử dụng 50%
                width = int(screen_width * 0.5)
                height = int(screen_height * 0.5)
                is_fullscreen = False

            return ((width, height), is_fullscreen)

        except Exception as e:
            self.logger.error(f"Tính kích thước cửa sổ thất bại: {e}", exc_info=True)
            # Khi lỗi, trả về 50% màn hình
            try:
                desktop = QApplication.desktop()
                screen_rect = desktop.availableGeometry()
                return (
                    (int(screen_rect.width() * 0.5), int(screen_rect.height() * 0.5)),
                    False,
                )
            except Exception:
                return (self.DEFAULT_WINDOW_SIZE, False)

    def _load_qml(self):
        """
        Tải giao diện QML.
        """
        self.qml_widget = QQuickWidget()
        self.qml_widget.setResizeMode(QQuickWidget.SizeRootObjectToView)
        self.qml_widget.setClearColor(Qt.white)

        # Đăng ký mô hình dữ liệu vào ngữ cảnh QML
        qml_context = self.qml_widget.rootContext()
        qml_context.setContextProperty("displayModel", self.display_model)

        # Tải file QML
        qml_file = Path(__file__).parent / "gui_display.qml"
        self.qml_widget.setSource(QUrl.fromLocalFile(str(qml_file)))

        # Đặt làm widget trung tâm của cửa sổ chính
        layout = QVBoxLayout(self.root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.qml_widget)
        
        # Đảm bảo cửa sổ cho phép thay đổi kích thước
        self.root.setMinimumSize(1024, 768)  # Kích thước tối thiểu
        self.root.setMaximumSize(1920, 1080)  # Kích thước tối đa (tùy chỉnh)
        self.root.setWindowFlags(Qt.Window)  # Đảm bảo cửa sổ có khung và có thể resize
        self.root.show()        

    def _setup_interactions(self):
        """
        Thiết lập tương tác (tín hiệu, khay hệ thống)
        """
        self._connect_qml_signals()

    async def _finalize_startup(self):
        """
        Hoàn thành quy trình khởi động.
        """
        await self.update_emotion("neutral")

        # Quyết định chế độ hiển thị dựa trên cấu hình
        if getattr(self, "_is_fullscreen", False):
            self.root.showFullScreen()
        else:
            self.root.show()

        self._setup_system_tray()

    # =========================================================================
    # Kết nối tín hiệu
    # =========================================================================

    def _connect_qml_signals(self):
        """
        Kết nối tín hiệu QML với các slot Python.
        """
        root_object = self.qml_widget.rootObject()
        if not root_object:
            self.logger.warning("Không tìm thấy đối tượng gốc QML, không thể thiết lập kết nối tín hiệu")
            return

        # Bản đồ tín hiệu nút
        button_signals = {
            "manualButtonPressed": self._on_manual_button_press,
            "manualButtonReleased": self._on_manual_button_release,
            "autoButtonClicked": self._on_auto_button_click,
            "abortButtonClicked": self._on_abort_button_click,
            "modeButtonClicked": self._on_mode_button_click,
            "sendButtonClicked": self._on_send_button_click,
            "settingsButtonClicked": self._on_settings_button_click,
        }

        # Bản đồ tín hiệu điều khiển tiêu đề
        titlebar_signals = {
            "titleMinimize": self._minimize_window,
            "titleClose": self._quit_application,
            "titleDragStart": self._on_title_drag_start,
            "titleDragMoveTo": self._on_title_drag_move,
            "titleDragEnd": self._on_title_drag_end,
        }

        # Kết nối tín hiệu hàng loạt
        for signal_name, handler in {**button_signals, **titlebar_signals}.items():
            try:
                getattr(root_object, signal_name).connect(handler)
            except AttributeError:
                self.logger.debug(f"Tín hiệu {signal_name} không tồn tại (có thể là tính năng tùy chọn)")

        self.logger.debug("Kết nối tín hiệu QML đã được thiết lập")

    # =========================================================================
    # Xử lý sự kiện nút
    # =========================================================================

    def _on_manual_button_press(self):
        """
        Nút chế độ thủ công được nhấn.
        """
        self._dispatch_callback("button_press")

    def _on_manual_button_release(self):
        """
        Nút chế độ thủ công được thả.
        """
        self._dispatch_callback("button_release")

    def _on_auto_button_click(self):
        """
        Nút chế độ tự động được nhấn.
        """
        self._dispatch_callback("auto")

    def _on_abort_button_click(self):
        """
        Nút hủy được nhấn.
        """
        self._dispatch_callback("abort")

    def _on_mode_button_click(self):
        """
        Nút chuyển đổi chế độ đối thoại được nhấn.
        """
        if self._callbacks["mode"] and not self._callbacks["mode"]():
            return

        self.auto_mode = not self.auto_mode
        mode_text = "Đối thoại tự động" if self.auto_mode else "Đối thoại thủ công"
        self.display_model.update_mode_text(mode_text)
        self.display_model.set_auto_mode(self.auto_mode)

    def _on_send_button_click(self, text: str):
        """
        Xử lý nút gửi văn bản được nhấn.
        """
        text = text.strip()
        if not text or not self._callbacks["send_text"]:
            return

        try:
            task = asyncio.create_task(self._callbacks["send_text"](text))
            task.add_done_callback(
                lambda t: t.cancelled()
                or not t.exception()
                or self.logger.error(
                    f"Nhiệm vụ gửi văn bản lỗi: {t.exception()}", exc_info=True
                )
            )
        except Exception as e:
            self.logger.error(f"Lỗi khi gửi văn bản: {e}")

    def _on_settings_button_click(self):
        """
        Xử lý nút cài đặt được nhấn.
        """
        try:
            from src.views.settings import SettingsWindow

            settings_window = SettingsWindow(self.root)
            settings_window.exec_()
        except Exception as e:
            self.logger.error(f"Mở cửa sổ cài đặt thất bại: {e}", exc_info=True)

    def _dispatch_callback(self, callback_name: str, *args):
        """
        Bộ phân phối callback chung.
        """
        callback = self._callbacks.get(callback_name)
        if callback:
            callback(*args)

    # =========================================================================
    # Kéo cửa sổ
    # =========================================================================

    def _on_title_drag_start(self, _x, _y):
        """
        Bắt đầu kéo tiêu đề.
        """
        self._dragging = True
        self._drag_position = QCursor.pos() - self.root.pos()

    def _on_title_drag_move(self, _x, _y):
        """
        Di chuyển tiêu đề khi kéo.
        """
        if self._dragging and self._drag_position:
            self.root.move(QCursor.pos() - self._drag_position)

    def _on_title_drag_end(self):
        """
        Kết thúc kéo tiêu đề.
        """
        self._dragging = False
        self._drag_position = None

    # =========================================================================
    # Quản lý biểu cảm
    # =========================================================================

    def _get_emotion_asset_path(self, emotion_name: str) -> str:
        """
        Lấy đường dẫn file tài nguyên biểu cảm, tự động khớp với các phần mở rộng phổ biến.
        """
        if emotion_name in self._emotion_cache:
            return self._emotion_cache[emotion_name]

        assets_dir = find_assets_dir()
        if not assets_dir:
            path = "😊"
        else:
            emotion_dir = assets_dir / "emojis"
            # Thử tìm file biểu cảm, nếu thất bại thì quay lại trạng thái neutral
            path = (
                str(self._find_emotion_file(emotion_dir, emotion_name))
                or str(self._find_emotion_file(emotion_dir, "neutral"))
                or "😊"
            )

        self._emotion_cache[emotion_name] = path
        return path

    def _find_emotion_file(self, emotion_dir: Path, name: str) -> Optional[Path]:
        """
        Tìm file biểu cảm trong thư mục chỉ định.
        """
        for ext in self.EMOTION_EXTENSIONS:
            file_path = emotion_dir / f"{name}{ext}"
            if file_path.exists():
                return file_path
        return None

    # =========================================================================
    # Cài đặt hệ thống
    # =========================================================================

    def _setup_signal_handlers(self):
        """
        Thiết lập bộ xử lý tín hiệu (Ctrl+C)
        """
        try:
            signal.signal(
                signal.SIGINT,
                lambda *_: QTimer.singleShot(0, self._quit_application),
            )
        except Exception as e:
            self.logger.warning(f"Thiết lập bộ xử lý tín hiệu thất bại: {e}")

    def _setup_activation_handler(self):
        """
        Thiết lập bộ xử lý kích hoạt ứng dụng (nhấp vào biểu tượng Dock trên macOS để khôi phục cửa sổ)
        """
        try:
            import platform

            if platform.system() != "Darwin":
                return

            self.app.applicationStateChanged.connect(self._on_application_state_changed)
            self.logger.debug("Đã thiết lập bộ xử lý kích hoạt ứng dụng (hỗ trợ Dock trên macOS)")
        except Exception as e:
            self.logger.warning(f"Thiết lập bộ xử lý kích hoạt ứng dụng thất bại: {e}")

    def _on_application_state_changed(self, state):
        """
        Xử lý thay đổi trạng thái ứng dụng (khi nhấp vào Dock trên macOS để khôi phục cửa sổ)
        """
        if state == Qt.ApplicationActive and self.root and not self.root.isVisible():
            QTimer.singleShot(0, self._show_main_window)

    def _setup_system_tray(self):
        """
        Thiết lập khay hệ thống.
        """
        if os.getenv("XIAOZHI_DISABLE_TRAY") == "1":
            self.logger.warning("Đã vô hiệu hóa khay hệ thống thông qua biến môi trường (XIAOZHI_DISABLE_TRAY=1)")
            return

        try:
            from src.views.components.system_tray import SystemTray

            self.system_tray = SystemTray(self.root)

            # Kết nối tín hiệu khay (sử dụng QTimer để đảm bảo thực hiện trên luồng chính)
            tray_signals = {
                "show_window_requested": self._show_main_window,
                "settings_requested": self._on_settings_button_click,
                "quit_requested": self._quit_application,
            }

            for signal_name, handler in tray_signals.items():
                getattr(self.system_tray, signal_name).connect(
                    lambda h=handler: QTimer.singleShot(0, h)
                )

        except Exception as e:
            self.logger.error(f"Khởi tạo thành phần khay hệ thống thất bại: {e}", exc_info=True)

    # =========================================================================
    # Điều khiển cửa sổ
    # =========================================================================

    def _show_main_window(self):
        """
        Hiển thị cửa sổ chính.
        """
        if not self.root:
            return

        if self.root.isMinimized():
            self.root.showNormal()
        if not self.root.isVisible():
            self.root.show()
        self.root.activateWindow()
        self.root.raise_()

    def _minimize_window(self):
        """
        Thu nhỏ cửa sổ.
        """
        if self.root:
            self.root.showMinimized()

    def _quit_application(self):
        """
        Thoát ứng dụng.
        """
        self.logger.info("Bắt đầu thoát ứng dụng...")
        self._running = False

        if self.system_tray:
            self.system_tray.hide()

        try:
            from src.application import Application

            app = Application.get_instance()
            if not app:
                QApplication.quit()
                return

            loop = asyncio.get_event_loop()
            if not loop.is_running():
                QApplication.quit()
                return

            # Tạo nhiệm vụ đóng và thiết lập thời gian chờ
            shutdown_task = asyncio.create_task(app.shutdown())

            def on_shutdown_complete(task):
                if not task.cancelled() and task.exception():
                    self.logger.error(f"Lỗi khi đóng ứng dụng: {task.exception()}")
                else:
                    self.logger.info("Ứng dụng đã đóng bình thường")
                QApplication.quit()

            def force_quit():
                if not shutdown_task.done():
                    self.logger.warning("Đóng quá thời gian chờ, buộc thoát")
                    shutdown_task.cancel()
                QApplication.quit()

            shutdown_task.add_done_callback(on_shutdown_complete)
            QTimer.singleShot(self.QUIT_TIMEOUT_MS, force_quit)

        except Exception as e:
            self.logger.error(f"Đóng ứng dụng thất bại: {e}")
            QApplication.quit()

    def _closeEvent(self, event):
        """
        Xử lý sự kiện đóng cửa sổ.
        """
        # Nếu khay hệ thống khả dụng, thu nhỏ vào khay
        if self.system_tray and (
            getattr(self.system_tray, "is_available", lambda: False)()
            or getattr(self.system_tray, "is_visible", lambda: False)()
        ):
            self.logger.info("Đóng cửa sổ: Thu nhỏ vào khay")
            QTimer.singleShot(0, self.root.hide)
            event.ignore()
        else:
            QTimer.singleShot(0, self._quit_application)
            event.accept()
