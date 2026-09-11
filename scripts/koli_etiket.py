#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MOBIKS koli etiketi üretici — 600x840 px PNG, ürün türü başına 1 adet."""

import os
import re
import datetime
import gspread
from google.oauth2.service_account import Credentials
from PIL import Image, ImageDraw, ImageFont

W, H = 600, 840
NAVY = (26, 42, 94)
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GREY = (90, 90, 90)

FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
FONT_B = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
f = lambda size, bold=False: ImageFont.truetype(FONT_B if bold else FONT, size)

OUT_DIR = '/tmp/claude-0/-home-user-mobiks-doseme/a9b86234-aa23-527c-9454-3ed13e122ec0/scratchpad/etiketler_png'
os.makedirs(OUT_DIR, exist_ok=True)

# kullanıcının açıkça hariç tuttukları (STK zaten kural gereği hariç)
HARIC = {
    ('146481', 'ZK10-B OTURMA ÜNİTESİ SAĞ', 'G129 (AÇIK GRİ)'),
    ('146481', 'ZK10-C OTURMA ÜNİTESİ', 'K9K9 (KIRMIZI)'),
    ('146763', 'ZK07A İKİLİ', 'G129 (AÇIK GRİ)'),
    ('146763', 'ZK07B İKİLİ BÜYÜK', 'G129 (AÇIK GRİ)'),
    ('147167', 'ZK06 TEKLİ', 'K9K9 (KIRMIZI)'),
    ('151063', 'PAY TEKLİ', 'AURA 1375'),
}

TR = str.maketrans({'Ü': 'U', 'ü': 'u', 'Ş': 'S', 'ş': 's', 'İ': 'I', 'ı': 'i',
                    'Ğ': 'G', 'ğ': 'g', 'Ö': 'O', 'ö': 'o', 'Ç': 'C', 'ç': 'c'})


def slug(text, maxlen=40):
    s = text.translate(TR).upper()
    s = re.sub(r'[^A-Z0-9]+', '_', s).strip('_')
    return s[:maxlen].strip('_')


def norm(v):
    return re.sub(r'\s+', ' ', str(v if v is not None else '')).strip()


def kumas_slug_kaynak(k):
    """Dosya adı için kumaşı sadeleştirir: ALT/ÜST, OTURUM/SIRT kelimelerini atar."""
    parcalar = split_kumas(k)
    if len(parcalar) == 2:
        return f'{parcalar[0][1]} {parcalar[1][1]}'
    return k


def split_kumas(k):
    """Çift kumaşlı ürünlerde iki satır döndürür, tekse tek satır."""
    up = k.upper()
    m = re.match(r'ALT\s*KUMAŞ\s*:?\s*(.*?)\s*ÜST\s*KUMAŞ\s*:?\s*(.*)$', up)
    if m:
        return [('ALT KUMAŞ', m.group(1).strip()), ('ÜST KUMAŞ', m.group(2).strip())]
    m = re.match(r'OTURUM\s*:?\s*(.*?)\s*SIRT\s*:?\s*(.*)$', up)
    if m:
        return [('OTURUM', m.group(1).strip()), ('SIRT', m.group(2).strip())]
    return [('KUMAŞ', k)]


def fit(draw, text, font_path, max_size, max_w, min_size=14, bold=False):
    size = max_size
    while size > min_size:
        font = f(size, bold)
        if draw.textlength(text, font=font) <= max_w:
            return font
        size -= 2
    return f(min_size, bold)


def wrap(draw, text, font, max_w, max_lines=2):
    words, lines, cur = text.split(' '), [], ''
    for w in words:
        trial = f'{cur} {w}'.strip()
        if draw.textlength(trial, font=font) <= max_w:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w
            if len(lines) == max_lines:
                break
    if cur and len(lines) < max_lines:
        lines.append(cur)
    return lines[:max_lines]


def etiket_ciz(item, path):
    img = Image.new('RGB', (W, H), WHITE)
    d = ImageDraw.Draw(img)

    # siyah çerçeve
    d.rectangle([6, 6, W - 7, H - 7], outline=BLACK, width=4)

    # lacivert başlık barı — sadece "KOLİ ETİKETİ"
    bar_top, bar_h = 10, 112
    d.rectangle([10, bar_top, W - 11, bar_top + bar_h], fill=NAVY)
    title_font = f(52, True)
    tw = d.textlength('KOLİ ETİKETİ', font=title_font)
    d.text(((W - tw) / 2, bar_top + (bar_h - 60) / 2), 'KOLİ ETİKETİ',
           font=title_font, fill=WHITE)

    x = 42
    max_w = W - 2 * x
    y = bar_top + bar_h + 38

    def alan(etiket, deger, deger_size=38, bold=False, gap=26):
        nonlocal y
        d.text((x, y), etiket, font=f(20), fill=GREY)
        y += 26
        font = fit(d, deger, FONT_B if bold else FONT, deger_size, max_w, 16, bold)
        for line in wrap(d, deger, font, max_w, max_lines=2):
            d.text((x, y), line, font=font, fill=BLACK)
            y += font.size + 6
        y += gap

    alan('MÜŞTERİ NO', item['musteri'] or '-')
    alan('SİPARİŞ NO', item['sip'])
    alan('ÜRÜN', item['urun'], deger_size=46, bold=True)
    for basl, deg in split_kumas(item['kumas']):
        alan(basl, deg or '-', deger_size=34, gap=18)
    alan('CİLA / AYAK', item['cila'] or '-', deger_size=34)

    # alt sol: tarih
    d.text((x, H - 66), f"Tarih: {item['tarih']}", font=f(24), fill=BLACK)

    img.save(path)


