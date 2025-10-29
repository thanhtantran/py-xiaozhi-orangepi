# -*- coding: utf-8 -*-
"""
Mô hình dữ liệu kích hoạt cửa sổ - Dùng để liên kết dữ liệu QML
"""

from PyQt5.QtCore import QObject, pyqtProperty, pyqtSignal


class ActivationModel(QObject):
    """
    Mô hình dữ liệu kích hoạt cửa sổ, dùng để liên kết dữ liệu giữa Python và QML.
    """

    # Tín hiệu thay đổi thuộc tính
    serialNumberChanged = pyqtSignal()
    macAddressChanged = pyqtSignal()
    activationStatusChanged = pyqtSignal()
    activationCodeChanged = pyqtSignal()
    statusColorChanged = pyqtSignal()

    # Tín hiệu thao tác của người dùng
    copyCodeClicked = pyqtSignal()
    retryClicked = pyqtSignal()
    closeClicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

        # Thuộc tính riêng
        self._serial_number = "--"
        self._mac_address = "--"
        self._activation_status = "Đang kiểm tra..."
        self._activation_code = "--"
        self._status_color = "#6c757d"

    # Thuộc tính số sê-ri
    @pyqtProperty(str, notify=serialNumberChanged)
    def serialNumber(self):
        return self._serial_number

    @serialNumber.setter
    def serialNumber(self, value):
        if self._serial_number != value:
            self._serial_number = value
            self.serialNumberChanged.emit()

    # Thuộc tính địa chỉ MAC
    @pyqtProperty(str, notify=macAddressChanged)
    def macAddress(self):
        return self._mac_address

    @macAddress.setter
    def macAddress(self, value):
        if self._mac_address != value:
            self._mac_address = value
            self.macAddressChanged.emit()

    # Thuộc tính trạng thái kích hoạt
    @pyqtProperty(str, notify=activationStatusChanged)
    def activationStatus(self):
        return self._activation_status

    @activationStatus.setter
    def activationStatus(self, value):
        if self._activation_status != value:
            self._activation_status = value
            self.activationStatusChanged.emit()

    # Thuộc tính mã kích hoạt
    @pyqtProperty(str, notify=activationCodeChanged)
    def activationCode(self):
        return self._activation_code

    @activationCode.setter
    def activationCode(self, value):
        if self._activation_code != value:
            self._activation_code = value
            self.activationCodeChanged.emit()

    # Thuộc tính màu trạng thái
    @pyqtProperty(str, notify=statusColorChanged)
    def statusColor(self):
        return self._status_color

    @statusColor.setter
    def statusColor(self, value):
        if self._status_color != value:
            self._status_color = value
            self.statusColorChanged.emit()

    # Phương thức tiện lợi
    def update_device_info(self, serial_number=None, mac_address=None):
        """
        Cập nhật thông tin thiết bị.
        """
        if serial_number is not None:
            self.serialNumber = serial_number
        if mac_address is not None:
            self.macAddress = mac_address

    def update_activation_status(self, status, color="#6c757d"):
        """
        Cập nhật trạng thái kích hoạt.
        """
        self.activationStatus = status
        self.statusColor = color

    def update_activation_code(self, code):
        """
        Cập nhật mã kích hoạt.
        """
        self.activationCode = code

    def reset_activation_code(self):
        """
        Đặt lại mã kích hoạt.
        """
        self.activationCode = "--"

    def set_status_activated(self):
        """
        Đặt trạng thái thành đã kích hoạt.
        """
        self.update_activation_status("Đã kích hoạt", "#28a745")
        self.reset_activation_code()

    def set_status_not_activated(self):
        """
        Đặt trạng thái thành chưa kích hoạt.
        """
        self.update_activation_status("Chưa kích hoạt", "#dc3545")

    def set_status_inconsistent(self, local_activated=False, server_activated=False):
        """
        Đặt trạng thái không nhất quán.
        """
        if local_activated and not server_activated:
            self.update_activation_status("Trạng thái không nhất quán (cần kích hoạt lại)", "#ff9900")
        else:
            self.update_activation_status("Trạng thái không nhất quán (đã sửa)", "#28a745")
