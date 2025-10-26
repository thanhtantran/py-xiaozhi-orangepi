# py-xiaozhi cho thiết bị Orange Pi

[English](README-en.md) | Tiếng Việt

## Giới thiệu

- Bản chỉnh sửa Python-based Xiaozhi AI cho ai muốn thử nghiệm Xiaozhi AI trên các thiết bị Orange Pi, có thể chạy song song cùng các MCP Server.
- Bản chỉnh sửa này lấy gốc từ [py-xiaozhi](https://github.com/huangjunsen0406/py-xiaozhi), lược bỏ các phần không cần thiết chỉ để chạy trên Orange Pi.
- Nếu bạn cần một bản chạy trên tất cả các thiết bị PC, MAC, v.v. thì hãy dùng bản gốc.
- Phiên này này dùng GNU Lesser General Public License v2.1, nghĩa là nếu bạn sử dụng mã nguồn này, bạn chỉ được phép phân phối miễn phí cho người khác, mà không được bán.
- Nếu bạn thấy mã nguồn này hữu ích, hãy Star cho mã nguồn, và ghé qua [Orange Pi Việt Nam](https://orangepi.vn) mua hàng ủng hộ.

## Demo

- [Video hướng dẫn cài đặt](https://www.youtube.com) (Vietnames only)

## Các tính năng

- Các tính năng sẽ có giống y hệt như phiên bản gốc, và sẽ có cập nhật thêm các tính năng khác phù hợp với Orange Pi.
- Size QTwindow được mở to hơn để có một phiên bản Xiaozhi AI to hơn về cả hình và tiếng.
- Sẽ mở rộng thêm sử dụng NPU của Orange Pi để thay thế máy chủ xiaozhi.me

### Các thiết bị hỗ trợ

- Các phiên bản Orange Pi ARM64 có xuất hình ra HDMI như Orange Pi 3B, Orange Pi 4A, Orange Pi Zero3, Orange Pi 4 LTS, Orange Pi 5 ... đều dùng được
- Các phiên bản Pi khác như Raspberry Pi, Banana Pi, Rice Pi, ... cũng có thể dùng được, nhưng không chắc chắn, và tôi không hỗ trợ.

## Yêu cầu hệ thống

### Yêu cầu cơ bản

- **Python Version**: 3.9 - 3.12
- **Operating System**: Ubuntu / Debian
- **Audio Devices**: Microphone and speaker devices
- **Network Connection**: Internet ổn định (để kết nối đến Xiaozhi.me)

### Yêu cầu cấu hình

- **Memory**: At least 4GB RAM (8GB+ recommended)
- **Processor**: ARM64 SoC như Rockchip, Allwinner
- **Storage**: Ít nhất 2GB ổ đĩa (for model files and cache)
- **Audio**: Audio devices supporting 16kHz sampling rate

### Các yêu cầu khác

- **Voice Wake-up**: Requires downloading Sherpa-ONNX speech recognition models
- **Camera Features**: Requires camera device and OpenCV support

## Hướng dẫn sử dụng

### Hướng dẫn sử dụng cơ bản

```bash
# Clone project
git clone https://github.com/thanhtantran/py-xiaozhi-orangepi.git
cd py-xiaozhi-orangepi

# Bổ sung và cập nhật hệ thống
sudo add-apt-repository universe
sudo add-apt-repository multiverse
sudo apt update

# Cài các công cụ Python nếu chưa có
sudo apt install python3-dev python3-pip python3-venv -y

# Cài PyQT system-based
sudo apt install python3-pyqt5 python3-pyqt5.* -y
sudo apt install qml-module-qtquick-layouts \
                 qml-module-qtquick-controls \
                 qml-module-qtquick-controls2 \
                 qml-module-qtgraphicaleffects -y

# Tạo Python Virtual Env
rm -rf xiaozhi-venv
python -m venv xiaozhi-venv --system-site-packages
source xiaozhi-venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run program - GUI mode (default)
python main.py

# Run program - CLI mode
python main.py --mode cli

# Specify communication protocol
python main.py --protocol websocket  # WebSocket (default)
python main.py --protocol mqtt       # MQTT protocol
```

### Hướng dẫn sử dụng nâng cao

- Sẽ cập nhật tại [Diễn đàn Orange Pi](https://forum.orangepi.vn)

## License

[GNU Lesser General Public License v2.1](LICENSE)
