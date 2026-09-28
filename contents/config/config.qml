import QtQuick
import org.kde.plasma.configuration

ConfigModel {
    ConfigCategory {
        name: "Görünüm"
        icon: "preferences-desktop-display"
        source: "ConfigGeneral.qml"
    }
    ConfigCategory {
        name: "Bağlantılar"
        icon: "network-connect"
        source: "ConfigConnections.qml"
    }
}
