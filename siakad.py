#!/usr/bin/env python3
"""CLI: login SIAKAD lalu simpan halaman Daftar Hadir ke tmp/daftar_hadir.html.

    ./.venv/bin/python siakad.py
"""
from __future__ import annotations

from bs4 import BeautifulSoup

from autobuka import Credentials, PROJECT_ROOT, SiakadClient


def page_title(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    if soup.title and soup.title.string:
        return soup.title.string.strip()
    return "(tanpa judul)"


def main() -> int:
    client = SiakadClient()
    print("→ Login …")
    client.login(Credentials.from_env())
    resp = client.get("dosen/daftar_hadir")
    resp.raise_for_status()
    print(f"✓ Login OK — {page_title(resp.text)}")

    out = PROJECT_ROOT / "tmp"
    out.mkdir(exist_ok=True)
    dest = out / "daftar_hadir.html"
    dest.write_text(resp.text, encoding="utf-8")
    print(f"✓ Tersimpan: {dest} ({len(resp.text):,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
