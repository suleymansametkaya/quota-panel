# Yapay Zekâ Limitleri

KDE Plasma 6 panelinde Codex, Claude Code ve Antigravity kullanım limitlerini gösteren Türkçe widget.

## Kurulum

Python 3, KDE Plasma 6 ve `kpackagetool6` gerekir. Kaynak dizininden kurmak veya güncellemek için:

```sh
kpackagetool6 -t Plasma/Applet -i .
# Daha önce kuruluysa: kpackagetool6 -t Plasma/Applet -u .
```

Ardından panelin **Araç Takımı Ekle** menüsünden **Yapay Zekâ Limitleri** widget'ını ekleyin. Hazır `.plasmoid` paketi proje veri dizinindeki `outputs/` altında tutulur.

## Veri kaynakları

- **Codex:** Oturum açılmış Codex CLI'nin `app-server` limit bilgisini okur.
- **Claude Code:** Widget ayarlarından kurulan durum satırı bağlantısı, limitleri yerel önbelleğe aktarır. Veriler Claude Code oturumu açıldıktan sonra görünür.
- **Antigravity CLI:** Widget ayarlarından kurulan durum satırı bağlantısı, kota bilgisini yerel JSON dosyasına aktarır. CLI oturumunda `/usage` çalıştırılması gerekebilir.

Hesap anahtarları ve oturum dosyaları bu depoya alınmaz. Widget, kullanım verilerini çalıştığı makinedeki kullanıcı oturumundan okur.
