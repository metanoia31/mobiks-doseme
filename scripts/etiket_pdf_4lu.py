#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KOLİ ETİKETİ — PDF, A4 sayfada 4 etiket (2x2)."""

import re
import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.colors import Color
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

pdfmetrics.registerFont(TTFont('DejaVu', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'))
pdfmetrics.registerFont(TTFont('DejaVu-Bold', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'))

NAVY = Color(26 / 255, 42 / 255, 94 / 255)
GREY = Color(0.35, 0.35, 0.35)

import argparse
import os

ap = argparse.ArgumentParser(
    description='KOLİ ETİKETİ PDF (A4 sayfada 4 etiket). İki kullanım şekli:\n'
                '  1) Sayfa1den çek:  --sip 152618 --urun-ara LEVEL\n'
                '  2) Elle gir:       --sip ... --musteri ... --urun ... --kumas ... --adet ...',
    formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument('--sip', required=True, help='Sipariş no')
ap.add_argument('--urun-ara', default=None,
                help='Sayfa1den çekerken ürün adı filtresi (parça eşleşme, ör. LEVEL)')
ap.add_argument('--musteri')
ap.add_argument('--urun')
ap.add_argument('--kumas', help='Verilirse elle giriş modu kullanılır')
ap.add_argument('--cila', default='')
ap.add_argument('--adet', type=int, help='Elle giriş modunda zorunlu; Sayfa1 modunda tümünü ezer')
ap.add_argument('--etiket-adi', default=None, help='Dosya adındaki ürün bölümü (çoklu kalemde)')
ap.add_argument('--out-dir', default='.')
args = ap.parse_args()


def _sayfa1den_cek(sip, urun_ara):
    """Sayfa1den ilgili siparişin kalemlerini okur."""
    import gspread
    from google.oauth2.service_account import Credentials
    creds = Credentials.from_service_account_file(
        os.environ.get('MOBIKS_CREDENTIALS_FILE', '.gizli/service_account.json'),
        scopes=['https://www.googleapis.com/auth/spreadsheets'])
    sh = gspread.authorize(creds).open_by_key(
        os.environ.get('MOBIKS_SHEET_ID', '1XgVQFzauhAXmd4x6GlglReXYoOJjIiYZpNXxg9IgGXc'))
    nrm = lambda v: re.sub(r'\s+', ' ', str(v if v is not None else '')).strip()

    bulunan = []
    for r in sh.worksheet('Sayfa1').get('A2:M', value_render_option='UNFORMATTED_VALUE'):
        if not r or not nrm(r[0]):
            continue
        g = lambda j: nrm(r[j]) if len(r) > j else ''
        if g(0) != sip:
            continue
        if urun_ara and urun_ara.upper() not in g(3).upper():
            continue
        adet = r[7] if len(r) > 7 and isinstance(r[7], (int, float)) else 0
        if adet <= 0:
            continue
        bulunan.append(dict(sip=g(0), musteri=g(1), urun=g(3), cila=g(4),
                            kumas=g(6), adet=int(adet)))
    return bulunan


if args.kumas:   # elle giriş modu
    if not (args.musteri and args.urun and args.adet):
        ap.error('elle giriş için --musteri, --urun ve --adet gerekli')
    ITEMS = [dict(sip=args.sip, musteri=args.musteri, urun=args.urun,
                  kumas=args.kumas, cila=args.cila, adet=args.adet)]
else:            # Sayfa1den çek
    ITEMS = _sayfa1den_cek(args.sip, args.urun_ara)
    if not ITEMS:
        ap.error(f'Sayfa1de eşleşen kalem bulunamadı (sip={args.sip}, '
                 f'ürün filtresi={args.urun_ara!r})')
    if args.adet:
        for it in ITEMS:
            it['adet'] = args.adet

TR = str.maketrans({'Ü': 'U', 'Ş': 'S', 'İ': 'I', 'Ğ': 'G', 'Ö': 'O', 'Ç': 'C'})


def slug(text, maxlen=40):
    return re.sub(r'[^A-Z0-9]+', '_', text.translate(TR).upper()).strip('_')[:maxlen].strip('_')

PAGE_W, PAGE_H = A4
COLS, ROWS = 2, 2
PER_PAGE = COLS * ROWS
MARGIN = 0.8 * 72 / 2.54
LABEL_W = (PAGE_W - 2 * MARGIN) / COLS
LABEL_H = (PAGE_H - 2 * MARGIN) / ROWS


def kumas_slug_kaynak(k):
    p = split_kumas(k)
    return f'{p[0][1]} {p[1][1]}' if len(p) == 2 else k


def split_kumas(k):
    up = k.upper()
    m = re.match(r'ALT\s*KUMAŞ\s*:?\s*(.*?)\s*ÜST\s*KUMAŞ\s*:?\s*(.*)$', up)
    if m:
        return [('ALT KUMAŞ', m.group(1).strip()), ('ÜST KUMAŞ', m.group(2).strip())]
    m = re.match(r'OTURUM\s*:?\s*(.*?)\s*SIRT\s*:?\s*(.*)$', up)
    if m:
        return [('OTURUM', m.group(1).strip()), ('SIRT', m.group(2).strip())]
    return [('KUMAŞ', k)]


def fit(text, font, max_size, max_w, min_size=10):
    size = max_size
    while size > min_size and pdfmetrics.stringWidth(text, font, size) > max_w:
        size -= 1
    return size


def etiket_ciz(c, item, x0, y0, tarih):
    # siyah çerçeve
    c.setStrokeColorRGB(0, 0, 0)
    c.setLineWidth(2)
    c.rect(x0 + 4, y0 + 4, LABEL_W - 8, LABEL_H - 8)

    # lacivert başlık barı — sadece "KOLİ ETİKETİ"
    bar_h = 54
    bar_y = y0 + LABEL_H - 8 - bar_h
    c.setFillColor(NAVY)
    c.rect(x0 + 6, bar_y, LABEL_W - 12, bar_h, fill=1, stroke=0)
    c.setFillColorRGB(1, 1, 1)
    c.setFont('DejaVu-Bold', 26)
    tw = c.stringWidth('KOLİ ETİKETİ', 'DejaVu-Bold', 26)
    c.drawString(x0 + (LABEL_W - tw) / 2, bar_y + (bar_h - 26) / 2 + 4, 'KOLİ ETİKETİ')

    x = x0 + 26
    inner_w = LABEL_W - 52
    y = bar_y - 26
    alt_sinir = y0 + 44  # tarih satırının üstü — içerik buranın altına inmemeli

    def alan(baslik, deger, size=19, bold=False, bosluk=9):
        nonlocal y
        c.setFillColor(GREY)
        c.setFont('DejaVu', 10)
        c.drawString(x, y, baslik)
        y -= 18
        c.setFillColorRGB(0, 0, 0)
        font = 'DejaVu-Bold' if bold else 'DejaVu'
        fs = fit(deger, font, size, inner_w, 9)
        c.setFont(font, fs)
        c.drawString(x, y, deger)
        y -= (fs + bosluk)

    alan('MÜŞTERİ NO', item['musteri'] or '-')
    alan('SİPARİŞ NO', item['sip'])
    alan('ÜRÜN', item['urun'], size=22, bold=True)
    for basl, deg in split_kumas(item['kumas']):
        alan(basl, deg or '-', size=18, bosluk=7)
    alan('CİLA / AYAK', item['cila'] or '-', size=18)

    assert y >= alt_sinir - 6, f'İÇERİK TAŞTI: y={y:.0f} < sınır={alt_sinir:.0f}'

    # alt sol: tarih
    c.setFillColorRGB(0, 0, 0)
    c.setFont('DejaVu', 11)
    c.drawString(x, y0 + 26, f'Tarih: {tarih}')


def main():
    toplam = sum(it['adet'] for it in ITEMS)
    if len(ITEMS) == 1:
        it = ITEMS[0]
        ad = (f"ETIKET_SIP{it['sip']}_{slug(it['urun'], 30)}"
              f"_{slug(kumas_slug_kaynak(it['kumas']), 40)}_x{it['adet']}")
    else:
        etiket = args.etiket_adi or args.urun_ara or 'KALEMLER'
        ad = f'ETIKET_SIP{args.sip}_{slug(etiket, 30)}_x{toplam}'

    out = os.path.join(args.out_dir, f'{ad}.pdf')
    tarih = datetime.date.today().strftime('%d.%m.%Y')
    c = canvas.Canvas(out, pagesize=A4)

    i = 0
    for it in ITEMS:
        print(f"   {it['urun']} | {it['kumas']} | cila={it['cila'] or '-'} | {it['adet']} etiket")
        for _ in range(it['adet']):
            if i and i % PER_PAGE == 0:
                c.showPage()
            slot = i % PER_PAGE
            x0 = MARGIN + (slot % COLS) * LABEL_W
            y0 = PAGE_H - MARGIN - (slot // COLS + 1) * LABEL_H
            etiket_ciz(c, it, x0, y0, tarih)
            i += 1
    c.save()
    print(f'{toplam} etiket / {-(-toplam // PER_PAGE)} sayfa -> {out}')


if __name__ == '__main__':
    main()
