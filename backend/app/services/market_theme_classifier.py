THEME_KEYWORDS = {
    "AI infra": (
        "llm",
        "model deployment",
        "kubernetes",
        "serving",
        "inference",
        "platform",
    ),
    "agent / RAG": ("agent", "rag", "retrieval", "workflow", "tool use"),
    "data platform": ("data pipeline", "warehouse", "analytics", "etl"),
    "Web3 infra": ("protocol", "node", "validator", "rpc", "chain"),
    "wallet / payment": ("wallet", "payment", "card", "fiat", "settlement"),
    "security": ("security", "audit", "threat", "vulnerability"),
    "risk / compliance": ("risk", "compliance", "kyc", "aml", "fraud"),
    "trading infra": ("trading", "market making", "exchange", "liquidity"),
    "developer tools": ("sdk", "api", "developer", "tooling"),
    "enterprise AI integration": (
        "enterprise",
        "implementation",
        "deployment",
        "solution",
    ),
}


def classify_market_theme(title: str, description: str) -> str:
    text = f"{title} {description}".lower()
    for theme, keywords in THEME_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            return theme
    return "other"
