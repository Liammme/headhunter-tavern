from app.crawlers.adapters.abetterweb3 import ABetterWeb3Adapter
from app.crawlers.adapters.aijobsnet import AIJobsNetAdapter
from app.crawlers.adapters.bonjour_bio import BonjourBioAdapter
from app.crawlers.adapters.cryptocurrencyjobs import CryptocurrencyJobsAdapter
from app.crawlers.adapters.cryptojobslist import CryptoJobsListAdapter
from app.crawlers.adapters.dejob import DeJobAdapter
from app.crawlers.adapters.discourse_ai_jobs import OpenRoboticsJobsAdapter, PyTorchJobsAdapter
from app.crawlers.adapters.hn_whoishiring_ai import HNWhoIsHiringAIAdapter
from app.crawlers.adapters.jobicy_ai import JobicyAIAdapter
from app.crawlers.adapters.remoteok_ai import RemoteOKAIAdapter
from app.crawlers.adapters.web3career import Web3CareerAdapter
from app.crawlers.adapters.web3jobsai import Web3JobsAiAdapter
from app.crawlers.adapters.workatstartup_ai import WorkAtStartupAIAdapter

ADAPTERS = {
    "aijobsnet": AIJobsNetAdapter,
    "abetterweb3": ABetterWeb3Adapter,
    "bonjour_bio": BonjourBioAdapter,
    "cryptocurrencyjobs": CryptocurrencyJobsAdapter,
    "cryptojobslist": CryptoJobsListAdapter,
    "dejob": DeJobAdapter,
    "hn_whoishiring_ai": HNWhoIsHiringAIAdapter,
    "jobicy_ai": JobicyAIAdapter,
    "open_robotics_jobs": OpenRoboticsJobsAdapter,
    "pytorch_jobs": PyTorchJobsAdapter,
    "remoteok_ai": RemoteOKAIAdapter,
    "web3career": Web3CareerAdapter,
    "web3jobsai": Web3JobsAiAdapter,
    "workatstartup_ai": WorkAtStartupAIAdapter,
}
