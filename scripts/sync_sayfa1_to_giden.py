#!/usr/bin/env python3
"""
Sayfa1 -> GİDEN <AY> <YIL> senkron servisi.

Sayfa1'de I sütunu (AÇIKLAMA) "HAZIR ✓" olan satırları bulur, ilgili ayın
GİDEN sayfasına (yoksa oluşturarak) satır olarak ekler ve Sayfa1'den siler.

Kural gereği C, J, K sütunlarındaki formüllere ve koşullu biçimlendirmeye
(otomatik yeşil boyama) hiç dokunulmaz; sadece I sütunu okunur.
"""
import os
import sys
import time
import datetime
import argparse

import gspread
from google.oauth2.service_account import Credentials
from gspread.exceptions import APIError

SHEET_ID = os.environ.get("MOBIKS_SHEET_ID", "1XgVQFzauhAXmd4x6GlglReXYoOJjIiYZpNXxg9IgGXc")
CREDENTIALS_FILE = os.environ.get("MOBIKS_CREDENTIALS_FILE", ".gizli/service_account.json")
POLL_INTERVAL_SECONDS = int(os.environ.get("MOBIKS_POLL_INTERVAL_SECONDS", "60"))

SOURCE_SHEET_NAME = "Sayfa1"
READY_MARKER = "HAZIR ✓"

TR_MONTHS = {
    1: "OCAK", 2: "ŞUBAT", 3: "MART", 4: "NİSAN", 5: "MAYIS", 6: "HAZİRAN",
    7: "TEMMUZ", 8: "AĞUSTOS", 9: "EYLÜL", 10: "EKİM", 11: "KASIM", 12: "ARALIK",
}

GIDEN_HEADER = ["TARİH", "SİP", "MÜŞTERİ", "ÜRÜN", "KUMAŞ", "CİLA", "ADET", "BİRİM", "TOPLAM"]


def connect():
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=scopes)
    gc = gspread.authorize(creds)
    return gc.open_by_key(SHEET_ID)


def giden_sheet_name(date):
    return f"GİDEN {TR_MONTHS[date.month]} {date.year}"


def get_or_create_giden_sheet(sh, name):
    try:
        return sh.worksheet(name)
    except gspread.exceptions.WorksheetNotFound:
        ws = sh.add_worksheet(title=name, rows=200, cols=9)
        ws.update("A1", [[name]])
        ws.update("A3:I3", [GIDEN_HEADER])
        print(f"[{now_str()}] Yeni sayfa oluşturuldu: {name}")
        return ws


def as_number(value):
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


def now_str():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def process_once(sh):
    src = sh.worksheet(SOURCE_SHEET_NAME)
    rows = src.get("A2:L", value_render_option="UNFORMATTED_VALUE")

    today = datetime.date.today()
    target_name = giden_sheet_name(today)
    target_ws = None
    moved = 0

    ready_indices = []
    for offset, row in enumerate(rows):
        row_index = offset + 2  # Sayfa1'de gerçek satır no (1. satır başlık)
        aciklama = str(row[8]).strip() if len(row) > 8 else ""
        if aciklama == READY_MARKER:
            ready_indices.append(row_index)

    # Alttan yukarı doğru işle: silme sırasında üstteki satır numaraları bozulmasın
    for row_index in sorted(ready_indices, reverse=True):
        row = rows[row_index - 2]

        def cell(i):
            return row[i] if len(row) > i else ""

        sip_no = as_number(cell(0))
        musteri = cell(1)
        stok_adi = cell(3)     # -> ÜRÜN
        cila = cell(4)         # -> CİLA
        kumas = cell(6)        # -> KUMAŞ
        adet = as_number(cell(7))
        birim = as_number(cell(9))

        if target_ws is None:
            target_ws = get_or_create_giden_sheet(sh, target_name)

        new_row_values = target_ws.get_all_values()
        next_row = len(new_row_values) + 1

        target_ws.append_row(
            [
                today.strftime("%d.%m.%Y"),
                sip_no,
                musteri,
                stok_adi,
                kumas,
                cila,
                adet,
                birim,
            ],
            value_input_option="USER_ENTERED",
        )
        target_ws.update_acell(f"I{next_row}", f"=G{next_row}*H{next_row}")

        src.delete_rows(row_index)
        moved += 1
        print(f"[{now_str()}] SİP {sip_no} -> {target_name} (Sayfa1 satır {row_index} silindi)")

    return moved


def main():
    parser = argparse.ArgumentParser(description="Sayfa1 -> GİDEN senkron servisi")
    parser.add_argument("--once", action="store_true", help="Sürekli izlemek yerine tek seferlik çalıştır")
    args = parser.parse_args()

    if not os.path.exists(CREDENTIALS_FILE):
        print(f"HATA: Servis hesabı anahtarı bulunamadı: {CREDENTIALS_FILE}", file=sys.stderr)
        sys.exit(1)

    sh = connect()
    print(f"[{now_str()}] Bağlandı: {sh.title}")

    if args.once:
        moved = process_once(sh)
        print(f"[{now_str()}] Bitti. {moved} satır taşındı.")
        return

    print(f"[{now_str()}] İzleme başladı (her {POLL_INTERVAL_SECONDS} sn). Durdurmak için Ctrl+C.")
    while True:
        try:
            process_once(sh)
        except APIError as e:
            print(f"[{now_str()}] Google Sheets API hatası, tekrar denenecek: {e}", file=sys.stderr)
        except Exception as e:
            print(f"[{now_str()}] Beklenmeyen hata: {e}", file=sys.stderr)
        time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
