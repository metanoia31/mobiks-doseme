#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MOBIKS Takip — DASHBOARD sayfasını kurar (canlı formüllerle)."""

import gspread
from google.oauth2.service_account import Credentials

import os

SHEET_ID = os.environ.get('MOBIKS_SHEET_ID', '1XgVQFzauhAXmd4x6GlglReXYoOJjIiYZpNXxg9IgGXc')
CREDS = os.environ.get('MOBIKS_CREDENTIALS_FILE', '.gizli/service_account.json')

scopes = ['https://www.googleapis.com/auth/spreadsheets']
creds = Credentials.from_service_account_file(CREDS, scopes=scopes)
gc = gspread.authorize(creds)
sh = gc.open_by_key(SHEET_ID)

AYLAR = ['OCAK', 'ŞUBAT', 'MART', 'NİSAN', 'MAYIS', 'HAZİRAN',
         'TEMMUZ', 'AĞUSTOS', 'EYLÜL', 'EKİM', 'KASIM', 'ARALIK']
AY_CHOOSE = 'CHOOSE(MONTH(TODAY()),' + ','.join(f'"{a}"' for a in AYLAR) + ')'
BU_AY = f'"\'GİDEN "&{AY_CHOOSE}&" "&YEAR(TODAY())&"\'!'

# --- sayfayı oluştur / sıfırla ---------------------------------------------
try:
    ws = sh.worksheet('DASHBOARD')
    ws.clear()
except gspread.exceptions.WorksheetNotFound:
    ws = sh.add_worksheet(title='DASHBOARD', rows=60, cols=12, index=0)

# --- içerik -----------------------------------------------------------------
rows = [None] * 41  # 1..40 arası satırlar

rows[1] = ['MOBIKS SİPARİŞ TAKİP — DASHBOARD']
rows[2] = ['Tüm rakamlar Sayfa1 ve GİDEN sayfalarından canlı hesaplanır; elle güncelleme gerekmez.']

rows[4] = ['AÇIK SİPARİŞ', 'BEKLEYEN KALEM', 'BEKLEYEN ADET', 'BEKLEYEN TUTAR', 'SEVKE HAZIR ✓', 'BU AY SEVK (ADET)']
rows[5] = [
    '=COUNTUNIQUE(FILTER(Sayfa1!A2:A,Sayfa1!A2:A<>""))',
    '=COUNTA(Sayfa1!A2:A)',
    '=SUM(Sayfa1!H2:H)',
    '=SUM(Sayfa1!K2:K)',
    '=COUNTIF(Sayfa1!I2:I,"HAZIR ✓")',
    f'=IFERROR(SUM(INDIRECT({BU_AY}G4:G")),0)',
]

rows[7] = ['KUMAŞI GELEN KALEM', 'BU AY SEVK TUTAR', '2026 SEVK ADET', '2026 SEVK TUTAR']
rows[8] = [
    '=COUNTIF(Sayfa1!F2:F,"GELDİ")',
    f'=IFERROR(SUM(INDIRECT({BU_AY}I4:I")),0)',
    '=C24',
    '=D24',
]

rows[10] = ['AYLIK SEVKİYAT (2026)']
rows[11] = ['AY', 'KALEM', 'ADET', 'TUTAR']
for i, ay in enumerate(AYLAR):
    r = 12 + i
    ref = f'"\'GİDEN "&$A{r}&" 2026\'!'
    rows[r] = [
        ay,
        f'=IFERROR(COUNTA(INDIRECT({ref}A4:A")),0)',
        f'=IFERROR(SUM(INDIRECT({ref}G4:G")),0)',
        f'=IFERROR(SUM(INDIRECT({ref}I4:I")),0)',
    ]
rows[24] = ['TOPLAM', '=SUM(B12:B23)', '=SUM(C12:C23)', '=SUM(D12:D23)']

rows[26] = ['EN ÇOK BEKLEYEN ÜRÜNLER (Sayfa1)']
rows[27] = [
    '=IFERROR(QUERY(Sayfa1!D2:K,'
    '"select Col1, sum(Col5), sum(Col8) where Col1 is not null and Col1 != \'\' '
    'group by Col1 order by sum(Col5) desc limit 12 '
    'label Col1 \'ÜRÜN\', sum(Col5) \'ADET\', sum(Col8) \'TUTAR\'",0),"")'
]

