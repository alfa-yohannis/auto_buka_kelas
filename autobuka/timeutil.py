"""Utilitas waktu + sumber waktu (Strategy) yang mudah di-mock saat test."""
from __future__ import annotations

import email.utils
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

WIB = timezone(timedelta(hours=7))


def parse_http_date(value: str) -> datetime:
    """Parse header HTTP Date -> datetime aware (UTC)."""
    return email.utils.parsedate_to_datetime(value)


def parse_hhmm(value: str) -> Tuple[int, int]:
    """'10:00 - 12:50' atau '10:00:00.000' -> (10, 0)."""
    part = value.split("-")[0].strip()
    bits = part.split(":")
    return int(bits[0]), int(bits[1]) if len(bits) > 1 else 0


def class_start(tgl_absensi: str, jam: str) -> datetime:
    """Waktu mulai pertemuan (aware, WIB) dari TGL_ABSENSI + jam mulai."""
    tgl = (tgl_absensi or "")[:10]
    jam = (jam or "00:00:00")[:8]
    if len(jam) == 5:  # 'HH:MM'
        jam += ":00"
    return datetime.strptime(f"{tgl} {jam}", "%Y-%m-%d %H:%M:%S").replace(tzinfo=WIB)


class Clock:
    """Sumber waktu default (jam lokal)."""

    def now_utc(self) -> datetime:
        return datetime.now(timezone.utc)

    def now_wib(self) -> datetime:
        return self.now_utc().astimezone(WIB)

    def today_wib(self) -> str:
        return self.now_wib().strftime("%Y-%m-%d")


class ServerClock(Clock):
    """Clock tersinkron ke jam server (offset dari header Date)."""

    def __init__(self, offset: timedelta = timedelta(0)):
        self.offset = offset

    @classmethod
    def from_header_date(cls, header_date: str, local_utc: Optional[datetime] = None) -> "ServerClock":
        server = parse_http_date(header_date)
        local = local_utc or datetime.now(timezone.utc)
        return cls(server - local)

    def now_utc(self) -> datetime:
        return datetime.now(timezone.utc) + self.offset
