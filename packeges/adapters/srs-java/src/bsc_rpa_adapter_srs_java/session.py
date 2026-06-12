from typing import Self
import re
import subprocess

from win32process import GetWindowThreadProcessId
from win32api import TerminateProcess, OpenProcess, CloseHandle
from win32con import PROCESS_TERMINATE
from jab_rpa import JabDriver


class SrsJavaSession:
    __SRS_WINDOW_NAME = re.compile("(R.*|BANCO.*)")

    def __init__(
        self,
        javaws_path: str,
        srs_url: str,
        *,
        window_timeout: int = 60,  # seconds
        window_step: int = 5,  # seconds
    ) -> None:
        self._javaws_path: str = javaws_path
        self._srs_url: str = srs_url
        self._window_timeout: int = window_timeout
        self._window_step: int = window_step

    def start(self) -> None:
        subprocess.run([self._javaws_path, self._srs_url])
        self.driver: JabDriver = JabDriver(
            self.__SRS_WINDOW_NAME,
            window_timeout=self._window_timeout,
            window_step=self._window_step,
        )
        self.driver.start()

    def __enter__(self) -> Self:
        self.start()
        return self

    def stop(self) -> None:
        # TODO: replace this by "get_current_window_hwnd" when available on jab-rpa
        hwnd = self.driver.list_java_windows()[0].hwnd

        self.driver.stop()

        _, pid = GetWindowThreadProcessId(hwnd)
        handle = OpenProcess(PROCESS_TERMINATE, False, pid)
        TerminateProcess(handle, 0)
        CloseHandle(handle)

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
