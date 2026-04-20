from app.crawlers.adapters.abetterweb3 import ABetterWeb3Adapter
from app.crawlers.adapters.aijobsnet import AIJobsNetAdapter
from app.crawlers.adapters.cryptocurrencyjobs import CryptocurrencyJobsAdapter
from app.crawlers.adapters.cryptojobslist import CryptoJobsListAdapter
from app.crawlers.adapters.dejob import DeJobAdapter
from app.crawlers.adapters.web3career import Web3CareerAdapter
from app.crawlers.adapters.web3jobsai import Web3JobsAiAdapter
from app.crawlers.adapters.workatstartup_ai import WorkAtStartupAIAdapter

ADAPTERS = {
    "aijobsnet": AIJobsNetAdapter,
    "abetterweb3": ABetterWeb3Adapter,
    "cryptocurrencyjobs": CryptocurrencyJobsAdapter,
    "cryptojobslist": CryptoJobsListAdapter,
    "dejob": DeJobAdapter,
    "web3career": Web3CareerAdapter,
    "web3jobsai": Web3JobsAiAdapter,
    "workatstartup_ai": WorkAtStartupAIAdapter,
}
