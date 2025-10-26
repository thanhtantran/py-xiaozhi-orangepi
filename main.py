import argparse
import asyncio
import signal
import sys

from src.application import Application
from src.utils.logging_config import get_logger, setup_logging

logger = get_logger(__name__)


def parse_args():
    """
    Phân tích tham số dòng lệnh.
    """
    parser = argparse.ArgumentParser(description="Khách hàng AI Xiaozhi")
    parser.add_argument(
        "--mode",
        choices=["gui", "cli"],
        default="gui",
        help="Chế độ chạy: gui (giao diện đồ họa) hoặc cli (dòng lệnh)",
    )
    parser.add_argument(
        "--protocol",
        choices=["mqtt", "websocket"],
        default="websocket",
        help="Giao thức truyền thông: mqtt hoặc websocket",
    )
    parser.add_argument(
        "--skip-activation",
        action="store_true",
        help="Bỏ qua quy trình kích hoạt và khởi chạy ứng dụng trực tiếp (chỉ dùng để gỡ lỗi)",
    )
    return parser.parse_args()


async def handle_activation(mode: str) -> bool:
    """Xử lý quy trình kích hoạt thiết bị, phụ thuộc vào vòng lặp sự kiện hiện có.

    Args:
        mode: Chế độ chạy, "gui" hoặc "cli"

    Returns:
        bool: Kích hoạt thành công hay không
    """
    try:
        from src.core.system_initializer import SystemInitializer

        logger.info("Bắt đầu kiểm tra quy trình kích hoạt thiết bị...")

        system_initializer = SystemInitializer()
        # Sử dụng phương pháp xử lý kích hoạt trong SystemInitializer, tự động thích ứng với GUI/CLI
        result = await system_initializer.handle_activation_process(mode=mode)
        success = bool(result.get("is_activated", False))
        logger.info(f"Quy trình kích hoạt hoàn tất, kết quả: {success}")
        return success
    except Exception as e:
        logger.error(f"Lỗi quy trình kích hoạt: {e}", exc_info=True)
        return False


async def start_app(mode: str, protocol: str, skip_activation: bool) -> int:
    """
    Điểm khởi đầu chung để chạy ứng dụng (thực hiện trong vòng lặp sự kiện hiện có).
    """
    logger.info("Khởi chạy khách hàng AI Xiaozhi")

    # Xử lý quy trình kích hoạt 
    # nếu không bỏ qua quy trình kích hoạt:
    activation_success = await handle_activation(mode)
    if not activation_success:
        logger.error("Kích hoạt thiết bị thất bại, thoát chương trình")
        return 1
    else:
        logger.warning("Bỏ qua quy trình kích hoạt (chế độ gỡ lỗi)")

    # Tạo và khởi chạy ứng dụng
    app = Application.get_instance()
    return await app.run(mode=mode, protocol=protocol)


if __name__ == "__main__":
    exit_code = 1
    try:
        args = parse_args()
        setup_logging()

        # Phát hiện môi trường Wayland và thiết lập cấu hình plugin nền tảng Qt
        import os

        is_wayland = (
            os.environ.get("WAYLAND_DISPLAY")
            or os.environ.get("XDG_SESSION_TYPE") == "wayland"
        )

        if args.mode == "gui" and is_wayland:
            # Trong môi trường Wayland, đảm bảo Qt sử dụng plugin nền tảng chính xác
            if "QT_QPA_PLATFORM" not in os.environ:
                # Ưu tiên sử dụng plugin wayland, nếu thất bại thì quay về xcb (lớp tương thích X11)
                os.environ["QT_QPA_PLATFORM"] = "wayland;xcb"
                logger.info("Môi trường Wayland: Thiết lập QT_QPA_PLATFORM=wayland;xcb")

            # Vô hiệu hóa một số tính năng Qt không ổn định trong Wayland
            os.environ.setdefault("QT_WAYLAND_DISABLE_WINDOWDECORATION", "1")
            logger.info("Phát hiện môi trường Wayland hoàn tất, đã áp dụng cấu hình tương thích")

        # Thiết lập xử lý tín hiệu thống nhất: bỏ qua SIGTRAP trên macOS để tránh "trace trap" làm thoát tiến trình
        try:
            if hasattr(signal, "SIGINT"):
                # Để qasync/Qt xử lý Ctrl+C; giữ mặc định hoặc xử lý sau bởi lớp GUI
                pass
            if hasattr(signal, "SIGTERM"):
                # Cho phép tiến trình nhận tín hiệu kết thúc và đi theo đường dẫn đóng bình thường
                pass
            if hasattr(signal, "SIGTRAP"):
                signal.signal(signal.SIGTRAP, signal.SIG_IGN)
        except Exception:
            # Một số nền tảng/môi trường không hỗ trợ thiết lập các tín hiệu này, bỏ qua là được
            pass

        if args.mode == "gui":
            # Trong chế độ GUI, tạo QApplication và vòng lặp sự kiện qasync từ main
            try:
                import qasync
                from PyQt5.QtWidgets import QApplication
            except ImportError as e:
                logger.error(f"Chế độ GUI yêu cầu thư viện qasync và PyQt5: {e}")
                sys.exit(1)

            qt_app = QApplication.instance() or QApplication(sys.argv)

            loop = qasync.QEventLoop(qt_app)
            asyncio.set_event_loop(loop)
            logger.info("Đã tạo vòng lặp sự kiện qasync trong main")

            # Đảm bảo việc đóng cửa sổ cuối cùng không tự động thoát ứng dụng, tránh vòng lặp sự kiện dừng trước
            try:
                qt_app.setQuitOnLastWindowClosed(False)
            except Exception:
                pass

            with loop:
                exit_code = loop.run_until_complete(
                    start_app(args.mode, args.protocol, args.skip_activation)
                )
        else:
            # Chế độ CLI sử dụng vòng lặp sự kiện asyncio tiêu chuẩn
            exit_code = asyncio.run(
                start_app(args.mode, args.protocol, args.skip_activation)
            )

    except KeyboardInterrupt:
        logger.info("Chương trình bị người dùng gián đoạn")
        exit_code = 0
    except Exception as e:
        logger.error(f"Chương trình thoát bất thường: {e}", exc_info=True)
        exit_code = 1
    finally:
        sys.exit(exit_code)
