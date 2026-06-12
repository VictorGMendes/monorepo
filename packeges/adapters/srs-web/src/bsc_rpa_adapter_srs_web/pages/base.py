from contextlib import contextmanager
from collections.abc import Callable, Generator
from typing import Literal
from dataclasses import dataclass
import time
import re
from abc import ABC, abstractmethod
from typing import Protocol
import logging

from playwright.sync_api import Dialog, Page

from ..errors import SrsWebValidationError

logger = logging.getLogger(__name__)

# Types, constants and utils

_EXPECT_TIMEOUT = 30_000  # milliseconds
_VALIDATE_TIMEOUT = 30_000  # milliseconds
_SLICE_TIMEOUT = 200  # milliseconds


def _regex_eq(text: str) -> re.Pattern[str]:
    return re.compile(r"^\s*" + re.escape(text) + r"\s*$", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class DialogResult:
    kind: Literal["dialog"]
    dialog: Dialog


@dataclass(frozen=True, slots=True)
class OtherResult:
    kind: Literal["other"]


@dataclass(frozen=True, slots=True)
class TimeoutResult:
    kind: Literal["timeout"]


type RaceResult = DialogResult | OtherResult | TimeoutResult


@dataclass(slots=True)
class RaceResultInfo:
    value: RaceResult | None = None


@contextmanager
def expect_dialog_or(
    page: Page,
    *,
    dialog_predicate: Callable[[Dialog], bool],
    other_waiter: Callable[[int], bool],
    slice_ms: int = _SLICE_TIMEOUT,
    timeout_ms: int = _EXPECT_TIMEOUT,
) -> Generator[RaceResultInfo, None, None]:
    result_info = RaceResultInfo()
    matched_dialog: Dialog | None = None

    def handle(dialog: Dialog) -> None:
        nonlocal matched_dialog
        logger.info(f"Found dialog {dialog.message!r}. Dismissing.")
        dialog.dismiss()
        if dialog_predicate(dialog):
            matched_dialog = dialog

    page.on("dialog", handle)

    try:
        yield result_info

        deadline = time.monotonic() + (timeout_ms / 1000)  # s
        while True:
            if matched_dialog is not None:
                result_info.value = DialogResult("dialog", matched_dialog)
                return

            remaining = int((deadline - time.monotonic()) * 1000)  # ms
            if remaining <= 0:
                result_info.value = TimeoutResult("timeout")
                return

            if other_waiter(min(slice_ms, remaining)):
                result_info.value = OtherResult("other")
                return
    finally:
        page.remove_listener("dialog", handle)


class PlaywrightAssertionProtocol(Protocol):
    def __call__(self, *, timeout: int | float | None = None) -> None: ...


class SrsWebPage(ABC):
    def __init__(self, page: Page, validate_at_init: bool = True) -> None:
        self.page: Page = page
        self._elements()
        if validate_at_init:
            self.validate()

    @abstractmethod
    def _elements(self) -> None:
        """Define this page's elements. Called on `self.__init__` before `self.validate`"""

    def validate(self, timeout_ms: int | None = None) -> None:
        if timeout_ms is None:
            timeout_ms = _VALIDATE_TIMEOUT
        try:
            self._validate(timeout_ms)
        except AssertionError as e:
            raise SrsWebValidationError(f"{type(self)} validation failed.") from e

    @abstractmethod
    def _validate(self, timeout_ms: int) -> None: ...
