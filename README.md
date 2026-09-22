# JSON SEO Python SDK

Официальный Python-клиент [JSON SEO API](https://jsonseo.ru): выдача Яндекса, Google и Bing, картинки и видео, поисковые подсказки, Яндекс Вордстат, прогноз показов Директа и геолокация по IP.

- Работает на **Python 3.8 и выше**.
- Без зависимостей: только стандартная библиотека.
- Типы в комплекте (`py.typed`), редактор подсказывает поля ответов.
- Двадцать один метод сервиса.
- Три попытки на запрос по умолчанию: если сервис затупил, SDK сходит ещё раз сам.

## Установка

```bash
pip install jsonseo
```

Ключ берётся в [личном кабинете](https://jsonseo.ru).

## Быстрый старт

```python
from jsonseo import Client

client = Client("YOUR_KEY")

serp = client.yandex("купить ноутбук", region=213)

for position, result in enumerate(serp["results"], start=1):
    print(position, result["domain"], "—", result["title"])
```

Первый аргумент — основной параметр метода, остальное передаётся по имени:

```python
client.yandex("купить ноутбук", region=213, pages=2)
client.geoip("77.88.55.242")
client.wordstat_frequency("ремонт айфона", kind="exact")
```

---

# Примеры запросов

## Позиции сайта в Яндексе

`break_domain` останавливает сбор на нужном домене — платить за страницы ниже найденной позиции незачем.

```python
serp = client.yandex(
    "ремонт айфона",
    region=213,            # Москва
    pages=10,              # до 100 позиций
    break_domain="example.com",
)

for position, result in enumerate(serp["results"], start=1):
    if result["domain"].endswith("example.com"):
        print("Позиция:", position)
        break

print("Собрано страниц:", serp["pages"])
print("Нашлось всего:", serp["found_human"])
```

В ответе:

```python
{
    "pages": 3,
    "exhausted": False,
    "breakDomainHit": True,          # остановились на нужном домене
    "query": "ремонт айфона",
    "rawQuery": "ремонт айфона",
    "found": 28000000,
    "found_human": "нашлось 28 млн результатов",
    "lr": 213,
    "url": "https://yandex.ru/search/?text=...",
    "results": [
        {
            "url": "https://example.com/remont-iphone/",
            "domain": "example.com",
            "title": "Ремонт айфонов в Москве",
            "passage": "Починим за 30 минут...",
            "breadcrumbs": "example.com › услуги",
        },
    ],
}
```

## Выдача Google по нужному городу

Регион задаётся числовым ID из справочника — сервис сам соберёт `uule` и подставит `gl`.

```python
regions = client.google_regions("Казань")

serp = client.google(
    "заказать пиццу",
    region=regions["regions"][0]["id"],
    hl="ru",
    device="desktop",
    pages=2,
)
```

Если Google схлопнул часть результатов как «очень похожие», причина придёт в `filter_description`, а вернуть их можно параметром `filter`:

```python
serp = client.google("заказать пиццу", filter=0)
```

## Выдача Bing

```python
serp = client.bing("buy a laptop", mkt="en-US", pages=2)

print(serp["mkt"], serp["lang"])  # фактический рынок и язык
```

## Реклама на странице выдачи

Приходит отдельным списком, органика не меняется. Стоит +0.01 ₽ за страницу, на которой реклама нашлась.

```python
serp = client.yandex("пластиковые окна", region=213, ads=True)

for ad in serp.get("ads", []):
    print(ad["block"], "#{}".format(ad["position"]), "—", ad["domain"])
    print("  ", ad.get("title"))
```

`block` — где стоял блок: `top` до органики, `bottom` после неё, `inline` между результатами. Пустой список `ads` значит «рекламу просили, но её не было», а отсутствие ключа — «не просили».

## Ответ нейросети над выдачей

```python
serp = client.yandex("чем отличается osb от фанеры", ai=True)

answer = serp.get("aiAnswer")

if answer:
    print(answer["markdown"])

    for source in answer.get("sources", []):
        print("[{}]".format(source["id"]), source["domain"])
```

Стоит +0.01 ₽ и только когда ответ есть: если поисковик его не показал, запрос обойдётся в обычную цену. Доступен только с первой страницы.

## Картинки

```python
images = client.yandex_images(
    "скандинавский интерьер",
    orientation="horizontal",
    size="large",
    format="jpg",
    pages=2,
)

for image in images["results"]:
    print("{}×{}".format(image.get("width"), image.get("height")), image["url"])
    print("   источник:", image["sourceUrl"])
```

Те же параметры работают у `google_images()` и `bing_images()` — SDK переводит общий фильтр в родной параметр движка. Если у поисковика такого значения нет, придёт `ValidationError` с указанием, чем заменить.

## Видео

```python
videos = client.google_video("как заменить ремень грм", duration="long", hl="ru")

for video in videos["results"]:
    print(video["title"], "—", video.get("durationText"))
    print("  ", video["url"], "({})".format(video.get("provider")))
```

Поле `duration` приходит в секундах, но не всегда: у прямых эфиров вместо длины стоит `LIVE`. Отбор вида `duration < 600` молча выбросит такие ролики — ориентируйтесь на `durationText`, он на месте всегда.

## Поисковые подсказки

```python
suggest = client.yandex_suggest("купить кв", region=213)

print(suggest["results"])
# ['купить квартиру в москве', 'купить квартиру в новостройке', ...]
```

Есть у всех трёх поисковиков: `yandex_suggest()`, `google_suggest()`, `bing_suggest()`.

## Справочник регионов

```python
regions = client.yandex_regions("Казань")

for region in regions["regions"]:
    print(region["id"], "—", region["name"], "({})".format(region["subname"]))
# 43 — Казань (Республика Татарстан)
```

Бесплатно, но ключ нужен: по нему считается лимит запросов в минуту. У `google_regions()` в ответе дополнительно приходит готовая строка `uule`.

## Вордстат: частота запроса

```python
frequency = client.wordstat_frequency(
    "ремонт айфона",
    kind="exact",      # точная частотность: "!ремонт !айфона"
    region=213,
)

print(frequency["results"]["totalValue"])  # 27356
```

Вид частотности задаётся параметром `kind`, кавычки и операторы расставит сервис — фразу передавайте как есть:

| `kind` | Что считает |
| --- | --- |
| `base` | Базовая: фраза как есть |
| `phrase` | Фразовая: `"фраза"` |
| `exact` | Точная: `"!слово !слово"` — для прогноза трафика берут её |
| `superexact` | Сверхточная: `"[!слово !слово]"` |

## Вордстат: расширение семантики

```python
wordstat = client.wordstat("ремонт айфона", region=[213, 2])

for phrase in wordstat["results"]["popular"]:
    print(phrase["value"], phrase["text"])

for phrase in wordstat["results"]["associations"]:
    print(phrase["value"], phrase["text"])
```

`popular` — что ищут вместе с фразой, `associations` — соседняя семантика.

## Вордстат: сезонность

```python
graph = client.wordstat_graph("купить ёлку", graph_type="month")

for point in graph["results"]["graph"]:
    print(point["text"], point["absolute"])
# июнь 2026 9042
# июль 2026 11780
```

`month` и `week` отдают историю с 2018 года, `day` — последние 60 дней.

## Вордстат: география спроса

```python
geo = client.wordstat_map("купить ноутбук", map_type="regions")

for row in geo["results"]["rows"]:
    print(row["text"], row["absolute"], "индекс", row["popularity"])
```

`popularity` — affinity-индекс: 100 означает средний по стране интерес, выше — повышенный. В каждой строке приходит `region_id`, его можно сразу подставить в `region` других методов.

## Прогноз показов Яндекс Директа

Рекламный кабинет не нужен. Список фраз передаётся списком — SDK склеит его сам.

```python
forecast = client.direct(
    ["ремонт айфона", "замена экрана iphone", '"ремонт айфона"'],
    region=213,
    period="month",
)

for row in forecast["results"]:
    print("{}: {} показов".format(row["phrase"], row["shows"]))

    for place, bid in row["positions"].items():
        print("   {}: ставка {} ₽, бюджет {} ₽, кликов {}".format(
            place, bid["bid"], bid["budget"], bid["clicks"]
        ))
```

Вид частотности задаётся операторами прямо во фразе: `ремонт айфона` — базовая, `"ремонт айфона"` — фразовая, `"!ремонт !айфона"` — точная.

Стоимость — 0.01 ₽ за пачку до 4000 символов, это около 150 обычных фраз. За один запрос принимается до 1000 фраз, на аккаунт — не больше 100 запросов в час.

## Геолокация по IP

```python
location = client.geoip("77.88.55.242")

print(location["country"]["name"], location["region"]["name"])
print(location["latitude"], location["longitude"])
```

ID региона тот же, что у Яндекса, — его можно сразу подставить в `region` методов выдачи и Вордстата:

```python
serp = client.yandex("доставка пиццы", region=location["region"]["id"])
```

## Баланс

```python
balance = client.balance()

print(balance["balance"], balance["currency"])  # 123.45 RUB
```

---

# Справочник методов

| Метод | Путь API | Что делает |
| --- | --- | --- |
| `yandex()` | `/yandex` | Органическая выдача Яндекса |
| `yandex_suggest()` | `/yandex/suggest` | Поисковые подсказки |
| `yandex_regions()` | `/yandex/regions` | Справочник регионов, бесплатно |
| `yandex_images()` | `/yandex/images` | Поиск по картинкам |
| `yandex_video()` | `/yandex/video` | Поиск по видео |
| `google()` | `/google` | Органическая выдача Google |
| `google_suggest()` | `/google/suggest` | Подсказки |
| `google_regions()` | `/google/regions` | Регионы и готовый `uule`, бесплатно |
| `google_images()` | `/google/images` | Поиск по картинкам |
| `google_video()` | `/google/video` | Поиск по видео |
| `bing()` | `/bing` | Органическая выдача Bing |
| `bing_suggest()` | `/bing/suggest` | Подсказки |
| `bing_images()` | `/bing/images` | Поиск по картинкам |
| `bing_video()` | `/bing/video` | Поиск по видео |
| `wordstat()` | `/wordstat` | Популярные и похожие запросы |
| `wordstat_frequency()` | `/wordstat/frequency` | Частота запроса одним числом |
| `wordstat_graph()` | `/wordstat/graph` | Динамика по месяцам, неделям, дням |
| `wordstat_map()` | `/wordstat/map` | География показов |
| `direct()` | `/direct` | Прогноз показов Яндекс Директа |
| `geoip()` | `/geoip` | Геолокация по IPv4, бесплатно |
| `balance()` | `/balance` | Остаток на счёте, бесплатно |

Полный список параметров каждого метода — в [документации](https://jsonseo.ru/docs).

Появился метод, которого ещё нет в SDK? Его можно вызвать напрямую:

```python
client.call("новый/метод", {"параметр": "значение"})      # разберёт JSON
client.call_raw("новый/метод", {"параметр": "значение"})  # вернёт тело как есть
```

# Как SDK помогает с параметрами

**Списки передаются списками.** Фразы для Директа склеиваются переводом строки, остальные списки — запятой:

```python
client.direct(["ремонт айфона", "ремонт телефона", "замена экрана"])
client.wordstat("ремонт", region=[213, 2], device=["desktop", "phone"])
```

**Флаги принимаются флагами.** `True` и `False` уезжают как `1` и `0`:

```python
client.yandex("купить ноутбук", ai=True, ads=True)
```

**`None` и пустой список не отправляются.** Необязательный параметр, который вы ещё не посчитали, можно не вычищать из вызова руками.

**Родные параметры поисковиков проходят насквозь.** Вертикали принимают не только общие фильтры, но и `tbs` у Google, `isize` у Яндекса, `qft` у Bing.

# Ошибки

Всё, что бросает SDK, наследуется от `JsonSeoError`.

| Ошибка | Статус | Когда |
| --- | --- | --- |
| `ValidationError` | 422 | Параметры не приняты. `errors` — сообщения по полям, `fields` — их имена |
| `UnauthorizedError` | 403, 401 | Ключ не передан или недействителен |
| `PaymentRequiredError` | 402 | На счёте не хватает средств |
| `RateLimitError` | 429 | Превышен лимит частоты |
| `ServiceUnavailableError` | 503 | Выдачу получить не вышло. Деньги не списаны |
| `ApiError` | прочие | Любой другой отказ сервиса |

У всех ошибок сервиса есть `status`, `body`, разобранный `payload` и `retry_after` — срок, который назвал сервис, если он его назвал.

| Ошибка | Когда |
| --- | --- |
| `NetworkError` | До сервиса не достучались: сеть, DNS, TLS |
| `TimeoutError` | Ответа не дождались |
| `IncompleteResponseError` | Соединение оборвалось посреди тела |
| `ParseError` | Ответ пришёл, но не разобрался как JSON. `body` — тело как есть |
| `InvalidArgumentError` | SDK забраковал аргументы, запрос не отправлялся |

```python
from jsonseo import PaymentRequiredError, RateLimitError, ValidationError

try:
    serp = client.yandex("купить ноутбук", pages=50)
except ValidationError as error:
    for field, messages in error.errors.items():
        print(field, ":", ", ".join(messages))
except PaymentRequiredError:
    print("Баланс кончился:", client.balance()["balance"])
except RateLimitError as error:
    print("Вернуться через", error.retry_after, "с")
```

`TimeoutError` наследует и встроенный `TimeoutError`, так что привычный `except TimeoutError` его тоже поймает.

# Повторы

**У каждого запроса три попытки по умолчанию: одна основная и две повторных.** Если сервис затупил и выдачу собрать не вышло (`503`), SDK сам сходит ещё дважды, и обычно этого хватает. `attempts=1` отключает повторы совсем.

`429`, `5xx` и обрывы связи повторяются автоматически — это ровно те отказы, за которые сервис денег не берёт. Отказы по ключу, балансу и параметрам не повторяются: сами они не изменятся.

Таймаут и оборвавшееся посреди тела соединение не повторяются, и это намеренно: работу на стороне сервиса обрыв у клиента не отменяет — выдача будет собрана и оплачена, а повтор стоил бы ещё раз. Если ответ не успевает прийти, поднимайте `timeout`, а не `attempts`.

Пауза между попытками удваивается и разбавляется случайной добавкой. Если сервис прислал `Retry-After`, SDK не вернётся раньше названного срока. Когда сервис просит ждать дольше `max_retry_delay`, SDK не ждёт вовсе, а отдаёт ошибку с `retry_after` — решение остаётся за вами.

# Настройки клиента

```python
client = Client(
    "YOUR_KEY",
    base_url="https://jsonseo.ru/api",  # адрес API
    timeout=300.0,                      # сколько ждать ответа на попытку, секунд
    attempts=3,                         # всего попыток, вместе с первой
    retry_delay=1.0,                    # стартовая пауза между попытками
    max_retry_delay=30.0,               # потолок паузы
    auth="header",                      # или "query" — ключ в параметре key
    user_agent="мой-проект/1.0",
    transport=my_transport,             # свой транспорт
)
```

Настройки — только именованные аргументы, поэтому опечатку ловит сам Python: `Client("YOUR_KEY", timeuot=5)` не запустится.

Таймаут по умолчанию намеренно большой: многостраничный запрос выдачи собирается минутами, и обрыв на стороне клиента не отменяет запрос на стороне сервиса — деньги за него уже списаны. Считается он на **каждую попытку** отдельно, а не на весь вызов.

Ключ по умолчанию едет в заголовке `Authorization: Bearer`, а не в адресе: так он не оседает в логах прокси и серверов. `auth="query"` нужен там, где заголовки до API не доходят.

# Свой транспорт

Если HTTP в проекте уже ходит через `requests`, `httpx` или что-то своё, SDK можно отдать этот клиент — достаточно объекта с одним методом:

Транспорт обязан бросать ошибки SDK: от их класса зависит, повторит клиент запрос или нет. Чужие исключения пройдут мимо политики повторов и мимо пользовательского `except JsonSeoError`.

```python
import requests

from jsonseo import IncompleteResponseError, NetworkError, TimeoutError
from jsonseo.transport import Response

class RequestsTransport:
    def __init__(self, session):
        self.session = session

    def send(self, method, url, headers, body, timeout):
        try:
            response = self.session.request(
                method, url, headers=headers, data=body, timeout=timeout
            )
        except requests.Timeout as error:
            raise TimeoutError("Ответа не дождались.") from error
        except requests.ConnectionError as error:
            raise NetworkError("Запрос не удался: {}.".format(error)) from error

        try:
            text = response.text
        except requests.RequestException as error:
            # Заголовки уже пришли: выдача собрана и оплачена, повторять нельзя.
            raise IncompleteResponseError("Ответ пришёл не целиком.") from error

        return Response(response.status_code, dict(response.headers), text)
```

Тот же приём годится для тестов: подмените транспорт заглушкой, и запросы никуда не пойдут.

# Разработка

```bash
python -m unittest discover -s tests -t .
```

Тесты идут без сети: транспорт подменяется заглушкой.

# Лицензия

MIT.
