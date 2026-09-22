"""
Формы ответов API — как подсказки редактору.

На поведение не влияют: методы возвращают обычные словари.
"""

from typing import Any, Dict, List, Optional

try:
    from typing import TypedDict
except ImportError:  # pragma: no cover - Python 3.7 и старше
    from typing_extensions import TypedDict  # type: ignore


class SearchResult(TypedDict, total=False):
    """Органический результат выдачи."""

    url: str
    domain: str
    title: str
    passage: str
    breadcrumbs: str
    #: Тип документа: pdf, doc, xls. Отсутствует у обычных страниц.
    mime: str
    mime_type: str


class AiAnswerSource(TypedDict, total=False):
    """Источник, на который опирается ответ нейросети."""

    id: int
    url: str
    domain: str
    title: str
    description: str
    #: Сколько сносок ведёт на источник. Только Яндекс и Bing.
    citations: int


class AiAnswer(TypedDict, total=False):
    """Блок нейросети над выдачей: Алиса AI, AI Overview, Copilot."""

    markdown: str
    sources: List[AiAnswerSource]
    #: Только Яндекс: уточняющие вопросы под ответом.
    followUps: List[str]


class AdSitelink(TypedDict, total=False):
    """Быстрая ссылка под текстом объявления."""

    title: str
    url: str
    description: str


class Ad(TypedDict, total=False):
    """Рекламное объявление со страницы выдачи."""

    #: top до органики, bottom после неё, inline между результатами.
    block: str
    position: int
    #: Страница выдачи, нумерация с нуля и абсолютная.
    page: int
    domain: str
    url: str
    displayUrl: str
    title: str
    description: str
    label: str
    #: text или gallery. Только Яндекс.
    format: str
    group: int
    sitelinks: List[AdSitelink]


class SearchResponse(TypedDict, total=False):
    """Ответ органической выдачи — общий для Яндекса, Google и Bing."""

    #: Сколько страниц получено — ровно за них и списано.
    pages: int
    #: Выдача закончилась, повторять с большим pages незачем.
    exhausted: bool
    breakDomainHit: bool
    query: str
    rawQuery: str
    region: str
    #: Только Google: почему часть результатов скрыта.
    filter_description: str
    #: Только Яндекс: сколько нашлось, округлённо самим поисковиком.
    found: Optional[int]
    found_human: str
    mkt: str
    lang: str
    lr: int
    url: str
    results: List[SearchResult]
    aiAnswer: AiAnswer
    #: Только при ads=1. Пустой список — просили, но рекламы не было.
    ads: List[Ad]


class ImageResult(TypedDict, total=False):
    """Карточка картинки: первые четыре поля есть всегда."""

    url: str
    title: str
    domain: str
    sourceUrl: str
    thumbnail: str
    width: int
    height: int
    thumbnailWidth: int
    thumbnailHeight: int
    bytes: int


class ImagesResponse(TypedDict, total=False):
    """Ответ поиска по картинкам."""

    pages: int
    exhausted: bool
    query: str
    url: str
    results: List[ImageResult]
    ads: List[Ad]


class VideoResult(TypedDict, total=False):
    """Карточка видео."""

    url: str
    title: str
    domain: str
    thumbnail: str
    #: Длительность в секундах. Нет поля — длина неизвестна, а не ноль.
    duration: int
    durationText: str
    published: int
    publishedText: str
    views: str
    provider: str
    channel: str
    description: str
    breadcrumbs: str


class VideoResponse(TypedDict, total=False):
    """Ответ поиска по видео."""

    pages: int
    exhausted: bool
    query: str
    url: str
    results: List[VideoResult]


class SuggestResponse(TypedDict, total=False):
    """Ответ поисковых подсказок."""

    query: str
    results: List[str]
    #: Только Яндекс: регион, в котором собраны подсказки.
    lr: str


class YandexRegion(TypedDict, total=False):
    """Регион Яндекса из справочника."""

    id: int
    name: str
    subname: str
    lat: float
    lon: float


class YandexRegionsResponse(TypedDict, total=False):
    name: str
    lang: str
    regions: List[YandexRegion]


class GoogleRegion(TypedDict, total=False):
    """Регион Google: вместе с ID приходит готовый uule."""

    id: int
    name: str
    subname: str
    type: str
    type_name: str
    canonical_name: str
    uule: str
    lat: float
    lon: float


class GoogleRegionsResponse(TypedDict, total=False):
    name: str
    lang: str
    regions: List[GoogleRegion]


class WordstatPhrase(TypedDict, total=False):
    text: str
    value: int


class WordstatResults(TypedDict, total=False):
    #: Что ищут вместе с этой фразой.
    popular: List[WordstatPhrase]
    #: Соседняя семантика.
    associations: List[WordstatPhrase]


class WordstatResponse(TypedDict, total=False):
    text: str
    region: str
    device: str
    results: WordstatResults


class WordstatFrequencyResults(TypedDict, total=False):
    #: Частота запроса одним числом.
    totalValue: int


class WordstatFrequencyResponse(TypedDict, total=False):
    text: str
    region: str
    device: str
    results: WordstatFrequencyResults


class WordstatGraphPoint(TypedDict, total=False):
    date: str
    text: str
    absolute: int
    relative: float


class WordstatGraphResults(TypedDict, total=False):
    graph: List[WordstatGraphPoint]


class WordstatGraphResponse(TypedDict, total=False):
    text: str
    region: str
    device: str
    type: str
    results: WordstatGraphResults


class WordstatMapRow(TypedDict, total=False):
    type: str
    text: str
    absolute: int
    #: Affinity-индекс: 100 — средний интерес.
    popularity: float
    relative: float
    #: ID региона для region других методов; None, если название неоднозначно.
    region_id: Optional[int]


class WordstatMapResults(TypedDict, total=False):
    rows: List[WordstatMapRow]


class WordstatMapResponse(TypedDict, total=False):
    text: str
    device: str
    type: str
    results: WordstatMapResults


class DirectPosition(TypedDict, total=False):
    """Прогноз по одному месту аукциона."""

    bid: float
    budget: float
    clicks: int
    ctr: float
    shows: int


class DirectForecast(TypedDict, total=False):
    phrase: str
    shows: int
    #: Места аукциона: набор задаёт сам Директ.
    positions: Dict[str, DirectPosition]


class DirectResponse(TypedDict, total=False):
    geo: int
    period: str
    #: На сколько пачек разбит список — по ним считается стоимость.
    batches: int
    processed: int
    results: List[DirectForecast]
    errors: List[str]


class GeoipRegion(TypedDict, total=False):
    #: ID тот же, что у Яндекса: годится для region.
    id: int
    name: str


class GeoipCountry(TypedDict, total=False):
    id: int
    name: str
    iso_name: str


class GeoipResponse(TypedDict, total=False):
    ip: str
    latitude: float
    longitude: float
    region: GeoipRegion
    country: GeoipCountry


class BalanceResponse(TypedDict, total=False):
    balance: float
    currency: str


#: Значение параметра: список склеивается, флаг даёт 1/0, None не уедет.
ParamValue = Any
