"""
Module component khay hệ thống, cung cấp chức năng icon khay hệ thống, menu và chỉ báo trạng thái.
"""

from typing import Optional

from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtGui import QBrush, QColor, QIcon, QPainter, QPixmap
from PyQt5.QtWidgets import QAction, QMenu, QSystemTrayIcon, QWidget

from src.utils.logging_config import get_logger


class SystemTray(QObject):
    """
    Component khay hệ thống.
    """

    # Định nghĩa signal
    show_window_requested = pyqtSignal()
    settings_requested = pyqtSignal()
    quit_requested = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        self.logger = get_logger("SystemTray")
        self.parent_widget = parent

        # Component liên quan đến khay
        self.tray_icon = None
        self.tray_menu = None

        # Liên quan đến trạng thái
        self.current_status = ""
        self.is_connected = True

        # Khởi tạo khay
        self._setup_tray()

    def _setup_tray(self):
        """
        Thiết lập icon khay hệ thống.
        """
        try:
            # Kiểm tra hệ thống có hỗ trợ khay hệ thống không
            if not QSystemTrayIcon.isSystemTrayAvailable():
                self.logger.warning("Hệ thống không hỗ trợ chức năng khay hệ thống")
                return

            # Tạo menu khay
            self._create_tray_menu()

            # Tạo icon khay hệ thống (không gắn QWidget làm đối tượng cha, tránh vòng đời cửa sổ ảnh hưởng đến icon khay, ngăn crash khi ẩn/đóng trên macOS)
            self.tray_icon = QSystemTrayIcon()
            self.tray_icon.setContextMenu(self.tray_menu)

            # Trước khi hiển thị, đặt một icon placeholder để tránh cảnh báo QSystemTrayIcon::setVisible: No Icon set
            try:
                # Sử dụng một chấm tròn màu đơn sắc làm placeholder ban đầu
                pixmap = QPixmap(16, 16)
                pixmap.fill(QColor(0, 0, 0, 0))
                painter = QPainter(pixmap)
                painter.setRenderHint(QPainter.Antialiasing)
                painter.setBrush(QBrush(QColor(0, 180, 0)))
                painter.setPen(QColor(0, 0, 0, 0))
                painter.drawEllipse(2, 2, 12, 12)
                painter.end()
                self.tray_icon.setIcon(QIcon(pixmap))
            except Exception:
                pass

            # Kết nối sự kiện của icon khay
            self.tray_icon.activated.connect(self._on_tray_activated)

            # Đặt icon ban đầu (tránh crash khi vẽ lần đầu trên một số nền tảng, trì hoãn thực thi khi vòng lặp sự kiện rảnh)
            try:
                from PyQt5.QtCore import QTimer

                QTimer.singleShot(0, lambda: self.update_status("Chờ lệnh", connected=True))
            except Exception:
                self.update_status("Chờ lệnh", connected=True)

            # Hiển thị icon khay hệ thống
            self.tray_icon.show()
            self.logger.info("Icon khay hệ thống đã được khởi tạo")

        except Exception as e:
            self.logger.error(f"Khởi tạo icon khay hệ thống thất bại: {e}", exc_info=True)

    def _create_tray_menu(self):
        """
        Tạo menu chuột phải khay.
        """
        self.tray_menu = QMenu()

        # Thêm mục menu hiển thị cửa sổ chính
        show_action = QAction("Hiển thị cửa sổ chính", self.parent_widget)
        show_action.triggered.connect(self._on_show_window)
        self.tray_menu.addAction(show_action)

        # Thêm dòng phân cách
        self.tray_menu.addSeparator()

        # Thêm mục menu cài đặt
        settings_action = QAction("Cấu hình tham số", self.parent_widget)
        settings_action.triggered.connect(self._on_settings)
        self.tray_menu.addAction(settings_action)

        # Thêm dòng phân cách
        self.tray_menu.addSeparator()

        # Thêm mục menu thoát
        quit_action = QAction("Thoát chương trình", self.parent_widget)
        quit_action.triggered.connect(self._on_quit)
        self.tray_menu.addAction(quit_action)

    def _on_tray_activated(self, reason):
        """
        Xử lý sự kiện click icon khay.
        """
        if reason == QSystemTrayIcon.Trigger:  # Click đơn
            self.show_window_requested.emit()

    def _on_show_window(self):
        """
        Xử lý click mục menu hiển thị cửa sổ.
        """
        self.show_window_requested.emit()

    def _on_settings(self):
        """
        Xử lý click mục menu cài đặt.
        """
        self.settings_requested.emit()

    def _on_quit(self):
        """
        Xử lý click mục menu thoát.
        """
        self.quit_requested.emit()

    def update_status(self, status: str, connected: bool = True):
        """Cập nhật trạng thái icon khay.

        Args:
            status: Văn bản trạng thái
            connected: Trạng thái kết nối
        """
        if not self.tray_icon:
            return

        self.current_status = status
        self.is_connected = connected

        try:
            icon_color = self._get_status_color(status, connected)

            # Tạo icon với màu chỉ định
            pixmap = QPixmap(16, 16)
            pixmap.fill(QColor(0, 0, 0, 0))  # Nền trong suốt

            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setBrush(QBrush(icon_color))
            painter.setPen(QColor(0, 0, 0, 0))  # Viền trong suốt
            painter.drawEllipse(2, 2, 12, 12)
            painter.end()

            # Đặt icon
            self.tray_icon.setIcon(QIcon(pixmap))

            # Đặt văn bản tooltip
            tooltip = f"Trợ lý AI Tiểu Trí - {status}"
            self.tray_icon.setToolTip(tooltip)

        except Exception as e:
            self.logger.error(f"Cập nhật icon khay hệ thống thất bại: {e}")

    def _get_status_color(self, status: str, connected: bool) -> QColor:
        """Trả về màu tương ứng dựa trên trạng thái.

        Args:
            status: Văn bản trạng thái
            connected: Trạng thái kết nối

        Returns:
            QColor: Màu tương ứng
        """
        if not connected:
            return QColor(128, 128, 128)  # Màu xám - Chưa kết nối

        if "lỗi" in status.lower() or "错误" in status:
            return QColor(255, 0, 0)  # Màu đỏ - Trạng thái lỗi
        elif "nghe" in status.lower() or "聆听" in status:
            return QColor(255, 200, 0)  # Màu vàng - Trạng thái đang nghe
        elif "nói" in status.lower() or "说话" in status:
            return QColor(0, 120, 255)  # Màu xanh dương - Trạng thái đang nói
        else:
            return QColor(0, 180, 0)  # Màu xanh lá - Trạng thái chờ lệnh/đã khởi động

    def show_message(
        self,
        title: str,
        message: str,
        icon_type=QSystemTrayIcon.Information,
        duration: int = 2000,
    ):
        """Hiển thị thông báo khay.

        Args:
            title: Tiêu đề thông báo
            message: Nội dung thông báo
            icon_type: Loại icon
            duration: Thời gian hiển thị (mili giây)
        """
        if self.tray_icon and self.tray_icon.isVisible():
            self.tray_icon.showMessage(title, message, icon_type, duration)

    def hide(self):
        """
        Ẩn icon khay.
        """
        if self.tray_icon:
            self.tray_icon.hide()

    def is_visible(self) -> bool:
        """
        Kiểm tra icon khay có hiển thị không.
        """
        return self.tray_icon and self.tray_icon.isVisible()

    def is_available(self) -> bool:
        """
        Kiểm tra khay hệ thống có khả dụng không.
        """
        return QSystemTrayIcon.isSystemTrayAvailable()
