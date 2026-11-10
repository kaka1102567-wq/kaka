"""Minimal Intervals.icu API client (stdlib only).

Auth: Intervals uses HTTP basic auth with username "API_KEY" and the key as
password. If INTERVALS_API_KEY is set, this client sends it. In a Claude cloud
environment the key is injected by the network proxy instead, so the variable
can stay unset there.
"""

from __future__ import annotations

import base64
import json
import os
import urllib.parse
import urllib.request

BASE_URL = "https://intervals.icu/api/v1"


class IntervalsClient:
    def __init__(self, athlete_id: str | None = None, api_key: str | None = None):
        self.athlete_id = athlete_id or os.environ.get("INTERVALS_ATHLETE_ID", "")
        if not self.athlete_id:
            raise ValueError("Set INTERVALS_ATHLETE_ID (e.g. i123456)")
        self.api_key = api_key if api_key is not None else os.environ.get("INTERVALS_API_KEY")

    def _get(self, path: str, params: dict | None = None):
        url = f"{BASE_URL}/athlete/{self.athlete_id}{path}"
        if params:
            url += "?" + urllib.parse.urlencode(params)
        # Cloudflare in front of Intervals rejects the default Python-urllib UA.
        req = urllib.request.Request(url, headers={"Accept": "application/json",
                                                   "User-Agent": "health-coach-agent/1.0"})
        if self.api_key and self.api_key != "proxy-injected":
            token = base64.b64encode(f"API_KEY:{self.api_key}".encode()).decode()
            req.add_header("Authorization", f"Basic {token}")
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())

    def athlete(self) -> dict:
        return self._get("")

    def wellness(self, oldest: str, newest: str) -> list[dict]:
        return self._get("/wellness", {"oldest": oldest, "newest": newest})

    def activities(self, oldest: str, newest: str) -> list[dict]:
        return self._get("/activities", {"oldest": oldest, "newest": newest})
