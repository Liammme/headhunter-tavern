from app.crawlers.base import SourceAdapter
from app.crawlers.adapters.japan_dev import JapanDevAdapter

JAPAN_ADAPTERS: dict[str, type[SourceAdapter]] = {
    "japan_dev": JapanDevAdapter,
}
