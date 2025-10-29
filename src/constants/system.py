# 系统常量定义
from enum import Enum


class InitializationStage(Enum):
    """
    De phan nay tieng Anh cho de hieu
    """

    DEVICE_FINGERPRINT = "Phase 1: Device Identity Preparation"
    CONFIG_MANAGEMENT = "Phase 2: Configuration Management Initialization"
    OTA_CONFIG = "Phase 3: OTA Configuration Acquisition"
    ACTIVATION = "Phase 4: Activation Process"


class SystemConstants:
    """
   System constants.
    """

    # 应用信息
    APP_NAME = "py-xiaozhi"
    APP_VERSION = "2.0.0"
    BOARD_TYPE = "bread-compact-wifi"

    # 默认超时设置
    DEFAULT_TIMEOUT = 10
    ACTIVATION_MAX_RETRIES = 60
    ACTIVATION_RETRY_INTERVAL = 5

    # 文件名常量
    CONFIG_FILE = "config.json"
    EFUSE_FILE = "efuse.json"
