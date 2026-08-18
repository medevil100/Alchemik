"""
Yahoo transport layer (curl_cffi).

A single fresh session impersonating Chrome is used for cookie, crumb,
screener and chart requests. The transport is injectable so offline tests can
substitute a fake without touching the network.
"""

from typing import Protocol


class Response:
    """Neutral HTTP response wrapper (status code + decoded text)."""

    def __init__(self, status_code: int, text: str, url: str = ""):
        self.status_code = status_code
        self.text = text
        self.url = url

    def json(self):
        import json

        return json.loads(self.text)

    def __repr__(self) -> str:
        return f"Response(status_code={self.status_code}, url={self.url!r})"


class Transport(Protocol):
    """Minimal transport contract used by YahooSession."""

    request_count: int

    def get(self, url: str, params: dict = None, timeout: int = 30) -> Response: ...
    def post(self, url: str, data: str = None, headers: dict = None,
             params: dict = None, timeout: int = 30) -> Response: ...


class CurlCffiTransport:
    """
    Production transport backed by curl_cffi.requests.Session with Chrome
    impersonation, a single fresh session, timeout=30, allow_redirects=False,
    and no retry / no fallback.
    """

    TIMEOUT = 30

    def __init__(self):
        from curl_cffi import requests

        self._session = requests.Session(impersonate="chrome")
        self.request_count = 0
        self.requests_log: list = []

    @property
    def cookies(self):
        """Expose the underlying cookie jar holder (has .jar)."""
        return self._session.cookies

    def _record(self):
        self.request_count += 1

    def get(self, url: str, params: dict = None, timeout: int = TIMEOUT) -> Response:
        self._record()
        response = self._session.get(
            url,
            params=params,
            timeout=timeout,
            allow_redirects=False,
        )
        self.requests_log.append({
            "method": "GET",
            "url": url,
            "status_code": response.status_code,
        })
        return Response(status_code=response.status_code, text=response.text, url=str(response.url))

    def post(self, url: str, data: str = None, headers: dict = None,
             params: dict = None, timeout: int = TIMEOUT) -> Response:
        self._record()
        response = self._session.post(
            url,
            data=data,
            headers=headers,
            params=params,
            timeout=timeout,
            allow_redirects=False,
        )
        self.requests_log.append({
            "method": "POST",
            "url": url,
            "status_code": response.status_code,
        })
        return Response(status_code=response.status_code, text=response.text, url=str(response.url))
