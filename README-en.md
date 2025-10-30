# py-xiaozhi for Orange Pi

[English](README-en.md) | Vietnamese

## Introduction

- A Python-based modified version of Xiaozhi AI for those who want to experiment with Xiaozhi AI on Orange Pi devices, which can run alongside MCP Servers.
- This version is based on [py-xiaozhi](https://github.com/huangjunsen0406/py-xiaozhi), with unnecessary components removed to work specifically on Orange Pi.
- If you need a version that runs on all devices such as PC, MAC, etc., please use the original version.
- This edition uses the **GNU Lesser General Public License v2.1**, which means if you use this source code, you may only distribute it freely to others and **not sell it**.
- If you find this project useful, please give it a **Star**, and consider visiting [Orange Pi Vietnam](https://orangepi.vn) to support by purchasing products.

## Demo
- Video demo (Vietnames only)
- [Installation Tutorial Video](https://www.youtube.com) (Vietnamese only)

## Features

- Features are identical to the original version, with additional updates and optimizations for Orange Pi.
- The **QT window size** is enlarged to create a bigger and more visually appealing Xiaozhi AI interface.
- Future updates will utilize the **NPU of Orange Pi** to replace the remote Xiaozhi.me server.

### Supported Devices

- All **Orange Pi ARM64** models with HDMI output such as **Orange Pi 3B, Orange Pi 4A, Orange Pi Zero3, Orange Pi 4 LTS, Orange Pi 5**, etc.
- Other SBCs like **Raspberry Pi, Banana Pi, Rice Pi**, etc. may also work, but are **not guaranteed** or officially supported.

## System Requirements

### Basic Requirements

- **Python Version**: 3.9 - 3.12  
- **Operating System**: Ubuntu / Debian  
- **Audio Devices**: Microphone and speaker devices  
- **Network Connection**: Stable Internet (to connect to Xiaozhi.me)

### Hardware Requirements

- **Memory**: At least 4GB RAM (8GB+ recommended)  
- **Processor**: ARM64 SoC such as Rockchip or Allwinner  
- **Storage**: At least 2GB of free disk space (for model files and cache)  
- **Audio**: Audio devices supporting 16kHz sampling rate

### Additional Requirements

- **Voice Wake-up**: Requires downloading Sherpa-ONNX speech recognition models  
- **Camera Features**: Requires a camera device with OpenCV support  

## Usage Guide

### Basic Usage

```bash
# Clone project
git clone https://github.com/thanhtantran/py-xiaozhi-orangepi.git
cd py-xiaozhi-orangepi

# Add and update system repositories
sudo add-apt-repository universe
sudo add-apt-repository multiverse
sudo apt update

# Install Python tools if not already available
sudo apt install python3-dev python3-pip python3-venv -y

# Install system-based PyQT
sudo apt install python3-pyqt5 python3-pyqt5.* -y
sudo apt install qml-module-qtquick-layouts                  qml-module-qtquick-controls                  qml-module-qtquick-controls2                  qml-module-qtgraphicaleffects -y

# Create Python Virtual Environment
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

### Advanced Usage

- Advanced setup and guides will be updated on the [Orange Pi Forum](https://forum.orangepi.vn)

## License

[GNU Lesser General Public License v2.1](LICENSE)
