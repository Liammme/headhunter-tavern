from app.crawlers.base import SourceAdapter
from app.crawlers.adapters.daijob import DaijobAdapter
from app.crawlers.adapters.gaijinpot import GaijinPotAdapter
from app.crawlers.adapters.green_japan import GreenJapanAdapter
from app.crawlers.adapters.japan_dev import JapanDevAdapter
from app.crawlers.adapters.mynavi_tenshoku import MynaviTenshokuAdapter
from app.crawlers.adapters.type_jp import TypeJpAdapter
from app.crawlers.adapters.wantedly import WantedlyAdapter
from app.crawlers.adapters.withb import WithBAdapter

JAPAN_ADAPTERS: dict[str, type[SourceAdapter]] = {
    "daijob": DaijobAdapter,
    "gaijinpot": GaijinPotAdapter,
    "green_japan": GreenJapanAdapter,
    "japan_dev": JapanDevAdapter,
    "mynavi_tenshoku": MynaviTenshokuAdapter,
    "type_jp": TypeJpAdapter,
    "wantedly": WantedlyAdapter,
    "withb": WithBAdapter,
}
