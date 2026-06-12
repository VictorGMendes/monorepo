import time
from datetime import datetime, timedelta
from typing import Protocol
from abc import abstractmethod
from collections.abc import Callable

from bs4 import BeautifulSoup

from .errors import NwMfaTimerError

# mfa_provider: Callable[[float], str]
# (timeout: float) -> str

type MfaProviderType = Callable[[float], str]
_STEP = 10  # seconds
_EMAIL_SUBJECT = "Código de Acesso"
_P_START = "Segue o código de acesso"


class EmailProtocol(Protocol):
    @property
    @abstractmethod
    def body_html(self) -> str: ...


class OutlookProtocol(Protocol):
    @abstractmethod
    def find_email(
        self, account: str, folder: str, filter: str
    ) -> EmailProtocol | None: ...


def email_mfa_provider(
    outlook: OutlookProtocol, account: str, folder: str
) -> MfaProviderType:
    def provider(timeout: float) -> str:
        start = time.monotonic()
        dt = (datetime.now() - timedelta(seconds=timeout)).strftime("%Y-%m-%d %H:%M")
        filter = f"[ReceivedTime] >= '{dt}' AND [Subject] = '{_EMAIL_SUBJECT}'"
        while time.monotonic() - start <= timeout:
            mail = outlook.find_email(account, folder, filter)
            if mail is not None:
                soup = BeautifulSoup(mail.body_html, features="lxml")
                p_texts = [
                    p.text for p in soup.find_all("p") if p.text.startswith(_P_START)
                ]
                if p_texts:
                    p_text = p_texts[0]
                    code = p_text.split(":")[1][:-1].strip()
                    return code
            time.sleep(_STEP)
        raise NwMfaTimerError("Token timer exceeded.")

    return provider
