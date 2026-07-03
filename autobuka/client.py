"""SiakadClient — Facade untuk sesi HTTP + autentikasi SIAKAD (Laravel)."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

import requests
from bs4 import BeautifulSoup

from .config import BASE_URL, USER_AGENT, Credentials
from .timeutil import parse_http_date


class LoginError(RuntimeError):
    """Login ditolak / halaman tak sesuai harapan."""


class HttpError(RuntimeError):
    """Respons HTTP non-2xx dari endpoint."""


class SiakadClient:
    """Menyembunyikan detail requests.Session, CSRF, dan header AJAX.

    Alur khas:
        client = SiakadClient()
        client.login(Credentials.from_env())
        resp = client.post_ajax("dosen/daftar_hadir/search", data)
    """

    LOGIN = "login"
    LOGIN_PROCESS = "login_process"
    DAFTAR_HADIR = "dosen/daftar_hadir"

    def __init__(self, base_url: str = BASE_URL, session: Optional[requests.Session] = None):
        self.base_url = base_url.rstrip("/")
        self.session = session or requests.Session()
        self.session.headers.update(
            {
                "User-Agent": USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "id,en;q=0.9",
            }
        )
        self._csrf_token: Optional[str] = None

    # -- util ---------------------------------------------------------------
    def url(self, path: str) -> str:
        return f"{self.base_url}/{path.lstrip('/')}"

    @staticmethod
    def _extract_token(html: str) -> str:
        soup = BeautifulSoup(html, "html.parser")
        field = soup.find("input", attrs={"name": "_token"})
        if field and field.get("value"):
            return field["value"]
        meta = soup.find("meta", attrs={"name": "csrf-token"})
        if meta and meta.get("content"):
            return meta["content"]
        raise LoginError("CSRF token (_token / meta csrf-token) tidak ditemukan")

    # -- auth ---------------------------------------------------------------
    def login(self, creds: Credentials) -> None:
        resp = self.session.get(self.url(self.LOGIN), timeout=30)
        resp.raise_for_status()
        payload = {
            "_token": self._extract_token(resp.text),
            "email": creds.username,
            "password": creds.password,
            "remember_me": "on",
        }
        resp = self.session.post(
            self.url(self.LOGIN_PROCESS),
            data=payload,
            headers={"Referer": self.url(self.LOGIN), "Origin": self.base_url},
            timeout=30,
        )
        resp.raise_for_status()
        if resp.url.rstrip("/").endswith("/login") or 'name="password"' in resp.text:
            raise LoginError(f"Login gagal — cek USERNAME/PASSWORD (halaman akhir {resp.url})")
        self._csrf_token = None  # token lama tak valid setelah sesi diregenerasi

    def csrf_token(self, refresh: bool = False) -> str:
        """Ambil (dan cache) token dari halaman terautentikasi."""
        if self._csrf_token and not refresh:
            return self._csrf_token
        resp = self.session.get(self.url(self.DAFTAR_HADIR), timeout=30)
        resp.raise_for_status()
        self._csrf_token = self._extract_token(resp.text)
        return self._csrf_token

    # -- requests -----------------------------------------------------------
    def get(self, path: str, **kwargs) -> requests.Response:
        return self.session.get(self.url(path), timeout=30, **kwargs)

    def post_ajax(self, path: str, data: dict) -> requests.Response:
        headers = {
            "X-CSRF-TOKEN": self.csrf_token(),
            "X-Requested-With": "XMLHttpRequest",
            "Referer": self.url(self.DAFTAR_HADIR),
            "Origin": self.base_url,
        }
        resp = self.session.post(self.url(path), data=data, headers=headers, timeout=30)
        if not resp.ok:
            raise HttpError(f"HTTP {resp.status_code} dari {self.url(path)}: {resp.text[:500]}")
        return resp

    def server_time(self) -> datetime:
        """Waktu server (aware UTC) dari header Date."""
        resp = self.session.head(self.url(self.LOGIN), timeout=15)
        return parse_http_date(resp.headers["Date"])
