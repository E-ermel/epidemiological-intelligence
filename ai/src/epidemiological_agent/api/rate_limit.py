import math
import threading
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request


def client_ip(request: Request) -> str:
    """
    On Cloud Run the TCP peer (request.client) is Google's front end,
    not the user, so the real address comes from X-Forwarded-For. The
    *last* entry is used, not the first: the front end appends the
    address it actually saw, while anything before it is whatever the
    client chose to send -- taking the first entry would let anyone
    dodge the limit by sending a fake header.
    """

    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[-1].strip()

    if request.client is not None:
        return request.client.host

    return "unknown"


class RateLimiter:
    """
    Sliding-window limit per client IP, used as a FastAPI dependency
    (`dependencies=[Depends(limiter)]`).

    In-memory on purpose: no Redis/Memorystore to run for this. The
    trade-off is that each Cloud Run instance counts separately, so the
    effective ceiling is max_requests x live instances -- fine for
    stopping a request loop, not a precise quota. The OpenAI spend
    limit is the hard backstop for /chat.
    """

    def __init__(self, max_requests: int, window_seconds: int) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def __call__(self, request: Request) -> None:
        key = client_ip(request)
        now = time.monotonic()

        with self._lock:
            hits = self._hits[key]

            while hits and now - hits[0] >= self.window_seconds:
                hits.popleft()

            if len(hits) >= self.max_requests:
                retry_after = math.ceil(self.window_seconds - (now - hits[0]))
                raise HTTPException(
                    status_code=429,
                    detail="Limite de requisições atingido. Tente novamente mais tarde.",
                    headers={"Retry-After": str(retry_after)},
                )

            hits.append(now)

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


# Cada mensagem do chat gasta créditos da OpenAI (às vezes várias
# chamadas, com tools); 20/hora cobre uma conversa normal com folga.
chat_rate_limit = RateLimiter(max_requests=20, window_seconds=3600)

# Retreino é um job de até 1h (2 CPU / 4 GiB). Além deste limite, as
# rotas recusam com 409 enquanto já houver uma execução rodando.
retrain_rate_limit = RateLimiter(max_requests=3, window_seconds=3600)
