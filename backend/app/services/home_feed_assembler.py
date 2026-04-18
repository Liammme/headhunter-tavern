def assemble_home_payload(*, intelligence: dict, day_payloads: list[dict]) -> dict:
    return {
        "intelligence": intelligence,
        "days": day_payloads,
    }
