from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.utils.config_manager import ConfigManager
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class ShortcutsSettingsWidget(QWidget):
    """
    Thành phần cài đặt phím tắt.
    """

    # Định nghĩa tín hiệu
    settings_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.config = ConfigManager.get_instance()
        self.shortcuts_config = self.config.get_config("SHORTCUTS", {})
        self.init_ui()

    def init_ui(self):
        """
        Khởi tạo UI.
        """
        layout = QVBoxLayout()

        # Tùy chọn kích hoạt phím tắt
        self.enable_checkbox = QCheckBox("Kích hoạt phím tắt toàn cầu")
        self.enable_checkbox.setChecked(self.shortcuts_config.get("ENABLED", True))
        self.enable_checkbox.toggled.connect(self.on_settings_changed)
        layout.addWidget(self.enable_checkbox)

        # Nhóm cấu hình phím tắt
        shortcuts_group = QGroupBox("Cấu hình phím tắt")
        shortcuts_layout = QVBoxLayout()

        # Tạo các điều khiển cấu hình phím tắt
        self.shortcut_widgets = {}

        # Nhấn giữ để nói
        self.shortcut_widgets["MANUAL_PRESS"] = self.create_shortcut_config(
            "Nhấn giữ để nói", self.shortcuts_config.get("MANUAL_PRESS", {})
        )
        shortcuts_layout.addWidget(self.shortcut_widgets["MANUAL_PRESS"])

        # Tự động hội thoại
        self.shortcut_widgets["AUTO_TOGGLE"] = self.create_shortcut_config(
            "Tự động hội thoại", self.shortcuts_config.get("AUTO_TOGGLE", {})
        )
        shortcuts_layout.addWidget(self.shortcut_widgets["AUTO_TOGGLE"])

        # Ngắt hội thoại
        self.shortcut_widgets["ABORT"] = self.create_shortcut_config(
            "Ngắt hội thoại", self.shortcuts_config.get("ABORT", {})
        )
        shortcuts_layout.addWidget(self.shortcut_widgets["ABORT"])

        # Chuyển đổi chế độ
        self.shortcut_widgets["MODE_TOGGLE"] = self.create_shortcut_config(
            "Chuyển đổi chế độ", self.shortcuts_config.get("MODE_TOGGLE", {})
        )
        shortcuts_layout.addWidget(self.shortcut_widgets["MODE_TOGGLE"])

        # Hiện/ẩn cửa sổ
        self.shortcut_widgets["WINDOW_TOGGLE"] = self.create_shortcut_config(
            "Hiện/ẩn cửa sổ", self.shortcuts_config.get("WINDOW_TOGGLE", {})
        )
        shortcuts_layout.addWidget(self.shortcut_widgets["WINDOW_TOGGLE"])

        shortcuts_group.setLayout(shortcuts_layout)
        layout.addWidget(shortcuts_group)

        # Khu vực nút bấm
        btn_layout = QHBoxLayout()
        self.reset_btn = QPushButton("Khôi phục mặc định")
        self.reset_btn.clicked.connect(self.reset_to_defaults)
        btn_layout.addWidget(self.reset_btn)

        self.apply_btn = QPushButton("Áp dụng")
        self.apply_btn.clicked.connect(self.apply_settings)
        btn_layout.addWidget(self.apply_btn)

        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def create_shortcut_config(self, title, config):
        """
        Tạo điều khiển cấu hình phím tắt đơn lẻ.
        """
        widget = QWidget()
        layout = QHBoxLayout()

        # Tiêu đề
        layout.addWidget(QLabel(f"{title}:"))

        # Chọn phím sửa đổi
        modifier_combo = QComboBox()
        modifier_combo.addItems(["Ctrl", "Alt", "Shift"])
        current_modifier = config.get("modifier", "ctrl").title()
        modifier_combo.setCurrentText(current_modifier)
        modifier_combo.currentTextChanged.connect(self.on_settings_changed)
        layout.addWidget(modifier_combo)

        # Chọn phím
        key_combo = QComboBox()
        key_combo.addItems([chr(i) for i in range(ord("a"), ord("z") + 1)])  # a-z
        current_key = config.get("key", "j").lower()
        key_combo.setCurrentText(current_key)
        key_combo.currentTextChanged.connect(self.on_settings_changed)
        layout.addWidget(key_combo)

        widget.setLayout(layout)
        widget.modifier_combo = modifier_combo
        widget.key_combo = key_combo
        return widget

    def on_settings_changed(self):
        """
        Callback khi cài đặt thay đổi.
        """
        self.settings_changed.emit()

    def apply_settings(self):
        """
        Áp dụng cài đặt.
        """
        try:
            # Cập nhật trạng thái kích hoạt
            self.config.update_config(
                "SHORTCUTS.ENABLED", self.enable_checkbox.isChecked()
            )

            # Cập nhật các cấu hình phím tắt
            for key, widget in self.shortcut_widgets.items():
                modifier = widget.modifier_combo.currentText().lower()
                key_value = widget.key_combo.currentText().lower()

                self.config.update_config(f"SHORTCUTS.{key}.modifier", modifier)
                self.config.update_config(f"SHORTCUTS.{key}.key", key_value)

            # Tải lại cấu hình
            self.config.reload_config()
            self.shortcuts_config = self.config.get_config("SHORTCUTS", {})

            logger.info("Cài đặt phím tắt đã được lưu")

        except Exception as e:
            logger.error(f"Lưu cài đặt phím tắt thất bại: {e}")

    def reset_to_defaults(self):
        """
        Khôi phục cài đặt mặc định.
        """
        # Cấu hình mặc định
        defaults = {
            "ENABLED": True,
            "MANUAL_PRESS": {"modifier": "ctrl", "key": "j"},
            "AUTO_TOGGLE": {"modifier": "ctrl", "key": "k"},
            "ABORT": {"modifier": "ctrl", "key": "q"},
            "MODE_TOGGLE": {"modifier": "ctrl", "key": "m"},
            "WINDOW_TOGGLE": {"modifier": "ctrl", "key": "w"},
        }

        # Cập nhật UI
        self.enable_checkbox.setChecked(defaults["ENABLED"])

        for key, config in defaults.items():
            if key == "ENABLED":
                continue

            widget = self.shortcut_widgets.get(key)
            if widget:
                widget.modifier_combo.setCurrentText(config["modifier"].title())
                widget.key_combo.setCurrentText(config["key"].lower())

        # Kích hoạt tín hiệu thay đổi
        self.on_settings_changed()
