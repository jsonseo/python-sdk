"""Как SDK ходит в сеть. Подменяется в тестах и в проектах со своим клиентом."""

import http.client
import socket
import urllib.error
import urllib.request
from typing import Dict, Optional

from .errors import IncompleteResponseError, JsonSeoError, NetworkError, TimeoutError


class Response:
    """Сырой ответ транспорта: статус, заголовки и тело как есть."""

    __slots__ = ("status", "headers", "body")

    def __init__(self, status: int, headers: Dict[str, str], body: str) -> None:
        self.status = int(status)
        # Имена в нижнем регистре — HTTP их регистр не различает.
        self.headers = {name.lower(): value for name, value in headers.items()}
        self.body = body

    def header(self, name: str) -> Optional[str]:
        return self.headers.get(name.lower())


class UrllibTransport:
    """
    Транспорт на стандартной библиотеке: пакет остаётся без зависимостей.

    Свой транспорт — это объект с таким же методом send. Он обязан бросать
    ошибки SDK: от их класса зависит, повторит клиент запрос или нет.
    """

    def send(
        self,
        method: str,
        url: str,
        headers: Dict[str, str],
        body: Optional[str],
        timeout: float,
    ) -> Response:
        data = body.encode("utf-8") if body is not None else None
        request = urllib.request.Request(url, data=data, method=method)

        for name, value in headers.items():
            # urllib сам подставляет свой User-Agent, если его не задать.
            request.add_header(name, value)

        response = self._open(request, timeout)

        # Чтение тела намеренно вынесено из-под обработки ошибок соединения:
        # сюда мы попадаем, только когда заголовки уже пришли, а значит
        # выдача собрана и оплачена. Любой сбой отсюда повторять нельзя.
        with response:
            return self._read(response)

    def _open(self, request: urllib.request.Request, timeout: float):
        try:
            return urllib.request.urlopen(request, timeout=timeout)
        except urllib.error.HTTPError as error:
            # Это не сбой, а ответ с кодом 4xx или 5xx: сообщение сервиса
            # о причине отказа лежит в теле, и терять его нельзя.
            return error
        except socket.timeout as error:
            raise TimeoutError("Ответа от JSON SEO API не дождались.") from error
        except urllib.error.URLError as error:
            if isinstance(error.reason, socket.timeout):
                raise TimeoutError("Ответа от JSON SEO API не дождались.") from error

            raise NetworkError("Запрос к JSON SEO API не удался: {}.".format(error.reason)) from error
        except OSError as error:
            raise NetworkError("Запрос к JSON SEO API не удался: {}.".format(error)) from error

    def _read(self, response) -> Response:
        try:
            raw = response.read()
        except http.client.IncompleteRead as error:
            raise IncompleteResponseError(self._incomplete_message(error)) from error
        except socket.timeout as error:
            raise TimeoutError("Ответа от JSON SEO API не дождались: тело пришло не целиком.") from error
        except JsonSeoError:
            # Наши собственные ошибки наследуют OSError и не должны попадать
            # под общий перехват ниже.
            raise
        except OSError as error:
            # Сброс соединения на середине тела: чистого EOF не было, но
            # выдача всё равно уже собрана и оплачена.
            raise IncompleteResponseError(
                "Ответ от JSON SEO API пришёл не целиком: {}.".format(error)
            ) from error

        headers = {name: value for name, value in response.headers.items()}

        return Response(response.status, headers, raw.decode("utf-8", errors="replace"))

    def _incomplete_message(self, error: http.client.IncompleteRead) -> str:
        # У обрыва chunked-ответа expected равен None: сколько обещали,
        # неизвестно, и придумывать число нельзя.
        if error.expected is None:
            return "Ответ от JSON SEO API пришёл не целиком: получено {} байт, передача оборвалась.".format(
                len(error.partial)
            )

        return "Ответ от JSON SEO API пришёл не целиком: получено {} из {} байт.".format(
            len(error.partial), len(error.partial) + error.expected
        )
