from abc import ABC, abstractmethod
import logging

from jab_rpa import JabDriver
from jab_rpa.locator import LocatorNotFound

from ..errors import SrsJavaValidationError

logger = logging.getLogger(__name__)

# Types, constants and utils

_WAIT_FOR_TIMEOUT = 60  # seconds
_WAIT_FOR_SLICE = 2  # seconds
_VALIDATE_TIMEOUT = 60  # seconds
_VALIDATE_SLICE = 2  # seconds
_STD_STATES = "enabled.focusable.visible.showing"


class SrsJavaPage(ABC):
    def __init__(self, driver: JabDriver, validate_at_init: bool = True) -> None:
        self.driver: JabDriver = driver
        self._locators()
        if validate_at_init:
            self.validate()

    @abstractmethod
    def _locators(self) -> None:
        """Define this page's locators. Called on `self.__init__` before `self.validate`"""

    def validate(
        self, timeout_ms: int = _VALIDATE_TIMEOUT, slice_ms: int = _VALIDATE_SLICE
    ) -> None:
        try:
            self._validate(timeout_ms, slice_ms)
        except LocatorNotFound as e:
            raise SrsJavaValidationError(f"{type(self)} validation failed.") from e

    @abstractmethod
    def _validate(self, timeout_ms: int, slice_ms: int) -> None: ...