def main():
    scopes = ['https://www.googleapis.com/auth/spreadsheets']
    creds = Credentials.from_service_account_file('.gizli/service_account.json', scopes=scopes)
    gc = gspread.authorize(creds)
    sh = gc.open_by_key('1XgVQFzauhAXmd4x6GlglReXYoOJjIiYZpNXxg9IgGXc')
    rows = sh.worksheet('Sayfa1').get('A2:L180', value_render_option='UNFORMATTED_VALUE')

    tarih = datetime.date.today().strftime('%d.%m.%Y')
    gruplar, atlanan = {}, []

    for offset, r in enumerate(rows):
        satir = offset + 2
        if not r or not norm(r[0]):
            continue
        g = lambda i: norm(r[i]) if len(r) > i else ''
        sip, musteri, urun, cila, kumas = g(0), g(1), g(3), g(4), g(6)

        if musteri.upper() == 'STK':
            atlanan.append((satir, sip, urun, 'STK — kural gereği basılmaz'))
            continue
        if (sip, urun, kumas) in HARIC:
            atlanan.append((satir, sip, urun, 'kullanıcı hariç tuttu'))
            continue
        adet = r[7] if len(r) > 7 else 0
        if not isinstance(adet, (int, float)) or adet <= 0:
            atlanan.append((satir, sip, urun, f'adet={adet!r}'))
            continue

        key = (sip, musteri, urun, kumas, cila)
        if key in gruplar:
            gruplar[key]['adet'] += int(adet)
            gruplar[key]['satirlar'].append(satir)
        else:
            gruplar[key] = dict(sip=sip, musteri=musteri, urun=urun, kumas=kumas,
                                cila=cila, adet=int(adet), tarih=tarih, satirlar=[satir])

    print(f'Etiket üretilecek ürün türü: {len(gruplar)}')
    print(f'Atlanan satır: {len(atlanan)}')
    for a in atlanan:
        print('   satır', a[0], '|', a[1], '|', a[2], '->', a[3])

    birlesen = [v for v in gruplar.values() if len(v['satirlar']) > 1]
    if birlesen:
        print(f'\nAynı ürün türünde birleşen satırlar ({len(birlesen)} grup):')
        for v in birlesen:
            print('   ', v['sip'], v['urun'], v['kumas'], '| satırlar', v['satirlar'], '| toplam adet', v['adet'])

    kullanilan, cakisma = set(), []
    for it in gruplar.values():
        taban = (f"ETIKET_SIP{it['sip']}_{slug(it['urun'], 30)}"
                 f"_{slug(kumas_slug_kaynak(it['kumas']), 40)}_x{it['adet']}")
        fname = f'{taban}.png'
        if fname in kullanilan:
            # aynı sipariş/ürün/kumaş farklı müşteriye gidiyor -> müşteri no ile ayır
            ek = slug(it['musteri'], 20) or slug(it['cila'], 16) or 'ALT'
            fname = f"ETIKET_SIP{it['sip']}_{slug(it['urun'], 30)}" \
                    f"_{slug(kumas_slug_kaynak(it['kumas']), 40)}_{ek}_x{it['adet']}.png"
            cakisma.append((f'{taban}.png', fname))
            i = 2
            while fname in kullanilan:
                fname = f'{taban}_{ek}_{i}.png'
                i += 1
        kullanilan.add(fname)
        etiket_ciz(it, os.path.join(OUT_DIR, fname))

    if cakisma:
        print(f'\nAd çakışması çözüldü ({len(cakisma)}):')
        for t, f_ in cakisma:
            print('   ', t, '->', f_)

    print(f'\n{len(gruplar)} grup / {len(kullanilan)} PNG üretildi -> {OUT_DIR}')
    assert len(kullanilan) == len(gruplar), 'DOSYA SAYISI GRUP SAYISINDAN AZ!'


if __name__ == '__main__':
    main()
