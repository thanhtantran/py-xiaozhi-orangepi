from pathlib import Path

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QCheckBox, QComboBox, QLineEdit, QWidget

from src.utils.config_manager import ConfigManager
from src.utils.logging_config import get_logger


class SystemOptionsWidget(QWidget):
    """
    Component cài đặt tùy chọn hệ thống.
    """

    # Định nghĩa signal
    settings_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = get_logger(__name__)
        self.config_manager = ConfigManager.get_instance()

        # Tham chiếu điều khiển UI
        self.ui_controls = {}

        # Khởi tạo UI
        self._setup_ui()
        self._connect_events()
        self._load_config_values()

    def _setup_ui(self):
        """
        Thiết lập giao diện UI.
        """
        try:
            from PyQt5 import uic

            ui_path = Path(__file__).parent / "system_options_widget.ui"
            uic.loadUi(str(ui_path), self)

            # Lấy tham chiếu điều khiển UI
            self._get_ui_controls()

        except Exception as e:
            self.logger.error(f"Thiết lập UI tùy chọn hệ thống thất bại: {e}", exc_info=True)
            raise

    def _get_ui_controls(self):
        """
        Lấy tham chiếu điều khiển UI.
        """
        # Điều khiển tùy chọn hệ thống
        self.ui_controls.update(
            {
                "client_id_edit": self.findChild(QLineEdit, "client_id_edit"),
                "device_id_edit": self.findChild(QLineEdit, "device_id_edit"),
                "ota_url_edit": self.findChild(QLineEdit, "ota_url_edit"),
                "websocket_url_edit": self.findChild(QLineEdit, "websocket_url_edit"),
                "websocket_token_edit": self.findChild(
                    QLineEdit, "websocket_token_edit"
                ),
                "authorization_url_edit": self.findChild(
                    QLineEdit, "authorization_url_edit"
                ),
                "activation_version_combo": self.findChild(
                    QComboBox, "activation_version_combo"
                ),
                "window_size_combo": self.findChild(QComboBox, "window_size_combo"),
            }
        )

        # Điều khiển cấu hình MQTT
        self.ui_controls.update(
            {
                "mqtt_endpoint_edit": self.findChild(QLineEdit, "mqtt_endpoint_edit"),
                "mqtt_client_id_edit": self.findChild(QLineEdit, "mqtt_client_id_edit"),
                "mqtt_username_edit": self.findChild(QLineEdit, "mqtt_username_edit"),
                "mqtt_password_edit": self.findChild(QLineEdit, "mqtt_password_edit"),
                "mqtt_publish_topic_edit": self.findChild(
                    QLineEdit, "mqtt_publish_topic_edit"
                ),
                "mqtt_subscribe_topic_edit": self.findChild(
                    QLineEdit, "mqtt_subscribe_topic_edit"
                ),
            }
        )

        # Điều khiển cấu hình AEC
        self.ui_controls.update(
            {
                "aec_enabled_check": self.findChild(QCheckBox, "aec_enabled_check"),
            }
        )

    def _connect_events(self):
        """
        Kết nối xử lý sự kiện.
        """
        # Kết nối tín hiệu thay đổi cho tất cả điều khiển đầu vào
        for control in self.ui_controls.values():
            if isinstance(control, QLineEdit):
                control.textChanged.connect(self.settings_changed.emit)
            elif isinstance(control, QComboBox):
                control.currentTextChanged.connect(self.settings_changed.emit)
            elif isinstance(control, QCheckBox):
                control.stateChanged.connect(self.settings_changed.emit)

    def _load_config_values(self):
        """
        Tải giá trị từ file cấu hình vào điều khiển UI.
        """
        try:
            # Tùy chọn hệ thống
            client_id = self.config_manager.get_config("SYSTEM_OPTIONS.CLIENT_ID", "")
            self._set_text_value("client_id_edit", client_id)

            device_id = self.config_manager.get_config("SYSTEM_OPTIONS.DEVICE_ID", "")
            self._set_text_value("device_id_edit", device_id)

            ota_url = self.config_manager.get_config(
                "SYSTEM_OPTIONS.NETWORK.OTA_VERSION_URL", ""
            )
            self._set_text_value("ota_url_edit", ota_url)

            websocket_url = self.config_manager.get_config(
                "SYSTEM_OPTIONS.NETWORK.WEBSOCKET_URL", ""
            )
            self._set_text_value("websocket_url_edit", websocket_url)

            websocket_token = self.config_manager.get_config(
                "SYSTEM_OPTIONS.NETWORK.WEBSOCKET_ACCESS_TOKEN", ""
            )
            self._set_text_value("websocket_token_edit", websocket_token)

            auth_url = self.config_manager.get_config(
                "SYSTEM_OPTIONS.NETWORK.AUTHORIZATION_URL", ""
            )
            self._set_text_value("authorization_url_edit", auth_url)

            # Phiên bản kích hoạt
            activation_version = self.config_manager.get_config(
                "SYSTEM_OPTIONS.NETWORK.ACTIVATION_VERSION", "v1"
            )
            if self.ui_controls["activation_version_combo"]:
                combo = self.ui_controls["activation_version_combo"]
                combo.setCurrentText(activation_version)

            # Chế độ kích thước cửa sổ
            window_size_mode = self.config_manager.get_config(
                "SYSTEM_OPTIONS.WINDOW_SIZE_MODE", "default"
            )
            if self.ui_controls["window_size_combo"]:
                # Ánh xạ giá trị cấu hình đến văn bản hiển thị (mặc định = 50%)
                mode_to_text = {
                    "default": "Mặc định",
                    "screen_75": "75%",
                    "screen_100": "100%",
                }
                combo = self.ui_controls["window_size_combo"]
                combo.setCurrentText(mode_to_text.get(window_size_mode, "Mặc định"))

            # Cấu hình MQTT
            mqtt_info = self.config_manager.get_config(
                "SYSTEM_OPTIONS.NETWORK.MQTT_INFO", {}
            )
            if mqtt_info:
                self._set_text_value(
                    "mqtt_endpoint_edit", mqtt_info.get("endpoint", "")
                )
                self._set_text_value(
                    "mqtt_client_id_edit", mqtt_info.get("client_id", "")
                )
                self._set_text_value(
                    "mqtt_username_edit", mqtt_info.get("username", "")
                )
                self._set_text_value(
                    "mqtt_password_edit", mqtt_info.get("password", "")
                )
                self._set_text_value(
                    "mqtt_publish_topic_edit", mqtt_info.get("publish_topic", "")
                )
                self._set_text_value(
                    "mqtt_subscribe_topic_edit", mqtt_info.get("subscribe_topic", "")
                )

            # Cấu hình AEC
            aec_enabled = self.config_manager.get_config("AEC_OPTIONS.ENABLED", True)
            self._set_check_value("aec_enabled_check", aec_enabled)

        except Exception as e:
            self.logger.error(f"Tải giá trị cấu hình tùy chọn hệ thống thất bại: {e}", exc_info=True)

    def _set_text_value(self, control_name: str, value: str):
        """
        Đặt giá trị cho điều khiển văn bản.
        """
        control = self.ui_controls.get(control_name)
        if control and hasattr(control, "setText"):
            control.setText(str(value) if value is not None else "")

    def _get_text_value(self, control_name: str) -> str:
        """
        Lấy giá trị từ điều khiển văn bản.
        """
        control = self.ui_controls.get(control_name)
        if control and hasattr(control, "text"):
            return control.text().strip()
        return ""

    def _set_check_value(self, control_name: str, value: bool):
        """
        Đặt giá trị cho điều khiển hộp kiểm.
        """
        control = self.ui_controls.get(control_name)
        if control and hasattr(control, "setChecked"):
            control.setChecked(bool(value))

    def _get_check_value(self, control_name: str) -> bool:
        """
        Lấy giá trị từ điều khiển hộp kiểm.
        """
        control = self.ui_controls.get(control_name)
        if control and hasattr(control, "isChecked"):
            return control.isChecked()
        return False

    def get_config_data(self) -> dict:
        """
        Lấy dữ liệu cấu hình hiện tại.
        """
        config_data = {}

        try:
            # ID khách hàng và ID thiết bị
            client_id = self._get_text_value("client_id_edit")
            if client_id:
                config_data["SYSTEM_OPTIONS.CLIENT_ID"] = client_id

            device_id = self._get_text_value("device_id_edit")
            if device_id:
                config_data["SYSTEM_OPTIONS.DEVICE_ID"] = device_id

            # Tùy chọn hệ thống - Cấu hình mạng
            ota_url = self._get_text_value("ota_url_edit")
            if ota_url:
                config_data["SYSTEM_OPTIONS.NETWORK.OTA_VERSION_URL"] = ota_url

            websocket_url = self._get_text_value("websocket_url_edit")
            if websocket_url:
                config_data["SYSTEM_OPTIONS.NETWORK.WEBSOCKET_URL"] = websocket_url

            websocket_token = self._get_text_value("websocket_token_edit")
            if websocket_token:
                config_data["SYSTEM_OPTIONS.NETWORK.WEBSOCKET_ACCESS_TOKEN"] = (
                    websocket_token
                )

            authorization_url = self._get_text_value("authorization_url_edit")
            if authorization_url:
                config_data["SYSTEM_OPTIONS.NETWORK.AUTHORIZATION_URL"] = (
                    authorization_url
                )

            # Phiên bản kích hoạt
            if self.ui_controls["activation_version_combo"]:
                activation_version = self.ui_controls[
                    "activation_version_combo"
                ].currentText()
                config_data["SYSTEM_OPTIONS.NETWORK.ACTIVATION_VERSION"] = (
                    activation_version
                )

            # Chế độ kích thước cửa sổ
            if self.ui_controls["window_size_combo"]:
                # Ánh xạ văn bản hiển thị đến giá trị cấu hình (mặc định = 50%)
                text_to_mode = {
                    "Mặc định": "default",
                    "75%": "screen_75",
                    "100%": "screen_100",
                }
                window_size_text = self.ui_controls["window_size_combo"].currentText()
                window_size_mode = text_to_mode.get(window_size_text, "default")
                config_data["SYSTEM_OPTIONS.WINDOW_SIZE_MODE"] = window_size_mode

            # Cấu hình MQTT
            mqtt_config = {}
            mqtt_endpoint = self._get_text_value("mqtt_endpoint_edit")
            if mqtt_endpoint:
                mqtt_config["endpoint"] = mqtt_endpoint

            mqtt_client_id = self._get_text_value("mqtt_client_id_edit")
            if mqtt_client_id:
                mqtt_config["client_id"] = mqtt_client_id

            mqtt_username = self._get_text_value("mqtt_username_edit")
            if mqtt_username:
                mqtt_config["username"] = mqtt_username

            mqtt_password = self._get_text_value("mqtt_password_edit")
            if mqtt_password:
                mqtt_config["password"] = mqtt_password

            mqtt_publish_topic = self._get_text_value("mqtt_publish_topic_edit")
            if mqtt_publish_topic:
                mqtt_config["publish_topic"] = mqtt_publish_topic

            mqtt_subscribe_topic = self._get_text_value("mqtt_subscribe_topic_edit")
            if mqtt_subscribe_topic:
                mqtt_config["subscribe_topic"] = mqtt_subscribe_topic

            if mqtt_config:
                # Lấy cấu hình MQTT hiện có và cập nhật
                existing_mqtt = self.config_manager.get_config(
                    "SYSTEM_OPTIONS.NETWORK.MQTT_INFO", {}
                )
                existing_mqtt.update(mqtt_config)
                config_data["SYSTEM_OPTIONS.NETWORK.MQTT_INFO"] = existing_mqtt

            # Cấu hình AEC
            aec_enabled = self._get_check_value("aec_enabled_check")
            config_data["AEC_OPTIONS.ENABLED"] = aec_enabled

        except Exception as e:
            self.logger.error(f"Lấy dữ liệu cấu hình tùy chọn hệ thống thất bại: {e}", exc_info=True)

        return config_data

    def reset_to_defaults(self):
        """
        Đặt lại về giá trị mặc định.
        """
        try:
            # Lấy cấu hình mặc định
            default_config = ConfigManager.DEFAULT_CONFIG

            # Tùy chọn hệ thống
            self._set_text_value(
                "ota_url_edit",
                default_config["SYSTEM_OPTIONS"]["NETWORK"]["OTA_VERSION_URL"],
            )
            self._set_text_value("websocket_url_edit", "")
            self._set_text_value("websocket_token_edit", "")
            self._set_text_value(
                "authorization_url_edit",
                default_config["SYSTEM_OPTIONS"]["NETWORK"]["AUTHORIZATION_URL"],
            )

            if self.ui_controls["activation_version_combo"]:
                self.ui_controls["activation_version_combo"].setCurrentText(
                    default_config["SYSTEM_OPTIONS"]["NETWORK"]["ACTIVATION_VERSION"]
                )

            # Xóa cấu hình MQTT
            self._set_text_value("mqtt_endpoint_edit", "")
            self._set_text_value("mqtt_client_id_edit", "")
            self._set_text_value("mqtt_username_edit", "")
            self._set_text_value("mqtt_password_edit", "")
            self._set_text_value("mqtt_publish_topic_edit", "")
            self._set_text_value("mqtt_subscribe_topic_edit", "")

            # Giá trị mặc định cho cấu hình AEC
            default_aec = default_config.get("AEC_OPTIONS", {})
            self._set_check_value(
                "aec_enabled_check", default_aec.get("ENABLED", False)
            )

            self.logger.info("Cấu hình tùy chọn hệ thống đã được đặt lại về giá trị mặc định")

        except Exception as e:
            self.logger.error(f"Đặt lại cấu hình tùy chọn hệ thống thất bại: {e}", exc_info=True)
