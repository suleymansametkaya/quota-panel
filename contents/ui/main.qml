import QtQuick
import QtQuick.Layouts
import org.kde.kirigami as Kirigami
import org.kde.plasma.components as PC3
import org.kde.plasma.core as PlasmaCore
import org.kde.plasma.plasma5support as Plasma5Support
import org.kde.plasma.plasmoid

PlasmoidItem {
    id: root

    property var snapshot: ({"providers": []})
    property bool loading: false
    property string refreshError: ""
    property double nowMs: Date.now()
    readonly property bool english: plasmoid.configuration.language === "en"
    readonly property string appTitle: text("Yapay Zekâ Limitleri", "AI Quota Limits")
    readonly property var visibleProviders: (snapshot.providers || []).filter(provider => {
        if (provider.id === "codex" && !plasmoid.configuration.showCodex) return false
        if (provider.id === "claude" && !plasmoid.configuration.showClaude) return false
        if (provider.id === "antigravity" && !plasmoid.configuration.showAntigravity) return false
        return !plasmoid.configuration.hideUnavailable || (provider.windows || []).length > 0
    })
    readonly property var topProvider: {
        const withData = visibleProviders.find(provider => (provider.windows || []).length > 0);
        return withData || (visibleProviders.length > 0 ? visibleProviders[0] : null);
    }
    readonly property var ringData: {
        const selected = visibleProviders.find(provider => provider.id === plasmoid.configuration.ringProvider)
        return selected || visibleProviders.find(provider => (provider.windows || []).length > 0) || null
    }
    readonly property int ringRemaining: ringData && ringData.windows && ringData.windows.length > 0
                                         ? Math.max(0, 100 - ringData.windows[0].used) : -1
    readonly property string scriptPath: decodeURIComponent(Qt.resolvedUrl("../code/usage.py").toString().replace("file://", ""))

    Plasmoid.title: root.appTitle
    Plasmoid.icon: "view-statistics"
    toolTipMainText: ""
    toolTipSubText: ""
    toolTipItem: Item {
        implicitWidth: 122
        implicitHeight: tooltipContent.implicitHeight

        ColumnLayout {
            id: tooltipContent
            width: parent.width
            spacing: 3

            PC3.Label {
                Layout.fillWidth: true
                text: root.topProvider ? root.providerName(root.topProvider) : root.appTitle
                horizontalAlignment: Text.AlignHCenter
                font.bold: true
            }

            PC3.Label {
                visible: root.refreshError.length > 0
                text: root.refreshError
                color: "#ef7878"
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }

            Repeater {
                model: root.topProvider ? root.tooltipWindows(root.topProvider) : []
                delegate: RowLayout {
                    required property var modelData
                    Layout.fillWidth: true
                    spacing: 4

                    PC3.Label {
                        text: modelData.label
                        Layout.fillWidth: true
                    }
                    PC3.Label {
                        text: "%" + modelData.remaining
                        horizontalAlignment: Text.AlignRight
                        Layout.preferredWidth: 32
                    }
                }
            }

            PC3.Label {
                visible: !root.topProvider || root.tooltipWindows(root.topProvider).length === 0
                text: root.text("Limit verisi bekleniyor", "Waiting for quota data")
            }
        }
    }

    function text(turkish, englishText) {
        return english ? englishText : turkish;
    }

    function providerName(provider) {
        if (english && provider.id === "claude") return "Claude Code";
        return provider.name;
    }

    function percentLabel(remaining) {
        return english ? remaining + "% remaining" : "%" + remaining + " Kaldı";
    }

    function windowLabel(name) {
        const translations = {
            "Codex · 5 saat": "Codex · 5 hours",
            "Codex · Haftalık": "Codex · Weekly",
            "5 Saatlik": "5-hour",
            "Haftalık": "Weekly",
            "Gemini · 5 Saat": "Gemini · 5 hours",
            "Gemini · Haftalık": "Gemini · Weekly",
            "Claude ve OpenAI Modelleri · 5 Saat": "Claude & OpenAI Models · 5 hours",
            "Claude ve OpenAI Modelleri · Haftalık": "Claude & OpenAI Models · Weekly",
            "Diğer Modeller · 5 Saat": "Claude & OpenAI Models · 5 hours",
            "Diğer Modeller · Haftalık": "Claude & OpenAI Models · Weekly"
        };
        if (english) return translations[name] || name;
        if (name === "Diğer Modeller · 5 Saat") return "Claude ve OpenAI Modelleri · 5 Saat";
        if (name === "Diğer Modeller · Haftalık") return "Claude ve OpenAI Modelleri · Haftalık";
        return name;
    }

    function messageText(message) {
        if (!english) return message;
        const translations = {
            "Veri alınamadı": "Usage data unavailable",
            "Son alınan veri": "Last known data",
            "Claude Code oturumunda ilk yanıttan sonra limit verisi görünür": "Quota appears after Claude Code's first response",
            "Son Claude oturumundan": "From the last Claude session",
            "CLI oturumundan henüz kota verisi gelmedi": "No quota data received from the CLI session yet",
            "Son Antigravity oturumundan": "From the last Antigravity session",
            "Kullanım verisi yok": "No usage data",
            "Süre bilinmiyor": "Duration unknown"
        };
        return translations[message] || message;
    }

    function tooltipWindows(provider) {
        const windows = provider.windows || [];
        const fiveHour = windows.find(window => /5 saat|5s|5 hour/i.test(window.name));
        const weekly = windows.find(window => /haftalık|7 gün|weekly/i.test(window.name));
        const percent = window => Math.max(0, Math.min(100, 100 - window.used));
        const lines = [];
        if (fiveHour) lines.push({label: text("5 Saatlik", "5-hour"), remaining: percent(fiveHour)});
        if (weekly && weekly !== fiveHour) lines.push({label: text("Haftalık", "Weekly"), remaining: percent(weekly)});
        if (lines.length === 0) {
            windows.slice(0, 2).forEach(window => lines.push({label: windowLabel(window.name), remaining: percent(window)}));
        }
        return lines;
    }

    function resetTimestamp(value) {
        if (value === null || value === undefined || value === "") return 0;
        let timestamp = Number(value);
        if (!isFinite(timestamp)) timestamp = Date.parse(String(value));
        else if (timestamp < 1000000000000) timestamp *= 1000;
        return isFinite(timestamp) && timestamp > 0 ? timestamp : 0;
    }

    function resetDateLabel(timestamp) {
        if (!timestamp) return "";
        const date = new Date(timestamp);
        if (isNaN(date.getTime())) return "";
        const months = english
            ? ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
            : ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"];
        const pad = number => ("0" + number).slice(-2);
        return date.getDate() + " " + months[date.getMonth()] + " "
               + pad(date.getHours()) + ":" + pad(date.getMinutes());
    }

    function remainingTimeLabel(timestamp) {
        if (!timestamp) return "";
        const totalMinutes = Math.ceil((timestamp - nowMs) / 60000);
        if (totalMinutes <= 0) return text("Yenilendi", "Reset");
        const days = Math.floor(totalMinutes / 1440);
        const hours = Math.floor((totalMinutes % 1440) / 60);
        const minutes = totalMinutes % 60;
        const parts = [];
        if (days > 0) parts.push(days + text(" Gün", days === 1 ? " day" : " days"));
        if (hours > 0) parts.push(hours + text(" Saat", hours === 1 ? " hour" : " hours"));
        if (minutes > 0 || parts.length === 0) parts.push(minutes + text(" Dakika", minutes === 1 ? " minute" : " minutes"));
        return parts.join(" ") + text(" Kaldı", " left");
    }

    function usageColor(used) {
        const remaining = 100 - used;
        const threshold = Math.max(1, Math.min(90, plasmoid.configuration.warningThreshold));
        if (remaining <= threshold) return "#ef7878";
        if (remaining <= threshold + 20) return "#f0b86d";
        return "#74d5bb";
    }

    function markRefreshFailure() {
        refreshError = text("Yenileme başarısız; önceki veriler gösteriliyor.", "Refresh failed; showing previous data.");
        const providers = (snapshot.providers || []).map(provider => {
            if (provider.state !== "ok") return provider;
            return Object.assign({}, provider, {state: "stale"});
        });
        snapshot = Object.assign({}, snapshot, {providers: providers});
    }

    function refresh(force = false) {
        if (loading) return;
        loading = true;
        refreshError = "";
        const source = String(plasmoid.configuration.antigravitySource || "");
        const providers = [];
        if (plasmoid.configuration.showCodex) providers.push("codex");
        if (plasmoid.configuration.showClaude) providers.push("claude");
        if (plasmoid.configuration.showAntigravity) providers.push("antigravity");
        const command = "python3 '" + scriptPath.replace(/'/g, "'\\''")
                        + "' --antigravity-source '" + source.replace(/'/g, "'\\''") + "'"
                        + " --providers '" + providers.join(",") + "'"
                        + (force ? " --force-refresh" : "");
        usageSource.connectSource(command);
    }

    Plasma5Support.DataSource {
        id: usageSource
        engine: "executable"
        connectedSources: []
        onNewData: (sourceName, data) => {
            disconnectSource(sourceName);
            root.loading = false;
            if (data["exit code"] !== 0 || !data.stdout) {
                root.markRefreshFailure();
                return;
            }
            try {
                const result = JSON.parse(data.stdout);
                if (!result || !Array.isArray(result.providers)) throw new Error("Eksik sağlayıcı listesi");
                root.snapshot = result;
                root.refreshError = "";
            } catch (error) {
                console.warn("Quota Panel: veri ayrıştırılamadı", error);
                root.markRefreshFailure();
            }
        }
    }

    Timer {
        interval: Math.max(1, Math.min(60, plasmoid.configuration.refreshMinutes)) * 60000
        repeat: true
        running: true
        triggeredOnStart: true
        onTriggered: root.refresh(false)
    }

    Timer {
        interval: 60000
        repeat: true
        running: true
        onTriggered: root.nowMs = Date.now()
    }

    compactRepresentation: Item {
        implicitWidth: 36
        Layout.minimumWidth: 36
        Layout.preferredWidth: 36
        Layout.maximumWidth: 36
        implicitHeight: Kirigami.Units.gridUnit * 2

        Canvas {
            id: ring
            anchors.centerIn: parent
            width: 20
            height: 20
            onPaint: {
                const context = getContext("2d");
                context.clearRect(0, 0, width, height);
                const fraction = root.ringRemaining < 0 ? 0 : root.ringRemaining / 100;
                context.beginPath();
                context.arc(10, 10, 8, 0, Math.PI * 2);
                context.strokeStyle = "#777777";
                context.lineWidth = 2.5;
                context.stroke();
                context.beginPath();
                context.arc(10, 10, 8, -Math.PI / 2, -Math.PI / 2 + fraction * Math.PI * 2);
                context.strokeStyle = root.ringRemaining < 0 ? "#999999" : root.usageColor(100 - root.ringRemaining);
                context.lineWidth = 2.5;
                context.stroke();
            }
            Connections {
                target: root
                function onRingRemainingChanged() { ring.requestPaint(); }
                function onVisibleProvidersChanged() { ring.requestPaint(); }
            }
        }

        MouseArea {
            anchors.fill: parent
            onClicked: root.expanded = !root.expanded
        }
    }

    fullRepresentation: Item {
        id: popup
        implicitWidth: 345
        readonly property real maximumPopupHeight: 520
        readonly property real desiredHeight: Math.min(maximumPopupHeight, content.implicitHeight + 28)
        implicitHeight: desiredHeight
        Layout.preferredWidth: implicitWidth
        Layout.preferredHeight: desiredHeight
        Layout.minimumHeight: desiredHeight
        Layout.maximumHeight: desiredHeight

        Flickable {
            id: viewport
            anchors.fill: parent
            clip: true
            contentWidth: width
            contentHeight: content.implicitHeight + 28
            flickableDirection: Flickable.VerticalFlick
            boundsBehavior: Flickable.StopAtBounds

            ColumnLayout {
                id: content
                x: 14
                y: 14
                width: viewport.width - 28
                height: implicitHeight
                spacing: 12

            RowLayout {
                Layout.fillWidth: true
                PC3.Label {
                    text: root.appTitle
                    font.bold: true
                    font.pixelSize: 17
                    Layout.fillWidth: true
                }
                PC3.ToolButton {
                    icon.name: "view-refresh"
                    enabled: !root.loading
                    onClicked: root.refresh(true)
                }
                PC3.ToolButton {
                    icon.name: "configure"
                    onClicked: Plasmoid.internalAction("configure").trigger()
                }
            }

            PC3.Label {
                visible: root.refreshError.length > 0
                text: root.refreshError
                color: "#ef7878"
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }

            Repeater {
                model: root.visibleProviders
                delegate: ColumnLayout {
                    required property int index
                    required property var modelData
                    Layout.fillWidth: true
                    spacing: 5

                    RowLayout {
                        Layout.fillWidth: true
                        PC3.Label {
                            text: root.providerName(modelData)
                            font.bold: true
                            Layout.fillWidth: true
                        }
                        PC3.Label {
                            text: modelData.state === "ok" ? root.text("Canlı", "Live") :
                                  modelData.state === "stale" ? root.text("Eski veri", "Stale data") : root.text("Veri yok", "No data")
                            opacity: 0.65
                            font.pixelSize: 11
                        }
                    }

                    Repeater {
                        model: modelData.windows || []
                        delegate: ColumnLayout {
                            required property var modelData
                            Layout.fillWidth: true
                            spacing: 2
                            RowLayout {
                                Layout.fillWidth: true
                                PC3.Label {
                                    text: root.windowLabel(modelData.name)
                                    Layout.fillWidth: true
                                    elide: Text.ElideRight
                                }
                                PC3.Label {
                                    text: root.percentLabel(Math.max(0, 100 - modelData.used))
                                    color: root.usageColor(modelData.used)
                                }
                            }
                            Rectangle {
                                Layout.fillWidth: true
                                height: 5
                                radius: 3
                                color: Qt.rgba(0.5, 0.5, 0.5, 0.25)
                                Rectangle {
                                    width: parent.width * Math.max(0, Math.min(1, (100 - modelData.used) / 100))
                                    height: parent.height
                                    radius: parent.radius
                                    color: root.usageColor(modelData.used)
                                }
                            }
                            RowLayout {
                                id: resetRow
                                readonly property double resetTime: root.resetTimestamp(modelData.resetsAt)
                                visible: plasmoid.configuration.showResetTime && resetTime > 0
                                Layout.fillWidth: true
                                spacing: 4
                                PC3.Label {
                                    text: root.text("Yenilenme: ", "Resets: ") + root.resetDateLabel(resetRow.resetTime)
                                    Layout.fillWidth: true
                                    elide: Text.ElideRight
                                    opacity: 0.58
                                    font.pixelSize: 11
                                }
                                PC3.Label {
                                    text: root.remainingTimeLabel(resetRow.resetTime)
                                    opacity: 0.7
                                    font.pixelSize: 11
                                }
                            }
                        }
                    }

                    PC3.Label {
                        visible: !modelData.windows || modelData.windows.length === 0
                        text: root.messageText(modelData.message || "Kullanım verisi yok")
                        opacity: 0.65
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                    }

                    PC3.Label {
                        visible: plasmoid.configuration.showCredits && modelData.id === "codex" && modelData.resetCredits > 0
                        text: modelData.resetCredits + root.text(" yenileme hakkı var", " reset credits available")
                        opacity: 0.7
                        font.pixelSize: 11
                    }

                    Rectangle {
                        visible: index < root.visibleProviders.length - 1
                        Layout.fillWidth: true
                        height: 1
                        color: Qt.rgba(0.5, 0.5, 0.5, 0.22)
                    }
                }
            }

                PC3.Label {
                    visible: root.visibleProviders.length === 0
                    text: root.loading ? root.text("Limitler okunuyor…", "Loading quotas…") : root.text("Gösterilecek veri yok. Ayarlardan servisleri seç.", "No data to show. Choose services in Settings.")
                    Layout.fillWidth: true
                }
            }
        }
    }
}
