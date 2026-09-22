"""Клиент JSON SEO API."""

import email.utils
import json
import random
import time
import urllib.parse
from typing import Any, Dict, Optional, Sequence, Union

from .errors import (
    IncompleteResponseError,
    InvalidArgumentError,
    NetworkError,
    ParseError,
    TimeoutError,
    api_error_for,
)
from .transport import Response, UrllibTransport
from .types import (
    BalanceResponse,
    DirectResponse,
    GeoipResponse,
    GoogleRegionsResponse,
    ImagesResponse,
    SearchResponse,
    SuggestResponse,
    VideoResponse,
    WordstatFrequencyResponse,
    WordstatGraphResponse,
    WordstatMapResponse,
    WordstatResponse,
    YandexRegionsResponse,
)

__all__ = ["Client"]

VERSION = "1.0.0"
DEFAULT_BASE_URL = "https://jsonseo.ru/api"

Primary = Union[str, int, Sequence[str], None]


class Client:
    """
    Клиент JSON SEO API.

    >>> client = Client("ВАШ_КЛЮЧ")
    >>> serp = client.yandex("купить ноутбук", region=213)
    """

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 300.0,
        attempts: int = 3,
        retry_delay: float = 1.0,
        max_retry_delay: float = 30.0,
        auth: str = "header",
        user_agent: Optional[str] = None,
        transport: Any = None,
    ) -> None:
        if not isinstance(api_key, str) or api_key.strip() == "":
            raise InvalidArgumentError(
                "Нужен API-ключ: возьмите его в личном кабинете на https://jsonseo.ru."
            )

        if auth not in ("header", "query"):
            raise InvalidArgumentError(
                'Настройка auth принимает "header" или "query", получено: {!r}.'.format(auth)
            )

        if not isinstance(attempts, int) or isinstance(attempts, bool) or attempts < 1:
            raise InvalidArgumentError(
                "Настройка attempts ожидает целое число не меньше 1, получено: {!r}.".format(attempts)
            )

        self._api_key = api_key.strip()
        self._base_url = base_url.rstrip("/")
        # Многостраничная выдача идёт минутами, и оборванный запрос всё
        # равно будет досчитан и оплачен.
        self._timeout = float(timeout)
        self._attempts = attempts
        self._retry_delay = float(retry_delay)
        self._max_retry_delay = float(max_retry_delay)
        self._auth = auth
        self._user_agent = user_agent or "jsonseo-python/{}".format(VERSION)
        self._transport = transport or UrllibTransport()

    # --- Яндекс ---

    def yandex(self, text: Primary = None, **params: Any) -> SearchResponse:
        """Органическая выдача Яндекса: мобильная, регион 213. 0.01 ₽ за страницу."""
        return self._request("yandex", self._primary(text, "text", params))

    def yandex_suggest(self, text: Primary = None, **params: Any) -> SuggestResponse:
        """Подсказки Яндекса: до 50 фраз с учётом региона. 0.01 ₽ за запрос."""
        return self._request("yandex/suggest", self._primary(text, "text", params))

    def yandex_regions(self, name: Primary = None, **params: Any) -> YandexRegionsResponse:
        """Код региона (lr) по названию города или области. Бесплатно, нужен ключ."""
        return self._request("yandex/regions", self._primary(name, "name", params))

    def yandex_images(self, q: Primary = None, **params: Any) -> ImagesResponse:
        """Картинки Яндекса: 20 карточек на страницу, 0.01 ₽ за страницу."""
        return self._request("yandex/images", self._primary(q, "q", params))

    def yandex_video(self, q: Primary = None, **params: Any) -> VideoResponse:
        """Видео Яндекса: 20 карточек на страницу, 0.01 ₽ за страницу."""
        return self._request("yandex/video", self._primary(q, "q", params))

    # --- Google ---

    def google(self, q: Primary = None, **params: Any) -> SearchResponse:
        """Органическая выдача google.com: мобильная, 0.01 ₽ за страницу."""
        return self._request("google", self._primary(q, "q", params))

    def google_suggest(self, q: Primary = None, **params: Any) -> SuggestResponse:
        """Подсказки Google: до ~15 фраз. 0.01 ₽ за запрос."""
        return self._request("google/suggest", self._primary(q, "q", params))

    def google_regions(self, name: Primary = None, **params: Any) -> GoogleRegionsResponse:
        """ID региона Google по названию и готовый uule. Бесплатно, нужен ключ."""
        return self._request("google/regions", self._primary(name, "name", params))

    def google_images(self, q: Primary = None, **params: Any) -> ImagesResponse:
        """Картинки Google: 100 карточек на страницу, 0.01 ₽ за страницу."""
        return self._request("google/images", self._primary(q, "q", params))

    def google_video(self, q: Primary = None, **params: Any) -> VideoResponse:
        """Видео Google: 10 карточек на страницу, 0.01 ₽ за страницу."""
        return self._request("google/video", self._primary(q, "q", params))

    # --- Bing ---

    def bing(self, q: Primary = None, **params: Any) -> SearchResponse:
        """Органическая выдача bing.com: без локации — Россия, 0.01 ₽ за страницу."""
        return self._request("bing", self._primary(q, "q", params))

    def bing_suggest(self, q: Primary = None, **params: Any) -> SuggestResponse:
        """Подсказки Bing. 0.01 ₽ за запрос."""
        return self._request("bing/suggest", self._primary(q, "q", params))

    def bing_images(self, q: Primary = None, **params: Any) -> ImagesResponse:
        """Картинки Bing: count карточек (по умолчанию 35), дальше 700-й не листает."""
        return self._request("bing/images", self._primary(q, "q", params))

    def bing_video(self, q: Primary = None, **params: Any) -> VideoResponse:
        """Видео Bing: count карточек на страницу, по умолчанию 105."""
        return self._request("bing/video", self._primary(q, "q", params))

    # --- Вордстат ---

    def wordstat(self, text: Primary = None, **params: Any) -> WordstatResponse:
        """Популярные и похожие запросы. 0.01 ₽ за запрос."""
        return self._request("wordstat", self._primary(text, "text", params))

    def wordstat_frequency(self, text: Primary = None, **params: Any) -> WordstatFrequencyResponse:
        """Частота запроса одним числом — results.totalValue. 0.01 ₽ за запрос."""
        return self._request("wordstat/frequency", self._primary(text, "text", params))

    def wordstat_graph(self, text: Primary = None, **params: Any) -> WordstatGraphResponse:
        """Динамика показов: month и week — с 2018 года, day — последние 60 дней."""
        return self._request("wordstat/graph", self._primary(text, "text", params))

    def wordstat_map(self, text: Primary = None, **params: Any) -> WordstatMapResponse:
        """Показы по регионам и городам. popularity — affinity-индекс, 100 — средний."""
        return self._request("wordstat/map", self._primary(text, "text", params))

    # --- Директ и служебные ---

    def direct(self, phrases: Primary = None, **params: Any) -> DirectResponse:
        """
        Прогноз показов Директа со ставками и бюджетом. Кабинет не нужен.

        Список фраз передаётся как есть — SDK склеит его сам. Вид частотности
        задаётся операторами во фразе: "ремонт айфона" — фразовая,
        "!ремонт !айфона" — точная.
        """
        return self._request("direct", self._primary(phrases, "phrases", params))

    def geoip(self, ip: Primary = None, **params: Any) -> GeoipResponse:
        """Страна, регион и координаты по IPv4. Бесплатно, нужен ключ."""
        return self._request("geoip", self._primary(ip, "ip", params))

    def balance(self) -> BalanceResponse:
        """Текущий баланс. Бесплатно, нужен ключ."""
        return self._request("balance", {})

    # --- Запасной выход ---

    def call(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Произвольный метод API — если в сервисе появился новый."""
        return self._request(path, dict(params or {}))

    def call_raw(self, path: str, params: Optional[Dict[str, Any]] = None) -> str:
        """То же, но ответ возвращается строкой без разбора."""
        return self._request(path, dict(params or {}), decode_json=False)

    # --- Внутреннее ---

    def _primary(self, value: Primary, name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Даёт вызывать метод позиционно: yandex("купить ноутбук").

        Дубль (и позиционно, и по имени) ловит сам Python: у аргумента то же
        имя, что у параметра, и вызов не состоится.
        """
        if value is not None:
            params[name] = value

        return params

    def _request(self, path: str, params: Dict[str, Any], decode_json: bool = True) -> Any:
        """
        Выполняет запрос, повторяя те отказы, за которые сервис не берёт
        денег: 429, 5xx и обрывы связи до того, как ответ начал приходить.
        """
        query = self._normalize(params)

        if self._auth == "query":
            query["key"] = self._api_key

        headers = {
            "Accept": "application/json" if decode_json else "application/xml, text/xml",
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": self._user_agent,
        }

        if self._auth == "header":
            headers["Authorization"] = "Bearer " + self._api_key

        # Всегда POST: длинные списки фраз в GET не помещаются.
        url = "{}/{}".format(self._base_url, path.lstrip("/"))
        body = urllib.parse.urlencode(query)

        attempt = 0

        while True:
            try:
                response = self._transport.send("POST", url, headers, body, self._timeout)
            except NetworkError as error:
                # Таймаут и обрыв на середине тела не повторяем: выдача уже
                # собрана и оплачена.
                if (
                    self._is_last_attempt(attempt)
                    or isinstance(error, (TimeoutError, IncompleteResponseError))
                ):
                    raise

                time.sleep(self._backoff(attempt))
                attempt += 1

                continue

            if 200 <= response.status < 300:
                return self._decode(response.body) if decode_json else response.body

            retry_after = self._retry_after(response)
            error = api_error_for(
                response.status, response.body, self._decode_quietly(response.body), retry_after
            )

            # Проснуться раньше названного срока — снова получить тот же
            # отказ. Ждать дольше потолка не станем: отдаём ошибку.
            if (
                self._is_last_attempt(attempt)
                or not self._is_retryable(response.status)
                or (retry_after is not None and retry_after > self._max_retry_delay)
            ):
                raise error

            # Не раньше, чем просит сервис, и не чаще своего бэкоффа:
            # Retry-After прошедшей датой даёт ноль.
            pause = self._backoff(attempt)
            time.sleep(pause if retry_after is None else max(float(retry_after), pause))
            attempt += 1

    def _is_last_attempt(self, attempt: int) -> bool:
        """Попытки нумеруются с нуля: при attempts = 3 у последней индекс 2."""
        return attempt + 1 >= self._attempts

    def _is_retryable(self, status: int) -> bool:
        return status == 429 or status >= 500

    def _normalize(self, params: Dict[str, Any]) -> Dict[str, str]:
        """Приводит параметры к тому виду, в каком их ждёт форма запроса."""
        normalized = {}

        for name, value in params.items():
            if value is None:
                continue

            if isinstance(value, bool):
                normalized[name] = "1" if value else "0"

                continue

            if isinstance(value, (list, tuple)):
                items = list(value)

                # Пустой список — «параметр не задан»: от region= сервис
                # отказал бы валидацией.
                if not items:
                    continue

                # Фразы — переводом строки: запятая в них встречается.
                separator = "\n" if name == "phrases" else ","
                normalized[name] = separator.join(
                    self._scalar(item, "{}[{}]".format(name, index)) for index, item in enumerate(items)
                )

                continue

            normalized[name] = self._scalar(value, name)

        return normalized

    def _scalar(self, value: Any, name: str) -> str:
        if isinstance(value, bool):
            return "1" if value else "0"

        if isinstance(value, (int, float)):
            return str(value)

        if isinstance(value, str):
            return value

        if isinstance(value, (set, frozenset)):
            raise InvalidArgumentError(
                "Параметр {} получил множество: порядок его обхода не определён, "
                "и запрос перестал бы быть воспроизводимым. Передайте список.".format(name)
            )

        raise InvalidArgumentError(
            "Значение параметра {} должно быть строкой, числом, флагом или списком "
            "таких значений, получено: {!r}.".format(name, value)
        )

    def _decode(self, body: str) -> Any:
        try:
            return json.loads(body)
        except ValueError as error:
            # Тело кладём в ошибку: страница выдачи уже оплачена.
            raise ParseError(
                "Ответ JSON SEO API не разобрался как JSON: {}.".format(error), body
            ) from error

    def _decode_quietly(self, body: str) -> Dict[str, Any]:
        """Тело ошибки может быть и не JSON — тогда подробностей просто нет."""
        try:
            parsed = json.loads(body)
        except ValueError:
            return {}

        return parsed if isinstance(parsed, dict) else {}

    def _retry_after(self, response: Response) -> Optional[int]:
        """
        Сколько секунд просит подождать сервис. RFC 9110 разрешает число
        секунд и HTTP-дату, разбираются обе.
        """
        value = response.header("retry-after")

        if value is None:
            return None

        value = value.strip()

        # isdigit() истинно и для юникод-цифр вроде «²», которые int() не
        # берёт: без проверки на ASCII запрос падал бы голым ValueError.
        if value.isascii() and value.isdigit():
            return int(value)

        try:
            when = email.utils.parsedate_to_datetime(value)
        except (TypeError, ValueError):
            return None

        if when is None:
            return None

        return max(0, int(when.timestamp() - time.time()))

    def _backoff(self, attempt: int) -> float:
        """
        Пауза удваивается с каждой попыткой; случайная добавка разводит
        параллельные запросы, чтобы они не вернулись разом.
        """
        delay = self._retry_delay * (2 ** attempt)

        # Потолок накладывается после добавки, иначе она бы его превышала.
        return min(delay + delay * 0.25 * random.random(), self._max_retry_delay)