values = [rows[i] if rows[i] else [''] for i in range(1, 41)]
ws.update(range_name='A1:F40', values=[r + [''] * (6 - len(r)) for r in values],
          value_input_option='USER_ENTERED')

print('Değerler yazıldı.')

# --- biçimlendirme ----------------------------------------------------------
sid = ws.id

INK = {'red': 0.043, 'green': 0.043, 'blue': 0.043}          # #0b0b0b
MUTED = {'red': 0.537, 'green': 0.529, 'blue': 0.506}        # #898781
BLUE = {'red': 0.165, 'green': 0.471, 'blue': 0.839}         # #2a78d6
BLUE_SOFT = {'red': 0.804, 'green': 0.886, 'blue': 0.984}    # #cde2fb
SURFACE = {'red': 0.988, 'green': 0.988, 'blue': 0.984}      # #fcfcfb
GRID = {'red': 0.882, 'green': 0.878, 'blue': 0.851}         # #e1e0d9


def cell_fmt(row1, col1, row2, col2, fmt, fields):
    return {'repeatCell': {
        'range': {'sheetId': sid, 'startRowIndex': row1 - 1, 'endRowIndex': row2,
                  'startColumnIndex': col1 - 1, 'endColumnIndex': col2},
        'cell': {'userEnteredFormat': fmt},
        'fields': fields,
    }}


