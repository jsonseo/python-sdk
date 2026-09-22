import unittest

from jsonseo import (
    ApiError,
    Client,
    PaymentRequiredError,
    RateLimitError,
    ServiceUnavailableError,
    UnauthorizedError,
    ValidationError,
)
from tests.fake import FakeTransport


class TimeoutInheritanceTest(unittest.TestCase):
    """Привычный except со встроенным TimeoutError обязан ловить и нашу."""

    def test_our_timeout_is_also_a_builtin_timeout(self):
        from jsonseo import JsonSeoError, NetworkError
        from jsonseo import TimeoutError as JsonSeoTimeoutError

        error = JsonSeoTimeoutError("не дождались")

        self.assertIsInstance(error, TimeoutError)
        self.assertIsInstance(error, NetworkError)
        self.assertIsInstance(error, JsonSeoError)


class ErrorsTest(unittest.TestCase):
    """Повторы выключены: проверяется разбор отказа, а не поведение при нём."""

    def setUp(self) -> None:
        self.transport = FakeTransport()

    def client(self) -> Client:
        return Client("KEY", transport=self.transport, attempts=1)

    def test_missing_funds(self):
        self.transport.queue_json({"message": "На аккаунте недостаточно средств."}, 402)

        with self.assertRaises(PaymentRequiredError) as caught:
            self.client().yandex("тест")

        self.assertEqual(402, caught.exception.status)
        self.assertEqual("На аккаунте недостаточно средств.", caught.exception.message)

    def test_bad_key(self):
        for status in (401, 403):
            transport = FakeTransport().queue_json({"message": "Недействительный токен."}, status)

            with self.assertRaises(UnauthorizedError):
                Client("KEY", transport=transport, attempts=1).yandex("тест")

    def test_validation_carries_field_messages(self):
        self.transport.queue_json(
            {"message": "Введите запрос", "errors": {"text": ["Введите запрос"]}}, 422
        )

        with self.assertRaises(ValidationError) as caught:
            self.client().yandex("")

        self.assertEqual({"text": ["Введите запрос"]}, caught.exception.errors)
        self.assertEqual(["text"], caught.exception.fields)

    def test_validation_without_fields(self):
        self.transport.queue_json({"message": "Что-то не так"}, 422)

        with self.assertRaises(ValidationError) as caught:
            self.client().yandex("тест")

        self.assertEqual({}, caught.exception.errors)

    def test_rate_limit_keeps_retry_after(self):
        self.transport.queue_json({"message": "Too Many Attempts."}, 429, {"Retry-After": "17"})

        with self.assertRaises(RateLimitError) as caught:
            self.client().yandex("тест")

        self.assertEqual(17, caught.exception.retry_after)

    def test_rate_limit_without_header(self):
        self.transport.queue_json({"message": "Too Many Attempts."}, 429)

        with self.assertRaises(RateLimitError) as caught:
            self.client().yandex("тест")

        self.assertIsNone(caught.exception.retry_after)

    def test_failed_search(self):
        self.transport.queue_json({"message": "Сервис временно недоступен."}, 503)

        with self.assertRaises(ServiceUnavailableError):
            self.client().yandex("тест")

    def test_unknown_status_is_still_an_api_error(self):
        self.transport.queue_json({"message": "Чайник"}, 418)

        with self.assertRaises(ApiError) as caught:
            self.client().yandex("тест")

        self.assertEqual(418, caught.exception.status)

    def test_non_json_error_body_keeps_status(self):
        self.transport.queue_raw("<html>502 Bad Gateway</html>", 502)

        with self.assertRaises(ApiError) as caught:
            self.client().yandex("тест")

        self.assertEqual(502, caught.exception.status)
        self.assertEqual("<html>502 Bad Gateway</html>", caught.exception.body)
        self.assertEqual({}, caught.exception.payload)
        self.assertEqual("JSON SEO API вернул ошибку 502.", caught.exception.message)


if __name__ == "__main__":
    unittest.main()
