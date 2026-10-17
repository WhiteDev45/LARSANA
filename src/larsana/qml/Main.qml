import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs

ApplicationWindow {
    id: win
    width: 760; height: 534
    minimumWidth: 720; minimumHeight: 520
    visible: true
    title: "LARSANA"
    property var snapshotData: JSON.parse(backend.state)
    property bool dark: snapshotData.settings.dark
    property color bg: dark ? "#1c1e21" : "#faf8f4"
    property color surface: dark ? "#24272b" : "#ffffff"
    property color ink: dark ? "#f4efe6" : "#282820"
    property color muted: dark ? "#ada99f" : "#89877d"
    property color line: dark ? "#373a3e" : "#e8e4da"
    property color accent: "#d7683f"
    property string notice: "Ready when you are."
    property bool closing: false
    color: bg
    font.family: "Inter"
    font.pixelSize: 13
    onClosing: function(close) {
        if (!closing) { close.accepted = false; notice = "Stopping services safely…"; backend.shutdown() }
    }
    Connections {
        target: backend
        function onCompleted(message) { notice = message }
        function onDetail(message) { extensionsText.text = message; extensionsDialog.open() }
        function onError(message) { errorText.text = message; errorDialog.open(); notice = "An action needs your attention." }
        function onShutdownReady() { closing = true; win.close() }
    }
    function choices(kind) { return snapshotData.installed[kind].map(function(r) { return r.series }) }
    function runtimeVersion(kind, fallback) {
        var list = snapshotData.installed[kind]
        return list.length ? list[list.length - 1].version : fallback
    }
    function anyRunning() { return snapshotData.status.web === "Running" || snapshotData.status.php === "Running" || snapshotData.status.mariadb === "Running" }

    component SoftButton: Button {
        id: control
        property bool primary: false
        implicitHeight: 39
        leftPadding: 16; rightPadding: 16
        hoverEnabled: true
        background: Rectangle {
            radius: 9
            color: control.primary ? (control.hovered ? "#bf5630" : accent) : (control.hovered ? (dark ? "#393b40" : "#f1eee7") : surface)
            border.color: control.primary ? "transparent" : line
            opacity: control.enabled ? 1 : .5
        }
        contentItem: Text { text: control.text; font: control.font; color: control.primary ? "#fffaf3" : ink; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter; opacity: control.enabled ? 1 : .45 }
    }
    component VersionPicker: ComboBox {
        id: picker
        implicitWidth: 112; implicitHeight: 32
        font.pixelSize: 12
        background: Rectangle { color: dark ? "#2d3035" : "#f6f4ee"; radius: 7; border.color: line }
        contentItem: Text { leftPadding: 9; rightPadding: 24; text: picker.displayText; color: ink; font: picker.font; verticalAlignment: Text.AlignVCenter }
        delegate: ItemDelegate { required property string modelData; required property int index; width: picker.width; text: modelData; highlighted: picker.highlightedIndex === index }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 28
        spacing: 0
        RowLayout {
            spacing: 13
            Image { source: "larsana.svg"; Layout.preferredWidth: 44; Layout.preferredHeight: 44; sourceSize.width: 88; sourceSize.height: 88 }
            ColumnLayout {
                spacing: 2
                Text { text: "LARSANA"; font.pixelSize: 22; font.weight: Font.DemiBold; font.letterSpacing: 2.2; color: ink }
                Text { text: "Your local development companion."; font.pixelSize: 12; color: muted }
            }
            Item { Layout.fillWidth: true }
            SoftButton { text: "Preferences"; implicitHeight: 33; font.pixelSize: 12; enabled: !backend.busy; onClicked: { rootField.text = snapshotData.root; webPort.value = snapshotData.settings.port; dbPort.value = snapshotData.settings.db_port; darkToggle.checked = dark; preferences.open() } }
            SoftButton { text: "Menu  ☰"; implicitHeight: 33; font.pixelSize: 12; onClicked: mainMenu.popup() }
        }
        RowLayout {
            Layout.topMargin: 29; Layout.bottomMargin: 12
            Text { text: "LOCAL ENVIRONMENT"; color: muted; font.pixelSize: 10; font.weight: Font.DemiBold; font.letterSpacing: 1.7 }
            Item { Layout.fillWidth: true }
            Rectangle { width: 6; height: 6; radius: 3; color: anyRunning() ? "#65a483" : muted }
            Text { text: backend.busy ? "Working…" : anyRunning() ? "Services active" : "All services stopped"; color: muted; font.pixelSize: 11 }
        }
        Rectangle {
            Layout.fillWidth: true; Layout.preferredHeight: 191
            color: surface; radius: 12; border.color: line
            Column {
                anchors.fill: parent
                Repeater {
                    model: [
                        {key: "web", label: snapshotData.settings.web === "apache" ? "Apache" : "Nginx", subtitle: "Web server", badge: "W", kind: snapshotData.settings.web, version: runtimeVersion(snapshotData.settings.web, "Not installed")},
                        {key: "php", label: "PHP", subtitle: "Language runtime", badge: "P", kind: "php", version: snapshotData.settings.php},
                        {key: "mariadb", label: "MariaDB", subtitle: "Database server", badge: "D", kind: "mariadb", version: snapshotData.settings.mariadb}
                    ]
                    delegate: Item {
                        required property var modelData
                        required property int index
                        width: parent.width; height: 63
                        RowLayout {
                            anchors.fill: parent; anchors.leftMargin: 17; anchors.rightMargin: 17; spacing: 13
                            Rectangle {
                                width: 33; height: 33; radius: 9; color: dark ? "#34312d" : "#f5f0e8"
                                Text { anchors.centerIn: parent; text: modelData.badge; color: modelData.key === "php" ? "#8983af" : accent; font.weight: Font.DemiBold; font.pixelSize: 13 }
                            }
                            ColumnLayout {
                                spacing: 2; Layout.preferredWidth: 123
                                Text { text: modelData.label; color: ink; font.pixelSize: 14; font.weight: Font.Medium }
                                Text { text: modelData.subtitle; color: muted; font.pixelSize: 10 }
                            }
                            VersionPicker {
                                model: modelData.key === "web" ? ["apache", "nginx"] : choices(modelData.kind)
                                currentIndex: model.indexOf(modelData.key === "web" ? snapshotData.settings.web : snapshotData.settings[modelData.key])
                                displayText: modelData.key === "web" ? modelData.version : (model.length ? (currentIndex >= 0 ? currentText : snapshotData.settings[modelData.key] + " · missing") : "Not installed")
                                enabled: !backend.busy
                                onActivated: backend.select(modelData.key, currentText)
                            }
                            Item { Layout.fillWidth: true }
                            Rectangle { width: 6; height: 6; radius: 3; color: snapshotData.status[modelData.key] === "Running" ? "#65a483" : snapshotData.status[modelData.key] === "Failed" ? "#d86450" : muted }
                            Text { Layout.preferredWidth: 58; text: snapshotData.status[modelData.key]; color: muted; font.pixelSize: 11 }
                            Text { Layout.preferredWidth: 57; horizontalAlignment: Text.AlignRight; text: modelData.key === "php" ? "FPM" : ":" + (modelData.key === "web" ? snapshotData.settings.port : snapshotData.settings.db_port); color: muted; font.pixelSize: 11 }
                            ToolButton { text: "⋯"; font.pixelSize: 21; enabled: !backend.busy; onClicked: { serviceMenu.kind = modelData.key; serviceMenu.popup() } }
                        }
                        Rectangle { anchors.bottom: parent.bottom; x: 17; width: parent.width - 34; height: 1; color: line; visible: index < 2 }
                    }
                }
            }
        }
        RowLayout {
            Layout.topMargin: 17; spacing: 8
            Text { text: "⌁"; color: accent; font.pixelSize: 18 }
            Text { text: snapshotData.root; color: muted; font.pixelSize: 11; elide: Text.ElideMiddle; Layout.fillWidth: true }
            Text { text: snapshotData.projects.length + " projects"; color: muted; font.pixelSize: 11 }
            ToolButton { text: "+ New"; font.pixelSize: 11; enabled: !backend.busy; onClicked: projectDialog.open() }
        }
        Item { Layout.fillHeight: true; Layout.minimumHeight: 12 }
        RowLayout {
            Layout.fillWidth: true; spacing: 8
            SoftButton { text: anyRunning() ? "■   Stop All" : "▷   Start All"; primary: true; Layout.preferredWidth: 146; enabled: !backend.busy; onClicked: anyRunning() ? backend.stopAll() : backend.startAll() }
            SoftButton { text: "◎  Web"; Layout.fillWidth: true; onClicked: backend.open("web") }
            SoftButton { text: "▤  phpMyAdmin"; Layout.fillWidth: true; onClicked: backend.open("database") }
            SoftButton { text: "›_  Terminal"; Layout.fillWidth: true; onClicked: backend.open("terminal") }
            SoftButton { text: "⌑  Root"; Layout.fillWidth: true; onClicked: backend.open("root") }
        }
        Rectangle { Layout.topMargin: 23; Layout.fillWidth: true; height: 1; color: line }
        RowLayout {
            Layout.topMargin: 12
            Text { text: notice; color: muted; font.pixelSize: 10; Layout.fillWidth: true; elide: Text.ElideRight }
            BusyIndicator { running: backend.busy; visible: running; Layout.preferredWidth: 16; Layout.preferredHeight: 16 }
            Text { text: "LINUX EDITION  /  1.2.2"; color: muted; font.pixelSize: 9; font.letterSpacing: 1 }
        }
    }
    Menu {
        id: serviceMenu
        property string kind: "web"
        MenuItem { text: "Start"; onTriggered: backend.service(serviceMenu.kind, "start") }
        MenuItem { text: "Stop"; onTriggered: backend.service(serviceMenu.kind, "stop") }
        MenuItem { text: "Restart"; onTriggered: backend.service(serviceMenu.kind, "restart") }
        MenuSeparator {}
        MenuItem { text: "View logs"; onTriggered: backend.open("log:" + serviceMenu.kind) }
        MenuItem { text: "Configuration"; onTriggered: backend.open("config:" + serviceMenu.kind) }
    }
    Menu {
        id: mainMenu
        MenuItem { text: "Start All"; enabled: !backend.busy; onTriggered: backend.startAll() }
        MenuItem { text: "Stop All"; enabled: !backend.busy; onTriggered: backend.stopAll() }
        MenuSeparator {}
        Menu {
            title: snapshotData.settings.web === "apache" ? "Apache" : "Nginx"
            Menu { title: "Server"
                MenuItem { text: "Apache"; checkable: true; checked: snapshotData.settings.web === "apache"; enabled: !backend.busy; onTriggered: backend.select("web", "apache") }
                MenuItem { text: "Nginx · stable"; checkable: true; checked: snapshotData.settings.web === "nginx"; enabled: !backend.busy; onTriggered: backend.select("web", "nginx") }
            }
            MenuItem { text: "Start"; enabled: !backend.busy; onTriggered: backend.service("web", "start") }
            MenuItem { text: "Stop"; enabled: !backend.busy; onTriggered: backend.service("web", "stop") }
            MenuItem { text: "Restart"; enabled: !backend.busy; onTriggered: backend.service("web", "restart") }
            MenuSeparator {}
            MenuItem { text: "Configuration"; onTriggered: backend.open("config:web") }
            MenuItem { text: "Logs"; onTriggered: backend.open("log:web") }
        }
        Menu {
            title: "PHP"
            Menu { title: "Version"
                Repeater { model: snapshotData.installed.php
                    delegate: MenuItem {
                        required property var modelData
                        text: modelData.version + (modelData.channel === "legacy" ? " · legacy" : "")
                        checkable: true; checked: snapshotData.settings.php === modelData.series; enabled: !backend.busy
                        onTriggered: backend.select("php", modelData.series)
                    }
                }
            }
            MenuItem { text: "Restart"; enabled: !backend.busy; onTriggered: backend.service("php", "restart") }
            MenuItem { text: "Extensions"; enabled: !backend.busy; onTriggered: backend.extensions() }
            MenuItem { text: "php.ini"; onTriggered: backend.open("config:php") }
            MenuItem { text: "Logs"; onTriggered: backend.open("log:php") }
        }
        Menu {
            title: "MariaDB"
            Menu { title: "Version"
                Repeater { model: snapshotData.installed.mariadb
                    delegate: MenuItem {
                        required property var modelData
                        text: modelData.version + (modelData.channel === "lts" ? " · LTS" : " · stable")
                        checkable: true; checked: snapshotData.settings.mariadb === modelData.series; enabled: !backend.busy
                        onTriggered: backend.select("mariadb", modelData.series)
                    }
                }
            }
            MenuItem { text: "Start"; enabled: !backend.busy; onTriggered: backend.service("mariadb", "start") }
            MenuItem { text: "Stop"; enabled: !backend.busy; onTriggered: backend.service("mariadb", "stop") }
            MenuItem { text: "Restart"; enabled: !backend.busy; onTriggered: backend.service("mariadb", "restart") }
            MenuItem { text: "Configuration"; onTriggered: backend.open("config:mariadb") }
            MenuItem { text: "Logs"; onTriggered: backend.open("log:mariadb") }
        }
        MenuSeparator {}
        Menu { title: "Projects"; Repeater { model: snapshotData.projects; delegate: MenuItem { required property string modelData; text: modelData; onTriggered: backend.open("project:" + modelData) } } }
        MenuItem { text: "New PHP project…"; onTriggered: projectDialog.open() }
        MenuItem { text: "Enable project .test domain…"; onTriggered: domainDialog.open() }
        MenuItem { text: "Runtime packages…"; onTriggered: runtimeDialog.open() }
        MenuSeparator {}
        MenuItem { text: "About LARSANA"; onTriggered: aboutDialog.open() }
        MenuSeparator {}
        MenuItem { text: "Exit"; onTriggered: backend.shutdown() }
    }
    Dialog {
        id: projectDialog; anchors.centerIn: parent; width: 400; title: "New PHP project"; modal: true
        standardButtons: Dialog.Ok | Dialog.Cancel
        ColumnLayout {
            width: parent.width; spacing: 12
            Label { text: "Lowercase letters, numbers and hyphens."; wrapMode: Text.WordWrap; Layout.fillWidth: true }
            TextField { id: projectName; Layout.fillWidth: true; placeholderText: "my-project" }
            Label { text: projectName.text + ".localhost:" + snapshotData.settings.port; opacity: .6 }
        }
        onAccepted: { backend.createProject(projectName.text); projectName.clear() }
    }
    Dialog {
        id: domainDialog; anchors.centerIn: parent; width: 430; title: "Enable .test domain"; modal: true
        standardButtons: Dialog.Ok | Dialog.Cancel
        ColumnLayout {
            width: parent.width; spacing: 12
            Label { text: "Select a project. The system will ask for administrator authentication to add its local .test domain."; wrapMode: Text.WordWrap; Layout.fillWidth: true }
            ComboBox { id: domainProject; model: snapshotData.projects; Layout.fillWidth: true }
        }
        onAccepted: backend.enableDomain(domainProject.currentText)
    }
    Dialog {
        id: preferences; anchors.centerIn: parent; width: 450; title: "Preferences"; modal: true
        standardButtons: Dialog.Save | Dialog.Cancel
        ColumnLayout {
            width: parent.width; spacing: 12
            Label { text: "Stop All before changing the workspace or ports."; wrapMode: Text.WordWrap; Layout.fillWidth: true }
            Label { text: "Document root" }
            TextField { id: rootField; Layout.fillWidth: true }
            RowLayout { Label { text: "Web port"; Layout.preferredWidth: 130 } SpinBox { id: webPort; from: 1024; to: 65535; editable: true } }
            RowLayout { Label { text: "MariaDB port"; Layout.preferredWidth: 130 } SpinBox { id: dbPort; from: 1024; to: 65535; editable: true } }
            Switch { id: darkToggle; text: "Dark appearance" }
        }
        onAccepted: backend.preferences(rootField.text, webPort.value, dbPort.value, darkToggle.checked)
    }
    Dialog {
        id: extensionsDialog; anchors.centerIn: parent; width: 430; title: "Loaded PHP extensions"; modal: true
        standardButtons: Dialog.Ok
        ScrollView { width: parent.width; height: 300; TextArea { id: extensionsText; readOnly: true; selectByMouse: true } }
    }
    Dialog {
        id: errorDialog; anchors.centerIn: parent; width: Math.min(win.width - 50, 650); title: "Unable to complete action"; modal: true
        standardButtons: Dialog.Ok
        ScrollView { width: parent.width; height: 240; TextArea { id: errorText; readOnly: true; wrapMode: TextEdit.Wrap; selectByMouse: true } }
    }
    Dialog {
        id: runtimeDialog; anchors.centerIn: parent; width: 480; title: "Runtime packages"; modal: true; standardButtons: Dialog.Ok
        Label { width: parent.width; wrapMode: Text.WordWrap; text: "The complete LARSANA package includes all runtimes.\n\nPHP: 8.1 (legacy), 8.2, 8.3, 8.4, 8.5\nNginx: stable only\nMariaDB: stable / GA only; separate data per series\n\nAll runtimes are included in the single LARSANA installer.\n\nRuntime location:\n" + snapshotData.installed.php.map(function(x){return x.root}).join("\n") }
    }
    Dialog {
        id: aboutDialog; anchors.centerIn: parent; width: 440; title: "LARSANA 1.2.2"; modal: true; standardButtons: Dialog.Ok
        Label { width: parent.width; wrapMode: Text.WordWrap; text: "Local development, on Linux.\n\nAn independent desktop environment inspired by Laragon workflows.\n\nLARSANA source: GPL-3.0-or-later.\nRuntime components retain their upstream licenses." }
    }
}
