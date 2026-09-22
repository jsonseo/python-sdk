"""
Официальный Python SDK для JSON SEO API.

>>> from jsonseo import Client
>>> client = Client("ВАШ_КЛЮЧ")
>>> serp = client.yandex("купить ноутбук", region=213)
"""

from .client import VERSION, Client
from .errors import (
    ApiError,
    IncompleteResponseError,
    InvalidArgumentError,
    JsonSeoError,
    NetworkError,
    ParseError,
    PaymentRequiredError,
    RateLimitError,
    ServiceUnavailableError,
    TimeoutError,
    UnauthorizedError,
    ValidationError,
)
from .transport import Response, UrllibTransport

__version__ = VERSION

__all__ = [
    "Client",
    "Response",
    "UrllibTransport",
    "JsonSeoError",
    "ApiError",
    "PaymentRequiredError",
    "UnauthorizedError",
    "ValidationError",
    "RateLimitError",
    "ServiceUnavailableError",
    "NetworkError",
    "TimeoutError",
    "IncompleteResponseError",
    "ParseError",
    "InvalidArgumentError",
    "__version__",
]
