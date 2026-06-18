from collections import defaultdict, deque
from datetime import datetime, timedelta

from fastapi import Header, HTTPException, Request, status

from app.core.config import settings

RATE_LIMIT_PER_MINUTE = 60
_REQUEST_LOG: dict[str, deque[datetime]] = defaultdict(deque)


def require_bd_contacts_api_token(
    request: Request,
    authorization: str | None = Header(default=None),
) -> None:
    expected_token = settings.bd_contacts_api_token
    if not expected_token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="BD contacts API token is not configured",
        )
    _enforce_rate_limit(request)
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    provided_token = authorization.removeprefix("Bearer ").strip()
    if provided_token != expected_token:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid bearer token")


def _enforce_rate_limit(request: Request) -> None:
    client_host = request.client.host if request.client else "unknown"
    now = datetime.now()
    cutoff = now - timedelta(minutes=1)
    request_times = _REQUEST_LOG.setdefault(client_host, deque())
    while request_times and request_times[0] < cutoff:
        request_times.popleft()
    if len(request_times) >= RATE_LIMIT_PER_MINUTE:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Rate limit exceeded")
    request_times.append(now)
