import os
from pathlib import Path

from PyQt5.QtWidgets import (
    QDialog,
    QMessageBox,
    QPushButton,
    QTabWidget,
)

from src.utils.config_manager import ConfigManager
from src.utils.logging_config import get_logger
from src.views.settings.components.audio import AudioWidget
from src.views.settings.components.camera import CameraWidget
from src.views.settings.components.shortcuts_settings import ShortcutsSettingsWidget
from src.views.settings.components.system_options import SystemOptionsWidget
from src.views.settings.components.wake_word import WakeWordWidget


class SettingsWindow(QDialog):
    """
    Cửa sổ cấu hình tham số.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = get_logger(__name__)
        self.config_manager = ConfigManager.get_instance()

        # Tham chiếu component
        self.system_options_tab = None
        self.wake_word_tab = None
        self.camera_tab = None
        self.audio_tab = None
        self.shortcuts_tab = None

        # Điều khiển UI
        self.ui_controls = {}

        # Khởi tạo UI
        self._setup_ui()
        self._connect_events()

    def _setup_ui(self):
        """
        Thiết lập giao diện UI.
        """
        try:
            from PyQt5 import uic

            ui_path = Path(__file__).parent / "settings_window.ui"
            uic.loadUi(str(ui_path), self)

            # Lấy tham chiếu điều khiển UI
            self._get_ui_controls()

            # Thêm các tab component
            self._add_component_tabs()

        except Exception as e:
            self.logger.error(f"Thiết lập UI thất bại: {e}", exc_info=True)
            raise

    def _add_component_tabs(self):
        """
        Thêm các tab component.
        """
        try:
            # Lấy TabWidget
            tab_widget = self.findChild(QTabWidget, "tabWidget")
            if not tab_widget:
                self.logger.error("Không tìm thấy điều khiển TabWidget")
                return

            # Xóa các tab hiện có (nếu có)
            tab_widget.clear()

            # Tạo và thêm component tùy chọn hệ thống
            self.system_options_tab = SystemOptionsWidget()
            tab_widget.addTab(self.system_options_tab, "Tùy chọn")
            self.system_options_tab.settings_changed.connect(self._on_settings_changed)

            # Tạo và thêm component từ đánh thức
            self.wake_word_tab = WakeWordWidget()
            tab_widget.addTab(self.wake_word_tab, "Wakeword")
            self.wake_word_tab.settings_changed.connect(self._on_settings_changed)

            # Tạo và thêm component camera
            self.camera_tab = CameraWidget()
            tab_widget.addTab(self.camera_tab, "Camera")
            self.camera_tab.settings_changed.connect(self._on_settings_changed)

            # Tạo và thêm component thiết bị âm thanh
            self.audio_tab = AudioWidget()
            tab_widget.addTab(self.audio_tab, "Âm thanh")
            self.audio_tab.settings_changed.connect(self._on_settings_changed)

            # Tạo và thêm component cài đặt phím tắt
            self.shortcuts_tab = ShortcutsSettingsWidget()
            tab_widget.addTab(self.shortcuts_tab, "Phím tắt")
            self.shortcuts_tab.settings_changed.connect(self._on_settings_changed)

            self.logger.debug("Thêm tất cả các tab component thành công")

        except Exception as e:
            self.logger.error(f"Thêm tab component thất bại: {e}", exc_info=True)

    def _on_settings_changed(self):
        """
        Callback thay đổi cài đặt.
        """
        # Có thể thêm một số gợi ý hoặc logic khác ở đây

    def _get_ui_controls(self):
        """
        Lấy tham chiếu điều khiển UI.
        """
        # Chỉ cần lấy các điều khiển nút chính
        self.ui_controls.update(
            {
                "save_btn": self.findChild(QPushButton, "save_btn"),
                "cancel_btn": self.findChild(QPushButton, "cancel_btn"),
                "reset_btn": self.findChild(QPushButton, "reset_btn"),
            }
        )

    def _connect_events(self):
        """
        Kết nối xử lý sự kiện.
        """
        if self.ui_controls["save_btn"]:
            self.ui_controls["save_btn"].clicked.connect(self._on_save_clicked)

        if self.ui_controls["cancel_btn"]:
            self.ui_controls["cancel_btn"].clicked.connect(self.reject)

        if self.ui_controls["reset_btn"]:
            self.ui_controls["reset_btn"].clicked.connect(self._on_reset_clicked)

    # Tải cấu hình hiện được xử lý bởi từng component, không cần xử lý trong cửa sổ chính

    # Đã xóa các phương thức thao tác điều khiển không còn cần thiết, hiện được xử lý bởi từng component

    def _on_save_clicked(self):
        """
        Sự kiện click nút lưu.
        """
        try:
            # Thu thập tất cả dữ liệu cấu hình
            success = self._save_all_config()

            if success:
                # Hiển thị lưu thành công và nhắc khởi động lại
                reply = QMessageBox.question(
                    self,
                    "Lưu cấu hình thành công",
                    "Cấu hình đã được lưu thành công!\n\nĐể cấu hình có hiệu lực, khuyến nghị khởi động lại phần mềm.\nKhởi động lại ngay bây giờ?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.Yes,
                )

                if reply == QMessageBox.Yes:
                    self._restart_application()
                else:
                    self.accept()
            else:
                QMessageBox.warning(self, "Lỗi", "Lưu cấu hình thất bại, vui lòng kiểm tra giá trị đã nhập.")

        except Exception as e:
            self.logger.error(f"Lưu cấu hình thất bại: {e}", exc_info=True)
            QMessageBox.critical(self, "Lỗi", f"Xảy ra lỗi khi lưu cấu hình: {str(e)}")

    def _save_all_config(self) -> bool:
        """
        Lưu tất cả cấu hình.
        """
        try:
            # Thu thập dữ liệu cấu hình từ các component
            all_config_data = {}

            # Cấu hình tùy chọn hệ thống
            if self.system_options_tab:
                system_config = self.system_options_tab.get_config_data()
                all_config_data.update(system_config)

            # Cấu hình từ đánh thức
            if self.wake_word_tab:
                wake_word_config = self.wake_word_tab.get_config_data()
                all_config_data.update(wake_word_config)
                # Lưu file từ đánh thức
                self.wake_word_tab.save_keywords()

            # Cấu hình camera
            if self.camera_tab:
                camera_config = self.camera_tab.get_config_data()
                all_config_data.update(camera_config)

            # Cấu hình thiết bị âm thanh
            if self.audio_tab:
                audio_config = self.audio_tab.get_config_data()
                all_config_data.update(audio_config)

            # Cấu hình phím tắt
            if self.shortcuts_tab:
                # Component phím tắt có phương thức lưu riêng
                self.shortcuts_tab.apply_settings()

            # Cập nhật cấu hình hàng loạt
            for config_path, value in all_config_data.items():
                self.config_manager.update_config(config_path, value)

            self.logger.info("Lưu cấu hình thành công")
            return True

        except Exception as e:
            self.logger.error(f"Lỗi khi lưu cấu hình: {e}", exc_info=True)
            return False

    def _on_reset_clicked(self):
        """
        Sự kiện click nút reset.
        """
        reply = QMessageBox.question(
            self,
            "Xác nhận reset",
            "Bạn có chắc chắn muốn reset tất cả cấu hình về giá trị mặc định không?\nĐiều này sẽ xóa tất cả cài đặt hiện tại.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            self._reset_to_defaults()

    def _reset_to_defaults(self):
        """
        Reset về giá trị mặc định.
        """
        try:
            # Để các component reset về giá trị mặc định
            if self.system_options_tab:
                self.system_options_tab.reset_to_defaults()

            if self.wake_word_tab:
                self.wake_word_tab.reset_to_defaults()

            if self.camera_tab:
                self.camera_tab.reset_to_defaults()

            if self.audio_tab:
                self.audio_tab.reset_to_defaults()

            if self.shortcuts_tab:
                self.shortcuts_tab.reset_to_defaults()

            self.logger.info("Cấu hình tất cả component đã được reset về giá trị mặc định")

        except Exception as e:
            self.logger.error(f"Reset cấu hình thất bại: {e}", exc_info=True)
            QMessageBox.critical(self, "Lỗi", f"Xảy ra lỗi khi reset cấu hình: {str(e)}")

    def _restart_application(self):
        """
        Khởi động lại ứng dụng.
        """
        try:
            self.logger.info("Người dùng chọn khởi động lại ứng dụng")

            # Đóng cửa sổ cài đặt
            self.accept()

            # Khởi động lại chương trình trực tiếp
            self._direct_restart()

        except Exception as e:
            self.logger.error(f"Khởi động lại ứng dụng thất bại: {e}", exc_info=True)
            QMessageBox.warning(
                self, "Khởi động lại thất bại", "Khởi động lại tự động thất bại, vui lòng khởi động lại phần mềm thủ công để cấu hình có hiệu lực."
            )

    def _direct_restart(self):
        """
        Khởi động lại chương trình trực tiếp.
        """
        try:
            import sys

            from PyQt5.QtWidgets import QApplication

            # Lấy đường dẫn và tham số của chương trình đang thực thi
            python = sys.executable
            script = sys.argv[0]
            args = sys.argv[1:]

            self.logger.info(f"Lệnh khởi động lại: {python} {script} {' '.join(args)}")

            # Đóng ứng dụng hiện tại
            QApplication.quit()

            # Khởi động instance mới
            if getattr(sys, "frozen", False):
                # Môi trường đóng gói
                os.execv(sys.executable, [sys.executable] + args)
            else:
                # Môi trường phát triển
                os.execv(python, [python, script] + args)

        except Exception as e:
            self.logger.error(f"Khởi động lại trực tiếp thất bại: {e}", exc_info=True)

    def closeEvent(self, event):
        """
        Sự kiện đóng cửa sổ.
        """
        self.logger.debug("Cửa sổ cài đặt đã đóng")
        super().closeEvent(event)
