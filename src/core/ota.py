import asyncio
import json
import socket
import ssl

import aiohttp

from src.constants.system import SystemConstants
from src.utils.config_manager import ConfigManager
from src.utils.device_fingerprint import DeviceFingerprint
from src.utils.logging_config import get_logger


class Ota:
    _instance = None
    _lock = asyncio.Lock()

    def __init__(self):
        self.logger = get_logger(__name__)
        self.config = ConfigManager.get_instance()
        self.device_fingerprint = DeviceFingerprint.get_instance()
        self.mac_addr = None
        self.ota_version_url = None
        self.local_ip = None
        self.system_info = None

    @classmethod
    async def get_instance(cls):
        if cls._instance is None:
            async with cls._lock:
                if cls._instance is None:
                    instance = cls()
                    await instance.init()
                    cls._instance = instance
        return cls._instance

    async def init(self):
        """
        Khởi tạo thể hiện OTA.
        """
        self.local_ip = await self.get_local_ip()
        # Lấy ID thiết bị (địa chỉ MAC) từ cấu hình
        self.mac_addr = self.config.get_config("SYSTEM_OPTIONS.DEVICE_ID")
        # Lấy URL OTA
        self.ota_version_url = self.config.get_config(
            "SYSTEM_OPTIONS.NETWORK.OTA_VERSION_URL"
        )

    async def get_local_ip(self):
        """
        Lấy địa chỉ IP của máy một cách bất đồng bộ.
        """
        try:
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(None, self._sync_get_ip)
        except Exception as e:
            self.logger.error(f"Không thể lấy IP của máy: {e}")
            return "127.0.0.1"

    def _sync_get_ip(self):
        """
        Lấy địa chỉ IP của máy một cách đồng bộ.
        """
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]

    def build_payload(self):
        """
        Xây dựng payload cho yêu cầu OTA.
        """
        # Lấy hmac_key từ efuse.json làm elf_sha256
        hmac_key = self.device_fingerprint.get_hmac_key()
        elf_sha256 = hmac_key if hmac_key else "unknown"

        return {
            "application": {
                "version": SystemConstants.APP_VERSION,
                "elf_sha256": elf_sha256,
            },
            "board": {
                "type": SystemConstants.BOARD_TYPE,
                "name": SystemConstants.APP_NAME,
                "ip": self.local_ip,
                "mac": self.mac_addr,
            },
        }

    def build_headers(self):
        """
        Xây dựng headers cho yêu cầu OTA.
        """
        app_version = SystemConstants.APP_VERSION
        board_type = SystemConstants.BOARD_TYPE
        app_name = SystemConstants.APP_NAME

        # Headers cơ bản
        headers = {
            "Device-Id": self.mac_addr,
            "Client-Id": self.config.get_config("SYSTEM_OPTIONS.CLIENT_ID"),
            "Content-Type": "application/json",
            "User-Agent": f"{board_type}/{app_name}-{app_version}",
            "Accept-Language": "zh-CN",
        }

        # Thêm header Activation-Version dựa trên phiên bản kích hoạt
        activation_version = self.config.get_config(
            "SYSTEM_OPTIONS.NETWORK.ACTIVATION_VERSION", "v1"
        )

        # Chỉ thêm header Activation-Version cho giao thức v2
        if activation_version == "v2":
            headers["Activation-Version"] = app_version
            self.logger.debug(f"Giao thức v2: Thêm header Activation-Version: {app_version}")
        else:
            self.logger.debug("Giao thức v1: Không thêm header Activation-Version")

        return headers

    async def get_ota_config(self):
        """
        Lấy thông tin cấu hình từ máy chủ OTA (MQTT, WebSocket, v.v.)
        """
        if not self.mac_addr:
            self.logger.error("ID thiết bị (địa chỉ MAC) chưa được cấu hình")
            raise ValueError("ID thiết bị chưa được cấu hình")

        if not self.ota_version_url:
            self.logger.error("URL OTA chưa được cấu hình")
            raise ValueError("URL OTA chưa được cấu hình")

        headers = self.build_headers()
        payload = self.build_payload()

        try:
            # Vô hiệu hóa xác thực SSL để hỗ trợ chứng chỉ tự ký
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE

            # Sử dụng aiohttp để gửi yêu cầu một cách bất đồng bộ
            timeout = aiohttp.ClientTimeout(total=10)
            connector = aiohttp.TCPConnector(ssl=ssl_context)
            async with aiohttp.ClientSession(
                timeout=timeout, connector=connector
            ) as session:
                async with session.post(
                    self.ota_version_url, headers=headers, json=payload
                ) as response:
                    # Kiểm tra mã trạng thái HTTP
                    if response.status != 200:
                        self.logger.error(f"Lỗi từ máy chủ OTA: HTTP {response.status}")
                        raise ValueError(f"Máy chủ OTA trả về mã trạng thái lỗi: {response.status}")

                    # Phân tích dữ liệu JSON
                    response_data = await response.json()

                    # Thông tin gỡ lỗi: in toàn bộ phản hồi OTA
                    self.logger.debug(
                        f"Dữ liệu trả về từ máy chủ OTA: "
                        f"{json.dumps(response_data, indent=4, ensure_ascii=False)}"
                    )

                    return response_data

        except asyncio.TimeoutError:
            self.logger.error("Yêu cầu OTA đã hết thời gian, vui lòng kiểm tra mạng hoặc trạng thái máy chủ")
            raise ValueError("Yêu cầu OTA đã hết thời gian! Vui lòng thử lại sau.")

        except aiohttp.ClientError as e:
            self.logger.error(f"Yêu cầu OTA thất bại: {e}")
            raise ValueError("Không thể kết nối đến máy chủ OTA, vui lòng kiểm tra kết nối mạng!")

    async def update_mqtt_config(self, response_data):
        """
        Cập nhật thông tin cấu hình MQTT.
        """
        if "mqtt" in response_data:
            self.logger.info("Đã tìm thấy thông tin cấu hình MQTT")
            mqtt_info = response_data["mqtt"]
            if mqtt_info:
                # Cập nhật cấu hình
                success = self.config.update_config(
                    "SYSTEM_OPTIONS.NETWORK.MQTT_INFO", mqtt_info
                )
                if success:
                    self.logger.info("Cấu hình MQTT đã được cập nhật")
                    return mqtt_info
                else:
                    self.logger.error("Cập nhật cấu hình MQTT thất bại")
            else:
                self.logger.warning("Cấu hình MQTT trống")
        else:
            self.logger.info("Không tìm thấy thông tin cấu hình MQTT")

        return None

    async def update_websocket_config(self, response_data):
        """
        Cập nhật thông tin cấu hình WebSocket.
        """
        if "websocket" in response_data:
            self.logger.info("Đã tìm thấy thông tin cấu hình WebSocket")
            websocket_info = response_data["websocket"]

            # Cập nhật URL WebSocket
            if "url" in websocket_info:
                self.config.update_config(
                    "SYSTEM_OPTIONS.NETWORK.WEBSOCKET_URL", websocket_info["url"]
                )
                self.logger.info(f"URL WebSocket đã được cập nhật: {websocket_info['url']}")

            # Cập nhật Token WebSocket
            token_value = websocket_info.get("token", "test-token") or "test-token"
            self.config.update_config(
                "SYSTEM_OPTIONS.NETWORK.WEBSOCKET_ACCESS_TOKEN", token_value
            )
            self.logger.info("Token WebSocket đã được cập nhật")

            return websocket_info
        else:
            self.logger.info("Không tìm thấy thông tin cấu hình WebSocket")

        return None

    async def fetch_and_update_config(self):
        """
        Lấy và cập nhật tất cả thông tin cấu hình.
        """
        try:
            # Lấy cấu hình OTA
            response_data = await self.get_ota_config()

            # Cập nhật cấu hình MQTT
            mqtt_config = await self.update_mqtt_config(response_data)

            # Cập nhật cấu hình WebSocket
            websocket_config = await self.update_websocket_config(response_data)

            # Trả về dữ liệu phản hồi hoàn chỉnh, phục vụ cho quy trình kích hoạt
            return {
                "response_data": response_data,
                "mqtt_config": mqtt_config,
                "websocket_config": websocket_config,
            }

        except Exception as e:
            self.logger.error(f"Không thể lấy và cập nhật cấu hình: {e}")
            raise
