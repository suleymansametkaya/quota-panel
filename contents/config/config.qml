import QtQuick
import org.kde.plasma.configuration
import org.kde.plasma.plasmoid

ConfigModel {
    id: root
    readonly property bool english: Plasmoid.configuration.language === "en"

    ConfigCategory {
        name: root.english ? "Appearance" : "Görünüm"
        icon: "preferences-desktop-display"
        source: "ConfigGeneral.qml"
    }
    ConfigCategory {
        name: root.english ? "Connections" : "Bağlantılar"
        icon: "network-connect"
        source: "ConfigConnections.qml"
    }
}
