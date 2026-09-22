"""Заглушка транспорта: отдаёт сложенные ответы и запоминает, что просили."""

import urllib.parse
from typing import Any, Dict, List, Optional

from jsonseo.transport import Response


class FakeTransport:
    def __init__(self) -> None:
        self.requests: List[Dict[str, Any]] = []
        self._queue: List[Any] = []

    def queue_json(self, body: Any, status: int = 200, headers: Optional[Dict[str, str]] = None):
        import json

        self._queue.append(Response(status, headers or {}, json.dumps(body)))

        return self

    def queue_raw(self, body: str, status: int = 200, headers: Optional[Dict[str, str]] = None):
        self._queue.append(Response(status, headers or {}, body))

        return self

    def queue_error(self, error: BaseException):
        self._queue.append(error)

        return self

    def send(self, method: str, url: str, headers: Dict[str, str], body: Optional[str], timeout: float):
        self.requests.append(
            {
                "method": method,
                "url": url,
                "headers": headers,
                "body": body,
                "params": dict(urllib.parse.parse_qsl(body or "", keep_blank_values=True)),
                "timeout": timeout,
            }
        )

        if not self._queue:
            raise AssertionError("В очереди заглушки не осталось ответов, а запрос пришёл.")

        nxt = self._queue.pop(0)

        if isinstance(nxt, BaseException):
            raise nxt

        return nxt

    @property
    def count(self) -> int:
        return len(self.requests)

    def params(self, index: int = 0) -> Dict[str, str]:
        return self.requests[index]["params"]
