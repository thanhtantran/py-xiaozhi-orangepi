# -*- coding: utf-8 -*-
"""
Lớp cửa sổ cơ sở - Lớp cơ sở cho tất cả các cửa sổ PyQt
Hỗ trợ thao tác bất đồng bộ và tích hợp qasync
"""

import asyncio
from typing import Optional

from PyQt5.QtCore import QTimer, pyqtSignal
from PyQt5.QtWidgets import QMainWindow, QWidget

from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class BaseWindow(QMainWindow):
    """
    Lớp cơ sở cho tất cả các cửa sổ, cung cấp hỗ trợ bất đồng bộ.
    """

    # Định nghĩa signal
    window_closed = pyqtSignal()
    status_updated = pyqtSignal(str)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.logger = get_logger(self.__class__.__name__)

        # Quản lý tác vụ bất đồng bộ
        self._tasks = set()
        self._shutdown_event = asyncio.Event()

        # Timer dùng để cập nhật UI định kỳ (phối hợp với thao tác bất đồng bộ)
        self._update_timer = QTimer()
        self._update_timer.timeout.connect(self._on_timer_update)

        # Khởi tạo UI
        self._setup_ui()
        self._setup_connections()
        self._setup_styles()

        self.logger.debug(f"{self.__class__.__name__} khởi tạo hoàn tất")

    def _setup_ui(self):
        """Thiết lập UI - lớp con ghi đè"""

    def _setup_connections(self):
        """Thiết lập kết nối signal - lớp con ghi đè"""

    def _setup_styles(self):
        """Thiết lập style - lớp con ghi đè"""

    def _on_timer_update(self):
        """Callback cập nhật timer - lớp con ghi đè"""

    def start_update_timer(self, interval_ms: int = 1000):
        """
        Khởi động cập nhật định kỳ.
        """
        self._update_timer.start(interval_ms)
        self.logger.debug(f"Khởi động cập nhật định kỳ, khoảng thời gian: {interval_ms}ms")

    def stop_update_timer(self):
        """
        Dừng cập nhật định kỳ.
        """
        self._update_timer.stop()
        self.logger.debug("Dừng cập nhật định kỳ")

    def create_task(self, coro, name: str = None):
        """
        Tạo và quản lý tác vụ bất đồng bộ.
        """
        task = asyncio.create_task(coro, name=name)
        self._tasks.add(task)

        def done_callback(t):
            self._tasks.discard(t)
            if not t.cancelled() and t.exception():
                self.logger.error(f"Ngoại lệ tác vụ bất đồng bộ: {t.exception()}", exc_info=True)

        task.add_done_callback(done_callback)
        return task

    async def shutdown_async(self):
        """
        Đóng cửa sổ bất đồng bộ.
        """
        self.logger.info("Bắt đầu đóng cửa sổ bất đồng bộ")

        # Đặt sự kiện đóng
        self._shutdown_event.set()

        # Dừng timer
        self.stop_update_timer()

        # Hủy tất cả các tác vụ
        for task in self._tasks.copy():
            if not task.done():
                task.cancel()

        # Chờ các tác vụ hoàn thành
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)

        self.logger.info("Đóng cửa sổ bất đồng bộ hoàn tất")

    def closeEvent(self, event):
        """
        Sự kiện đóng cửa sổ.
        """
        self.logger.info("Sự kiện đóng cửa sổ được kích hoạt")

        # Đặt cờ sự kiện đóng
        self._shutdown_event.set()

        # Nếu là cửa sổ kích hoạt, hủy quy trình kích hoạt
        if hasattr(self, "device_activator") and self.device_activator:
            self.device_activator.cancel_activation()
            self.logger.info("Đã gửi signal hủy kích hoạt")

        # Phát signal đóng
        self.window_closed.emit()

        # Dừng timer
        self.stop_update_timer()

        # Hủy tất cả các tác vụ (cách đồng bộ)
        for task in self._tasks.copy():
            if not task.done():
                task.cancel()

        # Chấp nhận sự kiện đóng
        event.accept()

        self.logger.info("Xử lý đóng cửa sổ hoàn tất")

    def update_status(self, message: str):
        """
        Cập nhật thông báo trạng thái.
        """
        self.status_updated.emit(message)
        self.logger.debug(f"Cập nhật trạng thái: {message}")

    def is_shutdown_requested(self) -> bool:
        """
        Kiểm tra có yêu cầu đóng hay không.
        """
        return self._shutdown_event.is_set()
