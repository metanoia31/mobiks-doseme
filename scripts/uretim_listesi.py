#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ustaya üretim listesi — Excel kolon düzeninde, ürün fotoğraflı,
KUMAŞ'ın yanında geniş boş USTA NOTU sütunu.

Kullanım:
    python3 scripts/uretim_listesi.py --sonra 152771
    python3 scripts/uretim_listesi.py --sonra 152771 --foto-dizin ./fotograflar

Fotoğraflar `ÜRÜN RESİMLERİ` sayfasındaki URL'lerden indirilir. İnternet
erişimi Google Drive'a kapalıysa --foto-dizin ile yerel klasör verilebilir
(dosya adı ürün adı olmalı: "KUZ İKİLİ.jpg" gibi). Fotoğrafı bulunamayan
ürünlerde hücre boş bırakılır.
"""

import argparse
import datetime
import os
import re
import unicodedata

import gspread
from google.oauth2.service_account import Credentials
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

pdfmetrics.registerFont(TTFont('DejaVu', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'))
pdfmetrics.registerFont(TTFont('DejaVu-Bold', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'))

SHEET_ID = os.environ.get('MOBIKS_SHEET_ID', '1XgVQFzauhAXmd4x6GlglReXYoOJjIiYZpNXxg9IgGXc')
CREDS = os.environ.get('MOBIKS_CREDENTIALS_FILE', '.gizli/service_account.json')

NAVY = colors.HexColor('#1a2a5e')
GRID = colors.HexColor('#9a9a95')
BAND = colors.HexColor('#dfe6f5')
SIP_BAND = colors.HexColor('#eef2fa')

FOTO_W, FOTO_H = 62, 46          # punto — fotoğraf hücresinin iç ölçüsü

norm = lambda v: re.sub(r'\s+', ' ', str(v if v is not None else '')).strip()


def dosya_adi(urun):
    """Ürün adını dosya adıyla eşleştirmek için sadeleştirir."""
    s = unicodedata.normalize('NFKD', urun).encode('ascii', 'ignore').decode()
    return re.sub(r'[^a-z0-9]', '', s.lower())


def foto_indir(url, hedef):
    import urllib.request
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=30) as resp:
        veri = resp.read()
    if len(veri) < 1000 or veri[:15].lower().startswith(b'<!doctype html'):
        raise ValueError('görsel değil (HTML döndü)')
    with open(hedef, 'wb') as f:
        f.write(veri)
    return hedef


def foto_yukle(urunler, resim_url, foto_dizin, cache):
    """Ürün -> yerel dosya yolu sözlüğü döndürür."""
    os.makedirs(cache, exist_ok=True)
    yerel = {}
    yerel_index = {}
    if foto_dizin and os.path.isdir(foto_dizin):
        for f in os.listdir(foto_dizin):
            kok, uzanti = os.path.splitext(f)
            if uzanti.lower() in ('.jpg', '.jpeg', '.png', '.webp'):
                yerel_index[dosya_adi(kok)] = os.path.join(foto_dizin, f)

    basarisiz = []
    for u in sorted(urunler):
        anahtar = dosya_adi(u)
        if anahtar in yerel_index:
            yerel[u] = yerel_index[anahtar]
            continue
        url = resim_url.get(u)
        if not url:
            continue
        hedef = os.path.join(cache, f'{anahtar}.img')
        if os.path.exists(hedef) and os.path.getsize(hedef) > 1000:
            yerel[u] = hedef
            continue
        try:
            yerel[u] = foto_indir(url, hedef)
        except Exception as e:
            basarisiz.append((u, str(e)[:60]))
    return yerel, basarisiz


def foto_hucre(yol):
    """Fotoğrafı orantısını bozmadan hücreye sığdırır."""
    try:
        iw, ih = ImageReader(yol).getSize()
        olcek = min(FOTO_W / iw, FOTO_H / ih)
        return Image(yol, width=iw * olcek, height=ih * olcek)
    except Exception:
        return ''


def main():
    ap = argparse.ArgumentParser(description='Ustaya üretim listesi PDF')
    ap.add_argument('--sonra', default='152771',
                    help='Bu sipariş numarasından SONRAKİ siparişler listelenir')
    ap.add_argument('--foto-dizin', default=None,
                    help='Fotoğrafların bulunduğu yerel klasör (indirme kapalıysa)')
    ap.add_argument('--cache', default='.foto_cache')
    ap.add_argument('--out', default='URETIM_LISTESI.pdf')
    args = ap.parse_args()

    scopes = ['https://www.googleapis.com/auth/spreadsheets']
    creds = Credentials.from_service_account_file(CREDS, scopes=scopes)
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(SHEET_ID)

    resim_url = {norm(r[0]): norm(r[1])
                 for r in sh.worksheet('ÜRÜN RESİMLERİ').get_all_values()[1:]
                 if r and norm(r[0]) and len(r) > 1 and norm(r[1]).startswith('http')}

    kayitlar = []
    for r in sh.worksheet('Sayfa1').get('A2:M', value_render_option='UNFORMATTED_VALUE'):
        if not r or not norm(r[0]):
            continue
        g = lambda j: norm(r[j]) if len(r) > j else ''
        if g(0) <= args.sonra:
            continue
        adet = r[7] if len(r) > 7 and isinstance(r[7], (int, float)) else 0
        kayitlar.append(dict(sip=g(0), musteri=g(1), urun=g(3), cila=g(4), kumas_gelis=g(5),
                             kumas=g(6), adet=int(adet), aciklama=g(8), termin=g(12)))

    kayitlar.sort(key=lambda k: (k['sip'], k['urun'], k['kumas']))
    urunler = {k['urun'] for k in kayitlar}
    fotolar, basarisiz = foto_yukle(urunler, resim_url, args.foto_dizin, args.cache)

    print(f"Sipariş: {len({k['sip'] for k in kayitlar})} | kalem: {len(kayitlar)} | "
          f"adet: {sum(k['adet'] for k in kayitlar)}")
    print(f'Fotoğrafı bulunan ürün: {len(fotolar)}/{len(urunler)}')
    for u, hata in basarisiz:
        print(f'   fotoğraf alınamadı: {u} -> {hata}')

    h = ParagraphStyle('h', fontName='DejaVu', fontSize=7.5, leading=9.5)
    hb = ParagraphStyle('hb', fontName='DejaVu-Bold', fontSize=8, leading=10)
    hh = ParagraphStyle('hh', fontName='DejaVu-Bold', fontSize=7.5, leading=9.5)
    st_baslik = ParagraphStyle('b', fontName='DejaVu-Bold', fontSize=15, leading=18)
    st_alt = ParagraphStyle('a', fontName='DejaVu', fontSize=8.5, leading=11,
                            textColor=colors.HexColor('#555550'))

    doc = SimpleDocTemplate(args.out, pagesize=landscape(A4),
                            topMargin=10 * mm, bottomMargin=10 * mm,
                            leftMargin=8 * mm, rightMargin=8 * mm, title='Üretim Listesi')
    W = doc.width
    # FOTO, SİP.NO, MÜŞTERİ, ÜRÜN, CİLA, KUMAŞ, USTA NOTU, ADET, K.GELİŞ, TERMİN
    KOL = [W * 0.085, W * 0.05, W * 0.075, W * 0.125, W * 0.09,
           W * 0.15, W * 0.225, W * 0.04, W * 0.08, W * 0.08]
    BASLIK = ['FOTOĞRAF', 'SİP.NO', 'MÜŞTERİ NO', 'ÜRÜN', 'CİLA / AYAK', 'KUMAŞ',
              'USTA NOTU', 'ADET', 'KUMAŞ GELİŞ', 'TERMİN']

    veri = [[Paragraph(b, hh) for b in BASLIK]]
    stil = [
        ('GRID', (0, 0), (-1, -1), 0.5, GRID),
        ('BACKGROUND', (0, 0), (-1, 0), BAND),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),
        ('ALIGN', (7, 0), (-1, -1), 'CENTER'),
        ('TOPPADDING', (0, 1), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
    ]

    onceki = None
    for k in kayitlar:
        i = len(veri)
        if onceki is not None and k['sip'] != onceki:
            stil.append(('LINEABOVE', (0, i), (-1, i), 1.6, NAVY))
        if k['sip'] != onceki:
            stil.append(('BACKGROUND', (1, i), (1, i), SIP_BAND))
        onceki = k['sip']

        urun_p = Paragraph(k['urun'], hb)
        if k['aciklama']:
            urun_p = Paragraph(f"{k['urun']}<br/><font color='#b03030' size='6.5'>"
                               f"! {k['aciklama']}</font>", hb)

        veri.append([
            foto_hucre(fotolar[k['urun']]) if k['urun'] in fotolar else '',
            Paragraph(k['sip'], hb),
            Paragraph(k['musteri'], h),
            urun_p,
            Paragraph(k['cila'] or '-', h),
            Paragraph(k['kumas'] or '-', h),
            '',                                  # USTA NOTU — elle doldurulacak
            Paragraph(f"<b>{k['adet']}</b>", hb),
            Paragraph(k['kumas_gelis'] or '-', h),
            Paragraph(k['termin'] or '-', h),
        ])

    t = Table(veri, colWidths=KOL, repeatRows=1)
    t.setStyle(TableStyle(stil))

    doc.build([
        Paragraph('ÜRETİM LİSTESİ', st_baslik),
        Paragraph(f"{args.sonra} sonrası siparişler &nbsp;·&nbsp; "
                  f"{len({k['sip'] for k in kayitlar})} sipariş, {len(kayitlar)} kalem, "
                  f"{sum(k['adet'] for k in kayitlar)} adet &nbsp;·&nbsp; "
                  f"Liste tarihi: {datetime.date.today():%d.%m.%Y}", st_alt),
        Spacer(1, 6),
        t,
    ])
    print('PDF:', args.out)


if __name__ == '__main__':
    main()
