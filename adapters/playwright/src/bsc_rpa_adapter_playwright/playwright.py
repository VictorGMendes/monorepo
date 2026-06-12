from datetime import datetime
from typing import Self
import os
import logging
from pathlib import Path

from playwright.sync_api import (
    sync_playwright,
    PlaywrightContextManager,
    Playwright,
    Browser,
    BrowserContext,
    Page,
)

# Playwright Session class


class PlaywrightSession:
    def __init__(
        self,
        screenshot_folder: str,
        *,
        headless: bool = False,
        default_timeout_ms: int = 30_000,
        trace: bool = False,
        traces_dir: str | None = None,
        trace_file: str | None = None,
        executable_path: Path | None = None,
    ):
        self._screenshot_folder = screenshot_folder
        self._headless = headless
        self._default_timeout_ms = default_timeout_ms
        self._trace = trace
        self._traces_dir = traces_dir
        self._trace_file = trace_file
        self._executable_path = executable_path

        self._logger = logging.getLogger(type(self).__module__)
        self._logger.info(f"Initializing {self!r}")

        self._cm: PlaywrightContextManager
        self._playwright: Playwright
        self._browser: Browser
        self.ctx: BrowserContext

        self._logger.debug(f"{self} initialized")

    def __str__(self) -> str:
        return type(self).__name__

    def __repr__(self) -> str:
        return f"<{type(self).__module__}.{type(self).__qualname__} screenshot_folder={self._screenshot_folder!r} headless={self._headless!r} default_timeout_ms={self._default_timeout_ms!r} trace={self._trace!r} traces_dir={self._traces_dir!r} trace_file={self._trace_file!r} executable_path={self._executable_path!r}>"

    def new_page(self) -> Page:
        return self.ctx.new_page()

    def start(self) -> Self:
        self._logger.info(f"Starting {self!r}")
        try:
            self._cm = sync_playwright()
            self._playwright = self._cm.start()
            if self._trace:
                if self._executable_path is None:
                    self._browser = self._playwright.chromium.launch(
                        channel="chrome",
                        args=["--start-maximized"],
                        headless=self._headless,
                        traces_dir=self._traces_dir,
                    )
                else:
                    self._browser = self._playwright.chromium.launch(
                        executable_path=self._executable_path,
                        args=["--start-maximized"],
                        headless=self._headless,
                        traces_dir=self._traces_dir,
                    )
            else:
                if self._executable_path is None:
                    self._browser = self._playwright.chromium.launch(
                        channel="chrome",
                        args=["--start-maximized"],
                        headless=self._headless,
                    )
                else:
                    self._browser = self._playwright.chromium.launch(
                        executable_path=self._executable_path,
                        args=["--start-maximized"],
                        headless=self._headless,
                    )
            if self._headless:
                self.ctx = self._browser.new_context(
                    viewport={"width": 1920, "height": 1080}
                )
            else:
                self.ctx = self._browser.new_context(no_viewport=True)
            self.ctx.set_default_timeout(self._default_timeout_ms)
            self.ctx.set_default_navigation_timeout(
                max(30_000, self._default_timeout_ms)
            )

            if self._trace:
                self.ctx.tracing.start(
                    name=f"{self}_{datetime.now().strftime('%d%m%Y_%H%M%S')}",
                    title=f"{self}_{datetime.now().strftime('%d%m%Y_%H%M%S')}",
                    screenshots=True,
                    snapshots=True,
                    sources=False,
                )

        except Exception as e:
            self._logger.exception(f"Exception during {self}.start: {e}")
            raise
        self._logger.debug(f"{self} started")
        return self

    def stop(self) -> None:
        self._logger.info(f"Stopping {self!r}")
        try:
            try:
                if self.ctx and self._trace:
                    # Always stop tracing to capture evidence of failures
                    try:
                        self.ctx.tracing.stop(path=self._trace_file)
                    except Exception:
                        pass
            finally:
                if self.ctx is not None:
                    self._logger.debug(f"Closing context for {self}")
                    self.ctx.close()
                if self._browser is not None:
                    self._logger.debug(f"Closing browser for {self}")
                    self._browser.close()
                if self._playwright is not None:
                    self._logger.debug(f"Closing playwright for {self}")
                    self._playwright.stop()
        except Exception as e:
            self._logger.exception(f"Exception during {self}.stop: {e}")
            raise
        self._logger.debug(f"{self} stopped")

    def screenshot_all_pages(self, prefix: str) -> None:
        for i, page in enumerate(self.ctx.pages):
            try:
                page.screenshot(
                    path=os.path.join(
                        self._screenshot_folder,
                        f"{prefix}_page{i}_{datetime.now().strftime('%d%m%Y_%H%M%S')}.png",
                    )
                )
            except Exception as e:
                self._logger.warning(
                    f"Exception trying to screenshot: {e}", exc_info=True
                )

    def __enter__(self) -> Self:
        return self.start()

    def __exit__(self, exc_type, exc, tb) -> bool:
        try:
            if exc is not None:
                self._logger.exception(
                    f"Exception within {self!r} context: {exc_type}: {exc}"
                )
                self.screenshot_all_pages("Exception")

        finally:
            self.stop()
            return False

    def restart(self) -> None:
        self._logger.info(f"Restarting {self!r}")
        self.stop()
        self.start()
        self._logger.debug(f"{self} restarted")
