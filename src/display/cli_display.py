import asyncio
import logging
import os
import shutil
import sys
import termios
import tty
from collections import deque
from typing import Callable, Optional

from src.display.base_display import BaseDisplay


class CliDisplay(BaseDisplay):
    def __init__(self):
        super().__init__()
        self.running = True
        self._use_ansi = sys.stdout.isatty()
        self._loop = None
        self._last_drawn_rows = 0

        # Dữ liệu bảng điều khiển (khu vực hiển thị nội dung phía trên)
        self._dash_status = ""
        self._dash_connected = False
        self._dash_text = ""
        self._dash_emotion = ""
        # Bố cục: Chỉ gồm hai khu vực (khu vực hiển thị + khu vực nhập liệu)
        # Dành riêng hai dòng cho khu vực nhập liệu (dòng phân cách + dòng nhập liệu),
        # và thêm một dòng để xóa tràn ký tự tiếng Trung (nếu có)
        self._input_area_lines = 3
        self._dashboard_lines = 8  # Số dòng tối thiểu của khu vực hiển thị (sẽ thay đổi theo chiều cao của terminal)

        # Màu sắc/phong cách (chỉ hoạt động trong TTY)
        self._ansi = {
            "reset": "\x1b[0m",
            "bold": "\x1b[1m",
            "dim": "\x1b[2m",
            "blue": "\x1b[34m",
            "cyan": "\x1b[36m",
            "green": "\x1b[32m",
            "yellow": "\x1b[33m",
            "magenta": "\x1b[35m",
            }

        # Hàm callback
        self.auto_callback = None
        self.abort_callback = None
        self.send_text_callback = None
        self.mode_callback = None

        # Hàng đợi bất đồng bộ để xử lý lệnh
        self.command_queue = asyncio.Queue()

        # Bộ đệm nhật ký (chỉ hiển thị trên đầu CLI, không in trực tiếp vào console)
        self._log_lines: deque[str] = deque(maxlen=6)
        self._install_log_handler()

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
        self.auto_callback = auto_callback
        self.abort_callback = abort_callback
        self.send_text_callback = send_text_callback
        self.mode_callback = mode_callback

    async def update_button_status(self, text: str):
        """
        Cập nhật trạng thái nút bấm.
        """
        # Đơn giản hóa: Trạng thái nút bấm chỉ hiển thị trong bảng điều khiển
        self._dash_text = text
        await self._render_dashboard()

    async def update_status(self, status: str, connected: bool):
        """
        Cập nhật trạng thái (chỉ cập nhật bảng điều khiển, không thêm dòng mới).
        """
        self._dash_status = status
        self._dash_connected = bool(connected)
        await self._render_dashboard()

    async def update_text(self, text: str):
        """
        Cập nhật văn bản (chỉ cập nhật bảng điều khiển, không thêm dòng mới).
        """
        if text and text.strip():
            self._dash_text = text.strip()
            await self._render_dashboard()

    async def update_emotion(self, emotion_name: str):
        """
        Cập nhật biểu cảm (chỉ cập nhật bảng điều khiển, không thêm dòng mới).
        """
        self._dash_emotion = emotion_name
        await self._render_dashboard()

    async def start(self):
        """
        Khởi động CLI hiển thị bất đồng bộ.
        """
        self._loop = asyncio.get_running_loop()
        await self._init_screen()

        # Khởi động các tác vụ để xử lý lệnh
        command_task = asyncio.create_task(self._command_processor())
        input_task = asyncio.create_task(self._keyboard_input_loop())

        try:
            await asyncio.gather(command_task, input_task)
        except KeyboardInterrupt:
            await self.close()

    async def _command_processor(self):
        """
        Bộ xử lý lệnh.
        """
        while self.running:
            try:
                command = await asyncio.wait_for(self.command_queue.get(), timeout=1.0)
                if asyncio.iscoroutinefunction(command):
                    await command()
                else:
                    command()
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Lỗi xử lý lệnh: {e}")

    async def _keyboard_input_loop(self):
        """
        Vòng lặp nhập từ bàn phím.
        """
        try:
            while self.running:
                # Trong TTY, cố định khu vực nhập liệu ở dưới cùng
                if self._use_ansi:
                    await self._render_input_area()
                    # Tự xử lý nhập liệu (tắt chế độ hiển thị đầu vào của terminal), vẽ lại từng ký tự
                    cmd = await asyncio.to_thread(self._read_line_raw)
                    # Xóa khu vực nhập liệu (bao gồm cả phần tràn ký tự tiếng Trung) và làm mới nội dung phía trên
                    self._clear_input_area()
                    await self._render_dashboard()
                else:
                    cmd = await asyncio.to_thread(input)
                await self._handle_command(cmd.lower().strip())
        except asyncio.CancelledError:
            pass

    # ===== Chặn nhật ký và chuyển tiếp đến khu vực hiển thị =====
    def _install_log_handler(self) -> None:
        class _DisplayLogHandler(logging.Handler):
            def __init__(self, display: "CliDisplay"):
                super().__init__()
                self.display = display

            def emit(self, record: logging.LogRecord) -> None:
                try:
                    msg = self.format(record)
                    self.display._log_lines.append(msg)
                    loop = self.display._loop
                    if loop and self.display._use_ansi:
                        loop.call_soon_threadsafe(
                            lambda: asyncio.create_task(
                                self.display._render_dashboard()
                            )
                        )
                except Exception:
                    pass

        root = logging.getLogger()
        # Loại bỏ các handler ghi trực tiếp vào stdout/stderr để tránh ghi đè giao diện
        for h in list(root.handlers):
            if isinstance(h, logging.StreamHandler) and getattr(h, "stream", None) in (
                sys.stdout,
                sys.stderr,
            ):
                root.removeHandler(h)

        handler = _DisplayLogHandler(self)
        handler.setLevel(logging.WARNING)
        handler.setFormatter(
            logging.Formatter(
                fmt="%(asctime)s [%(name)s] - %(levelname)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        root.addHandler(handler)

    async def _handle_command(self, cmd: str):
        """
        Xử lý lệnh.
        """
        if cmd == "q":
            await self.close()
        elif cmd == "h":
            self._print_help()
        elif cmd == "r":
            if self.auto_callback:
                await self.command_queue.put(self.auto_callback)
        elif cmd == "x":
            if self.abort_callback:
                await self.command_queue.put(self.abort_callback)
        else:
            if self.send_text_callback:
                await self.send_text_callback(cmd)

    async def close(self):
        """
        Đóng CLI hiển thị.
        """
        self.running = False
        print("\nĐang đóng ứng dụng...\n")

    def _print_help(self):
        """
        Ghi thông tin trợ giúp vào khu vực hiển thị nội dung phía trên thay vì in trực tiếp.
        """
        help_text = "r: Bắt đầu/Dừng | x: Dừng | q: Thoát | h: Trợ giúp | Khác: Gửi văn bản"
        self._dash_text = help_text

    async def _init_screen(self):
        """
        Khởi tạo màn hình và vẽ hai khu vực (khu vực hiển thị + khu vực nhập liệu).
        """
        if self._use_ansi:
            # Xóa màn hình và quay lại góc trên bên trái
            sys.stdout.write("\x1b[2J\x1b[H")
            sys.stdout.flush()

        # Vẽ đầy đủ lần đầu tiên
        await self._render_dashboard(full=True)
        await self._render_input_area()

    def _goto(self, row: int, col: int = 1):
        sys.stdout.write(f"\x1b[{max(1,row)};{max(1,col)}H")

    def _term_size(self):
        try:
            size = shutil.get_terminal_size(fallback=(80, 24))
            return size.columns, size.lines
        except Exception:
            return 80, 24

    # ====== Hỗ trợ nhập liệu thô (Raw mode), tránh lỗi ký tự tiếng Trung ======
    def _read_line_raw(self) -> str:
        """
        Sử dụng chế độ thô để đọc một dòng: tắt hiển thị đầu vào, đọc từng ký tự và tự hiển thị,
        vẽ lại toàn bộ dòng để tránh lỗi xoá ký tự rộng (tiếng Trung).
        """
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            buffer: list[str] = []
            while True:
                ch = os.read(fd, 4)  # Đọc tối đa 4 byte, đủ để bao quát các ký tự UTF-8 phổ biến
                if not ch:
                    break
                try:
                    s = ch.decode("utf-8")
                except UnicodeDecodeError:
                    # Nếu không giải mã được UTF-8, tiếp tục đọc thêm cho đến khi giải mã được
                    while True:
                        ch += os.read(fd, 1)
                        try:
                            s = ch.decode("utf-8")
                            break
                        except UnicodeDecodeError:
                            continue

                if s in ("\r", "\n"):
                    # Enter: Xuống dòng, kết thúc nhập liệu
                    sys.stdout.write("\r\n")
                    sys.stdout.flush()
                    break
                elif s in ("\x7f", "\b"):
                    # Backspace: Xoá một ký tự Unicode
                    if buffer:
                        buffer.pop()
                    # Vẽ lại toàn bộ dòng để tránh lỗi xóa ký tự tiếng Trung
                    self._redraw_input_line("".join(buffer))
                elif s == "\x03":  # Ctrl+C
                    raise KeyboardInterrupt
                else:
                    buffer.append(s)
                    self._redraw_input_line("".join(buffer))

            return "".join(buffer)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

    def _redraw_input_line(self, content: str) -> None:
        """
        Xóa dòng nhập liệu và viết lại nội dung hiện tại, đảm bảo không còn sót ký tự tiếng Trung.
        """
        cols, rows = self._term_size()
        separator_row = max(1, rows - self._input_area_lines + 1)
        first_input_row = min(rows, separator_row + 1)
        prompt = "Nhập: " if not self._use_ansi else "\x1b[1m\x1b[36mNhập:\x1b[0m "
        self._goto(first_input_row, 1)
        sys.stdout.write("\x1b[2K")
        visible = content
        # Tránh vượt quá một dòng gây tràn
        max_len = max(1, cols - len("Nhập: ") - 1)
        if len(visible) > max_len:
            visible = visible[-max_len:]
        sys.stdout.write(f"{prompt}{visible}")
        sys.stdout.flush()

    async def _render_dashboard(self, full: bool = False):
        """
        Cập nhật khu vực hiển thị nội dung phía trên, không ảnh hưởng đến dòng nhập liệu.
        """

        # Cắt bớt văn bản dài để tránh bị tràn dòng
        def trunc(s: str, limit: int = 80) -> str:
            return s if len(s) <= limit else s[: limit - 1] + "…"

        lines = [
            f"Trạng thái: {trunc(self._dash_status)}",
            f"Kết nối: {'Đã kết nối' if self._dash_connected else 'Chưa kết nối'}",
            f"Biểu cảm: {trunc(self._dash_emotion)}",
            f"Văn bản: {trunc(self._dash_text)}",
        ]

        if not self._use_ansi:
            # Chế độ đơn giản: chỉ in dòng trạng thái cuối cùng
            print(f"\r{lines[0]}        ", end="", flush=True)
            return

        cols, rows = self._term_size()

        # Số dòng hiển thị khả dụng = Tổng số dòng terminal - số dòng khu vực nhập liệu
        usable_rows = max(5, rows - self._input_area_lines)

        # Một số hàm hỗ trợ tạo kiểu
        def style(s: str, *names: str) -> str:
            if not self._use_ansi:
                return s
            prefix = "".join(self._ansi.get(n, "") for n in names)
            return f"{prefix}{s}{self._ansi['reset']}"

        title = style(" Terminal AI CLI ", "bold", "cyan")
        # Thanh tiêu đề và thanh phân cách
        top_bar = "┌" + ("─" * (max(2, cols - 2))) + "┐"
        title_line = "│" + title.center(max(2, cols - 2)) + "│"
        sep_line = "├" + ("─" * (max(2, cols - 2))) + "┤"
        bottom_bar = "└" + ("─" * (max(2, cols - 2))) + "┘"

        # Số dòng nội dung khả dụng (trừ đi 4 dòng của khung)
        body_rows = max(1, usable_rows - 4)
        body = []
        for i in range(body_rows):
            text = lines[i] if i < len(lines) else ""
            text = style(text, "green") if i == 0 else text
            body.append("│" + text.ljust(max(2, cols - 2))[: max(2, cols - 2)] + "│")

        # Lưu vị trí con trỏ
        sys.stdout.write("\x1b7")

        # Xóa hoàn toàn vùng hiển thị trước khi vẽ lại
        total_rows = 4 + body_rows  # Khung trên 3 dòng + khung dưới 1 dòng + số dòng nội dung
        rows_to_clear = max(self._last_drawn_rows, total_rows)
        for i in range(rows_to_clear):
            self._goto(1 + i, 1)
            sys.stdout.write("\x1b[2K")

        # Vẽ khung trên
        self._goto(1, 1)
        sys.stdout.write("\x1b[2K" + top_bar[:cols])
        self._goto(2, 1)
        sys.stdout.write("\x1b[2K" + title_line[:cols])
        self._goto(3, 1)
        sys.stdout.write("\x1b[2K" + sep_line[:cols])

        # Vẽ nội dung chính
        for idx in range(body_rows):
            self._goto(4 + idx, 1)
            sys.stdout.write("\x1b[2K")
            sys.stdout.write(body[idx][:cols])

        # Vẽ khung dưới
        self._goto(4 + body_rows, 1)
        sys.stdout.write("\x1b[2K" + bottom_bar[:cols])

        # Phục hồi vị trí con trỏ
        sys.stdout.write("\x1b8")
        sys.stdout.flush()

        # Lưu lại chiều cao đã vẽ
        self._last_drawn_rows = total_rows

    def _clear_input_area(self):
        if not self._use_ansi:
            return
        cols, rows = self._term_size()
        separator_row = max(1, rows - self._input_area_lines + 1)
        first_input_row = min(rows, separator_row + 1)
        second_input_row = min(rows, separator_row + 2)
        # Lần lượt xóa dòng phân cách và hai dòng nhập liệu
        for r in [separator_row, first_input_row, second_input_row]:
            self._goto(r, 1)
            sys.stdout.write("\x1b[2K")
        sys.stdout.flush()

    async def _render_input_area(self):
        if not self._use_ansi:
            return
        cols, rows = self._term_size()
        separator_row = max(1, rows - self._input_area_lines + 1)
        first_input_row = min(rows, separator_row + 1)
        second_input_row = min(rows, separator_row + 2)

        # Lưu vị trí con trỏ
        sys.stdout.write("\x1b7")
        # Vẽ dòng phân cách
        self._goto(separator_row, 1)
        sys.stdout.write("\x1b[2K")
        sys.stdout.write("═" * max(1, cols))

        # Dòng nhắc nhập liệu
        self._goto(first_input_row, 1)
        sys.stdout.write("\x1b[2K")
        prompt = "Nhập: " if not self._use_ansi else "\x1b[1m\x1b[36mNhập:\x1b[0m "
        sys.stdout.write(prompt)

        # Dự phòng một dòng để xóa tràn
        self._goto(second_input_row, 1)
        sys.stdout.write("\x1b[2K")
        sys.stdout.flush()

        # Phục hồi vị trí con trỏ
        sys.stdout.write("\x1b8")
        self._goto(first_input_row, 1)
        sys.stdout.write(prompt)
        sys.stdout.flush()

    async def toggle_mode(self):
        """
        Chuyển đổi chế độ trong CLI (không hỗ trợ thực hiện).
        """
        self.logger.debug("Không hỗ trợ chuyển đổi chế độ trong CLI")

    async def toggle_window_visibility(self):
        """
        Chuyển đổi hiển thị cửa sổ trong CLI (không hỗ trợ thực hiện).
        """
        self.logger.debug("Không hỗ trợ chuyển đổi hiển thị cửa sổ trong CLI")
