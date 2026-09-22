import email.utils
import time
import unittest

from jsonseo import (
    Client,
    IncompleteResponseError,
    NetworkError,
    PaymentRequiredError,
    RateLimitError,
    ServiceUnavailableError,
    TimeoutError,
    UnauthorizedError,
    ValidationError,
)
from tests.fake import FakeTransport


class RetryTest(unittest.TestCase):
    """Паузы обнулены: проверяется решение о повторе, а не длительность сна."""

    def setUp(self) -> None:
        self.transport = FakeTransport()

    def client(self, **options) -> Client:
        options.setdefault("retry_delay", 0.0)
        options.setdefault("max_retry_delay", 0.0)

        return Client("KEY", transport=self.transport, **options)

    def test_three_attempts_by_default(self):
        """По умолчанию у запроса три попытки: одна основная и две повторных."""
        for _ in range(3):
            self.transport.queue_json({"message": "Недоступен"}, 503)
        self.transport.queue_json({"results": ["лишний"]})

        # Настройку не трогаем: проверяется именно значение по умолчанию.
        api = Client("KEY", transport=self.transport, retry_delay=0.0, max_retry_delay=0.0)

        with self.assertRaises(ServiceUnavailableError):
            api.yandex("тест")

        self.assertEqual(3, self.transport.count)

    def test_slow_service_succeeds_on_a_later_attempt(self):
        """Затупивший сервис успевает ответить с третьей попытки."""
        self.transport.queue_json({"message": "Недоступен"}, 503)
        self.transport.queue_json({"message": "Недоступен"}, 503)
        self.transport.queue_json({"results": ["ok"]})

        self.assertEqual(["ok"], self.client().yandex("тест")["results"])
        self.assertEqual(3, self.transport.count)

    def test_attempts_stop_at_the_configured_limit(self):
        for _ in range(3):
            self.transport.queue_json({"message": "Too Many Attempts."}, 429)

        with self.assertRaises(RateLimitError):
            self.client(attempts=3).yandex("тест")

        self.assertEqual(3, self.transport.count)

    def test_a_single_attempt_means_no_retries(self):
        self.transport.queue_error(NetworkError("сеть недоступна"))

        with self.assertRaises(NetworkError):
            self.client(attempts=1).yandex("тест")

        self.assertEqual(1, self.transport.count)

    def test_server_errors_are_retried(self):
        for status in (500, 502, 504):
            transport = FakeTransport()
            transport.queue_json({"message": "Ошибка"}, status).queue_json({"results": []})

            Client("KEY", transport=transport, retry_delay=0.0, max_retry_delay=0.0).yandex("тест")

            self.assertEqual(2, transport.count, "статус {} должен повторяться".format(status))

    def test_broken_connection_is_retried(self):
        self.transport.queue_error(NetworkError("соединение оборвано"))
        self.transport.queue_json({"results": []})

        self.client().yandex("тест")

        self.assertEqual(2, self.transport.count)

    def test_client_errors_are_not_retried(self):
        for status, expected in ((422, ValidationError), (402, PaymentRequiredError), (403, UnauthorizedError)):
            transport = FakeTransport().queue_json({"message": "нет"}, status)

            with self.assertRaises(expected):
                Client("KEY", transport=transport, retry_delay=0.0, max_retry_delay=0.0).yandex("тест")

            self.assertEqual(1, transport.count)

    def test_timeout_is_not_retried(self):
        """Сервис уже считает оплаченный запрос — повтор стоил бы ещё раз."""
        self.transport.queue_error(TimeoutError("не дождались"))
        self.transport.queue_json({"results": []})

        with self.assertRaises(TimeoutError):
            self.client().yandex("тест")

        self.assertEqual(1, self.transport.count)

    def test_incomplete_response_is_not_retried(self):
        self.transport.queue_error(IncompleteResponseError("пришло меньше обещанного"))
        self.transport.queue_json({"results": []})

        with self.assertRaises(IncompleteResponseError):
            self.client().yandex("тест")

        self.assertEqual(1, self.transport.count)

    def test_retry_after_sets_the_pause(self):
        """Проснуться раньше названного срока — снова получить тот же отказ."""
        self.transport.queue_json({"message": "Too Many Attempts."}, 429, {"Retry-After": "1"})
        self.transport.queue_json({"results": []})

        started = time.monotonic()
        self.client(max_retry_delay=30.0).yandex("тест")

        self.assertEqual(2, self.transport.count)
        # Допуск на зернистость таймера: на Windows сон отмеряется с
        # точностью до миллисекунд в меньшую сторону.
        self.assertGreaterEqual(time.monotonic() - started, 0.95)

    def test_retry_after_beyond_the_cap_stops_retrying(self):
        """Дольше потолка SDK не ждёт: отдаёт ошибку с retry_after."""
        self.transport.queue_json({"message": "Too Many Attempts."}, 429, {"Retry-After": "600"})
        self.transport.queue_json({"results": []})

        with self.assertRaises(RateLimitError) as caught:
            self.client(max_retry_delay=30.0).yandex("тест")

        self.assertEqual(1, self.transport.count)
        self.assertEqual(600, caught.exception.retry_after)

    def test_retry_after_accepts_an_http_date(self):
        """RFC 9110 разрешает и HTTP-дату."""
        when = email.utils.formatdate(time.time() + 600, usegmt=True)
        self.transport.queue_json({"message": "Too Many Attempts."}, 429, {"Retry-After": when})

        with self.assertRaises(RateLimitError) as caught:
            self.client(max_retry_delay=30.0).yandex("тест")

        self.assertGreater(caught.exception.retry_after, 500)

    def test_service_unavailable_also_keeps_retry_after(self):
        self.transport.queue_json({"message": "Недоступен"}, 503, {"Retry-After": "120"})

        with self.assertRaises(ServiceUnavailableError) as caught:
            self.client(max_retry_delay=30.0).yandex("тест")

        self.assertEqual(120, caught.exception.retry_after)

    def test_backoff_grows_and_respects_the_cap(self):
        """Во всех остальных тестах паузы обнулены, и сам бэкофф не исполняется."""
        client = Client("KEY", transport=self.transport, retry_delay=0.1, max_retry_delay=0.25)

        first = client._backoff(0)
        second = client._backoff(1)
        far = client._backoff(10)

        self.assertGreaterEqual(first, 0.1)
        self.assertLessEqual(first, 0.25)
        self.assertGreaterEqual(second, 0.2)
        self.assertLessEqual(far, 0.25, "потолок должен накладываться после джиттера")

    def test_pause_is_not_shorter_than_the_backoff(self):
        """Обратный случай: сервис просит меньше, чем наш собственный бэкофф."""
        self.transport.queue_json({"message": "Too Many Attempts."}, 429, {"Retry-After": "0"})
        self.transport.queue_json({"results": []})

        started = time.monotonic()
        self.client(retry_delay=0.3, max_retry_delay=5.0).yandex("тест")

        self.assertEqual(2, self.transport.count)
        self.assertGreaterEqual(time.monotonic() - started, 0.28)

    def test_retry_after_in_the_past_falls_back_to_backoff(self):
        when = email.utils.formatdate(time.time() - 600, usegmt=True)
        self.transport.queue_json({"message": "Too Many Attempts."}, 429, {"Retry-After": when})
        self.transport.queue_json({"results": []})

        self.client(max_retry_delay=5.0).yandex("тест")

        self.assertEqual(2, self.transport.count)

    def test_garbage_retry_after_does_not_break_the_request(self):
        """isdigit() истинно и для юникод-цифр, которые int() не берёт."""
        for value in ("\u00b2", "позже", ""):
            transport = FakeTransport()
            transport.queue_json({"message": "Too Many Attempts."}, 429, {"Retry-After": value})

            with self.assertRaises(RateLimitError) as caught:
                Client("KEY", transport=transport, attempts=1).yandex("тест")

            self.assertIsNone(caught.exception.retry_after, "значение {!r}".format(value))

    def test_repeated_request_carries_the_same_body(self):
        self.transport.queue_json({"message": "Недоступен"}, 503)
        self.transport.queue_json({"results": []})

        self.client().yandex("купить ноутбук", pages=3)

        self.assertEqual(self.transport.requests[0]["body"], self.transport.requests[1]["body"])


if __name__ == "__main__":
    unittest.main()
