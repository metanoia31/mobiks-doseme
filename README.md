# mobiks-doseme

MOBIKS sipariş takip sistemi için Google Sheets senkron aracı.

## Kurulum

```
pip install -r requirements.txt
```

Google servis hesabı anahtarını `.gizli/service_account.json` olarak yerleştirin
(bu dosya `.gitignore` ile git dışında tutulur, asla commit edilmez). Servis
hesabının e-posta adresinin Google Sheet'te Editör olarak paylaşılmış olması
gerekir.

## Kalıcı çözüm: Google Apps Script (önerilen)

`apps_script/SenkronSayfa1ToGiden.gs` dosyası aynı senkron mantığını Google'ın
kendi sunucularında, bir sunucu/bilgisayar açık kalmasına gerek kalmadan
çalıştırır (tablet dahil her cihazdan Sheet'i düzenlemek yeterli). Kurulum
adımları dosyanın başındaki yorumda yazıyor: Sheet -> Uzantılar -> Apps
Script -> kodu yapıştır -> her dakika çalışan bir zaman tetikleyicisi ekle.

## Alternatif: Python script (kendi sunucunda çalıştırman gerekir)

## Sayfa1 -> GİDEN senkronu

`Sayfa1` sayfasında I sütunu (AÇIKLAMA) "HAZIR ✓" olarak işaretlenen
satırları, bugünün ayına karşılık gelen `GİDEN <AY> <YIL>` sayfasına taşır
(sayfa yoksa otomatik oluşturur) ve Sayfa1'den siler. C, J, K sütunlarındaki
formüllere ve koşullu biçimlendirmeye dokunmaz.

Tek seferlik çalıştırma (test için):

```
python3 scripts/sync_sayfa1_to_giden.py --once
```

Sürekli izleme modu (varsayılan: her 60 saniyede bir kontrol eder):

```
python3 scripts/sync_sayfa1_to_giden.py
```

Ortam değişkenleri ile ayarlanabilir:

- `MOBIKS_SHEET_ID` — Google Sheets ID (varsayılan MOBIKS Takip dosyası)
- `MOBIKS_CREDENTIALS_FILE` — servis hesabı anahtar dosyası yolu (varsayılan `.gizli/service_account.json`)
- `MOBIKS_POLL_INTERVAL_SECONDS` — izleme aralığı, saniye (varsayılan 60)
