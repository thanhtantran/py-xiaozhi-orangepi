import threading
import time
from pathlib import Path

import numpy as np
import sounddevice as sd
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import (
    QComboBox,
    QLabel,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QWidget,
)

from src.utils.config_manager import ConfigManager
from src.utils.logging_config import get_logger


class AudioWidget(QWidget):
    """
    Thành phần cài đặt thiết bị âm thanh.
    """

    # Định nghĩa các tín hiệu
    settings_changed = pyqtSignal()
    status_message = pyqtSignal(str)
    reset_input_ui = pyqtSignal()
    reset_output_ui = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = get_logger(__name__)
        self.config_manager = ConfigManager.get_instance()

        # Tham chiếu điều khiển UI
        self.ui_controls = {}

        # Dữ liệu thiết bị
        self.input_devices = []
        self.output_devices = []

        # Trạng thái kiểm tra
        self.testing_input = False
        self.testing_output = False

        # Khởi tạo UI
        self._setup_ui()
        self._connect_events()
        self._scan_devices()
        self._load_config_values()

        # Kết nối tín hiệu cập nhật UI an toàn trong luồng
        try:
            self.status_message.connect(self._on_status_message)
            self.reset_input_ui.connect(self._reset_input_test_ui)
            self.reset_output_ui.connect(self._reset_output_test_ui)
        except Exception:
            pass

    def _setup_ui(self):
        """
        Thiết lập giao diện UI.
        """
        try:
            from PyQt5 import uic

            ui_path = Path(__file__).parent / "audio_widget.ui"
            uic.loadUi(str(ui_path), self)

            # Lấy tham chiếu điều khiển UI
            self._get_ui_controls()

        except Exception as e:
            self.logger.error(f"Thiết lập giao diện âm thanh thất bại: {e}", exc_info=True)
            raise

    def _get_ui_controls(self):
        """
        Lấy tham chiếu điều khiển UI.
        """
        self.ui_controls.update(
            {
                "input_device_combo": self.findChild(QComboBox, "input_device_combo"),
                "output_device_combo": self.findChild(QComboBox, "output_device_combo"),
                "input_info_label": self.findChild(QLabel, "input_info_label"),
                "output_info_label": self.findChild(QLabel, "output_info_label"),
                "test_input_btn": self.findChild(QPushButton, "test_input_btn"),
                "test_output_btn": self.findChild(QPushButton, "test_output_btn"),
                "scan_devices_btn": self.findChild(QPushButton, "scan_devices_btn"),
                "status_text": self.findChild(QTextEdit, "status_text"),
            }
        )

    def _connect_events(self):
        """
        Kết nối xử lý sự kiện.
        """
        # Sự kiện thay đổi thiết bị
        if self.ui_controls["input_device_combo"]:
            self.ui_controls["input_device_combo"].currentTextChanged.connect(
                self._on_input_device_changed
            )

        if self.ui_controls["output_device_combo"]:
            self.ui_controls["output_device_combo"].currentTextChanged.connect(
                self._on_output_device_changed
            )

        # Sự kiện nhấn nút
        if self.ui_controls["test_input_btn"]:
            self.ui_controls["test_input_btn"].clicked.connect(
                self._test_input_device
            )

        if self.ui_controls["test_output_btn"]:
            self.ui_controls["test_output_btn"].clicked.connect(
                self._test_output_device
            )

        if self.ui_controls["scan_devices_btn"]:
            self.ui_controls["scan_devices_btn"].clicked.connect(self._scan_devices)

    def _on_input_device_changed(self):
        """
        Sự kiện thay đổi thiết bị đầu vào.
        """
        self.settings_changed.emit()
        self._update_device_info()

    def _on_output_device_changed(self):
        """
        Sự kiện thay đổi thiết bị đầu ra.
        """
        self.settings_changed.emit()
        self._update_device_info()

    def _update_device_info(self):
        """
        Cập nhật hiển thị thông tin thiết bị.
        """
        try:
            # Cập nhật thông tin thiết bị đầu vào
            input_device_id = self.ui_controls["input_device_combo"].currentData()
            if input_device_id is not None:
                input_device = next(
                    (d for d in self.input_devices if d["id"] == input_device_id), None
                )
                if input_device:
                    info_text = f"Tần số mẫu: {int(input_device['sample_rate'])}Hz, Kênh: {input_device['channels']}"
                    self.ui_controls["input_info_label"].setText(info_text)
                else:
                    self.ui_controls["input_info_label"].setText("Không thể lấy thông tin thiết bị")
            else:
                self.ui_controls["input_info_label"].setText("Chưa chọn thiết bị")

            # Cập nhật thông tin thiết bị đầu ra
            output_device_id = self.ui_controls["output_device_combo"].currentData()
            if output_device_id is not None:
                output_device = next(
                    (d for d in self.output_devices if d["id"] == output_device_id),
                    None,
                )
                if output_device:
                    info_text = f"Tần số mẫu: {int(output_device['sample_rate'])}Hz, Kênh: {output_device['channels']}"
                    self.ui_controls["output_info_label"].setText(info_text)
                else:
                    self.ui_controls["output_info_label"].setText("Không thể lấy thông tin thiết bị")
            else:
                self.ui_controls["output_info_label"].setText("Chưa chọn thiết bị")

        except Exception as e:
            self.logger.error(f"Cập nhật thông tin thiết bị thất bại: {e}", exc_info=True)

    def _scan_devices(self):
        """
        Quét các thiết bị âm thanh.
        """
        try:
            self._append_status("Đang quét thiết bị âm thanh...")

            # Xóa danh sách thiết bị hiện tại
            self.input_devices.clear()
            self.output_devices.clear()

            # Lấy thiết bị mặc định của hệ thống
            default_input = sd.default.device[0] if sd.default.device else None
            default_output = sd.default.device[1] if sd.default.device else None

            # Quét tất cả thiết bị
            devices = sd.query_devices()
            for i, dev_info in enumerate(devices):
                device_name = dev_info["name"]

                # Thêm thiết bị đầu vào
                if dev_info["max_input_channels"] > 0:
                    default_mark = " (Mặc định)" if i == default_input else ""
                    self.input_devices.append(
                        {
                            "id": i,
                            "name": device_name + default_mark,
                            "raw_name": device_name,
                            "channels": dev_info["max_input_channels"],
                            "sample_rate": dev_info["default_samplerate"],
                        }
                    )

                # Thêm thiết bị đầu ra
                if dev_info["max_output_channels"] > 0:
                    default_mark = " (Mặc định)" if i == default_output else ""
                    self.output_devices.append(
                        {
                            "id": i,
                            "name": device_name + default_mark,
                            "raw_name": device_name,
                            "channels": dev_info["max_output_channels"],
                            "sample_rate": dev_info["default_samplerate"],
                        }
                    )

            # Cập nhật danh sách thiết bị trong combobox
            self._update_device_combos()

            # Tự động chọn thiết bị mặc định
            self._select_default_devices()

            self._append_status(
                f"Quét hoàn tất: Tìm thấy {len(self.input_devices)} thiết bị đầu vào, {len(self.output_devices)} thiết bị đầu ra"
            )

        except Exception as e:
            self.logger.error(f"Quét thiết bị âm thanh thất bại: {e}", exc_info=True)
            self._append_status(f"Quét thiết bị thất bại: {str(e)}")

    def _update_device_combos(self):
        """
        Cập nhật danh sách thiết bị trong combobox.
        """
        try:
            # Lưu lựa chọn hiện tại
            current_input = self.ui_controls["input_device_combo"].currentData()
            current_output = self.ui_controls["output_device_combo"].currentData()

            # Xóa và điền lại danh sách thiết bị đầu vào
            self.ui_controls["input_device_combo"].clear()
            for device in self.input_devices:
                self.ui_controls["input_device_combo"].addItem(
                    device["name"], device["id"]
                )

            # Xóa và điền lại danh sách thiết bị đầu ra
            self.ui_controls["output_device_combo"].clear()
            for device in self.output_devices:
                self.ui_controls["output_device_combo"].addItem(
                    device["name"], device["id"]
                )

            # Khôi phục lựa chọn trước đó
            if current_input is not None:
                index = self.ui_controls["input_device_combo"].findData(current_input)
                if index >= 0:
                    self.ui_controls["input_device_combo"].setCurrentIndex(index)

            if current_output is not None:
                index = self.ui_controls["output_device_combo"].findData(current_output)
                if index >= 0:
                    self.ui_controls["output_device_combo"].setCurrentIndex(index)

        except Exception as e:
            self.logger.error(f"Cập nhật danh sách thiết bị thất bại: {e}", exc_info=True)

    def _select_default_devices(self):
        """
        Tự động chọn thiết bị mặc định (giữ logic giống với audio_codec.py).
        """
        try:
            # Ưu tiên chọn thiết bị từ cấu hình, nếu không có thì chọn thiết bị mặc định của hệ thống
            config_input_id = self.config_manager.get_config(
                "AUDIO_DEVICES.input_device_id"
            )
            config_output_id = self.config_manager.get_config(
                "AUDIO_DEVICES.output_device_id"
            )

            # Chọn thiết bị đầu vào
            if config_input_id is not None:
                # Sử dụng thiết bị từ cấu hình
                index = self.ui_controls["input_device_combo"].findData(config_input_id)
                if index >= 0:
                    self.ui_controls["input_device_combo"].setCurrentIndex(index)
            else:
                # Tự động chọn thiết bị đầu vào mặc định (có đánh dấu "Mặc định")
                for i in range(self.ui_controls["input_device_combo"].count()):
                    if "Mặc định" in self.ui_controls["input_device_combo"].itemText(i):
                        self.ui_controls["input_device_combo"].setCurrentIndex(i)
                        break

            # Chọn thiết bị đầu ra
            if config_output_id is not None:
                # Sử dụng thiết bị từ cấu hình
                index = self.ui_controls["output_device_combo"].findData(config_output_id)
                if index >= 0:
                    self.ui_controls["output_device_combo"].setCurrentIndex(index)
            else:
                # Tự động chọn thiết bị đầu ra mặc định (có đánh dấu "Mặc định")
                for i in range(self.ui_controls["output_device_combo"].count()):
                    if "Mặc định" in self.ui_controls["output_device_combo"].itemText(i):
                        self.ui_controls["output_device_combo"].setCurrentIndex(i)
                        break

            # Cập nhật hiển thị thông tin thiết bị
            self._update_device_info()

        except Exception as e:
            self.logger.error(f"Chọn thiết bị mặc định thất bại: {e}", exc_info=True)

    def _test_input_device(self):
        """
        Kiểm tra thiết bị đầu vào.
        """
        if self.testing_input:
            return

        try:
            device_id = self.ui_controls["input_device_combo"].currentData()
            if device_id is None:
                QMessageBox.warning(self, "Thông báo", "Vui lòng chọn thiết bị đầu vào trước")
                return

            self.testing_input = True
            self.ui_controls["test_input_btn"].setEnabled(False)
            self.ui_controls["test_input_btn"].setText("Đang ghi âm...")

            # Thực hiện kiểm tra trong luồng
            test_thread = threading.Thread(
                target=self._do_input_test, args=(device_id,)
            )
            test_thread.daemon = True
            test_thread.start()

        except Exception as e:
            self.logger.error(f"Kiểm tra thiết bị đầu vào thất bại: {e}", exc_info=True)
            self._append_status(f"Kiểm tra thiết bị đầu vào thất bại: {str(e)}")
            self._reset_input_test_ui()

    def _do_input_test(self, device_id):
        """
        Thực hiện kiểm tra thiết bị đầu vào.
        """
        try:
            # Lấy thông tin thiết bị và tần số mẫu
            input_device = next(
                (d for d in self.input_devices if d["id"] == device_id), None
            )
            if not input_device:
                self._append_status_threadsafe("Lỗi: Không thể lấy thông tin thiết bị")
                return

            sample_rate = int(input_device["sample_rate"])
            duration = 3  # Thời gian ghi âm là 3 giây

            self._append_status_threadsafe(
                f"Bắt đầu kiểm tra ghi âm (Thiết bị: {device_id}, Tần số mẫu: {sample_rate}Hz)"
            )
            self._append_status_threadsafe("Hãy nói vào micro, ví dụ: 1, 2, 3...")

            # Đếm ngược trước khi ghi âm
            for i in range(3, 0, -1):
                self._append_status_threadsafe(f"Bắt đầu ghi âm sau {i} giây...")
                time.sleep(1)

            self._append_status_threadsafe("Đang ghi âm, vui lòng nói... (3 giây)")

            # Ghi âm
            recording = sd.rec(
                int(duration * sample_rate),
                samplerate=sample_rate,
                channels=1,
                device=device_id,
                dtype=np.float32,
            )
            sd.wait()

            self._append_status_threadsafe("Ghi âm hoàn tất, đang phân tích...")

            # Phân tích chất lượng ghi âm
            max_amplitude = np.max(np.abs(recording))
            rms = np.sqrt(np.mean(recording**2))

            # Kiểm tra hoạt động âm thanh
            frame_length = int(0.1 * sample_rate)  # Khung 100ms
            frames = []
            for i in range(0, len(recording) - frame_length, frame_length):
                frame_rms = np.sqrt(np.mean(recording[i : i + frame_length] ** 2))
                frames.append(frame_rms)

            active_frames = sum(1 for f in frames if f > 0.01)  # Số khung có hoạt động
            activity_ratio = active_frames / len(frames) if frames else 0

            # Phân tích kết quả kiểm tra
            if max_amplitude < 0.001:
                self._append_status_threadsafe("[Thất bại] Không phát hiện tín hiệu âm thanh")
                self._append_status_threadsafe(
                    "Hãy kiểm tra: 1) Kết nối micro 2) Âm lượng hệ thống 3) Quyền truy cập micro"
                )
            elif max_amplitude > 0.8:
                self._append_status_threadsafe("[Cảnh báo] Tín hiệu âm thanh quá tải")
                self._append_status_threadsafe("Hãy giảm độ nhạy hoặc âm lượng của micro")
            elif activity_ratio < 0.1:
                self._append_status_threadsafe("[Cảnh báo] Phát hiện âm thanh nhưng hoạt động giọng nói thấp")
                self._append_status_threadsafe(
                    "Hãy nói vào micro hoặc kiểm tra độ nhạy của micro"
                )
            else:
                self._append_status_threadsafe("[Thành công] Kiểm tra ghi âm thành công")
                self._append_status_threadsafe(
                    f"Dữ liệu âm thanh: Âm lượng tối đa={max_amplitude:.1%}, Âm lượng trung bình={rms:.1%}, Hoạt động={activity_ratio:.1%}"
                )
                self._append_status_threadsafe("Micro hoạt động bình thường")

        except Exception as e:
            self.logger.error(f"Kiểm tra ghi âm thất bại: {e}", exc_info=True)
            self._append_status_threadsafe(f"[Lỗi] Kiểm tra ghi âm thất bại: {str(e)}")
            if "Permission denied" in str(e) or "access" in str(e).lower():
                self._append_status_threadsafe(
                    "Có thể do vấn đề quyền, hãy kiểm tra quyền truy cập micro của hệ thống"
                )
        finally:
            # Đặt lại trạng thái UI (quay về luồng chính)
            self._reset_input_ui_threadsafe()

    def _test_output_device(self):
        """
        Kiểm tra thiết bị đầu ra.
        """
        if self.testing_output:
            return

        try:
            device_id = self.ui_controls["output_device_combo"].currentData()
            if device_id is None:
                QMessageBox.warning(self, "Thông báo", "Vui lòng chọn thiết bị đầu ra trước")
                return

            self.testing_output = True
            self.ui_controls["test_output_btn"].setEnabled(False)
            self.ui_controls["test_output_btn"].setText("Đang phát...")

            # Thực hiện kiểm tra trong luồng
            test_thread = threading.Thread(
                target=self._do_output_test, args=(device_id,)
            )
            test_thread.daemon = True
            test_thread.start()

        except Exception as e:
            self.logger.error(f"Kiểm tra thiết bị đầu ra thất bại: {e}", exc_info=True)
            self._append_status(f"Kiểm tra thiết bị đầu ra thất bại: {str(e)}")
            self._reset_output_test_ui()

    def _do_output_test(self, device_id):
        """
        Thực hiện kiểm tra thiết bị đầu ra.
        """
        try:
            # Lấy thông tin thiết bị và tần số mẫu
            output_device = next(
                (d for d in self.output_devices if d["id"] == device_id), None
            )
            if not output_device:
                self._append_status_threadsafe("Lỗi: Không thể lấy thông tin thiết bị")
                return

            sample_rate = int(output_device["sample_rate"])
            duration = 2.0  # Thời gian phát âm thanh
            frequency = 440  # Âm A 440Hz

            self._append_status_threadsafe(
                f"Bắt đầu kiểm tra phát âm thanh (Thiết bị: {device_id}, Tần số mẫu: {sample_rate}Hz)"
            )
            self._append_status_threadsafe("Hãy chuẩn bị tai nghe/loa, sắp phát âm thanh kiểm tra...")

            # Đếm ngược trước khi phát âm thanh
            for i in range(3, 0, -1):
                self._append_status_threadsafe(f"Bắt đầu phát sau {i} giây...")
                time.sleep(1)

            self._append_status_threadsafe(
                f"Đang phát âm thanh kiểm tra {frequency}Hz ({duration} giây)..."
            )

            # Tạo âm thanh kiểm tra (sóng hình sin)
            t = np.linspace(0, duration, int(sample_rate * duration))
            # Thêm hiệu ứng mờ dần để tránh âm thanh bị đột ngột
            fade_samples = int(0.1 * sample_rate)  # Mờ dần trong 0.1 giây
            audio = 0.3 * np.sin(2 * np.pi * frequency * t)

            # Áp dụng hiệu ứng mờ dần
            audio[:fade_samples] *= np.linspace(0, 1, fade_samples)
            audio[-fade_samples:] *= np.linspace(1, 0, fade_samples)

            # Phát âm thanh
            sd.play(audio, samplerate=sample_rate, device=device_id)
            sd.wait()

            self._append_status_threadsafe("Phát âm thanh hoàn tất")
            self._append_status_threadsafe(
                "Hướng dẫn kiểm tra: Nếu nghe thấy âm thanh rõ ràng, tai nghe/loa đang hoạt động bình thường"
            )
            self._append_status_threadsafe(
                "Nếu không nghe thấy âm thanh, hãy kiểm tra cài đặt âm lượng hoặc chọn thiết bị đầu ra khác"
            )

        except Exception as e:
            self.logger.error(f"Kiểm tra phát âm thanh thất bại: {e}", exc_info=True)
            self._append_status_threadsafe(f"[Lỗi] Kiểm tra phát âm thanh thất bại: {str(e)}")
        finally:
            # Đặt lại trạng thái UI (quay về luồng chính)
            self._reset_output_ui_threadsafe()

    def _reset_input_test_ui(self):
        """
        Đặt lại trạng thái UI kiểm tra đầu vào.
        """
        self.testing_input = False
        self.ui_controls["test_input_btn"].setEnabled(True)
        self.ui_controls["test_input_btn"].setText("Kiểm tra ghi âm")

    def _reset_input_ui_threadsafe(self):
        """
        Đặt lại trạng thái UI kiểm tra đầu vào trong luồng an toàn.
        """
        try:
            self.reset_input_ui.emit()
        except Exception as e:
            self.logger.error(f"Đặt lại trạng thái UI kiểm tra đầu vào trong luồng an toàn thất bại: {e}")

    def _reset_output_test_ui(self):
        """
        Đặt lại trạng thái UI kiểm tra đầu ra.
        """
        self.testing_output = False
        self.ui_controls["test_output_btn"].setEnabled(True)
        self.ui_controls["test_output_btn"].setText("Kiểm tra phát âm thanh")

    def _reset_output_ui_threadsafe(self):
        """
        Đặt lại trạng thái UI kiểm tra đầu ra trong luồng an toàn.
        """
        try:
            self.reset_output_ui.emit()
        except Exception as e:
            self.logger.error(f"Đặt lại trạng thái UI kiểm tra đầu ra trong luồng an toàn thất bại: {e}")

    def _append_status(self, message):
        """
        Thêm thông tin trạng thái.
        """
        try:
            if self.ui_controls["status_text"]:
                current_time = time.strftime("%H:%M:%S")
                formatted_message = f"[{current_time}] {message}"
                self.ui_controls["status_text"].append(formatted_message)
                # Cuộn xuống cuối
                self.ui_controls["status_text"].verticalScrollBar().setValue(
                    self.ui_controls["status_text"].verticalScrollBar().maximum()
                )
        except Exception as e:
            self.logger.error(f"Thêm thông tin trạng thái thất bại: {e}", exc_info=True)

    def _append_status_threadsafe(self, message):
        """
        Thêm thông tin trạng thái vào QTextEdit trong luồng an toàn (qua tín hiệu quay về luồng chính).
        """
        try:
            if not self.ui_controls.get("status_text"):
                return
            current_time = time.strftime("%H:%M:%S")
            formatted_message = f"[{current_time}] {message}"
            self.status_message.emit(formatted_message)
        except Exception as e:
            self.logger.error(f"Thêm thông tin trạng thái trong luồng an toàn thất bại: {e}", exc_info=True)

    def _on_status_message(self, formatted_message: str):
        """
        Xử lý tín hiệu để thêm thông tin trạng thái vào QTextEdit.
        """
        try:
            if not self.ui_controls.get("status_text"):
                return
            self.ui_controls["status_text"].append(formatted_message)
            # Cuộn xuống cuối
            self.ui_controls["status_text"].verticalScrollBar().setValue(
                self.ui_controls["status_text"].verticalScrollBar().maximum()
            )
        except Exception as e:
            self.logger.error(f"Thêm trạng thái thất bại: {e}")

    def _load_config_values(self):
        """
        Tải giá trị từ file cấu hình vào các UI control.
        """
        try:
            # Lấy cấu hình thiết bị âm thanh
            audio_config = self.config_manager.get_config("AUDIO_DEVICES", {})

            # Cài đặt thiết bị đầu vào
            input_device_id = audio_config.get("input_device_id")
            if input_device_id is not None:
                index = self.ui_controls["input_device_combo"].findData(input_device_id)
                if index >= 0:
                    self.ui_controls["input_device_combo"].setCurrentIndex(index)

            # Cài đặt thiết bị đầu ra
            output_device_id = audio_config.get("output_device_id")
            if output_device_id is not None:
                index = self.ui_controls["output_device_combo"].findData(output_device_id)
                if index >= 0:
                    self.ui_controls["output_device_combo"].setCurrentIndex(index)

            # Thông tin thiết bị sẽ tự động cập nhật khi thay đổi lựa chọn, không cần cài đặt thủ công

        except Exception as e:
            self.logger.error(f"Tải giá trị cấu hình thiết bị âm thanh thất bại: {e}", exc_info=True)

    def get_config_data(self) -> dict:
        """
        Lấy dữ liệu cấu hình hiện tại.
        """
        config_data = {}

        try:
            audio_config = {}

            # Cấu hình thiết bị đầu vào
            input_device_id = self.ui_controls["input_device_combo"].currentData()
            if input_device_id is not None:
                audio_config["input_device_id"] = input_device_id
                audio_config["input_device_name"] = self.ui_controls[
                    "input_device_combo"
                ].currentText()

            # Cấu hình thiết bị đầu ra
            output_device_id = self.ui_controls["output_device_combo"].currentData()
            if output_device_id is not None:
                audio_config["output_device_id"] = output_device_id
                audio_config["output_device_name"] = self.ui_controls[
                    "output_device_combo"
                ].currentText()

            # Thông tin tần số mẫu của thiết bị được tự động xác định, không cần người dùng cấu hình
            # Lưu tần số mẫu mặc định của thiết bị để sử dụng sau này
            input_device = next(
                (d for d in self.input_devices if d["id"] == input_device_id), None
            )
            if input_device:
                audio_config["input_sample_rate"] = int(input_device["sample_rate"])

            output_device = next(
                (d for d in self.output_devices if d["id"] == output_device_id), None
            )
            if output_device:
                audio_config["output_sample_rate"] = int(output_device["sample_rate"])

            if audio_config:
                config_data["AUDIO_DEVICES"] = audio_config

        except Exception as e:
            self.logger.error(f"Lấy dữ liệu cấu hình thiết bị âm thanh thất bại: {e}", exc_info=True)

        return config_data

    def reset_to_defaults(self):
        """
        Đặt lại về giá trị mặc định.
        """
        try:
            # Quét lại thiết bị
            self._scan_devices()

            # Sau khi quét, thông tin tần số mẫu của thiết bị sẽ tự động hiển thị, không cần cài đặt thủ công

            # Xóa hiển thị trạng thái
            if self.ui_controls["status_text"]:
                self.ui_controls["status_text"].clear()

            self._append_status("Đã đặt lại về cài đặt mặc định")
            self.logger.info("Cấu hình thiết bị âm thanh đã được đặt lại về mặc định")

        except Exception as e:
            self.logger.error(f"Đặt lại cấu hình thiết bị âm thanh thất bại: {e}", exc_info=True)