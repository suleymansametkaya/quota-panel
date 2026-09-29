import QtQuick
import QtQuick.Controls as QQC2
import QtQuick.Layouts
import org.kde.kirigami as Kirigami
import org.kde.kcmutils as KCM

KCM.SimpleKCM {
    id: page

    property alias cfg_showCodex: codex.checked
    property alias cfg_showClaude: claude.checked
    property alias cfg_showAntigravity: antigravity.checked
    property alias cfg_hideUnavailable: hideUnavailable.checked
    property alias cfg_showResetTime: showReset.checked
    property alias cfg_showCredits: showCredits.checked
    property alias cfg_refreshMinutes: refresh.value
    property alias cfg_warningThreshold: warning.value
    property string cfg_ringProvider: "codex"
    property string cfg_language: "tr"

    // Plasma passes every config key (and its generated Default value) to
    // every config page. Accept the connection setting here so opening this
    // page does not warn about an unused initial property.
    property string cfg_antigravitySource: ""

    // KConfig-generated defaults are only used by other configuration pages.
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

    readonly property bool english: cfg_language === "en"
    function text(turkish, englishText) { return english ? englishText : turkish }

    Kirigami.FormLayout {
        anchors.left: parent.left
        anchors.right: parent.right

    QQC2.CheckBox {
        id: codex
        Kirigami.FormData.label: page.text("Gösterilecek servisler:", "Services to show:")
        text: "Codex"
    }
    QQC2.CheckBox { id: claude; text: "Claude" }
    QQC2.CheckBox { id: antigravity; text: "Antigravity" }

    QQC2.ComboBox {
        id: language
        Kirigami.FormData.label: page.text("Dil:", "Language:")
        model: ["Türkçe", "English"]
        currentIndex: page.cfg_language === "en" ? 1 : 0
        onActivated: index => page.cfg_language = index === 1 ? "en" : "tr"
    }

    QQC2.ComboBox {
        id: ringChoice
        Kirigami.FormData.label: page.text("Panel halkası:", "Panel ring:")
        model: ["Codex", "Claude", "Antigravity"]
        currentIndex: Math.max(0, ["codex", "claude", "antigravity"].indexOf(page.cfg_ringProvider))
        onActivated: index => page.cfg_ringProvider = ["codex", "claude", "antigravity"][index]
    }

    QQC2.CheckBox {
        id: hideUnavailable
        Kirigami.FormData.label: page.text("Açılır pencere:", "Popup:")
        text: page.text("Verisi olmayan servisleri gizle", "Hide services without data")
    }
    QQC2.CheckBox { id: showReset; text: page.text("Yenilenme zamanını göster", "Show reset time") }
    QQC2.CheckBox { id: showCredits; text: page.text("Yenileme haklarını göster", "Show reset credits") }

    QQC2.SpinBox {
        id: refresh
        Kirigami.FormData.label: page.text("Yenileme aralığı (dk):", "Refresh interval (min):")
        from: 1
        to: 60
    }
    QQC2.SpinBox {
        id: warning
        Kirigami.FormData.label: page.text("Uyarı eşiği (% kalan):", "Warning threshold (% remaining):")
        from: 1
        to: 90
    }
    QQC2.Label {
        text: page.text("Kalan kullanım eşik değerin altına düştüğünde halka kırmızı görünür.", "The ring turns red when remaining quota falls below this threshold.")
        wrapMode: Text.WordWrap
        opacity: 0.7
        Layout.fillWidth: true
    }
    }
}
