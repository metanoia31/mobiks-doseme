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

ap = argparse.ArgumentParser(description='KOLİ ETİKETİ PDF (A4 sayfada 4 etiket)')
ap.add_argument('--sip', required=True)
ap.add_argument('--musteri', required=True)
ap.add_argument('--urun', required=True)
ap.add_argument('--kumas', required=True)
ap.add_argument('--cila', default='')
ap.add_argument('--adet', type=int, required=True)
ap.add_argument('--out-dir', default='/tmp/claude-0/-home-user-mobiks-doseme/'
                                     'a9b86234-aa23-527c-9454-3ed13e122ec0/scratchpad')
args = ap.parse_args()

ITEM = dict(sip=args.sip, musteri=args.musteri, urun=args.urun,
            kumas=args.kumas, cila=args.cila, adet=args.adet)

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
    out = os.path.join(args.out_dir,
                       f"ETIKET_SIP{ITEM['sip']}_{slug(ITEM['urun'], 30)}"
                       f"_{slug(kumas_slug_kaynak(ITEM['kumas']), 40)}_x{ITEM['adet']}.pdf")
    tarih = datetime.date.today().strftime('%d.%m.%Y')
    c = canvas.Canvas(out, pagesize=A4)
    for i in range(ITEM['adet']):
        if i and i % PER_PAGE == 0:
            c.showPage()
        slot = i % PER_PAGE
        x0 = MARGIN + (slot % COLS) * LABEL_W
        y0 = PAGE_H - MARGIN - (slot // COLS + 1) * LABEL_H
        etiket_ciz(c, ITEM, x0, y0, tarih)
    c.save()
    print(f"{ITEM['adet']} etiket / {-(-ITEM['adet'] // PER_PAGE)} sayfa -> {out}")


if __name__ == '__main__':
    main()
