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
    property var cfg_antigravitySourceDefault

    Kirigami.FormLayout {
        anchors.left: parent.left
        anchors.right: parent.right

    QQC2.CheckBox {
        id: codex
        Kirigami.FormData.label: "Gösterilecek servisler:"
        text: "Codex"
    }
    QQC2.CheckBox { id: claude; text: "Claude" }
    QQC2.CheckBox { id: antigravity; text: "Antigravity" }

    QQC2.ComboBox {
        id: ringChoice
        Kirigami.FormData.label: "Panel halkası:"
        model: ["Codex", "Claude", "Antigravity"]
        currentIndex: Math.max(0, ["codex", "claude", "antigravity"].indexOf(page.cfg_ringProvider))
        onActivated: index => page.cfg_ringProvider = ["codex", "claude", "antigravity"][index]
    }

    QQC2.CheckBox {
        id: hideUnavailable
        Kirigami.FormData.label: "Açılır pencere:"
        text: "Verisi olmayan servisleri gizle"
    }
    QQC2.CheckBox { id: showReset; text: "Yenilenme zamanını göster" }
    QQC2.CheckBox { id: showCredits; text: "Yenileme haklarını göster" }

    QQC2.SpinBox {
        id: refresh
        Kirigami.FormData.label: "Yenileme aralığı (dk):"
        from: 1
        to: 60
    }
    QQC2.SpinBox {
        id: warning
        Kirigami.FormData.label: "Uyarı eşiği (% kalan):"
        from: 1
        to: 90
    }
    QQC2.Label {
        text: "Kalan kullanım eşik değerin altına düştüğünde halka kırmızı görünür."
        wrapMode: Text.WordWrap
        opacity: 0.7
        Layout.fillWidth: true
    }
    }
}
