"""
Транспорт против настоящего сокета.

Заглушка в остальных тестах проверяет клиент, но не его самого, а
обнаружение обрыва живёт именно здесь — и молча обрезанное тело дороже
любой другой ошибки в библиотеке: клиент за эту выдачу уже заплатил.
"""

import socket
import struct
import threading
import unittest

from jsonseo import Client, IncompleteResponseError, NetworkError, TimeoutError
from jsonseo.transport import UrllibTransport


class Server:
    """Отвечает по заданному сценарию и закрывается, как велено."""

    def __init__(self, handler):
        self.handler = handler
        self.socket = socket.socket()
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(("127.0.0.1", 0))
        self.socket.listen(1)
        self.port = self.socket.getsockname()[1]
        self.thread = threading.Thread(target=self._serve, daemon=True)
        self.thread.start()

    def _serve(self):
        try:
            connection, _ = self.socket.accept()
        except OSError:
            return

        try:
            self._read_request(connection)
            self.handler(connection)
        except OSError:
            pass
        finally:
            try:
                connection.close()
            except OSError:
                pass

    def _read_request(self, connection):
        connection.settimeout(5)
        head = b""

        while b"\r\n\r\n" not in head:
            chunk = connection.recv(4096)

            if not chunk:
                return

            head += chunk

        # Тело запроса: без него клиент упрётся в обрыв вместо ответа.
        length = 0
        for line in head.split(b"\r\n"):
            if line.lower().startswith(b"content-length:"):
                length = int(line.split(b":")[1].strip())

        received = len(head.split(b"\r\n\r\n", 1)[1])
        while received < length:
            chunk = connection.recv(length - received)

            if not chunk:
                break

            received += len(chunk)

    @property
    def url(self):
        return "http://127.0.0.1:{}/api".format(self.port)

    def close(self):
        try:
            self.socket.close()
        except OSError:
            pass


def reset(connection):
    """Рвёт соединение через RST — так ведёт себя NAT или балансировщик."""
    connection.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack("ii", 1, 0))
    connection.close()


class TransportTest(unittest.TestCase):
    def send(self, server, timeout=5.0):
        return UrllibTransport().send(
            "POST",
            server.url + "/balance",
            {"Accept": "application/json", "Content-Type": "application/x-www-form-urlencoded"},
            "a=1",
            timeout,
        )

    def serve(self, handler):
        server = Server(handler)
        self.addCleanup(server.close)

        return server

    def test_reads_status_headers_and_body(self):
        body = b'{"balance":123.45,"currency":"RUB"}'

        def handler(connection):
            connection.sendall(
                b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n"
                b"X-Sample-Header: value\r\n"
                b"Content-Length: " + str(len(body)).encode() + b"\r\n"
                b"Connection: close\r\n\r\n" + body
            )

        response = self.send(self.serve(handler))

        self.assertEqual(200, response.status)
        self.assertEqual(body.decode(), response.body)
        self.assertEqual("application/json", response.header("Content-Type"))
        self.assertEqual("value", response.header("x-sample-header"))

    def test_keeps_error_status_and_retry_after(self):
        body = b'{"message":"Too Many Attempts."}'

        def handler(connection):
            connection.sendall(
                b"HTTP/1.1 429 Too Many Requests\r\nContent-Type: application/json\r\n"
                b"Retry-After: 17\r\n"
                b"Content-Length: " + str(len(body)).encode() + b"\r\n"
                b"Connection: close\r\n\r\n" + body
            )

        response = self.send(self.serve(handler))

        self.assertEqual(429, response.status)
        self.assertEqual("17", response.header("retry-after"))
        self.assertEqual(body.decode(), response.body)

    def test_truncated_body_with_clean_close(self):
        def handler(connection):
            connection.sendall(
                b"HTTP/1.1 200 OK\r\nContent-Length: 1000\r\n"
                b"Connection: close\r\n\r\n" + b'{"results":['
            )
            connection.close()

        with self.assertRaises(IncompleteResponseError):
            self.send(self.serve(handler))

    def test_truncated_body_with_reset(self):
        """Обрыв через RST — тот же обрыв на отдаче, повторять его нельзя."""

        def handler(connection):
            connection.sendall(
                b"HTTP/1.1 200 OK\r\nContent-Length: 1000\r\n"
                b"Connection: close\r\n\r\n" + b'{"results":['
            )
            reset(connection)

        with self.assertRaises(IncompleteResponseError):
            self.send(self.serve(handler))

    def test_truncated_chunked_body(self):
        def handler(connection):
            connection.sendall(
                b"HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\n"
                b"10\r\n{\"results\":[1,2,"
            )
            connection.close()

        with self.assertRaises(IncompleteResponseError) as caught:
            self.send(self.serve(handler))

        # У chunked-обрыва обещанной длины нет: выдумывать её нельзя.
        self.assertNotIn("из 0 байт", str(caught.exception))

    def test_silence_before_headers_is_a_timeout(self):
        def handler(connection):
            import time

            time.sleep(5)

        with self.assertRaises(TimeoutError):
            self.send(self.serve(handler), timeout=0.3)

    def test_refused_connection_is_a_network_error(self):
        """Запрос до сервиса не дошёл: такой отказ повторяемый."""
        probe = socket.socket()
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
        probe.close()

        with self.assertRaises(NetworkError) as caught:
            UrllibTransport().send(
                "POST", "http://127.0.0.1:{}/api/balance".format(port), {}, "a=1", 5.0
            )

        self.assertNotIsInstance(caught.exception, (TimeoutError, IncompleteResponseError))


class ClientOverRealSocketTest(unittest.TestCase):
    """Через клиент целиком: важна не только ошибка, но и число попыток."""

    def test_reset_during_body_is_not_retried(self):
        attempts = {"count": 0}
        lock = threading.Lock()
        listener = socket.socket()
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind(("127.0.0.1", 0))
        listener.listen(5)
        port = listener.getsockname()[1]
        self.addCleanup(listener.close)

        def serve():
            while True:
                try:
                    connection, _ = listener.accept()
                except OSError:
                    return

                with lock:
                    attempts["count"] += 1

                try:
                    connection.recv(65536)
                    connection.sendall(
                        b"HTTP/1.1 200 OK\r\nContent-Length: 1000\r\n\r\n" + b'{"results":['
                    )
                    reset(connection)
                except OSError:
                    pass

        threading.Thread(target=serve, daemon=True).start()

        client = Client(
            "KEY",
            base_url="http://127.0.0.1:{}/api".format(port),
            retry_delay=0.0,
            max_retry_delay=0.0,
        )

        with self.assertRaises(IncompleteResponseError):
            client.balance()

        with lock:
            self.assertEqual(1, attempts["count"], "обрыв на отдаче повторяться не должен")


if __name__ == "__main__":
    unittest.main()
