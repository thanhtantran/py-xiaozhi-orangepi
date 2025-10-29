from pathlib import Path

import cv2
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from src.utils.config_manager import ConfigManager
from src.utils.logging_config import get_logger


class CameraWidget(QWidget):
    """
    Thành phần cài đặt camera.
    """

    # Định nghĩa tín hiệu
    settings_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = get_logger(__name__)
        self.config_manager = ConfigManager.get_instance()

        # Tham chiếu đến các điều khiển UI
        self.ui_controls = {}

        # Liên quan đến xem trước
        self.camera = None
        self.preview_timer = QTimer()
        self.preview_timer.timeout.connect(self._update_preview_frame)
        self.is_previewing = False

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

            ui_path = Path(__file__).parent / "camera_widget.ui"
            uic.loadUi(str(ui_path), self)

            # Lấy tham chiếu đến các điều khiển UI
            self._get_ui_controls()

        except Exception as e:
            self.logger.error(f"Thiết lập UI camera thất bại: {e}", exc_info=True)
            raise

    def _get_ui_controls(self):
        """
        Lấy tham chiếu đến các điều khiển UI.
        """
        self.ui_controls.update(
            {
                "camera_index_spin": self.findChild(QSpinBox, "camera_index_spin"),
                "frame_width_spin": self.findChild(QSpinBox, "frame_width_spin"),
                "frame_height_spin": self.findChild(QSpinBox, "frame_height_spin"),
                "fps_spin": self.findChild(QSpinBox, "fps_spin"),
                "local_vl_url_edit": self.findChild(QLineEdit, "local_vl_url_edit"),
                "vl_api_key_edit": self.findChild(QLineEdit, "vl_api_key_edit"),
                "models_edit": self.findChild(QLineEdit, "models_edit"),
                "scan_camera_btn": self.findChild(QPushButton, "scan_camera_btn"),
                # Các điều khiển liên quan đến xem trước
                "preview_label": self.findChild(QLabel, "preview_label"),
                "start_preview_btn": self.findChild(QPushButton, "start_preview_btn"),
                "stop_preview_btn": self.findChild(QPushButton, "stop_preview_btn"),
            }
        )

    def _connect_events(self):
        """
        Kết nối xử lý sự kiện.
        """
        # Kết nối tín hiệu thay đổi cho tất cả các điều khiển đầu vào
        for control in self.ui_controls.values():
            if isinstance(control, QLineEdit):
                control.textChanged.connect(self.settings_changed.emit)
            elif isinstance(control, QSpinBox):
                if control == self.ui_controls.get("camera_index_spin"):
                    # Khi chỉ số camera thay đổi, tự động cập nhật xem trước
                    control.valueChanged.connect(self._on_camera_index_changed)
                else:
                    control.valueChanged.connect(self.settings_changed.emit)
            elif isinstance(control, QPushButton):
                continue

        # Nút quét camera
        if self.ui_controls["scan_camera_btn"]:
            self.ui_controls["scan_camera_btn"].clicked.connect(self._on_scan_camera)

        # Nút điều khiển xem trước
        if self.ui_controls["start_preview_btn"]:
            self.ui_controls["start_preview_btn"].clicked.connect(self._start_preview)

        if self.ui_controls["stop_preview_btn"]:
            self.ui_controls["stop_preview_btn"].clicked.connect(self._stop_preview)

    def _load_config_values(self):
        """
        Tải giá trị từ tệp cấu hình vào các điều khiển UI.
        """
        try:
            # Cấu hình camera
            camera_config = self.config_manager.get_config("CAMERA", {})
            self._set_spin_value(
                "camera_index_spin", camera_config.get("camera_index", 0)
            )
            self._set_spin_value(
                "frame_width_spin", camera_config.get("frame_width", 640)
            )
            self._set_spin_value(
                "frame_height_spin", camera_config.get("frame_height", 480)
            )
            self._set_spin_value("fps_spin", camera_config.get("fps", 30))
            self._set_text_value(
                "local_vl_url_edit", camera_config.get("Local_VL_url", "")
            )
            self._set_text_value("vl_api_key_edit", camera_config.get("VLapi_key", ""))
            self._set_text_value("models_edit", camera_config.get("models", ""))

        except Exception as e:
            self.logger.error(f"Tải giá trị cấu hình camera thất bại: {e}", exc_info=True)

    def _set_text_value(self, control_name: str, value: str):
        """
        Thiết lập giá trị cho điều khiển văn bản.
        """
        control = self.ui_controls.get(control_name)
        if control and hasattr(control, "setText"):
            control.setText(str(value) if value is not None else "")

    def _set_spin_value(self, control_name: str, value: int):
        """
        Thiết lập giá trị cho điều khiển số.
        """
        control = self.ui_controls.get(control_name)
        if control and hasattr(control, "setValue"):
            control.setValue(int(value) if value is not None else 0)

    def _get_text_value(self, control_name: str) -> str:
        """
        Lấy giá trị từ điều khiển văn bản.
        """
        control = self.ui_controls.get(control_name)
        if control and hasattr(control, "text"):
            return control.text().strip()
        return ""

    def _get_spin_value(self, control_name: str) -> int:
        """
        Lấy giá trị từ điều khiển số.
        """
        control = self.ui_controls.get(control_name)
        if control and hasattr(control, "value"):
            return control.value()
        return 0

    def _on_scan_camera(self):
        """
        Xử lý sự kiện khi nút quét camera được nhấn.
        """
        try:
            # Dừng xem trước hiện tại (tránh chiếm dụng camera)
            was_previewing = self.is_previewing
            if self.is_previewing:
                self._stop_preview()

            # Quét các camera có sẵn
            available_cameras = self._scan_available_cameras()

            if not available_cameras:
                QMessageBox.information(
                    self,
                    "Kết quả quét",
                    "Không phát hiện thiết bị camera có sẵn.\n"
                    "Vui lòng đảm bảo camera đã được kết nối và không bị chiếm dụng bởi chương trình khác.",
                )
                return

            # Nếu chỉ có một camera, sử dụng ngay
            if len(available_cameras) == 1:
                camera = available_cameras[0]
                self._apply_camera_settings(camera)
                QMessageBox.information(
                    self,
                    "Cài đặt hoàn tất",
                    f"Phát hiện 1 camera, đã tự động thiết lập:\n"
                    f"Chỉ số: {camera[0]}, Độ phân giải: {camera[1]}x{camera[2]}",
                )
            else:
                # Nếu có nhiều camera, hiển thị hộp thoại chọn
                selected_camera = self._show_camera_selection_dialog(available_cameras)
                if selected_camera:
                    self._apply_camera_settings(selected_camera)
                    QMessageBox.information(
                        self,
                        "Cài đặt hoàn tất",
                        f"Đã thiết lập camera:\n"
                        f"Chỉ số: {selected_camera[0]}, Độ phân giải: {selected_camera[1]}x{selected_camera[2]}",
                    )

            # Khôi phục trạng thái xem trước
            if was_previewing:
                QTimer.singleShot(500, self._start_preview)

        except Exception as e:
            self.logger.error(f"Quét camera thất bại: {e}", exc_info=True)
            QMessageBox.warning(self, "Lỗi", f"Đã xảy ra lỗi khi quét camera: {str(e)}")

    def _scan_available_cameras(self, max_devices: int = 5):
        """
        Quét các thiết bị camera có sẵn.
        """
        available_cameras = []

        try:
            for i in range(max_devices):
                try:
                    # Thử mở camera
                    cap = cv2.VideoCapture(i)

                    if cap.isOpened():
                        # Thử đọc một khung để xác minh camera hoạt động
                        ret, _ = cap.read()
                        if ret:
                            # Lấy độ phân giải mặc định
                            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                            available_cameras.append((i, width, height))

                            self.logger.info(f"Phát hiện camera {i}: {width}x{height}")

                    cap.release()

                except Exception as e:
                    self.logger.debug(f"Lỗi khi phát hiện camera {i}: {e}")
                    continue

        except Exception as e:
            self.logger.error(f"Lỗi trong quá trình quét camera: {e}", exc_info=True)

        return available_cameras

    def _show_camera_selection_dialog(self, available_cameras):
        """
        Hiển thị hộp thoại chọn camera.
        """
        try:
            dialog = QDialog(self)
            dialog.setWindowTitle("Chọn camera")
            dialog.setFixedSize(400, 300)

            layout = QVBoxLayout(dialog)

            # Nhãn tiêu đề
            title_label = QLabel(
                f"Phát hiện {len(available_cameras)} camera có sẵn, vui lòng chọn một:"
            )
            title_label.setStyleSheet("font-weight: bold; margin-bottom: 10px;")
            layout.addWidget(title_label)

            # Danh sách camera
            camera_list = QListWidget()
            for idx, width, height in available_cameras:
                item_text = f"Chỉ số {idx}: Độ phân giải {width}x{height}"
                item = QListWidgetItem(item_text)
                item.setData(Qt.UserRole, (idx, width, height))  # Lưu trữ dữ liệu camera
                camera_list.addItem(item)

            # Mặc định chọn camera đầu tiên
            if camera_list.count() > 0:
                camera_list.setCurrentRow(0)

            layout.addWidget(camera_list)

            # Nút
            button_box = QDialogButtonBox(
                QDialogButtonBox.Ok | QDialogButtonBox.Cancel, Qt.Horizontal
            )
            button_box.accepted.connect(dialog.accept)
            button_box.rejected.connect(dialog.reject)
            layout.addWidget(button_box)

            # Hiển thị hộp thoại
            if dialog.exec_() == QDialog.Accepted:
                current_item = camera_list.currentItem()
                if current_item:
                    return current_item.data(Qt.UserRole)

            return None

        except Exception as e:
            self.logger.error(f"Hiển thị hộp thoại chọn camera thất bại: {e}", exc_info=True)
            return None

    def _apply_camera_settings(self, camera_data):
        """
        Áp dụng cài đặt camera.
        """
        try:
            idx, width, height = camera_data
            self._set_spin_value("camera_index_spin", idx)
            self._set_spin_value("frame_width_spin", width)
            self._set_spin_value("frame_height_spin", height)

            self.logger.info(f"Áp dụng cài đặt camera: Chỉ số {idx}, {width}x{height}")

        except Exception as e:
            self.logger.error(f"Áp dụng cài đặt camera thất bại: {e}", exc_info=True)

    def get_config_data(self) -> dict:
        """
        Lấy dữ liệu cấu hình hiện tại.
        """
        config_data = {}

        try:
            # Cấu hình camera
            camera_config = {}
            camera_config["camera_index"] = self._get_spin_value("camera_index_spin")
            camera_config["frame_width"] = self._get_spin_value("frame_width_spin")
            camera_config["frame_height"] = self._get_spin_value("frame_height_spin")
            camera_config["fps"] = self._get_spin_value("fps_spin")

            local_vl_url = self._get_text_value("local_vl_url_edit")
            if local_vl_url:
                camera_config["Local_VL_url"] = local_vl_url

            vl_api_key = self._get_text_value("vl_api_key_edit")
            if vl_api_key:
                camera_config["VLapi_key"] = vl_api_key

            models = self._get_text_value("models_edit")
            if models:
                camera_config["models"] = models

            # Lấy cấu hình camera hiện tại và cập nhật
            existing_camera = self.config_manager.get_config("CAMERA", {})
            existing_camera.update(camera_config)
            config_data["CAMERA"] = existing_camera

        except Exception as e:
            self.logger.error(f"Lấy dữ liệu cấu hình camera thất bại: {e}", exc_info=True)

        return config_data

    def reset_to_defaults(self):
        """
        Đặt lại về giá trị mặc định.
        """
        try:
            # Lấy cấu hình mặc định
            default_config = ConfigManager.DEFAULT_CONFIG

            # Cấu hình camera
            camera_config = default_config["CAMERA"]
            self._set_spin_value("camera_index_spin", camera_config["camera_index"])
            self._set_spin_value("frame_width_spin", camera_config["frame_width"])
            self._set_spin_value("frame_height_spin", camera_config["frame_height"])
            self._set_spin_value("fps_spin", camera_config["fps"])
            self._set_text_value("local_vl_url_edit", camera_config["Local_VL_url"])
            self._set_text_value("vl_api_key_edit", camera_config["VLapi_key"])
            self._set_text_value("models_edit", camera_config["models"])

            self.logger.info("Cấu hình camera đã được đặt lại về giá trị mặc định")

        except Exception as e:
            self.logger.error(f"Đặt lại cấu hình camera thất bại: {e}", exc_info=True)

    def _on_camera_index_changed(self):
        """
        Xử lý sự kiện khi chỉ số camera thay đổi.
        """
        try:
            # Phát tín hiệu thay đổi cài đặt
            self.settings_changed.emit()

            # Nếu hiện đang xem trước, khởi động lại xem trước
            if self.is_previewing:
                self._restart_preview()

        except Exception as e:
            self.logger.error(f"Xử lý thay đổi chỉ số camera thất bại: {e}", exc_info=True)

    def _start_preview(self):
        """
        Bắt đầu xem trước camera.
        """
        try:
            if self.is_previewing:
                self._stop_preview()

            # Lấy tham số camera
            camera_index = self._get_spin_value("camera_index_spin")
            width = self._get_spin_value("frame_width_spin")
            height = self._get_spin_value("frame_height_spin")
            fps = self._get_spin_value("fps_spin")

            # Khởi tạo camera
            self.camera = cv2.VideoCapture(camera_index)

            if not self.camera.isOpened():
                self._show_preview_error(f"Không thể mở camera chỉ số {camera_index}")
                return

            # Thiết lập tham số camera
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
            self.camera.set(cv2.CAP_PROP_FPS, fps)

            # Kiểm tra xem camera có thể đọc được không
            ret, _ = self.camera.read()
            if not ret:
                self._show_preview_error("Camera không thể đọc hình ảnh")
                self.camera.release()
                self.camera = None
                return

            # Bắt đầu xem trước
            self.is_previewing = True
            self.preview_timer.start(max(1, int(1000 / fps)))

            # Cập nhật trạng thái nút
            self._update_preview_buttons(True)

            self.logger.info(f"Bắt đầu xem trước camera {camera_index}")

        except Exception as e:
            self.logger.error(f"Khởi động xem trước camera thất bại: {e}", exc_info=True)
            self._show_preview_error(f"Đã xảy ra lỗi khi khởi động xem trước: {str(e)}")
            self._cleanup_camera()

    def _stop_preview(self):
        """
        Dừng xem trước camera.
        """
        try:
            if not self.is_previewing:
                return

            # Dừng bộ hẹn giờ
            self.preview_timer.stop()
            self.is_previewing = False

            # Giải phóng camera
            self._cleanup_camera()

            # Xóa hiển thị xem trước
            if self.ui_controls["preview_label"]:
                self.ui_controls["preview_label"].setText(
                    "Khu vực xem trước camera\nNhấn để bắt đầu xem trước hình ảnh camera"
                )
                self.ui_controls["preview_label"].setPixmap(QPixmap())

            # Cập nhật trạng thái nút
            self._update_preview_buttons(False)

            self.logger.info("Dừng xem trước camera")

        except Exception as e:
            self.logger.error(f"Dừng xem trước camera thất bại: {e}", exc_info=True)

    def _restart_preview(self):
        """
        Khởi động lại xem trước (gọi khi tham số camera thay đổi).
        """
        if self.is_previewing:
            self._stop_preview()
            # Đợi một chút rồi khởi động lại, đảm bảo tài nguyên camera được giải phóng
            QTimer.singleShot(100, self._start_preview)

    def _update_preview_frame(self):
        """
        Cập nhật khung hình xem trước.
        """
        try:
            if not self.camera or not self.camera.isOpened():
                return

            ret, frame = self.camera.read()
            if not ret:
                self._show_preview_error("Không thể đọc hình ảnh từ camera")
                return

            # Chuyển đổi không gian màu BGR -> RGB
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # Lấy kích thước khung hình
            h, w, ch = rgb_frame.shape
            bytes_per_line = ch * w

            # Chuyển đổi thành QImage
            qt_image = QImage(
                rgb_frame.data, w, h, bytes_per_line, QImage.Format_RGB888
            )

            # Thu nhỏ đến kích thước nhãn xem trước
            if self.ui_controls["preview_label"]:
                label_size = self.ui_controls["preview_label"].size()
                scaled_image = qt_image.scaled(
                    label_size, Qt.KeepAspectRatio, Qt.SmoothTransformation
                )

                # Chuyển đổi thành QPixmap và hiển thị
                pixmap = QPixmap.fromImage(scaled_image)
                self.ui_controls["preview_label"].setPixmap(pixmap)

        except Exception as e:
            self.logger.error(f"Cập nhật khung hình xem trước thất bại: {e}", exc_info=True)
            self._show_preview_error(f"Đã xảy ra lỗi khi hiển thị hình ảnh: {str(e)}")

    def _update_preview_buttons(self, is_previewing: bool):
        """
        Cập nhật trạng thái nút xem trước.
        """
        try:
            if self.ui_controls["start_preview_btn"]:
                self.ui_controls["start_preview_btn"].setEnabled(not is_previewing)

            if self.ui_controls["stop_preview_btn"]:
                self.ui_controls["stop_preview_btn"].setEnabled(is_previewing)

        except Exception as e:
            self.logger.error(f"Cập nhật trạng thái nút xem trước thất bại: {e}", exc_info=True)

    def _show_preview_error(self, message: str):
        """
        Hiển thị thông báo lỗi trong khu vực xem trước.
        """
        try:
            if self.ui_controls["preview_label"]:
                self.ui_controls["preview_label"].setText(f"Lỗi xem trước:\n{message}")
                self.ui_controls["preview_label"].setPixmap(QPixmap())
        except Exception as e:
            self.logger.error(f"Hiển thị lỗi xem trước thất bại: {e}", exc_info=True)

    def _cleanup_camera(self):
        """
        Dọn dẹp tài nguyên camera.
        """
        try:
            if self.camera:
                self.camera.release()
                self.camera = None
        except Exception as e:
            self.logger.error(f"Dọn dẹp tài nguyên camera thất bại: {e}", exc_info=True)

    def closeEvent(self, event):
        """
        Dọn dẹp tài nguyên khi thành phần đóng.
        """
        try:
            self._stop_preview()
        except Exception as e:
            self.logger.error(f"Đóng thành phần camera thất bại: {e}", exc_info=True)
        super().closeEvent(event)
