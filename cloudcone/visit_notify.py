#!/usr/bin/env python3

import collections
import datetime
import ipaddress
import json
import os
import re
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


LISTEN_HOST = os.environ.get("VISIT_NOTIFY_HOST", "127.0.0.1")
LISTEN_PORT = int(os.environ.get("VISIT_NOTIFY_PORT", "8787"))
NTFY_BASE_URL = os.environ.get("NTFY_BASE_URL", "https://ntfy.sh").rstrip("/")
NTFY_TOPIC = os.environ["NTFY_TOPIC"]
NTFY_TOKEN = os.environ.get("NTFY_TOKEN", "")
ALLOWED_ORIGINS = {
    origin.strip()
    for origin in os.environ.get(
        "VISIT_ALLOWED_ORIGINS", "https://dttutty.com,https://www.dttutty.com"
    ).split(",")
    if origin.strip()
}

MAX_BODY_BYTES = 4096
RATE_WINDOW_SECONDS = 3600
PER_ADDRESS_LIMIT = 4
GLOBAL_LIMIT = 60


class RateLimiter:
    def __init__(self):
        self._lock = threading.Lock()
        self._by_address = collections.defaultdict(collections.deque)
        self._global = collections.deque()

    @staticmethod
    def _prune(entries, cutoff):
        while entries and entries[0] <= cutoff:
            entries.popleft()

    def allow(self, address):
        now = time.monotonic()
        cutoff = now - RATE_WINDOW_SECONDS
        with self._lock:
            self._prune(self._global, cutoff)
            address_entries = self._by_address[address]
            self._prune(address_entries, cutoff)
            if len(self._global) >= GLOBAL_LIMIT or len(address_entries) >= PER_ADDRESS_LIMIT:
                return False
            self._global.append(now)
            address_entries.append(now)
            return True


RATE_LIMITER = RateLimiter()


def client_address(headers, fallback):
    candidates = [headers.get("CF-Connecting-IP", "")]
    forwarded = headers.get("X-Forwarded-For", "")
    if forwarded:
        candidates.append(forwarded.split(",", 1)[0].strip())
    candidates.append(fallback)
    for candidate in candidates:
        try:
            return str(ipaddress.ip_address(candidate))
        except ValueError:
            continue
    return "unknown"


def clean_path(value):
    value = value if isinstance(value, str) else "/"
    value = value.split("?", 1)[0].split("#", 1)[0][:160]
    if not value.startswith("/") or not re.fullmatch(r"[A-Za-z0-9_./-]+", value):
        return "/"
    return value


def clean_referrer(value):
    value = value if isinstance(value, str) else "unknown"
    value = value.lower()[:120]
    if value in {"direct", "unknown"}:
        return value
    if not re.fullmatch(r"[a-z0-9.-]+", value):
        return "unknown"
    return value


def publish_notification(path, referrer):
    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    message = f"Page: {path}\nReferrer: {referrer}\nTime: {timestamp}"
    headers = {
        "Content-Type": "text/plain; charset=utf-8",
        "Title": "New visit to dttutty.com",
        "Tags": "eyes",
        "Priority": "3",
    }
    if NTFY_TOKEN:
        headers["Authorization"] = f"Bearer {NTFY_TOKEN}"
    topic = urllib.parse.quote(NTFY_TOPIC, safe="")
    request = urllib.request.Request(
        f"{NTFY_BASE_URL}/{topic}",
        data=message.encode("utf-8"),
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=8) as response:
        if response.status >= 300:
            raise RuntimeError(f"ntfy returned HTTP {response.status}")


class Handler(BaseHTTPRequestHandler):
    server_version = "visit-notify"
    sys_version = ""

    def log_message(self, message, *args):
        print(f"{self.log_date_time_string()} {message % args}", flush=True)

    def _origin(self):
        return self.headers.get("Origin", "")

    def _cors_headers(self):
        origin = self._origin()
        if origin in ALLOWED_ORIGINS:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")

    def _respond(self, status):
        self.send_response(status)
        self._cors_headers()
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        if self.path == "/healthz":
            self._respond(204)
        else:
            self._respond(404)

    def do_OPTIONS(self):
        if self.path != "/visit" or self._origin() not in ALLOWED_ORIGINS:
            self._respond(403)
            return
        self.send_response(204)
        self._cors_headers()
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Max-Age", "86400")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_POST(self):
        if self.path != "/visit":
            self._respond(404)
            return
        if self._origin() not in ALLOWED_ORIGINS:
            self._respond(403)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._respond(400)
            return
        if length <= 0 or length > MAX_BODY_BYTES:
            self._respond(413)
            return
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._respond(400)
            return
        address = client_address(self.headers, self.client_address[0])
        if not RATE_LIMITER.allow(address):
            self._respond(204)
            return
        try:
            publish_notification(
                clean_path(payload.get("path")), clean_referrer(payload.get("referrer"))
            )
        except (OSError, RuntimeError, urllib.error.URLError) as error:
            print(f"ntfy publish failed: {type(error).__name__}", flush=True)
            self._respond(502)
            return
        self._respond(204)


if __name__ == "__main__":
    server = ThreadingHTTPServer((LISTEN_HOST, LISTEN_PORT), Handler)
    print(f"Listening on {LISTEN_HOST}:{LISTEN_PORT}", flush=True)
    server.serve_forever()
