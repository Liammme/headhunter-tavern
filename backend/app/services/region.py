from typing import Literal

RegionCode = Literal["global", "japan"]

GLOBAL_REGION: RegionCode = "global"
JAPAN_REGION: RegionCode = "japan"
SUPPORTED_REGIONS: set[str] = {GLOBAL_REGION, JAPAN_REGION}


def normalize_region(region: str) -> RegionCode:
    if region == JAPAN_REGION:
        return JAPAN_REGION
    if region == GLOBAL_REGION:
        return GLOBAL_REGION
    raise ValueError(f"Unsupported region: {region}")
