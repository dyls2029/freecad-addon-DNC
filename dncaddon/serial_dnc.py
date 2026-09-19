import os
import time
import FreeCAD
import FreeCADGui

try:
    import serial
    import serial.tools.list_ports as serial_list_ports
except Exception:
    serial = None
    serial_list_ports = None

try:
    from .machine_profiles import list_profiles, load_profile, save_profile, delete_profile
    from .serial_session import SerialSession
except Exception:
    from machine_profiles import list_profiles, load_profile, save_profile, delete_profile
    from serial_session import SerialSession

try:
    from PySide6 import QtCore, QtWidgets, QtGui
except Exception:
    try:
        from PySide2 import QtCore, QtWidgets, QtGui
    except Exception:
        from PySide import QtCore, QtWidgets, QtGui


_DNC_DOCK_WIDGET = None


def _settings():
    return FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Mod/DNCAddon")


def get_setting(name, default):
    p = _settings()
    if isinstance(default, int):
        return p.GetInt(name, default)
    return p.GetString(name, str(default))


def set_setting(name, value):
    p = _settings()
    if isinstance(value, int):
        p.SetInt(name, value)
    else:
        p.SetString(name, str(value))


def get_serial_settings():
    return {
        "port": get_setting("port", ""),
        "baud": int(get_setting("baud", 115200)),
        "transport_mode": get_setting("transport_mode", "basic"),
        "rtscts": bool(int(get_setting("rtscts", 0))),
        "parity": get_setting("parity", "EVEN"),
        "bytesize": int(get_setting("bytesize", 7)),
        "stopbits": get_setting("stopbits", "TWO"),
        "line_ending": get_setting("line_ending", "CRLF"),
        "received_line_ending": get_setting("received_line_ending", "CRLF"),
        "raw_received": bool(int(get_setting("raw_received", 0))),
    }


def set_serial_settings(settings):
    set_setting("port", settings.get("port", ""))
    set_setting("baud", int(settings.get("baud", 115200)))
    set_setting("transport_mode", settings.get("transport_mode", "basic"))
    set_setting("rtscts", int(bool(settings.get("rtscts", False))))
    set_setting("parity", settings.get("parity", "EVEN"))
    set_setting("bytesize", int(settings.get("bytesize", 7)))
    set_setting("stopbits", settings.get("stopbits", "TWO"))
    set_setting("line_ending", settings.get("line_ending", "CRLF"))
    set_setting("received_line_ending", settings.get("received_line_ending", "CRLF"))
    set_setting("raw_received", int(bool(settings.get("raw_received", False))))


def find_serial_ports():
    if serial is None or serial_list_ports is None:
        return []
    try:
        return [info.device for info in serial_list_ports.comports()]
    except Exception:
        return []


