#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KOLİ ETİKETİ — PDF, A4 sayfada 4 etiket (2x2)."""

import re
import datetime
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

def _font_kaydet():
    """Arial benzeri, Türkçe karakter destekli yazı tipini 'Etiket' / 'Etiket-Bold' adıyla kaydeder."""
    adaylar = [
        ('/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf',
         '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf'),
        (r'C:\Windows\Fonts\arial.ttf', r'C:\Windows\Fonts\arialbd.ttf'),
        ('/Library/Fonts/Arial.ttf', '/Library/Fonts/Arial Bold.ttf'),
        ('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
         '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'),
    ]
    for normal, bold in adaylar:
        if os.path.exists(normal) and os.path.exists(bold):
            pdfmetrics.registerFont(TTFont('Etiket', normal))
            pdfmetrics.registerFont(TTFont('Etiket-Bold', bold))
            return
    raise SystemExit('Türkçe destekli yazı tipi bulunamadı (Arial / Liberation Sans / DejaVu Sans)')

import argparse
import os

_font_kaydet()

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
    # dış çerçeve
    c.setStrokeColorRGB(0, 0, 0)
    c.setLineWidth(1.5)
    c.rect(x0 + 6, y0 + 6, LABEL_W - 12, LABEL_H - 12)

    # siyah başlık barı
    bar_h = 40
    bar_y = y0 + LABEL_H - 12 - bar_h
    c.setFillColorRGB(0, 0, 0)
    c.rect(x0 + 10, bar_y, LABEL_W - 20, bar_h, fill=1, stroke=0)
    c.setFillColorRGB(1, 1, 1)
    c.setFont('Etiket-Bold', 20)
    tw = c.stringWidth('KOLİ ETİKETİ', 'Etiket-Bold', 20)
    c.drawString(x0 + (LABEL_W - tw) / 2, bar_y + 13, 'KOLİ ETİKETİ')

    # satırlar: sol başlık (küçük, kalın), sağda değer
    satirlar = [('MÜŞTERİ NO:', item['musteri'] or '-', 'Etiket-Bold', 18),
                ('SİPARİŞ NO:', item['sip'], 'Etiket-Bold', 18),
                ('ÜRÜN:', item['urun'], 'Etiket-Bold', 18)]
    for basl, deg in split_kumas(item['kumas']):
        satirlar.append((basl + ':', deg or '-', 'Etiket', 15))
    satirlar.append(('CİLA/AYAK:', item['cila'] or '-', 'Etiket', 15))
    satirlar.append(('SİPARİŞ TOPLAMI:', str(item.get('toplam', item['adet'])), 'Etiket-Bold', 18))

    x_lbl = x0 + 28
    x_val = x0 + 28 + 104
    val_w = LABEL_W - 28 - 104 - 28
    ust = bar_y - 30
    alt = y0 + 50
    adim = (ust - alt) / max(len(satirlar) - 1, 1)
    adim = min(adim, 44)
    y = ust
    for basl, deg, font, size in satirlar:
        c.setFillColorRGB(0, 0, 0)
        c.setFont('Etiket-Bold', 8)
        c.drawString(x_lbl, y + 2, basl)
        fs = fit(deg, font, size, val_w, 8)
        c.setFont(font, fs)
        c.drawString(x_val, y, deg)
        y -= adim

    # alt sol: tarih
    c.setFont('Etiket', 9)
    c.drawString(x0 + 28, y0 + 20, f'Tarih: {tarih}')


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
