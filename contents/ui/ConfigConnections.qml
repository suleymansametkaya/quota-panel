import QtQuick
import QtQuick.Controls as QQC2
import QtQuick.Dialogs
import QtQuick.Layouts
import org.kde.kirigami as Kirigami
import org.kde.kcmutils as KCM
import org.kde.plasma.plasmoid
import org.kde.plasma.plasma5support as Plasma5Support

KCM.SimpleKCM {
    id: page

    // Plasma injects the whole applet configuration into each page. These
    // values are not edited here; declaring them keeps page construction clean
    // and lets the framework preserve them if this page is saved.
    property var cfg_showCodex
    property var cfg_showClaude
    property var cfg_showAntigravity
    property var cfg_hideUnavailable
    property var cfg_showResetTime
    property var cfg_showCredits
    property var cfg_refreshMinutes
    property var cfg_warningThreshold
    property var cfg_ringProvider
    property var cfg_language

    property alias cfg_antigravitySource: sourcePath.text

    property var cfg_showCodexDefault
    property var cfg_showClaudeDefault
    property var cfg_showAntigravityDefault
    property var cfg_hideUnavailableDefault
    property var cfg_showResetTimeDefault
    property var cfg_showCreditsDefault
    property var cfg_refreshMinutesDefault
    property var cfg_warningThresholdDefault
    property var cfg_ringProviderDefault
    property var cfg_languageDefault
    property var cfg_antigravitySourceDefault
    property string resultMessage: english ? "Checking connections…" : "Bağlantılar denetleniyor…"
    readonly property bool english: Plasmoid.configuration.language === "en"
    readonly property string helperPath: decodeURIComponent(Qt.resolvedUrl("../code/connection.py").toString().replace("file://", ""))

    function text(turkish, englishText) { return english ? englishText : turkish }
    function localizedResult(message) {
        if (!english) return message
        const translations = {
            "Bağlantılar denetleniyor…": "Checking connections…",
            "İşlem tamamlandı.": "Done.",
            "İşlem tamamlanamadı.": "The operation could not be completed.",
            "Codex CLI hazır": "Codex CLI ready",
            "Codex CLI bulunamadı": "Codex CLI not found",
            "Codex CLI bulunamadı.": "Codex CLI not found.",
            "Claude bağlı": "Claude connected",
            "Claude bağlantısı kurulmadı": "Claude is not connected",
            "Antigravity verisi var": "Antigravity data found",
            "Antigravity bağlı; CLI oturumu bekleniyor": "Antigravity connected; waiting for a CLI session",
            "Antigravity CLI hazır": "Antigravity CLI ready",
            "Antigravity CLI kurulu değil": "Antigravity CLI is not installed",
            "Antigravity CLI kurulu değil.": "Antigravity CLI is not installed.",
            "Codex giriş penceresi açıldı.": "Codex sign-in window opened.",
            "Konsole bulunamadı. Terminalde 'codex login' çalıştır.": "Konsole not found. Run 'codex login' in a terminal.",
            "Konsole bulunamadı. Terminalde 'agy' çalıştır.": "Konsole not found. Run 'agy' in a terminal.",
            "Claude bağlantısı zaten kurulu.": "Claude connection is already set up.",
            "Claude bağlantısı kuruldu; sonraki Claude Code oturumunda veri gelecek.": "Claude is connected; data will arrive in the next Claude Code session.",
            "Claude Code CLI bulunamadı.": "Claude Code CLI not found.",
            "Claude'da farklı bir durum satırı var; üzerine yazılmadı.": "Claude already has a different status line; it was not overwritten.",
            "Antigravity CLI bulunamadı.": "Antigravity CLI not found.",
            "Antigravity CLI kurulu değil. Resmî kurulumdan sonra tekrar dene.": "Antigravity CLI is not installed. Try again after installing it.",
            "Antigravity açılıyor.": "Opening Antigravity.",
            "Antigravity başlatıcısı bulunamadı.": "Antigravity launcher not found.",
            "Antigravity CLI açıldı. /usage ile kotayı yenile.": "Antigravity CLI opened. Refresh quota with /usage.",
            "Antigravity CLI'da farklı bir durum satırı var; üzerine yazılmadı.": "Antigravity CLI already has a different status line; it was not overwritten.",
            "Bağlantı kuruldu. CLI'yi aç ve /usage çalıştır.": "Connected. Open the CLI and run /usage.",
            "Bağlantı kurulu. CLI'yi yeniden aç ve /usage çalıştır.": "Already connected. Reopen the CLI and run /usage."
        }
        if (translations[message]) return translations[message]
        if (message.indexOf("Claude bağlantısı kurulamadı: ") === 0)
            return "Claude connection failed: " + message.slice("Claude bağlantısı kurulamadı: ".length)
        if (message.indexOf("Antigravity CLI bağlantısı kurulamadı: ") === 0)
            return "Antigravity CLI connection failed: " + message.slice("Antigravity CLI bağlantısı kurulamadı: ".length)
        const fragments = message.split(" · ")
        return fragments.map(fragment => translations[fragment] || fragment).join(" · ")
    }

    function runAction(action) {
        const quoted = helperPath.replace(/'/g, "'\\''")
        actionSource.connectSource("python3 '" + quoted + "' " + action)
    }

    Plasma5Support.DataSource {
        id: actionSource
        engine: "executable"
        connectedSources: []
        onNewData: (sourceName, data) => {
            disconnectSource(sourceName)
            try {
                const result = JSON.parse(data.stdout || "{}")
                page.resultMessage = page.localizedResult(result.message || "İşlem tamamlandı.")
            } catch (error) {
                page.resultMessage = page.localizedResult("İşlem tamamlanamadı.")
            }
        }
    }
    Component.onCompleted: runAction("status")
    FileDialog {
        id: sourceDialog
        title: page.text("Antigravity veri dosyasını seç", "Select Antigravity data file")
        fileMode: FileDialog.OpenFile
        nameFilters: [page.text("JSON dosyaları (*.json)", "JSON files (*.json)")]
        onAccepted: sourcePath.text = decodeURIComponent(selectedFile.toString().replace(/^file:\/\//, ""))
    }

    Kirigami.FormLayout {
        anchors.left: parent.left
        anchors.right: parent.right

    QQC2.Label {
        Kirigami.FormData.label: page.text("Durum:", "Status:")
        text: page.resultMessage
        wrapMode: Text.WordWrap
        Layout.fillWidth: true
    }
    QQC2.Button {
        text: page.text("Bağlantıları yeniden denetle", "Check connections again")
        icon.name: "view-refresh"
        onClicked: page.runAction("status")
    }

    Kirigami.Separator { Kirigami.FormData.isSection: true; Kirigami.FormData.label: "Codex" }
    QQC2.Label {
        text: page.text("Codex CLI hesabının limitleri yerel oturumdan okunur. Giriş gerekiyorsa terminal aç.", "Limits are read from your local Codex CLI session. Open a terminal to sign in if needed.")
        wrapMode: Text.WordWrap
        Layout.fillWidth: true
    }
    QQC2.Button {
        text: page.text("Codex girişini aç", "Sign in to Codex")
        icon.name: "utilities-terminal"
        onClicked: page.runAction("login-codex")
    }

    Kirigami.Separator { Kirigami.FormData.isSection: true; Kirigami.FormData.label: "Claude" }
    QQC2.Label {
        text: page.text("Claude Code, ilk API yanıtından sonra limitlerini durum satırıyla widget'a iletir. Yenile düğmesi yeni Claude oturumu başlatmaz.", "Claude Code sends its usage limits to the widget after its first API response. Refresh does not start a new Claude session.")
        wrapMode: Text.WordWrap
        Layout.fillWidth: true
    }
    QQC2.Button {
        text: page.text("Claude bağlantısını kur", "Set up Claude connection")
        icon.name: "insert-link"
        onClicked: page.runAction("setup-claude")
    }

    Kirigami.Separator { Kirigami.FormData.isSection: true; Kirigami.FormData.label: "Antigravity" }
    QQC2.Label {
        text: page.text("Antigravity CLI ile giriş yaptıktan sonra widget yenilemede /usage kotasını doğrudan sorgular. Eski CLI sürümleri için durum satırı bağlantısını da kurabilirsin.", "After you sign in to the Antigravity CLI, the widget queries /usage when refreshed. You can also set up status-line capture for older CLI versions.")
        wrapMode: Text.WordWrap
        Layout.fillWidth: true
    }
    QQC2.Button {
        text: page.text("Antigravity CLI bağlantısını kur", "Set up Antigravity CLI")
        icon.name: "insert-link"
        onClicked: page.runAction("setup-antigravity-cli")
    }
    QQC2.Button {
        text: page.text("Antigravity CLI'yi aç", "Open Antigravity CLI")
        icon.name: "utilities-terminal"
        onClicked: page.runAction("open-antigravity-cli")
    }
    QQC2.Button {
        text: page.text("CLI kurulum yönergesini aç", "Open CLI installation guide")
        icon.name: "internet-web-browser"
        onClicked: Qt.openUrlExternally("https://antigravity.google/docs/cli/install/")
    }
    QQC2.Label {
        text: page.text("Alternatif: Başka bir entegrasyon kota JSON dosyası oluşturuyorsa dosyayı aşağıdan seç.", "Alternatively, select a quota JSON file created by another integration.")
        wrapMode: Text.WordWrap
        Layout.fillWidth: true
    }
    QQC2.TextField {
        id: sourcePath
        Kirigami.FormData.label: page.text("Veri dosyası:", "Data file:")
        placeholderText: page.text("Boşsa ~/.config/quota-panel/antigravity.json", "Leave empty to use ~/.config/quota-panel/antigravity.json")
        Layout.fillWidth: true
    }
    QQC2.Button {
        text: page.text("Dosya seç…", "Choose file…")
        icon.name: "document-open"
        onClicked: sourceDialog.open()
    }
    QQC2.Label {
        text: page.text('Biçim: {"windows":[{"name":"Günlük","used":35,"resetsAt":1780000000}]}', 'Format: {"windows":[{"name":"Daily","used":35,"resetsAt":1780000000}]}')
        wrapMode: Text.WrapAnywhere
        font.pixelSize: 11
        opacity: 0.7
        Layout.fillWidth: true
    }
    QQC2.Button {
        text: page.text("Antigravity uygulamasını aç", "Open Antigravity")
        icon.name: "application-x-executable"
        onClicked: page.runAction("open-antigravity")
    }
    }
}
