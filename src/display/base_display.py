from abc import ABC, abstractmethod
from typing import Callable, Optional

from src.utils.logging_config import get_logger


class BaseDisplay(ABC):
    """
    Lớp cơ sở trừu tượng cho giao diện hiển thị.
    """

    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)

    @abstractmethod
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

    @abstractmethod
    async def update_button_status(self, text: str):
        """
        Cập nhật trạng thái nút.
        """

    @abstractmethod
    async def update_status(self, status: str, connected: bool):
        """
        Cập nhật văn bản trạng thái.
        """

    @abstractmethod
    async def update_text(self, text: str):
        """
        Cập nhật văn bản TTS.
        """

    @abstractmethod
    async def update_emotion(self, emotion_name: str):
        """
        Cập nhật biểu cảm.
        """

    @abstractmethod
    async def start(self):
        """
        Khởi động hiển thị.
        """

    @abstractmethod
    async def close(self):
        """
        Đóng hiển thị.
        """
