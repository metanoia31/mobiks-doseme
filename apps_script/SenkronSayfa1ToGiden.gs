/**
 * Sayfa1 -> GİDEN <AY> <YIL> senkron scripti (Google Apps Script).
 *
 * Sayfa1'de I sütunu (AÇIKLAMA) "HAZIR ✓" olan satırları bulur, ilgili ayın
 * GİDEN sayfasına (yoksa oluşturarak) satır olarak ekler ve Sayfa1'den siler.
 *
 * Kurulum:
 * 1) Google Sheet'i aç -> Uzantılar (Extensions) -> Apps Script.
 * 2) Açılan editördeki varsayılan kodu silip bu dosyanın tamamını yapıştır.
 * 3) Kaydet (disket ikonu).
 * 4) Sol menüden "Tetikleyiciler" (saat ikonu) -> "Tetikleyici Ekle":
 *      - Çalıştırılacak fonksiyon: syncSayfa1ToGiden
 *      - Etkinlik kaynağı: Zamana dayalı (Time-driven)
 *      - Tür: Dakika zamanlayıcısı (Minutes timer) -> Her dakika (Every minute)
 *    Kaydet, Google hesabı izni isteyecek, onayla.
 *
 * Bu script Google'ın kendi sunucularında çalışır; bilgisayar/tablet kapalı
 * olsa da, oturum sona ermiş olsa da çalışmaya devam eder.
 */

var READY_MARKER = 'HAZIR ✓';
var SOURCE_SHEET_NAME = 'Sayfa1';
var GIDEN_HEADER = ['TARİH', 'SİP', 'MÜŞTERİ', 'ÜRÜN', 'KUMAŞ', 'CİLA', 'ADET', 'BİRİM', 'TOPLAM'];
var TR_MONTHS = {
  1: 'OCAK', 2: 'ŞUBAT', 3: 'MART', 4: 'NİSAN', 5: 'MAYIS', 6: 'HAZİRAN',
  7: 'TEMMUZ', 8: 'AĞUSTOS', 9: 'EYLÜL', 10: 'EKİM', 11: 'KASIM', 12: 'ARALIK'
};

function gidenSheetName_(date) {
  return 'GİDEN ' + TR_MONTHS[date.getMonth() + 1] + ' ' + date.getFullYear();
}

function getOrCreateGidenSheet_(ss, name) {
  var sheet = ss.getSheetByName(name);
  if (sheet) return sheet;
  sheet = ss.insertSheet(name);
  sheet.getRange('A1').setValue(name);
  sheet.getRange('A3:I3').setValues([GIDEN_HEADER]);
  return sheet;
}

function syncSayfa1ToGiden() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var src = ss.getSheetByName(SOURCE_SHEET_NAME);
  var lastRow = src.getLastRow();
  if (lastRow < 2) return;

  var data = src.getRange(2, 1, lastRow - 1, 12).getValues();
  var today = new Date();
  var targetName = gidenSheetName_(today);
  var targetSheet = null;
  var tz = ss.getSpreadsheetTimeZone();

  // Alttan yukarı doğru işle: silme sırasında üstteki satır no'ları bozulmasın
  for (var i = data.length - 1; i >= 0; i--) {
    var row = data[i];
    var aciklama = (row[8] || '').toString().trim();
    if (aciklama !== READY_MARKER) continue;

    if (!targetSheet) targetSheet = getOrCreateGidenSheet_(ss, targetName);

    var sipNo = row[0];
    var musteri = row[1];
    var stokAdi = row[3];  // -> ÜRÜN
    var cila = row[4];     // -> CİLA
    var kumas = row[6];    // -> KUMAŞ
    var adet = row[7];
    var birim = row[9];    // BİRİM FİYAT (hesaplanmış değer)

    var nextRow = targetSheet.getLastRow() + 1;
    targetSheet.getRange(nextRow, 1, 1, 8).setValues([[
      Utilities.formatDate(today, tz, 'dd.MM.yyyy'),
      sipNo, musteri, stokAdi, kumas, cila, adet, birim
    ]]);
    targetSheet.getRange(nextRow, 9).setFormula('=G' + nextRow + '*H' + nextRow);

    src.deleteRow(i + 2); // i 0-indeksli, veri Sayfa1'de 2. satırdan başlıyor
  }
}
