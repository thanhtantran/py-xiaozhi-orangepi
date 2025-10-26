# py-xiaozhi-orangepi

[English](README-en.md) | Tiếng Việt

## Giới thiệu

Bản chỉnh sửa Python-based Xiaozhi AI cho ai muốn thử nghiệm Xiaozhi AI trên các thiết bị Orange Pi, có thể chạy song song cùng các MCP Server
Bản chỉnh sửa này lấy gốc từ [py-xiaozhi](https://github.com/huangjunsen0406/py-xiaozhi), lược bỏ chỉ chạy trên Orange Pi

## Demo

- [Video hướng dẫn cài đặt](https://www.youtube.com) (Vietnames only)

## Các tính năng

### Core AI Capabilities

- **AI Voice Interaction**: Supports voice input and recognition, enabling intelligent human-computer interaction with natural conversation flow
- **Visual Multimodal**: Supports image recognition and processing, providing multimodal interaction capabilities and image content understanding
- **Intelligent Wake-up**: Supports multiple wake word activation for hands-free interaction (configurable)
- **Continuous Dialogue Mode**: Implements seamless conversation experience, enhancing user interaction fluidity

### MCP Tools Ecosystem

- **System Control Tools**: System status monitoring, application management, volume control, device management
- **Calendar Management Tools**: Full-featured calendar system with create, query, update, delete events, intelligent categorization and reminders
- **Timer Tools**: Countdown timer functionality with delayed MCP tool execution and parallel task management
- **Music Player Tools**: Online music search and playback with playback controls, lyrics display, and local cache management
- **12306 Query Tools**: 12306 railway ticket query with train tickets, transfer queries, and route information
- **Search Tools**: Web search and content retrieval with Bing search integration and intelligent content parsing
- **Recipe Tools**: Rich recipe database with search, category browsing, and intelligent recommendations
- **Map Tools**: Amap services with geocoding, route planning, nearby search, and weather queries
- **Bazi Fortune Tools**: Traditional Chinese fortune-telling with Bazi calculation, marriage analysis, and lunar calendar queries
- **Camera Tools**: Image capture and AI analysis with photo recognition and intelligent Q&A

### IoT Device Integration

- **Device Management Architecture**: Unified device management based on Thing pattern with asynchronous property and method calls
- **Smart Home Control**: Supports lighting, volume, temperature sensors, and other device control
- **State Synchronization**: Real-time status monitoring with incremental updates and concurrent state retrieval
- **Extensible Design**: Modular device drivers, easy to add new device types

### Advanced Audio Processing

- **Multi-level Audio Processing**: Supports Opus codec and real-time resampling
- **Voice Activity Detection**: VAD detector for intelligent interruption with real-time voice activity monitoring
- **Wake Word Detection**: Sherpa-ONNX-based offline speech recognition with multiple wake words and pinyin matching
- **Audio Stream Management**: Independent input/output streams with stream rebuild and error recovery
- **Audio Echo Cancellation**: Integrated WebRTC audio processing module providing high-quality echo cancellation
- **System Audio Recording**: Supports system audio recording with audio loopback processing

### User Interface

- **Graphical Interface**: Modern PyQt5-based GUI with Xiaozhi expressions and text display for enhanced visual experience
- **Command Line Mode**: CLI support suitable for embedded devices or GUI-less environments
- **System Tray**: Background operation support with integrated system tray functionality
- **Global Hotkeys**: Global hotkey support for improved usability
- **Settings Interface**: Complete settings management interface with configuration customization

### Security & Stability

- **Encrypted Audio Transmission**: WSS protocol support ensuring audio data security and preventing information leakage
- **Device Activation System**: Dual v1/v2 protocol activation with automatic verification code and device fingerprint handling
- **Error Recovery**: Complete error handling and recovery mechanisms with reconnection support

### Các thiết bị hỗ trợ

- Các phiên bản Orange Pi ARM64 có xuất hình ra HDMI như Orange Pi 3B, Orange Pi 4A, Orange Pi Zero3, Orange Pi 4 LTS, Orange Pi 5 ... đều dùng được
- Các phiên bản Pi khác như Raspberry Pi, Banana Pi, Rice Pi, ... có thể dùng được

## Yêu cầu hệ thống

### Yêu cầu cơ bản

- **Python Version**: 3.9 - 3.12
- **Operating System**: Ubuntu / Debian
- **Audio Devices**: Microphone and speaker devices
- **Network Connection**: Stable internet connection (for AI services and online features)

### Yêu cầu cấu hình

- **Memory**: At least 4GB RAM (8GB+ recommended)
- **Processor**: Modern CPU with AVX instruction set support
- **Storage**: At least 2GB available disk space (for model files and cache)
- **Audio**: Audio devices supporting 16kHz sampling rate

### Optional Feature Requirements

- **Voice Wake-up**: Requires downloading Sherpa-ONNX speech recognition models
- **Camera Features**: Requires camera device and OpenCV support

## Development Guide

### Development Environment Setup

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

## License

[MIT License](LICENSE)
