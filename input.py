import os
import sys
import time
from typing import Optional


def read_keypress() -> str:
    """
    Read a single keypress without requiring Enter (POSIX terminals).
    Returns a single-character string.
    """
    if os.name == "nt":
        import msvcrt
        ch = msvcrt.getch()
        if ch in (b"\x00", b"\xe0"):
            msvcrt.getch()
            return ""
        try:
            return ch.decode("utf-8", errors="ignore")
        except Exception:
            return ""
    else:
        import termios
        import tty

        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setcbreak(fd)  # cbreak: immediate input, but still handles signals
            ch = sys.stdin.read(1)
            return ch
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)


def read_keypress_timeout(timeout_sec: float) -> Optional[str]:
    if os.name == "nt":
        import msvcrt
        end = time.monotonic() + timeout_sec
        while time.monotonic() < end:
            if msvcrt.kbhit():
                ch = msvcrt.getch()
                if ch in (b"\x00", b"\xe0"):
                    msvcrt.getch()
                    return ""
                try:
                    return ch.decode("utf-8", errors="ignore")
                except Exception:
                    return ""
            time.sleep(0.01)
        return None
    else:
        import select
        import termios
        import tty

        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setcbreak(fd)
            ready, _, _ = select.select([sys.stdin], [], [], timeout_sec)
            if ready:
                return sys.stdin.read(1)
            return None
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)
