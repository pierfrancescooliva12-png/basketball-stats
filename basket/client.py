"""Client HTTP con limite di una richiesta al secondo e retry."""

import logging
import time

import requests

from . import config

log = logging.getLogger(__name__)


class RateLimitedClient:
    def __init__(self, min_interval: float = config.MIN_INTERVAL_S, retries: int = 3):
        self.min_interval = min_interval
        self.retries = retries
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": config.USER_AGENT,
            "Referer": config.SITE_BASE + "/",
        })
        self._last = 0.0
        self.n_requests = 0

    def _wait(self):
        delta = time.monotonic() - self._last
        if delta < self.min_interval:
            time.sleep(self.min_interval - delta)
        self._last = time.monotonic()

    def get(self, url: str, params: dict | None = None) -> requests.Response:
        for attempt in range(1, self.retries + 1):
            self._wait()
            self.n_requests += 1
            try:
                resp = self.session.get(url, params=params, timeout=30)
            except requests.RequestException as exc:
                log.warning("Errore di rete su %s (tentativo %d): %s", url, attempt, exc)
            else:
                # 404 è una risposta valida (es. giornata inesistente): la gestisce il chiamante
                if resp.status_code < 500:
                    return resp
                log.warning("HTTP %s su %s (tentativo %d)", resp.status_code, url, attempt)
            time.sleep(2 ** attempt)
        raise RuntimeError(f"Impossibile scaricare {url} dopo {self.retries} tentativi")