def run_dnc_console():
    global _DNC_DOCK_WIDGET

    if FreeCADGui is None:
        raise RuntimeError("FreeCADGui is not available")

    if _DNC_DOCK_WIDGET is not None:
        if _DNC_DOCK_WIDGET.isVisible():
            _DNC_DOCK_WIDGET.hide()
            _DNC_DOCK_WIDGET.deleteLater()
            _DNC_DOCK_WIDGET = None
        else:
            _DNC_DOCK_WIDGET.show()
            _DNC_DOCK_WIDGET.raise_()
            _DNC_DOCK_WIDGET.activateWindow()
        return

    main_window = FreeCADGui.getMainWindow()
    dialog = QtWidgets.QDockWidget("DNC Console", main_window)
    dialog.setObjectName("DNCConsoleDockWidget")
    dialog.setAllowedAreas(QtCore.Qt.AllDockWidgetAreas)
    dialog.setFeatures(QtWidgets.QDockWidget.DockWidgetMovable | QtWidgets.QDockWidget.DockWidgetFloatable)
    dialog.setWindowTitle("DNC Console")
    dialog.resize(900, 650)
    dialog.setMinimumSize(560, 400)

    content_widget = QtWidgets.QWidget(dialog)
    layout = QtWidgets.QVBoxLayout(content_widget)
    dialog.setWidget(content_widget)

    top_bar_container = QtWidgets.QWidget(content_widget)
    top_layout = QtWidgets.QHBoxLayout(top_bar_container)
    top_layout.setContentsMargins(0, 0, 0, 0)
    top_layout.setSpacing(6)

    top_scroll = QtWidgets.QScrollArea(content_widget)
    top_scroll.setWidgetResizable(True)
    top_scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
    top_scroll.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
    top_scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
    top_scroll.setWidget(top_bar_container)

    profile_combo = QtWidgets.QComboBox()
    profile_combo.addItem("<new>")
    for profile in list_profiles():
        profile_combo.addItem(profile)

    profile_name_edit = QtWidgets.QLineEdit()
    profile_name_edit.setPlaceholderText("profile name")

    load_profile_button = QtWidgets.QPushButton("Load profile")
    delete_profile_button = QtWidgets.QPushButton("Delete profile")
    connect_button = QtWidgets.QPushButton("Connect")
    disconnect_button = QtWidgets.QPushButton("Disconnect")
    send_button = QtWidgets.QPushButton("Send")
    receive_button = QtWidgets.QPushButton("Receive")
    send_received_button = QtWidgets.QPushButton("Send received")
    load_button = QtWidgets.QPushButton("Load file")
    save_button = QtWidgets.QPushButton("Save file")
    clear_button = QtWidgets.QPushButton("Clear")
    settings_button = QtWidgets.QPushButton("Serial settings")

    editor = QtWidgets.QPlainTextEdit()
    receive_box = QtWidgets.QPlainTextEdit()
    log_box = QtWidgets.QPlainTextEdit()
    receive_box.setReadOnly(False)
    log_box.setReadOnly(True)
    editor.setTabStopDistance(40)
    receive_box.setTabStopDistance(40)

    send_label = QtWidgets.QLabel("Sending")
    receive_label = QtWidgets.QLabel("Received")
    log_label = QtWidgets.QLabel("Log")

    send_container = QtWidgets.QWidget()
    send_layout = QtWidgets.QVBoxLayout(send_container)
    send_layout.setContentsMargins(0, 0, 0, 0)
    send_layout.addWidget(send_label)
    send_layout.addWidget(editor)

    receive_container = QtWidgets.QWidget()
    receive_layout = QtWidgets.QVBoxLayout(receive_container)
    receive_layout.setContentsMargins(0, 0, 0, 0)
    receive_layout.addWidget(receive_label)
    receive_layout.addWidget(receive_box)

    log_container = QtWidgets.QWidget()
    log_layout = QtWidgets.QVBoxLayout(log_container)
    log_layout.setContentsMargins(0, 0, 0, 0)
    log_layout.addWidget(log_label)
    log_layout.addWidget(log_box)

    splitter = QtWidgets.QSplitter(QtCore.Qt.Vertical)
    splitter.setChildrenCollapsible(False)
    splitter.addWidget(send_container)
    splitter.addWidget(receive_container)
    splitter.addWidget(log_container)

    top_layout.addWidget(profile_combo)
    top_layout.addWidget(profile_name_edit)
    top_layout.addWidget(load_profile_button)
    top_layout.addWidget(delete_profile_button)
    top_layout.addWidget(connect_button)
    top_layout.addWidget(disconnect_button)
    top_layout.addWidget(send_button)
    top_layout.addWidget(receive_button)
    top_layout.addWidget(send_received_button)
    top_layout.addWidget(load_button)
    top_layout.addWidget(save_button)
    top_layout.addWidget(clear_button)
    top_layout.addWidget(settings_button)

    layout.addWidget(top_scroll)
    layout.addWidget(splitter, 1)

    main_window.addDockWidget(QtCore.Qt.RightDockWidgetArea, dialog)
    _DNC_DOCK_WIDGET = dialog
    dialog.show()
    dialog.raise_()
    dialog.activateWindow()

    session = None
    receive_timer = QtCore.QTimer(dialog)
    receive_timer.setInterval(50)
    receiving = False
    receive_started_at = 0.0
    receive_last_data_at = 0.0
    receive_received_data = False
    receive_idle_timeout = 3.0
    receive_start_timeout = 10.0

    def close_session_on_destroyed(_widget=None):
        nonlocal session
        receive_timer.stop()
        if session is not None:
            session.close()
            session = None

    dialog.destroyed.connect(close_session_on_destroyed)

    def show_status(msg):
        log_box.appendPlainText(msg)


    def show_serial_settings_dialog():
        settings_dialog = QtWidgets.QDialog(dialog)
        settings_dialog.setWindowTitle("Serial settings")
        settings_dialog.resize(380, 280)
        form_layout = QtWidgets.QFormLayout(settings_dialog)

        current_settings = get_serial_settings()

        port_combo = QtWidgets.QComboBox()
        port_combo.setEditable(True)
        current_port = current_settings.get("port", "")
        ports = find_serial_ports()
        if ports:
            port_combo.addItems(ports)
        if current_port:
            port_combo.setCurrentText(current_port)
        elif port_combo.count():
            port_combo.setCurrentIndex(0)
        else:
            port_combo.setEditText("")

        baud_combo = QtWidgets.QComboBox()
        baud_combo.addItems(["9600", "19200", "38400", "57600", "115200", "230400", "460800"])
        baud_combo.setCurrentText(str(current_settings.get("baud", 115200)))

        transport_combo = QtWidgets.QComboBox()
        transport_combo.addItems(["Basic serial", "USB adapter / XON-XOFF"])
        transport_mode = current_settings.get("transport_mode", "basic")
        transport_combo.setCurrentIndex(0 if transport_mode == "basic" else 1)

        rtscts_check = QtWidgets.QCheckBox("RTS/CTS")
        rtscts_check.setChecked(bool(current_settings.get("rtscts", False)))

        parity_combo = QtWidgets.QComboBox()
        parity_combo.addItems(["None", "Even", "Odd", "Mark", "Space"])
        parity_value = str(current_settings.get("parity", "EVEN")).upper()
        parity_labels = {"NONE": "None", "EVEN": "Even", "ODD": "Odd", "MARK": "Mark", "SPACE": "Space"}
        parity_combo.setCurrentText(parity_labels.get(parity_value, "Even"))

        bytesize_combo = QtWidgets.QComboBox()
        bytesize_combo.addItems(["5", "6", "7", "8"])
        bytesize_combo.setCurrentText(str(current_settings.get("bytesize", 7)))

        stopbits_combo = QtWidgets.QComboBox()
        stopbits_combo.addItems(["1", "1.5", "2"])
        stopbits_combo.setCurrentText(str(current_settings.get("stopbits", "TWO")))

        line_ending_combo = QtWidgets.QComboBox()
        line_ending_combo.addItems(["CR", "LF", "CR/LF"])
        saved_line_ending = str(current_settings.get("line_ending", "CRLF")).upper().replace("/", "")
        if saved_line_ending == "CRLF":
            line_ending_combo.setCurrentText("CR/LF")
        elif saved_line_ending == "CR":
            line_ending_combo.setCurrentText("CR")
        elif saved_line_ending == "LF":
            line_ending_combo.setCurrentText("LF")
        else:
            line_ending_combo.setCurrentText("CR/LF")

        receive_line_ending_combo = QtWidgets.QComboBox()
        receive_line_ending_combo.addItems(["CR", "LF", "CR/LF", "LFCRCR"])
        saved_receive_line_ending = str(current_settings.get("received_line_ending", "CRLF")).upper().replace("/", "")
        if saved_receive_line_ending == "CRLF":
            receive_line_ending_combo.setCurrentText("CR/LF")
        elif saved_receive_line_ending == "CR":
            receive_line_ending_combo.setCurrentText("CR")
        elif saved_receive_line_ending == "LF":
            receive_line_ending_combo.setCurrentText("LF")
        elif saved_receive_line_ending == "LFCRCR":
            receive_line_ending_combo.setCurrentText("LFCRCR")
        else:
            receive_line_ending_combo.setCurrentText("CR/LF")

        refresh_button = QtWidgets.QPushButton("Refresh ports")
        apply_button = QtWidgets.QPushButton("Apply")
        save_profile_button = QtWidgets.QPushButton("Save profile")
        profile_name_for_settings = QtWidgets.QLineEdit()
        profile_name_for_settings.setPlaceholderText("profile name")
        profile_name_for_settings.setText(profile_name_edit.text().strip())
        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)

        raw_received_check = QtWidgets.QCheckBox("Output raw received serial bytes as hex")
        raw_received_check.setChecked(bool(current_settings.get("raw_received", False)))

        form_layout.addRow("Port", port_combo)
        form_layout.addRow("Baud", baud_combo)
        form_layout.addRow("Serial mode", transport_combo)
        form_layout.addRow(rtscts_check)
        form_layout.addRow("Parity", parity_combo)
        form_layout.addRow("Byte size", bytesize_combo)
        form_layout.addRow("Stop bits", stopbits_combo)
        form_layout.addRow("Send line ending", line_ending_combo)
        form_layout.addRow("Receive line ending", receive_line_ending_combo)
        form_layout.addRow(raw_received_check)
        form_layout.addRow("Profile name", profile_name_for_settings)
        form_layout.addRow(save_profile_button)
        form_layout.addRow(apply_button)
        form_layout.addRow(refresh_button, buttons)

        def apply_settings_from_dialog():
            new_settings = {
                "port": port_combo.currentText().strip(),
                "baud": int(baud_combo.currentText().strip()),
                "transport_mode": "adapter" if "adapter" in transport_combo.currentText().lower() else "basic",
                "rtscts": int(rtscts_check.isChecked()),
                "parity": parity_combo.currentText().upper()[:4] if parity_combo.currentText().upper()[:4] in ["NONE", "EVEN", "ODD", "MARK", "SPAC"] else "EVEN",
                "bytesize": int(bytesize_combo.currentText().strip()),
                "stopbits": stopbits_combo.currentText().strip(),
                "line_ending": line_ending_combo.currentText().strip().upper().replace("/", ""),
                "received_line_ending": receive_line_ending_combo.currentText().strip().upper().replace("/", ""),
                "raw_received": int(raw_received_check.isChecked()),
            }
            if new_settings["parity"] == "SPAC":
                new_settings["parity"] = "SPACE"
            elif new_settings["parity"] == "EVEN":
                new_settings["parity"] = "EVEN"
            elif new_settings["parity"] == "ODD":
                new_settings["parity"] = "ODD"
            elif new_settings["parity"] == "MARK":
                new_settings["parity"] = "MARK"
            elif new_settings["parity"] == "NONE":
                new_settings["parity"] = "NONE"
            set_serial_settings(new_settings)
            show_status("Serial settings applied")

        def refresh_ports():
            current_text = port_combo.currentText().strip()
            port_combo.clear()
            refreshed_ports = find_serial_ports()
            if refreshed_ports:
                port_combo.addItems(refreshed_ports)
            if current_text:
                port_combo.setCurrentText(current_text)
            elif port_combo.count():
                port_combo.setCurrentIndex(0)
            else:
                port_combo.setEditText("")

        refresh_button.clicked.connect(refresh_ports)
        apply_button.clicked.connect(apply_settings_from_dialog)
        save_profile_button.clicked.connect(lambda: save_profile_from_ui(profile_name_for_settings.text().strip() or profile_name_edit.text().strip()))
        buttons.accepted.connect(settings_dialog.accept)
        buttons.rejected.connect(settings_dialog.reject)

        exec_dialog = settings_dialog.exec if hasattr(settings_dialog, "exec") else settings_dialog.exec_
        if exec_dialog():
            apply_settings_from_dialog()
            show_status("Serial settings saved")

    def save_profile_from_ui(profile_name=None):
        profile_name = (profile_name or profile_name_edit.text().strip()).strip()
        if not profile_name:
            show_status("Enter a profile name")
            return
        settings = get_serial_settings()
        settings.update({"name": profile_name})
        save_profile(profile_name, settings)
        profile_name_edit.setText(profile_name)
        profile_combo.blockSignals(True)
        profile_combo.clear()
        profile_combo.addItem("<new>")
        for existing in list_profiles():
            profile_combo.addItem(existing)
        profile_combo.setCurrentText(profile_name)
        profile_combo.blockSignals(False)
        show_status(f"Saved profile {profile_name}")

    def load_selected_profile():
        profile_name = profile_combo.currentText().strip()
        if not profile_name or profile_name == "<new>":
            return
        data = load_profile(profile_name)
        if data is None:
            show_status("Profile not found")
            return
        profile_name_edit.setText(profile_name)
        set_serial_settings(data)
        show_status(f"Loaded profile {profile_name}")

    def delete_selected_profile():
        profile_name = profile_combo.currentText().strip()
        if not profile_name or profile_name == "<new>":
            return
        delete_profile(profile_name)
        profile_combo.blockSignals(True)
        profile_combo.clear()
        profile_combo.addItem("<new>")
        for existing in list_profiles():
            profile_combo.addItem(existing)
        profile_combo.blockSignals(False)
        show_status(f"Deleted profile {profile_name}")

    def connect_session():
        nonlocal session
        if session is not None:
            return
        settings = get_serial_settings()
        port = settings.get("port", "").strip()
        baudrate = str(settings.get("baud", 115200))
        if not port:
            show_status("Please select a serial port in Serial settings")
            return
        transport_mode = settings.get("transport_mode", "basic")
        rtscts = bool(settings.get("rtscts", False))
        session = SerialSession(
            port,
            baudrate,
            transport_mode=transport_mode,
            rtscts=rtscts,
            bytesize=settings.get("bytesize", 7),
            parity=settings.get("parity", "EVEN"),
            stopbits=settings.get("stopbits", "TWO"),
            line_ending=settings.get("line_ending", "CRLF"),
            received_line_ending=settings.get("received_line_ending", "CRLF"),
            raw_received=settings.get("raw_received", False),
        )
        try:
            session.open()
            show_status(f"Connected to {port} @ {baudrate}")
        except PermissionError as exc:
            session = None
            show_status(f"Could not open {port}: permission denied. The port may already be in use by another program or the device may not be available.")
        except OSError as exc:
            session = None
            show_status(f"Could not open {port}: {exc}")
        except Exception as exc:
            session = None
            show_status(f"Could not open {port}: {exc}")

    def disconnect_session():
        nonlocal session
        receive_timer.stop()
        if session is not None:
            session.close()
            session = None
            show_status("Disconnected")

    def send_program():
        nonlocal session
        if session is None:
            show_status("Connect first")
            return
        try:
            text = editor.toPlainText()
            for line in text.splitlines():
                session.send_line(line.strip())
                time.sleep(0.02)
            show_status("Send complete")
        except Exception as exc:
            show_status(f"Send failed: {exc}")

    def send_received_program():
        nonlocal session
        if session is None:
            show_status("Connect first")
            return
        try:
            text = receive_box.toPlainText()
            for line in text.splitlines():
                session.send_line(line.strip())
                time.sleep(0.02)
            show_status("Send received complete")
        except Exception as exc:
            show_status(f"Send received failed: {exc}")

    def stop_receiving(message):
        nonlocal receiving
        receive_timer.stop()
        if receiving:
            receiving = False
            receive_button.setText("Receive")
            show_status(message)

    def poll_receive():
        nonlocal receive_last_data_at, receive_received_data
        if session is None or not session.is_open():
            stop_receiving("Receive stopped: disconnected")
            return

        now = time.monotonic()
        chunk = session.read_all()
        if chunk:
            receive_box.moveCursor(QtGui.QTextCursor.End)
            receive_box.insertPlainText(chunk)
            receive_box.ensureCursorVisible()
            receive_received_data = True
            receive_last_data_at = now
        elif receive_received_data and now - receive_last_data_at >= receive_idle_timeout:
            stop_receiving("Receive complete")
        elif not receive_received_data and now - receive_started_at >= receive_start_timeout:
            stop_receiving("No response received")

    def receive_program():
        nonlocal session, receiving, receive_started_at, receive_last_data_at, receive_received_data
        if session is None:
            show_status("Connect first")
            return
        if receiving:
            stop_receiving("Receive stopped")
            return
        receiving = True
        receive_started_at = time.monotonic()
        receive_last_data_at = receive_started_at
        receive_received_data = False
        receive_button.setText("Receiving...")
        show_status("Receiving...")
        receive_timer.start()

    def load_file():
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(dialog, "Open G-code file", os.path.expanduser("~"), "G-code files (*.nc *.gcode *.tap *.ngc *.txt);;All files (*)")
        if file_path:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as handle:
                editor.setPlainText(handle.read())

    def save_file():
        file_path, _ = QtWidgets.QFileDialog.getSaveFileName(dialog, "Save received G-code", os.path.expanduser("~"), "G-code files (*.nc *.gcode *.tap *.ngc *.txt);;All files (*)")
        if file_path:
            with open(file_path, "w", encoding="utf-8") as handle:
                handle.write(receive_box.toPlainText())

    def clear_editor():
        editor.setPlainText("")
        receive_box.setPlainText("")
        log_box.setPlainText("")
    connect_button.clicked.connect(connect_session)
    disconnect_button.clicked.connect(disconnect_session)
    send_button.clicked.connect(send_program)
    receive_button.clicked.connect(receive_program)
    send_received_button.clicked.connect(send_received_program)
    load_button.clicked.connect(load_file)
    save_button.clicked.connect(save_file)
    clear_button.clicked.connect(clear_editor)
    settings_button.clicked.connect(show_serial_settings_dialog)
    receive_timer.timeout.connect(poll_receive)
    load_profile_button.clicked.connect(load_selected_profile)
    delete_profile_button.clicked.connect(delete_selected_profile)
    profile_combo.currentIndexChanged.connect(lambda _: None)
