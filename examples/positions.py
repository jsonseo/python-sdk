"""
Позиции сайта в Яндексе по списку запросов.

Запуск: JSONSEO_KEY=ваш_ключ python examples/positions.py
"""

import os

from jsonseo import Client, JsonSeoError

client = Client(os.environ["JSONSEO_KEY"])

domain = "example.com"
queries = ["купить ноутбук", "ноутбук недорого"]

for query in queries:
    try:
        # break_domain останавливает поиск: платить за страницы ниже незачем.
        serp = client.yandex(query, region=213, pages=10, break_domain=domain)
    except JsonSeoError as error:
        print("{}: ошибка — {}".format(query, error))

        continue

    # Сравнивать домены напрямую нельзя: выдача отдаёт их с поддоменом,
    # и example.com не совпал бы с www.example.com.
    position = next(
        (
            index + 1
            for index, result in enumerate(serp["results"])
            if result["domain"].lower() == domain or result["domain"].lower().endswith("." + domain)
        ),
        None,
    )

    print("{}: {}".format(query, position or "не найден в топ-{}".format(len(serp["results"]))))
