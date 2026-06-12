from typing import Self
from collections import deque
import logging
import time

from urllib.parse import ParseResult, urlparse
import niquests as requests

STD_HEADERS = {
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "accept-language": "en-US,en;q=0.9",
    "sec-ch-ua": '"Google Chrome";v="119", "Chromium";v="119", "Not?A_Brand";v="24"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "document",
    "sec-fetch-mode": "navigate",
    "sec-fetch-site": "none",
    "sec-fetch-user": "?1",
    "upgrade-insecure-requests": "1",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Referrer-Policy": "strict-origin-when-cross-origin",
}


class NewconWebSession:
    def __init__(
        self,
        std_headers: dict[str, str] = STD_HEADERS,
        verify: bool = True,
    ) -> None:
        self._logger = logging.getLogger(type(self).__module__)
        self._verify = verify

        self._logger.info(f"Initializing {self!r}")

        if std_headers is None:
            std_headers = dict()

        self._req_session = requests.Session()

        self._req_session.verify = verify
        self._req_session.headers.update(std_headers)
        self.history: deque[tuple[requests.Response, float]] = deque(maxlen=200)

        self._logger.debug(f"{self} initialized")

    def __str__(self) -> str:
        return type(self).__name__

    def __repr__(self) -> str:
        return (
            f"<{type(self).__module__}.{type(self).__qualname__} verify={self._verify}>"
        )

    def stop(self):
        self._logger.info(f"Stopping {self!r}")
        self._req_session.close()
        self._logger.debug(f"{self} stopped")

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args) -> bool:
        self.stop()
        return False

    def request(
        self, method: str | bytes, url: str | bytes, *args, **kwargs
    ) -> requests.Response:
        res = self._req_session.request(
            method=str(method), url=str(url), *args, **kwargs
        )
        self.history.append((res, time.time()))
        return res

    @property
    def last_response(self) -> requests.Response | None:
        if not self.history:
            None
        return self.history[-1][0]

    @property
    def url(self) -> str | None:
        if self.last_response is None:
            return None
        return self.last_response.url

    @property
    def parsed_url(self) -> ParseResult | None:
        # The full url usually is '{base_url}/{frame}?{query}'
        if self.url is None:
            return None
        return urlparse(self.url)

    @property
    def base_url(self) -> str | None:
        if self.parsed_url is None:
            return None
        return f"{self.parsed_url.scheme}://{self.parsed_url.netloc}"

    @property
    def path(self) -> str | None:
        if self.parsed_url is None:
            return None
        return self.parsed_url.path

    @property
    def query(self) -> str | None:
        if self.parsed_url is None:
            return None
        return self.parsed_url.query
