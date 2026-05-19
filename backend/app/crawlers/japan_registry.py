from app.crawlers.base import SourceAdapter
from app.crawlers.adapters.green_japan import GreenJapanAdapter
from app.crawlers.adapters.japan_dev import JapanDevAdapter

JAPAN_ADAPTERS: dict[str, type[SourceAdapter]] = {
    "green_japan": GreenJapanAdapter,
    "japan_dev": JapanDevAdapter,
}
