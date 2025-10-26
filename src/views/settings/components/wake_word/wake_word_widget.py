from pathlib import Path

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QWidget,
)

from src.utils.config_manager import ConfigManager
from src.utils.logging_config import get_logger
from src.utils.resource_finder import get_project_root, resource_finder

# Import thư viện chuyển đổi pinyin
try:
    from pypinyin import lazy_pinyin, Style
    PYPINYIN_AVAILABLE = True
except ImportError:
    PYPINYIN_AVAILABLE = False


class WakeWordWidget(QWidget):
    """
    Component cài đặt từ đánh thức.
    """

    # Định nghĩa signal
    settings_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = get_logger(__name__)
        self.config_manager = ConfigManager.get_instance()

        # Tham chiếu điều khiển UI
        self.ui_controls = {}

        # Bảng thanh mẫu (dùng để phân tách pinyin)
        self.initials = [
            'b', 'p', 'm', 'f', 'd', 't', 'n', 'l',
            'g', 'k', 'h', 'j', 'q', 'x',
            'zh', 'ch', 'sh', 'r', 'z', 'c', 's', 'y', 'w'
        ]

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

            ui_path = Path(__file__).parent / "wake_word_widget.ui"
            uic.loadUi(str(ui_path), self)

            # Lấy tham chiếu điều khiển UI
            self._get_ui_controls()

        except Exception as e:
            self.logger.error(f"Thiết lập UI từ đánh thức thất bại: {e}", exc_info=True)
            raise

    def _get_ui_controls(self):
        """
        Lấy tham chiếu điều khiển UI.
        """
        self.ui_controls.update(
            {
                "use_wake_word_check": self.findChild(QCheckBox, "use_wake_word_check"),
                "model_path_edit": self.findChild(QLineEdit, "model_path_edit"),
                "model_path_btn": self.findChild(QPushButton, "model_path_btn"),
                "wake_words_edit": self.findChild(QTextEdit, "wake_words_edit"),
            }
        )

    def _connect_events(self):
        """
        Kết nối xử lý sự kiện.
        """
        if self.ui_controls["use_wake_word_check"]:
            self.ui_controls["use_wake_word_check"].toggled.connect(
                self.settings_changed.emit
            )

        if self.ui_controls["model_path_edit"]:
            self.ui_controls["model_path_edit"].textChanged.connect(
                self.settings_changed.emit
            )

        if self.ui_controls["model_path_btn"]:
            self.ui_controls["model_path_btn"].clicked.connect(
                self._on_model_path_browse
            )

        if self.ui_controls["wake_words_edit"]:
            self.ui_controls["wake_words_edit"].textChanged.connect(
                self.settings_changed.emit
            )

    def _load_config_values(self):
        """
        Tải giá trị từ file cấu hình vào điều khiển UI.
        """
        try:
            # Cấu hình từ đánh thức
            use_wake_word = self.config_manager.get_config(
                "WAKE_WORD_OPTIONS.USE_WAKE_WORD", False
            )
            if self.ui_controls["use_wake_word_check"]:
                self.ui_controls["use_wake_word_check"].setChecked(use_wake_word)

            model_path = self.config_manager.get_config(
                "WAKE_WORD_OPTIONS.MODEL_PATH", ""
            )
            self._set_text_value("model_path_edit", model_path)

            # Đọc từ đánh thức từ file keywords.txt
            wake_words_text = self._load_keywords_from_file()
            if self.ui_controls["wake_words_edit"]:
                self.ui_controls["wake_words_edit"].setPlainText(wake_words_text)

        except Exception as e:
            self.logger.error(f"Tải giá trị cấu hình từ đánh thức thất bại: {e}", exc_info=True)

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

    def _on_model_path_browse(self):
        """
        Duyệt đường dẫn mô hình.
        """
        try:
            current_path = self._get_text_value("model_path_edit")
            if not current_path:
                # Sử dụng resource_finder để tìm thư mục models mặc định
                models_dir = resource_finder.find_models_dir()
                if models_dir:
                    current_path = str(models_dir)
                else:
                    # Nếu không tìm thấy, sử dụng thư mục models trong thư mục gốc dự án
                    project_root = resource_finder.get_project_root()
                    current_path = str(project_root / "models")

            selected_path = QFileDialog.getExistingDirectory(
                self, "Chọn thư mục mô hình", current_path
            )

            if selected_path:
                # Chuyển đổi sang đường dẫn tương đối (nếu áp dụng)
                relative_path = self._convert_to_relative_path(selected_path)
                self._set_text_value("model_path_edit", relative_path)
                self.logger.info(
                    f"Đã chọn đường dẫn mô hình: {selected_path}, lưu trữ dưới dạng: {relative_path}"
                )

        except Exception as e:
            self.logger.error(f"Duyệt đường dẫn mô hình thất bại: {e}", exc_info=True)
            QMessageBox.warning(self, "Lỗi", f"Xảy ra lỗi khi duyệt đường dẫn mô hình: {str(e)}")

    def _convert_to_relative_path(self, model_path: str) -> str:
        """
        Chuyển đổi đường dẫn tuyệt đối sang đường dẫn tương đối so với thư mục gốc dự án (nếu cùng ổ đĩa).
        """
        try:
            import os

            # Lấy thư mục gốc dự án
            project_root = get_project_root()

            # Kiểm tra có cùng ổ đĩa không (chỉ áp dụng trên Windows)
            if os.name == "nt":  # Hệ thống Windows
                model_path_drive = os.path.splitdrive(model_path)[0]
                project_root_drive = os.path.splitdrive(str(project_root))[0]

                # Nếu cùng ổ đĩa, tính đường dẫn tương đối
                if model_path_drive.lower() == project_root_drive.lower():
                    relative_path = os.path.relpath(model_path, project_root)
                    return relative_path
                else:
                    # Không cùng ổ đĩa, sử dụng đường dẫn tuyệt đối
                    return model_path
            else:
                # Hệ thống không phải Windows, tính trực tiếp đường dẫn tương đối
                try:
                    relative_path = os.path.relpath(model_path, project_root)
                    # Chỉ sử dụng đường dẫn tương đối khi không chứa ".."+os.sep
                    if not relative_path.startswith(
                        ".." + os.sep
                    ) and not relative_path.startswith("/"):
                        return relative_path
                    else:
                        # Đường dẫn tương đối chứa tìm kiếm lên trên, sử dụng đường dẫn tuyệt đối
                        return model_path
                except ValueError:
                    # Không thể tính đường dẫn tương đối (khác volume), sử dụng đường dẫn tuyệt đối
                    return model_path
        except Exception as e:
            self.logger.warning(f"Lỗi khi tính đường dẫn tương đối, sử dụng đường dẫn gốc: {e}")
            return model_path

    def _load_keywords_from_file(self) -> str:
        """
        Tải từ đánh thức từ file keywords.txt, chỉ hiển thị phần tiếng Trung.
        """
        try:
            # Lấy đường dẫn mô hình đã cấu hình
            model_path = self.config_manager.get_config(
                "WAKE_WORD_OPTIONS.MODEL_PATH", "models"
            )

            # Sử dụng resource_finder để tìm kiếm thống nhất (giữ nhất quán với runtime)
            model_dir = resource_finder.find_directory(model_path)

            if model_dir is None:
                self.logger.warning(f"Thư mục mô hình không tồn tại: {model_path}")
                return ""

            keywords_file = model_dir / "keywords.txt"

            if not keywords_file.exists():
                self.logger.warning(f"File từ khóa không tồn tại: {keywords_file}")
                return ""

            keywords = []
            with open(keywords_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and "@" in line and not line.startswith("#"):
                        # Chỉ trích xuất phần tiếng Trung sau @ để hiển thị
                        chinese_part = line.split("@", 1)[1].strip()
                        keywords.append(chinese_part)

            return "\n".join(keywords)

        except Exception as e:
            self.logger.error(f"Đọc file từ khóa thất bại: {e}")
            return ""

    def _split_pinyin(self, pinyin: str) -> list:
        """
        Phân tách pinyin theo thanh mẫu và vận mẫu.

        Ví dụ: "xiǎo" -> ["x", "iǎo"]
              "mǐ" -> ["m", "ǐ"]
        """
        if not pinyin:
            return []

        # Ưu tiên độ dài để thử khớp thanh mẫu (zh, ch, sh ưu tiên)
        for initial in sorted(self.initials, key=len, reverse=True):
            if pinyin.startswith(initial):
                final = pinyin[len(initial):]
                if final:
                    return [initial, final]
                else:
                    return [initial]

        # Không có thanh mẫu (thanh mẫu zero)
        return [pinyin]

    def _chinese_to_keyword_format(self, chinese_text: str) -> str:
        """
        Chuyển đổi tiếng Trung sang định dạng keyword.

        Args:
            chinese_text: Văn bản tiếng Trung, ví dụ "小米小米"

        Returns:
            Định dạng keyword, ví dụ "x iǎo m ǐ x iǎo m ǐ @小米小米"
        """
        if not PYPINYIN_AVAILABLE:
            self.logger.error("Thư viện pypinyin chưa được cài đặt, không thể tự động chuyển đổi")
            return f"# Chuyển đổi thất bại (thiếu pypinyin) - {chinese_text}"

        try:
            # Chuyển đổi sang pinyin có dấu thanh
            pinyin_list = lazy_pinyin(chinese_text, style=Style.TONE)

            # Phân tách từng pinyin
            split_parts = []
            for pinyin in pinyin_list:
                parts = self._split_pinyin(pinyin)
                split_parts.extend(parts)

            # Nối kết quả
            pinyin_str = " ".join(split_parts)
            keyword_line = f"{pinyin_str} @{chinese_text}"

            return keyword_line

        except Exception as e:
            self.logger.error(f"Chuyển đổi pinyin thất bại: {e}")
            return f"# Chuyển đổi thất bại - {chinese_text}"

    def _save_keywords_to_file(self, keywords_text: str):
        """
        Lưu từ đánh thức vào file keywords.txt, tự động chuyển đổi tiếng Trung sang định dạng pinyin.
        """
        try:
            # Kiểm tra pypinyin có khả dụng không
            if not PYPINYIN_AVAILABLE:
                QMessageBox.warning(
                    self,
                    "Thiếu phụ thuộc",
                    "Chức năng tự động chuyển đổi pinyin cần cài đặt thư viện pypinyin\n\n"
                    "Vui lòng chạy: pip install pypinyin",
                )
                return

            # Lấy đường dẫn mô hình đã cấu hình
            model_path = self.config_manager.get_config(
                "WAKE_WORD_OPTIONS.MODEL_PATH", "models"
            )

            # Sử dụng resource_finder để tìm kiếm thống nhất (giữ nhất quán với runtime)
            model_dir = resource_finder.find_directory(model_path)

            if model_dir is None:
                self.logger.error(f"Thư mục mô hình không tồn tại: {model_path}")
                QMessageBox.warning(
                    self,
                    "Lỗi",
                    f"Thư mục mô hình không tồn tại: {model_path}\nVui lòng cấu hình đường dẫn mô hình chính xác trước.",
                )
                return

            keywords_file = model_dir / "keywords.txt"

            # Xử lý văn bản từ khóa đầu vào (mỗi dòng một từ tiếng Trung)
            lines = [line.strip() for line in keywords_text.split("\n") if line.strip()]

            processed_lines = []
            for chinese_text in lines:
                # Tự động chuyển đổi sang định dạng pinyin
                keyword_line = self._chinese_to_keyword_format(chinese_text)
                processed_lines.append(keyword_line)

            # Ghi vào file
            with open(keywords_file, "w", encoding="utf-8") as f:
                f.write("\n".join(processed_lines) + "\n")

            self.logger.info(f"Lưu thành công {len(processed_lines)} từ khóa vào {keywords_file}")
            QMessageBox.information(
                self,
                "Lưu thành công",
                f"Lưu thành công {len(processed_lines)} từ đánh thức\n\n"
                f"Đã tự động chuyển đổi sang định dạng pinyin",
            )

        except Exception as e:
            self.logger.error(f"Lưu file từ khóa thất bại: {e}")
            QMessageBox.warning(self, "Lỗi", f"Lưu từ khóa thất bại: {str(e)}")

    def get_config_data(self) -> dict:
        """
        Lấy dữ liệu cấu hình hiện tại.
        """
        config_data = {}

        try:
            # Cấu hình từ đánh thức
            if self.ui_controls["use_wake_word_check"]:
                use_wake_word = self.ui_controls["use_wake_word_check"].isChecked()
                config_data["WAKE_WORD_OPTIONS.USE_WAKE_WORD"] = use_wake_word

            model_path = self._get_text_value("model_path_edit")
            if model_path:
                # Chuyển đổi sang đường dẫn tương đối (nếu áp dụng)
                relative_path = self._convert_to_relative_path(model_path)
                config_data["WAKE_WORD_OPTIONS.MODEL_PATH"] = relative_path

        except Exception as e:
            self.logger.error(f"Lấy dữ liệu cấu hình từ đánh thức thất bại: {e}", exc_info=True)

        return config_data

    def save_keywords(self):
        """
        Lưu từ đánh thức vào file.
        """
        if self.ui_controls["wake_words_edit"]:
            wake_words_text = self.ui_controls["wake_words_edit"].toPlainText().strip()
            self._save_keywords_to_file(wake_words_text)

    def reset_to_defaults(self):
        """
        Đặt lại về giá trị mặc định.
        """
        try:
            # Lấy cấu hình mặc định
            default_config = ConfigManager.DEFAULT_CONFIG

            # Cấu hình từ đánh thức
            wake_word_config = default_config["WAKE_WORD_OPTIONS"]
            if self.ui_controls["use_wake_word_check"]:
                self.ui_controls["use_wake_word_check"].setChecked(
                    wake_word_config["USE_WAKE_WORD"]
                )

            self._set_text_value("model_path_edit", wake_word_config["MODEL_PATH"])

            if self.ui_controls["wake_words_edit"]:
                # Sử dụng từ khóa mặc định để reset
                default_keywords = self._get_default_keywords()
                self.ui_controls["wake_words_edit"].setPlainText(default_keywords)

            self.logger.info("Cấu hình từ đánh thức đã được đặt lại về giá trị mặc định")

        except Exception as e:
            self.logger.error(f"Đặt lại cấu hình từ đánh thức thất bại: {e}", exc_info=True)

    def _get_default_keywords(self) -> str:
        """
        Lấy danh sách từ khóa mặc định, chỉ trả về tiếng Trung.
        """
        default_keywords = [
            "小爱同学",
            "你好问问",
            "小艺小艺",
            "小米小米",
            "你好小智",
            "贾维斯",
        ]
        return "\n".join(default_keywords)
