/**
 * İrsaliye -> Sayfa1 "HAZIR ✓" işaretleme (Google Apps Script).
 *
 * Bir irsaliyedeki kalemleri Sayfa1'de bulur ve I sütununa (AÇIKLAMA)
 * "HAZIR ✓" yazar. Ardından SenkronSayfa1ToGiden.gs'teki dakikalık tetikleyici
 * bu satırları otomatik olarak bu ayın GİDEN sayfasına taşır.
 *
 * Eşleşme: SİP (A) aynı + STOK ADI (D) ürün anahtarını içeriyor + KUMAŞ (G)
 * kumaş kodunu içeriyor. Sadece ADET (H) irsaliyedeki miktara birebir eşitse
 * işaretlenir; eksik/fazla/bulunamayan kalemler raporda gösterilir ve
 * dokunulmaz (elle bakılmalı).
 *
 * Kullanım:
 * 1) Bu dosyayı SenkronSayfa1ToGiden.gs ile aynı Apps Script projesine yeni
 *    dosya olarak ekle (Dosyalar -> + -> Komut dosyası).
 * 2) Önce irsaliyeKontrol fonksiyonunu çalıştır: hiçbir şeyi değiştirmez,
 *    sadece Yürütme günlüğüne (Execution log) rapor yazar.
 * 3) Rapor doğruysa irsaliyeSevkEt fonksiyonunu çalıştır.
 * Yeni irsaliye için IRSALIYE listesini güncellemek yeterli.
 */

var IRSALIYE_NO = 'IRS2026000000646'; // Zivella, 13.10.2026, 34 FF 2931
var IRSALIYE = [
  // [sip, ürün anahtarı, kumaş kodu, adet]
  ['152952', 'ADA SANDALYE', 'TT30506', 2],
  ['152952', 'ADA SANDALYE', 'TT30505', 2],
  ['152952', 'ADA SANDALYE', 'TT30502', 2],
  ['152952', 'PAY TEKLİ', 'TT30505', 11], // irsaliyede 2 satır: 5 + 6
  ['152952', 'PAY TEKLİ', 'TT30502', 5],
  ['152952', 'PAY TEKLİ', 'TT30506', 2],
  ['152952', 'PAY TEKLİ', 'TT30510', 6]
];

var IRS_READY_MARKER = 'HAZIR ✓';

function irsNorm_(v) {
  return (v === null || v === undefined ? '' : v).toString().replace(/\s+/g, ' ').trim().toUpperCase();
}

function irsaliyeEslestir_() {
  var src = SpreadsheetApp.getActiveSpreadsheet().getSheetByName('Sayfa1');
  var lastRow = src.getLastRow();
  var data = lastRow < 2 ? [] : src.getRange(2, 1, lastRow - 1, 9).getValues();
  var sonuc = [];

  IRSALIYE.forEach(function (k) {
    var sip = irsNorm_(k[0]), urun = irsNorm_(k[1]), kumas = irsNorm_(k[2]), adet = k[3];
    var satirlar = [];
    for (var i = 0; i < data.length; i++) {
      var r = data[i];
      if (irsNorm_(r[0]) !== sip) continue;
      if (irsNorm_(r[3]).indexOf(urun) === -1) continue;
      if (irsNorm_(r[6]).indexOf(kumas) === -1) continue;
      satirlar.push({ satir: i + 2, adet: Number(r[7]) || 0, hazir: irsNorm_(r[8]) === irsNorm_(IRS_READY_MARKER) });
    }
    var toplam = satirlar.reduce(function (s, x) { return s + x.adet; }, 0);
    var durum;
    if (!satirlar.length) durum = 'BULUNAMADI';
    else if (toplam === adet) durum = 'TAMAM';
    else durum = 'ADET FARKLI (Sayfa1: ' + toplam + ')';
    sonuc.push({ kalem: k, satirlar: satirlar, durum: durum });
  });
  return { sheet: src, sonuc: sonuc };
}

function irsaliyeRaporYaz_(sonuc) {
  Logger.log('İrsaliye ' + IRSALIYE_NO);
  sonuc.forEach(function (s) {
    var k = s.kalem;
    Logger.log((s.durum === 'TAMAM' ? '✓ ' : '✗ ') + k[0] + ' | ' + k[1] + ' | ' + k[2] + ' | ' + k[3] +
      ' adet -> ' + s.durum + (s.satirlar.length ? ' [satır ' + s.satirlar.map(function (x) { return x.satir; }).join(', ') + ']' : ''));
  });
}

/** Sadece rapor; Sheet'te hiçbir şey değişmez. */
function irsaliyeKontrol() {
  irsaliyeRaporYaz_(irsaliyeEslestir_().sonuc);
}

/** Adeti birebir tutan kalemleri "HAZIR ✓" yapar; diğerlerine dokunmaz. */
function irsaliyeSevkEt() {
  var e = irsaliyeEslestir_();
  irsaliyeRaporYaz_(e.sonuc);
  var n = 0;
  e.sonuc.forEach(function (s) {
    if (s.durum !== 'TAMAM') return;
    s.satirlar.forEach(function (x) {
      e.sheet.getRange(x.satir, 9).setValue(IRS_READY_MARKER);
      n++;
    });
  });
  Logger.log(n + ' satır "' + IRS_READY_MARKER + '" yapıldı. Senkron tetikleyicisi bunları GİDEN sayfasına taşıyacak.');
}
