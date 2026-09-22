"""Ошибки SDK."""

from typing import Any, Dict, List, Optional

_BuiltinTimeoutError = TimeoutError


class JsonSeoError(Exception):
    """Общий предок всех ошибок SDK."""


class ApiError(JsonSeoError):
    """Сервис ответил отказом. Тело сохраняется целиком."""

    def __init__(
        self,
        message: str,
        status: int,
        body: str = "",
        payload: Optional[Dict[str, Any]] = None,
        retry_after: Optional[int] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status = status
        self.body = body
        self.payload = payload or {}
        # Через сколько секунд вернуться. None, если срок не назван.
        self.retry_after = retry_after


class PaymentRequiredError(ApiError):
    """402: на счёте не хватает средств, см. balance()."""


class UnauthorizedError(ApiError):
    """403 или 401: ключ не передан или недействителен."""


class ServiceUnavailableError(ApiError):
    """503: выдачу получить не вышло. Деньги не списаны, SDK повторит сам."""


class RateLimitError(ApiError):
    """429: превышен лимит частоты. Срок повтора — в retry_after."""


class ValidationError(ApiError):
    """422: параметры не приняты. Деньги не списываются."""

    @property
    def errors(self) -> Dict[str, List[str]]:
        """Ошибки по именам параметров: {'text': ['Введите запрос']}."""
        raw = self.payload.get("errors")

        if not isinstance(raw, dict):
            return {}

        return {
            field: [str(m) for m in messages] if isinstance(messages, list) else [str(messages)]
            for field, messages in raw.items()
        }

    @property
    def fields(self) -> List[str]:
        """Забракованные параметры."""
        return list(self.errors)


class NetworkError(JsonSeoError):
    """До сервиса не достучались: сеть, DNS, TLS. Статуса нет."""


class TimeoutError(NetworkError, _BuiltinTimeoutError):  # noqa: A001
    """
    Ответа не дождались. Автоматически не повторяется: выдача всё равно
    будет собрана и оплачена. Нужен ответ — поднимайте timeout, не attempts.

    Наследует и встроенный TimeoutError, чтобы привычный except его ловил.
    """


class IncompleteResponseError(NetworkError):
    """
    Пришло меньше, чем обещал сервис. Автоматически не повторяется: выдача
    уже собрана и оплачена, обрыв случился на отдаче.
    """


class ParseError(JsonSeoError):
    """
    Успех, но тело не разобралось как JSON. Тело сохраняется: страница уже
    оплачена, и достать из неё данные руками лучше, чем не иметь ничего.
    """

    def __init__(self, message: str, body: str) -> None:
        super().__init__(message)
        self.body = body


class InvalidArgumentError(JsonSeoError):
    """SDK забраковал аргументы, запрос не отправлялся."""


_BY_STATUS = {
    401: UnauthorizedError,
    402: PaymentRequiredError,
    403: UnauthorizedError,
    422: ValidationError,
    429: RateLimitError,
    503: ServiceUnavailableError,
}


def api_error_for(
    status: int,
    body: str,
    payload: Dict[str, Any],
    retry_after: Optional[int],
) -> ApiError:
    """Собирает ошибку под этот HTTP-статус."""
    message = payload.get("message")

    if not isinstance(message, str) or message == "":
        message = "JSON SEO API вернул ошибку {}.".format(status)

    return _BY_STATUS.get(status, ApiError)(message, status, body, payload, retry_after)