reqs = [
    # tüm sayfa: yüzey rengi + font
    cell_fmt(1, 1, 60, 12,
             {'backgroundColor': SURFACE,
              'textFormat': {'fontFamily': 'Arial', 'fontSize': 10, 'foregroundColor': INK}},
             'userEnteredFormat(backgroundColor,textFormat)'),
    # başlık
    {'mergeCells': {'range': {'sheetId': sid, 'startRowIndex': 0, 'endRowIndex': 1,
                              'startColumnIndex': 0, 'endColumnIndex': 6}, 'mergeType': 'MERGE_ALL'}},
    cell_fmt(1, 1, 1, 6,
             {'textFormat': {'bold': True, 'fontSize': 16, 'foregroundColor': INK},
              'verticalAlignment': 'MIDDLE'},
             'userEnteredFormat(textFormat,verticalAlignment)'),
    {'updateDimensionProperties': {
        'range': {'sheetId': sid, 'dimension': 'ROWS', 'startIndex': 0, 'endIndex': 1},
        'properties': {'pixelSize': 42}, 'fields': 'pixelSize'}},
    # alt başlık
    {'mergeCells': {'range': {'sheetId': sid, 'startRowIndex': 1, 'endRowIndex': 2,
                              'startColumnIndex': 0, 'endColumnIndex': 6}, 'mergeType': 'MERGE_ALL'}},
    cell_fmt(2, 1, 2, 6,
             {'textFormat': {'fontSize': 9, 'foregroundColor': MUTED}},
             'userEnteredFormat.textFormat'),
    # KPI etiketleri (satır 4 ve 7)
    cell_fmt(4, 1, 4, 6,
             {'backgroundColor': BLUE, 'horizontalAlignment': 'CENTER',
              'textFormat': {'bold': True, 'fontSize': 9,
                             'foregroundColor': {'red': 1, 'green': 1, 'blue': 1}}},
             'userEnteredFormat(backgroundColor,horizontalAlignment,textFormat)'),
    cell_fmt(7, 1, 7, 4,
             {'backgroundColor': BLUE, 'horizontalAlignment': 'CENTER',
              'textFormat': {'bold': True, 'fontSize': 9,
                             'foregroundColor': {'red': 1, 'green': 1, 'blue': 1}}},
             'userEnteredFormat(backgroundColor,horizontalAlignment,textFormat)'),
    # KPI değerleri (satır 5 ve 8)
    cell_fmt(5, 1, 5, 6,
             {'backgroundColor': BLUE_SOFT, 'horizontalAlignment': 'CENTER',
              'numberFormat': {'type': 'NUMBER', 'pattern': '#,##0'},
              'textFormat': {'bold': True, 'fontSize': 18, 'foregroundColor': INK}},
             'userEnteredFormat(backgroundColor,horizontalAlignment,numberFormat,textFormat)'),
    cell_fmt(8, 1, 8, 4,
             {'backgroundColor': BLUE_SOFT, 'horizontalAlignment': 'CENTER',
              'numberFormat': {'type': 'NUMBER', 'pattern': '#,##0'},
              'textFormat': {'bold': True, 'fontSize': 18, 'foregroundColor': INK}},
             'userEnteredFormat(backgroundColor,horizontalAlignment,numberFormat,textFormat)'),
    # para birimi olan KPI'lar
    cell_fmt(5, 4, 5, 4, {'numberFormat': {'type': 'NUMBER', 'pattern': '#,##0 "₺"'}},
             'userEnteredFormat.numberFormat'),
    cell_fmt(8, 2, 8, 2, {'numberFormat': {'type': 'NUMBER', 'pattern': '#,##0 "₺"'}},
             'userEnteredFormat.numberFormat'),
    cell_fmt(8, 4, 8, 4, {'numberFormat': {'type': 'NUMBER', 'pattern': '#,##0 "₺"'}},
             'userEnteredFormat.numberFormat'),
    # KPI satır yükseklikleri
    {'updateDimensionProperties': {
        'range': {'sheetId': sid, 'dimension': 'ROWS', 'startIndex': 4, 'endIndex': 5},
        'properties': {'pixelSize': 34}, 'fields': 'pixelSize'}},
    {'updateDimensionProperties': {
        'range': {'sheetId': sid, 'dimension': 'ROWS', 'startIndex': 7, 'endIndex': 8},
        'properties': {'pixelSize': 34}, 'fields': 'pixelSize'}},
    # bölüm başlıkları
    cell_fmt(10, 1, 10, 4, {'textFormat': {'bold': True, 'fontSize': 12, 'foregroundColor': INK}},
             'userEnteredFormat.textFormat'),
    cell_fmt(26, 1, 26, 4, {'textFormat': {'bold': True, 'fontSize': 12, 'foregroundColor': INK}},
             'userEnteredFormat.textFormat'),
    # tablo başlık satırları
    cell_fmt(11, 1, 11, 4,
             {'backgroundColor': GRID, 'textFormat': {'bold': True, 'fontSize': 9}},
             'userEnteredFormat(backgroundColor,textFormat)'),
    cell_fmt(27, 1, 27, 3,
             {'backgroundColor': GRID, 'textFormat': {'bold': True, 'fontSize': 9}},
             'userEnteredFormat(backgroundColor,textFormat)'),
    # sayı formatları — aylık tablo
    cell_fmt(12, 2, 24, 3, {'numberFormat': {'type': 'NUMBER', 'pattern': '#,##0'}},
             'userEnteredFormat.numberFormat'),
    cell_fmt(12, 4, 24, 4, {'numberFormat': {'type': 'NUMBER', 'pattern': '#,##0 "₺"'}},
             'userEnteredFormat.numberFormat'),
    cell_fmt(24, 1, 24, 4, {'textFormat': {'bold': True}}, 'userEnteredFormat.textFormat'),
    # ürün tablosu sayı formatları
    cell_fmt(28, 2, 40, 2, {'numberFormat': {'type': 'NUMBER', 'pattern': '#,##0'}},
             'userEnteredFormat.numberFormat'),
    cell_fmt(28, 3, 40, 3, {'numberFormat': {'type': 'NUMBER', 'pattern': '#,##0 "₺"'}},
             'userEnteredFormat.numberFormat'),
    # sütun genişlikleri
    {'updateDimensionProperties': {
        'range': {'sheetId': sid, 'dimension': 'COLUMNS', 'startIndex': 0, 'endIndex': 1},
        'properties': {'pixelSize': 210}, 'fields': 'pixelSize'}},
    {'updateDimensionProperties': {
        'range': {'sheetId': sid, 'dimension': 'COLUMNS', 'startIndex': 1, 'endIndex': 6},
        'properties': {'pixelSize': 132}, 'fields': 'pixelSize'}},
    # gridlines kapat, ilk satırları dondur
    {'updateSheetProperties': {
        'properties': {'sheetId': sid, 'gridProperties': {'hideGridlines': True, 'frozenRowCount': 2}},
        'fields': 'gridProperties(hideGridlines,frozenRowCount)'}},
]

sh.batch_update({'requests': reqs})
print('Biçimlendirme uygulandı.')
