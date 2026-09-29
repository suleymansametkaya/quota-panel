import QtQuick
import QtQuick.Controls as QQC2
import QtQuick.Dialogs
import QtQuick.Layouts
import org.kde.kirigami as Kirigami
import org.kde.kcmutils as KCM
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
    property var cfg_antigravitySourceDefault
    property string resultMessage: "Bağlantılar denetleniyor…"
    readonly property string helperPath: decodeURIComponent(Qt.resolvedUrl("../code/connection.py").toString().replace("file://", ""))

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
                page.resultMessage = result.message || "İşlem tamamlandı."
            } catch (error) {
                page.resultMessage = "İşlem tamamlanamadı."
            }
        }
    }
    Component.onCompleted: runAction("status")
    FileDialog {
        id: sourceDialog
        title: "Antigravity veri dosyasını seç"
        fileMode: FileDialog.OpenFile
        nameFilters: ["JSON dosyaları (*.json)"]
        onAccepted: sourcePath.text = decodeURIComponent(selectedFile.toString().replace(/^file:\/\//, ""))
    }

    Kirigami.FormLayout {
        anchors.left: parent.left
        anchors.right: parent.right

    QQC2.Label {
        Kirigami.FormData.label: "Durum:"
        text: page.resultMessage
        wrapMode: Text.WordWrap
        Layout.fillWidth: true
    }
    QQC2.Button {
        text: "Bağlantıları yeniden denetle"
        icon.name: "view-refresh"
        onClicked: page.runAction("status")
    }

    Kirigami.Separator { Kirigami.FormData.isSection: true; Kirigami.FormData.label: "Codex" }
    QQC2.Label {
        text: "Codex CLI hesabının limitleri yerel oturumdan okunur. Giriş gerekiyorsa terminal aç."
        wrapMode: Text.WordWrap
        Layout.fillWidth: true
    }
    QQC2.Button {
        text: "Codex girişini aç"
        icon.name: "utilities-terminal"
        onClicked: page.runAction("login-codex")
    }

    Kirigami.Separator { Kirigami.FormData.isSection: true; Kirigami.FormData.label: "Claude" }
    QQC2.Label {
        text: "Claude Code, ilk API yanıtından sonra limitlerini durum satırıyla widget'a iletir. Yenile düğmesi yeni Claude oturumu başlatmaz."
        wrapMode: Text.WordWrap
        Layout.fillWidth: true
    }
    QQC2.Button {
        text: "Claude bağlantısını kur"
        icon.name: "insert-link"
        onClicked: page.runAction("setup-claude")
    }

    Kirigami.Separator { Kirigami.FormData.isSection: true; Kirigami.FormData.label: "Antigravity" }
    QQC2.Label {
        text: "Antigravity CLI ile giriş yaptıktan sonra widget yenilemede /usage kotasını doğrudan sorgular. Eski CLI sürümleri için durum satırı bağlantısını da kurabilirsin."
        wrapMode: Text.WordWrap
        Layout.fillWidth: true
    }
    QQC2.Button {
        text: "Antigravity CLI bağlantısını kur"
        icon.name: "insert-link"
        onClicked: page.runAction("setup-antigravity-cli")
    }
    QQC2.Button {
        text: "Antigravity CLI'yi aç"
        icon.name: "utilities-terminal"
        onClicked: page.runAction("open-antigravity-cli")
    }
    QQC2.Button {
        text: "CLI kurulum yönergesini aç"
        icon.name: "internet-web-browser"
        onClicked: Qt.openUrlExternally("https://antigravity.google/docs/cli/install/")
    }
    QQC2.Label {
        text: "Alternatif: Başka bir entegrasyon kota JSON dosyası oluşturuyorsa dosyayı aşağıdan seç."
        wrapMode: Text.WordWrap
        Layout.fillWidth: true
    }
    QQC2.TextField {
        id: sourcePath
        Kirigami.FormData.label: "Veri dosyası:"
        placeholderText: "Boşsa ~/.config/quota-panel/antigravity.json"
        Layout.fillWidth: true
    }
    QQC2.Button {
        text: "Dosya seç…"
        icon.name: "document-open"
        onClicked: sourceDialog.open()
    }
    QQC2.Label {
        text: 'Biçim: {"windows":[{"name":"Günlük","used":35,"resetsAt":1780000000}]}'
        wrapMode: Text.WrapAnywhere
        font.pixelSize: 11
        opacity: 0.7
        Layout.fillWidth: true
    }
    QQC2.Button {
        text: "Antigravity uygulamasını aç"
        icon.name: "application-x-executable"
        onClicked: page.runAction("open-antigravity")
    }
    }
}
