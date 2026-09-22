import unittest

from jsonseo import Client, InvalidArgumentError, ParseError
from tests.fake import FakeTransport


class ClientTest(unittest.TestCase):
    def setUp(self) -> None:
        self.transport = FakeTransport()

    def client(self, **options) -> Client:
        return Client("KEY", transport=self.transport, **options)

    def test_requires_api_key(self):
        with self.assertRaises(InvalidArgumentError):
            Client("   ")

    def test_rejects_unknown_option(self):
        # Настройки — только именованные аргументы, опечатку ловит сам Python.
        with self.assertRaises(TypeError):
            Client("KEY", retries=2)

    def test_rejects_unknown_auth_mode(self):
        with self.assertRaises(InvalidArgumentError):
            Client("KEY", auth="cookie")

    def test_rejects_meaningless_attempts(self):
        for attempts in (0, -5, 2.5, "3", True):
            with self.assertRaises(InvalidArgumentError, msg="attempts={!r}".format(attempts)):
                Client("KEY", attempts=attempts)

    def test_sends_key_in_authorization_header_by_default(self):
        self.transport.queue_json({"balance": 1.0, "currency": "RUB"})

        self.client().balance()

        self.assertEqual("Bearer KEY", self.transport.requests[0]["headers"]["Authorization"])
        self.assertNotIn("key", self.transport.params())

    def test_sends_key_in_parameter_when_asked(self):
        self.transport.queue_json({"balance": 1.0, "currency": "RUB"})

        self.client(auth="query").balance()

        self.assertNotIn("Authorization", self.transport.requests[0]["headers"])
        self.assertEqual("KEY", self.transport.params()["key"])

    def test_posts_to_the_method_path(self):
        self.transport.queue_json({"results": []})

        self.client().yandex("купить ноутбук")

        self.assertEqual("POST", self.transport.requests[0]["method"])
        self.assertEqual("https://jsonseo.ru/api/yandex", self.transport.requests[0]["url"])

    def test_base_url_without_trailing_slash(self):
        self.transport.queue_json({"results": []})

        self.client(base_url="http://localhost:8080/api/").yandex("тест")

        self.assertEqual("http://localhost:8080/api/yandex", self.transport.requests[0]["url"])

    def test_positional_argument_becomes_the_primary_parameter(self):
        self.transport.queue_json({"results": []}).queue_json({"results": []})

        api = self.client()
        api.yandex("купить ноутбук")
        api.google("купить ноутбук")

        self.assertEqual("купить ноутбук", self.transport.params(0)["text"])
        self.assertEqual("купить ноутбук", self.transport.params(1)["q"])

    def test_primary_parameter_may_be_named(self):
        self.transport.queue_json({"results": []})

        self.client().yandex(text="купить ноутбук", region=213)

        self.assertEqual("купить ноутбук", self.transport.params()["text"])

    def test_primary_parameter_twice_is_an_error(self):
        # Ловит сам Python: у позиционного аргумента то же имя, что у параметра.
        with self.assertRaises(TypeError):
            self.client().yandex("один", text="другой")

    def test_phrase_list_is_joined_with_newlines(self):
        self.transport.queue_json({"results": []})

        self.client().direct(["ремонт айфона", "ремонт телефона"])

        self.assertEqual("ремонт айфона\nремонт телефона", self.transport.params()["phrases"])

    def test_other_lists_are_joined_with_commas(self):
        self.transport.queue_json({"results": []})

        self.client().wordstat("ремонт", region=[213, 2], device=["desktop", "phone"])

        self.assertEqual("213,2", self.transport.params()["region"])
        self.assertEqual("desktop,phone", self.transport.params()["device"])

    def test_booleans_become_ones_and_zeros(self):
        self.transport.queue_json({"results": []})

        self.client().yandex("тест", ai=True, noreask=False)

        self.assertEqual("1", self.transport.params()["ai"])
        self.assertEqual("0", self.transport.params()["noreask"])

    def test_empty_values_are_not_sent(self):
        self.transport.queue_json({"results": []})

        self.client().yandex("тест", break_domain=None, region=[])

        self.assertNotIn("break_domain", self.transport.params())
        self.assertNotIn("region", self.transport.params())

    def test_floats_keep_a_decimal_point(self):
        self.transport.queue_json({})

        self.client().call("geoip", {"threshold": 0.5})

        self.assertEqual("0.5", self.transport.params()["threshold"])

    def test_bad_value_inside_a_list_names_its_position(self):
        with self.assertRaises(InvalidArgumentError) as caught:
            self.client().wordstat("ремонт", region=[213, object()])

        self.assertIn("region[1]", str(caught.exception))

    def test_user_agent_reaches_the_request(self):
        self.transport.queue_json({}).queue_json({})

        self.client().balance()
        self.assertTrue(self.transport.requests[0]["headers"]["User-Agent"].startswith("jsonseo-python/"))

        self.client(user_agent="мой-проект/1.0").balance()
        self.assertEqual("мой-проект/1.0", self.transport.requests[1]["headers"]["User-Agent"])

    def test_balance_sends_no_parameters_of_its_own(self):
        self.transport.queue_json({"balance": 0.0, "currency": "RUB"})

        self.client().balance()

        self.assertEqual("", self.transport.requests[0]["body"])

    def test_decodes_json_responses(self):
        self.transport.queue_json({"balance": 123.45, "currency": "RUB"})

        self.assertEqual({"balance": 123.45, "currency": "RUB"}, self.client().balance())

    def test_call_raw_returns_the_body_as_is(self):
        body = '<?xml version="1.0"?><yandexsearch></yandexsearch>'
        self.transport.queue_raw(body)

        self.assertEqual(body, self.client().call_raw("yandex/xml", {"query": "тест"}))
        self.assertEqual("application/xml, text/xml", self.transport.requests[0]["headers"]["Accept"])

    def test_unparsable_body_keeps_it_in_the_error(self):
        self.transport.queue_raw("<html>прокси съел ответ</html>")

        with self.assertRaises(ParseError) as caught:
            self.client().balance()

        self.assertEqual("<html>прокси съел ответ</html>", caught.exception.body)

    def test_timeout_reaches_the_transport(self):
        self.transport.queue_json({})

        self.client(timeout=12.5).balance()

        self.assertEqual(12.5, self.transport.requests[0]["timeout"])

    def test_leading_slash_in_path_is_ignored(self):
        self.transport.queue_json({}).queue_raw("тело")

        self.client().call("/geoip", {"ip": "1.2.3.4"})
        self.client().call_raw("/yandex/xml", {"query": "тест"})

        self.assertEqual("https://jsonseo.ru/api/geoip", self.transport.requests[0]["url"])
        self.assertEqual("https://jsonseo.ru/api/yandex/xml", self.transport.requests[1]["url"])

    def test_sets_are_rejected(self):
        """Порядок обхода множества не определён — запрос стал бы невоспроизводимым."""
        with self.assertRaises(InvalidArgumentError):
            self.client().wordstat("ремонт", device={"desktop", "phone"})

    def test_every_method_calls_its_own_path(self):
        """Опечатка в пути иначе всплыла бы только на боевом ключе."""
        methods = {
            "yandex": "yandex",
            "yandex_suggest": "yandex/suggest",
            "yandex_regions": "yandex/regions",
            "yandex_images": "yandex/images",
            "yandex_video": "yandex/video",
            "google": "google",
            "google_suggest": "google/suggest",
            "google_regions": "google/regions",
            "google_images": "google/images",
            "google_video": "google/video",
            "bing": "bing",
            "bing_suggest": "bing/suggest",
            "bing_images": "bing/images",
            "bing_video": "bing/video",
            "wordstat": "wordstat",
            "wordstat_frequency": "wordstat/frequency",
            "wordstat_graph": "wordstat/graph",
            "wordstat_map": "wordstat/map",
            "direct": "direct",
            "geoip": "geoip",
        }

        api = self.client()

        for index, (method, path) in enumerate(methods.items()):
            self.transport.queue_raw("{}")
            getattr(api, method)("тест")

            self.assertEqual(
                "https://jsonseo.ru/api/" + path,
                self.transport.requests[index]["url"],
                "метод {} ушёл не по своему адресу".format(method),
            )

        self.transport.queue_json({})
        api.balance()

        self.assertEqual("https://jsonseo.ru/api/balance", self.transport.requests[-1]["url"])
        self.assertEqual(len(methods) + 1, self.transport.count)


if __name__ == "__main__":
    unittest.main()
