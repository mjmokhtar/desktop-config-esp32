#!/usr/bin/env python3
"""
ESP32 IEEE 488.2 GPIO Controller - Universal Qt Version
Compatible with both PyQt5 and PySide2
"""

import sys
import json
import csv
from datetime import datetime
from typing import Optional, List, Dict
from dataclasses import dataclass
from enum import Enum

# Qt compatibility layer
try:
    # Try PySide2 first
    from PySide2.QtWidgets import *
    from PySide2.QtCore import *
    from PySide2.QtGui import *
    Signal = Signal  # PySide2 uses Signal
    print("Using PySide2")
    QT_LIB = "PySide2"
except ImportError:
    try:
        # Fall back to PyQt5
        from PyQt5.QtWidgets import *
        from PyQt5.QtCore import *
        from PyQt5.QtGui import *
        Signal = pyqtSignal  # PyQt5 uses pyqtSignal
        print("Using PyQt5")
        QT_LIB = "PyQt5"
    except ImportError:
        print("Error: No Qt library found!")
        print("Please install either PySide2 or PyQt5:")
        print("  pip install PySide2")
        print("  or")
        print("  pip install PyQt5")
        sys.exit(1)

import serial
import serial.tools.list_ports

# Modern style sheet
MODERN_STYLE = """
QMainWindow {
    background-color: #f5f5f5;
}
QWidget {
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 10pt;
}
QGroupBox {
    font-weight: bold;
    border: 2px solid #cccccc;
    border-radius: 5px;
    margin-top: 10px;
    padding-top: 10px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 5px 0 5px;
}
QPushButton {
    background-color: #0078d4;
    color: white;
    border: none;
    padding: 8px 16px;
    border-radius: 4px;
    font-weight: 500;
}
QPushButton:hover {
    background-color: #106ebe;
}
QPushButton:pressed {
    background-color: #005a9e;
}
QPushButton:checked {
    background-color: #40a040;
}
QPushButton:disabled {
    background-color: #cccccc;
    color: #666666;
}
QLineEdit, QComboBox, QSpinBox, QTextEdit {
    border: 1px solid #cccccc;
    border-radius: 4px;
    padding: 6px;
    background-color: white;
}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus {
    border: 2px solid #0078d4;
}
QTabWidget::pane {
    border: 1px solid #cccccc;
    background-color: white;
}
QTabBar::tab {
    background-color: #e0e0e0;
    padding: 8px 16px;
    margin-right: 2px;
}
QTabBar::tab:selected {
    background-color: white;
    border-bottom: 2px solid #0078d4;
}
QSlider::groove:horizontal {
    height: 6px;
    background: #cccccc;
    border-radius: 3px;
}
QSlider::handle:horizontal {
    background: #0078d4;
    width: 18px;
    margin: -6px 0;
    border-radius: 9px;
}
QSlider::handle:horizontal:hover {
    background: #106ebe;
}
QProgressBar {
    border: 1px solid #cccccc;
    border-radius: 4px;
    text-align: center;
}
QProgressBar::chunk {
    background-color: #0078d4;
    border-radius: 3px;
}
QCheckBox {
    spacing: 8px;
}
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border: 2px solid #cccccc;
    border-radius: 3px;
    background-color: white;
}
QCheckBox::indicator:checked {
    background-color: #0078d4;
    border: 2px solid #0078d4;
}
"""

class SerialWorker(QThread):
    """Worker thread for serial communication"""
    # Define signals based on Qt library
    if QT_LIB == "PyQt5":
        data_received = pyqtSignal(str)
        error_occurred = pyqtSignal(str)
        connection_lost = pyqtSignal()
    else:  # PySide2
        data_received = Signal(str)
        error_occurred = Signal(str)
        connection_lost = Signal()
    
    def __init__(self):
        super().__init__()
        self.serial_port = None
        self.is_running = False
        
    def connect_port(self, port, baudrate):
        """Connect to serial port"""
        try:
            self.serial_port = serial.Serial(port, baudrate, timeout=0.1)
            self.is_running = True
            return True
        except Exception as e:
            self.error_occurred.emit(str(e))
            return False
    
    def disconnect(self):
        """Disconnect from serial port"""
        self.is_running = False
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()
    
    def send_command(self, command):
        """Send command to device"""
        if self.serial_port and self.serial_port.is_open:
            try:
                self.serial_port.write(f"{command}\n".encode())
            except Exception as e:
                self.error_occurred.emit(f"Send error: {e}")
    
    def run(self):
        """Main thread loop"""
        while self.is_running:
            if self.serial_port and self.serial_port.is_open:
                try:
                    if self.serial_port.in_waiting:
                        data = self.serial_port.readline().decode('utf-8').strip()
                        if data:
                            self.data_received.emit(data)
                except Exception as e:
                    self.error_occurred.emit(f"Read error: {e}")
                    self.connection_lost.emit()
                    self.is_running = False
            self.msleep(10)

class LEDWidget(QWidget):
    """Custom LED indicator widget"""
    def __init__(self, size=30, parent=None):
        super().__init__(parent)
        self.size = size
        self.state = False
        self.setFixedSize(size, size)
        
    def setState(self, state):
        """Set LED state"""
        self.state = state
        self.update()
    
    def paintEvent(self, event):
        """Paint the LED"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw LED circle
        if self.state:
            # ON - Green with glow
            painter.setBrush(QBrush(QColor(0, 255, 0)))
            painter.setPen(QPen(QColor(0, 200, 0), 2))
        else:
            # OFF - Gray
            painter.setBrush(QBrush(QColor(100, 100, 100)))
            painter.setPen(QPen(QColor(60, 60, 60), 2))
        
        painter.drawEllipse(2, 2, self.size-4, self.size-4)
        
        # Add highlight for 3D effect
        if self.state:
            painter.setBrush(QBrush(QColor(150, 255, 150, 100)))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(6, 6, self.size//2, self.size//2)

class MainWindow(QMainWindow):
    """Main application window"""
    def __init__(self):
        super().__init__()
        self.serial_worker = SerialWorker()
        self.init_ui()
        self.setup_connections()
        self.update_port_list()
        self.msg_count = 0
        
    def init_ui(self):
        """Initialize user interface"""
        self.setWindowTitle("ESP32 GPIO Controller - IEEE 488.2/SCPI")
        self.setGeometry(100, 100, 1200, 800)
        self.setStyleSheet(MODERN_STYLE)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout(central_widget)
        
        # Connection bar
        conn_layout = QHBoxLayout()
        conn_layout.addWidget(QLabel("Port:"))
        
        self.port_combo = QComboBox()
        self.port_combo.setMinimumWidth(150)
        conn_layout.addWidget(self.port_combo)
        
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.update_port_list)
        conn_layout.addWidget(self.refresh_btn)
        
        conn_layout.addWidget(QLabel("Baud:"))
        self.baud_combo = QComboBox()
        self.baud_combo.addItems(['9600', '19200', '38400', '57600', '115200'])
        conn_layout.addWidget(self.baud_combo)
        
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.setCheckable(True)
        self.connect_btn.clicked.connect(self.toggle_connection)
        conn_layout.addWidget(self.connect_btn)
        
        conn_layout.addSpacing(20)
        
        self.status_label = QLabel("Disconnected")
        self.status_label.setStyleSheet("color: red; font-weight: bold;")
        conn_layout.addWidget(self.status_label)
        
        conn_layout.addStretch()
        
        # RX/TX LEDs
        conn_layout.addWidget(QLabel("RX:"))
        self.rx_led = LEDWidget(20)
        conn_layout.addWidget(self.rx_led)
        
        conn_layout.addWidget(QLabel("TX:"))
        self.tx_led = LEDWidget(20)
        conn_layout.addWidget(self.tx_led)
        
        main_layout.addLayout(conn_layout)
        
        # Create tab widget
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)
        
        # Create tabs
        self.create_control_tab()
        self.create_gpio_tab()
        self.create_pwm_tab()
        self.create_monitor_tab()
        self.create_log_tab()
        
    def create_control_tab(self):
        """Create main control tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # IEEE 488.2 Commands
        ieee_group = QGroupBox("IEEE 488.2 Commands")
        ieee_layout = QGridLayout(ieee_group)
        
        commands = [
            ("*IDN?", "Identification"),
            ("*RST", "Reset"),
            ("*TST?", "Self Test"),
            ("*CLS", "Clear Status"),
            ("*ESR?", "Event Status"),
            ("*STB?", "Status Byte"),
            ("SYST:STAT?", "System Status"),
            ("SYST:ERR?", "System Error"),
        ]
        
        for i, (cmd, desc) in enumerate(commands):
            btn = QPushButton(f"{cmd}\n{desc}")
            btn.clicked.connect(lambda checked, c=cmd: self.send_command(c))
            ieee_layout.addWidget(btn, i // 4, i % 4)
        
        layout.addWidget(ieee_group)
        
        # Custom Command
        custom_group = QGroupBox("Custom Command")
        custom_layout = QHBoxLayout(custom_group)
        
        self.cmd_input = QLineEdit()
        self.cmd_input.setPlaceholderText("Enter command...")
        self.cmd_input.returnPressed.connect(self.send_custom_command)
        custom_layout.addWidget(self.cmd_input)
        
        send_btn = QPushButton("Send")
        send_btn.clicked.connect(self.send_custom_command)
        custom_layout.addWidget(send_btn)
        
        layout.addWidget(custom_group)
        
        # Communication Log
        log_group = QGroupBox("Communication Log")
        log_layout = QVBoxLayout(log_group)
        
        self.comm_log = QTextEdit()
        self.comm_log.setReadOnly(True)
        self.comm_log.setFont(QFont("Consolas", 9))
        log_layout.addWidget(self.comm_log)
        
        btn_layout = QHBoxLayout()
        clear_btn = QPushButton("Clear Log")
        clear_btn.clicked.connect(self.comm_log.clear)
        btn_layout.addWidget(clear_btn)
        btn_layout.addStretch()
        log_layout.addLayout(btn_layout)
        
        layout.addWidget(log_group)
        
        self.tabs.addTab(tab, "Control")
        
    def create_gpio_tab(self):
        """Create GPIO control tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # LED Control
        led_group = QGroupBox("LED Control")
        led_layout = QHBoxLayout(led_group)
        
        self.led_widgets = []
        self.led_checks = []
        
        for i in range(3):
            vbox = QVBoxLayout()
            
            cb = QCheckBox(f"LED {i+1}")
            cb.toggled.connect(lambda checked, idx=i: self.toggle_led(idx+1, checked))
            vbox.addWidget(cb, alignment=Qt.AlignCenter)
            self.led_checks.append(cb)
            
            led = LEDWidget(40)
            vbox.addWidget(led, alignment=Qt.AlignCenter)
            self.led_widgets.append(led)
            
            led_layout.addLayout(vbox)
        
        led_layout.addStretch()
        layout.addWidget(led_group)
        
        # Relay Control
        relay_group = QGroupBox("Relay Control")
        relay_layout = QGridLayout(relay_group)
        
        self.relay_btns = []
        for i in range(4):
            btn = QPushButton(f"Relay {i+1}\nOFF")
            btn.setCheckable(True)
            btn.setMinimumHeight(80)
            btn.toggled.connect(lambda checked, idx=i: self.toggle_relay(idx+1, checked))
            relay_layout.addWidget(btn, i // 2, i % 2)
            self.relay_btns.append(btn)
        
        layout.addWidget(relay_group)
        
        # Pattern Control
        pattern_group = QGroupBox("LED Patterns")
        pattern_layout = QHBoxLayout(pattern_group)
        
        patterns = [
            ("Blink All", self.blink_pattern),
            ("Wave", self.wave_pattern),
            ("Chase", self.chase_pattern),
            ("All ON", lambda: self.all_leds(True)),
            ("All OFF", lambda: self.all_leds(False)),
        ]
        
        for name, func in patterns:
            btn = QPushButton(name)
            btn.clicked.connect(func)
            pattern_layout.addWidget(btn)
        
        layout.addWidget(pattern_group)
        
        layout.addStretch()
        self.tabs.addTab(tab, "GPIO")
        
    def create_pwm_tab(self):
        """Create PWM control tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # PWM Channel 1
        pwm1_group = QGroupBox("PWM Channel 1")
        pwm1_layout = QGridLayout(pwm1_group)
        
        pwm1_layout.addWidget(QLabel("Duty Cycle:"), 0, 0)
        
        self.pwm1_slider = QSlider(Qt.Horizontal)
        self.pwm1_slider.setRange(0, 100)
        self.pwm1_slider.valueChanged.connect(lambda v: self.pwm1_label.setText(f"{v}%"))
        self.pwm1_slider.sliderReleased.connect(lambda: self.set_pwm(1, self.pwm1_slider.value()))
        pwm1_layout.addWidget(self.pwm1_slider, 0, 1)
        
        self.pwm1_label = QLabel("0%")
        self.pwm1_label.setMinimumWidth(50)
        pwm1_layout.addWidget(self.pwm1_label, 0, 2)
        
        self.pwm1_spin = QSpinBox()
        self.pwm1_spin.setRange(0, 100)
        self.pwm1_spin.setSuffix("%")
        self.pwm1_spin.valueChanged.connect(self.pwm1_slider.setValue)
        pwm1_layout.addWidget(self.pwm1_spin, 0, 3)
        
        pwm1_layout.addWidget(QLabel("Frequency:"), 1, 0)
        
        self.pwm1_freq = QSpinBox()
        self.pwm1_freq.setRange(100, 20000)
        self.pwm1_freq.setSuffix(" Hz")
        self.pwm1_freq.setValue(5000)
        pwm1_layout.addWidget(self.pwm1_freq, 1, 1)
        
        pwm1_set_btn = QPushButton("Set Frequency")
        pwm1_set_btn.clicked.connect(lambda: self.set_pwm_freq(1, self.pwm1_freq.value()))
        pwm1_layout.addWidget(pwm1_set_btn, 1, 2)
        
        layout.addWidget(pwm1_group)
        
        # PWM Channel 2
        pwm2_group = QGroupBox("PWM Channel 2")
        pwm2_layout = QGridLayout(pwm2_group)
        
        pwm2_layout.addWidget(QLabel("Duty Cycle:"), 0, 0)
        
        self.pwm2_slider = QSlider(Qt.Horizontal)
        self.pwm2_slider.setRange(0, 100)
        self.pwm2_slider.valueChanged.connect(lambda v: self.pwm2_label.setText(f"{v}%"))
        self.pwm2_slider.sliderReleased.connect(lambda: self.set_pwm(2, self.pwm2_slider.value()))
        pwm2_layout.addWidget(self.pwm2_slider, 0, 1)
        
        self.pwm2_label = QLabel("0%")
        self.pwm2_label.setMinimumWidth(50)
        pwm2_layout.addWidget(self.pwm2_label, 0, 2)
        
        self.pwm2_spin = QSpinBox()
        self.pwm2_spin.setRange(0, 100)
        self.pwm2_spin.setSuffix("%")
        self.pwm2_spin.valueChanged.connect(self.pwm2_slider.setValue)
        pwm2_layout.addWidget(self.pwm2_spin, 0, 3)
        
        pwm2_layout.addWidget(QLabel("Frequency:"), 1, 0)
        
        self.pwm2_freq = QSpinBox()
        self.pwm2_freq.setRange(100, 20000)
        self.pwm2_freq.setSuffix(" Hz")
        self.pwm2_freq.setValue(5000)
        pwm2_layout.addWidget(self.pwm2_freq, 1, 1)
        
        pwm2_set_btn = QPushButton("Set Frequency")
        pwm2_set_btn.clicked.connect(lambda: self.set_pwm_freq(2, self.pwm2_freq.value()))
        pwm2_layout.addWidget(pwm2_set_btn, 1, 2)
        
        layout.addWidget(pwm2_group)
        
        # PWM Presets
        preset_group = QGroupBox("PWM Presets")
        preset_layout = QHBoxLayout(preset_group)
        
        presets = [
            ("0%", 0),
            ("25%", 25),
            ("50%", 50),
            ("75%", 75),
            ("100%", 100),
        ]
        
        for name, value in presets:
            btn = QPushButton(name)
            btn.clicked.connect(lambda checked, v=value: self.set_pwm_preset(v))
            preset_layout.addWidget(btn)
        
        layout.addWidget(preset_group)
        
        layout.addStretch()
        self.tabs.addTab(tab, "PWM")
        
    def create_monitor_tab(self):
        """Create monitoring tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Control
        control_layout = QHBoxLayout()
        
        self.monitor_btn = QPushButton("Start Monitoring")
        self.monitor_btn.setCheckable(True)
        self.monitor_btn.clicked.connect(self.toggle_monitoring)
        control_layout.addWidget(self.monitor_btn)
        
        control_layout.addWidget(QLabel("Update Rate:"))
        self.monitor_rate = QSpinBox()
        self.monitor_rate.setRange(100, 5000)
        self.monitor_rate.setSuffix(" ms")
        self.monitor_rate.setValue(1000)
        control_layout.addWidget(self.monitor_rate)
        
        control_layout.addStretch()
        layout.addLayout(control_layout)
        
        # Digital Inputs
        digital_group = QGroupBox("Digital Inputs")
        digital_layout = QGridLayout(digital_group)
        
        self.digital_labels = {}
        inputs = ["Button 1", "Button 2", "Sensor 1", "Sensor 2"]
        
        for i, name in enumerate(inputs):
            digital_layout.addWidget(QLabel(f"{name}:"), i, 0)
            
            led = LEDWidget(24)
            digital_layout.addWidget(led, i, 1)
            
            label = QLabel("LOW")
            digital_layout.addWidget(label, i, 2)
            
            self.digital_labels[name] = (led, label)
        
        read_btn = QPushButton("Read All")
        read_btn.clicked.connect(lambda: self.send_command("DIN:ALL?"))
        digital_layout.addWidget(read_btn, 4, 0, 1, 3)
        
        layout.addWidget(digital_group)
        
        # Analog Inputs
        analog_group = QGroupBox("Analog Inputs")
        analog_layout = QGridLayout(analog_group)
        
        # Channel 1
        analog_layout.addWidget(QLabel("Channel 1:"), 0, 0)
        self.analog1_progress = QProgressBar()
        self.analog1_progress.setRange(0, 3300)
        self.analog1_progress.setFormat("%v mV")
        analog_layout.addWidget(self.analog1_progress, 0, 1)
        
        self.analog1_label = QLabel("0 mV")
        self.analog1_label.setMinimumWidth(80)
        analog_layout.addWidget(self.analog1_label, 0, 2)
        
        # Channel 2
        analog_layout.addWidget(QLabel("Channel 2:"), 1, 0)
        self.analog2_progress = QProgressBar()
        self.analog2_progress.setRange(0, 3300)
        self.analog2_progress.setFormat("%v mV")
        analog_layout.addWidget(self.analog2_progress, 1, 1)
        
        self.analog2_label = QLabel("0 mV")
        self.analog2_label.setMinimumWidth(80)
        analog_layout.addWidget(self.analog2_label, 1, 2)
        
        read_analog_btn = QPushButton("Read Analog")
        read_analog_btn.clicked.connect(lambda: self.send_command("AIN:ALL?"))
        analog_layout.addWidget(read_analog_btn, 2, 0, 1, 3)
        
        layout.addWidget(analog_group)
        
        # Interrupt Counter
        int_group = QGroupBox("Interrupt Counter")
        int_layout = QHBoxLayout(int_group)
        
        self.int_lcd = QLCDNumber()
        self.int_lcd.setDigitCount(8)
        self.int_lcd.setSegmentStyle(QLCDNumber.Flat)
        self.int_lcd.setMinimumHeight(60)
        int_layout.addWidget(self.int_lcd)
        
        btn_layout = QVBoxLayout()
        read_int = QPushButton("Read")
        read_int.clicked.connect(lambda: self.send_command("INT:COUNT?"))
        btn_layout.addWidget(read_int)
        
        reset_int = QPushButton("Reset")
        reset_int.clicked.connect(lambda: self.send_command("INT:RESET"))
        btn_layout.addWidget(reset_int)
        
        int_layout.addLayout(btn_layout)
        
        layout.addWidget(int_group)
        
        layout.addStretch()
        self.tabs.addTab(tab, "Monitor")
        
    def create_log_tab(self):
        """Create data logging tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Control
        control_layout = QHBoxLayout()
        
        self.log_btn = QPushButton("Start Logging")
        self.log_btn.setCheckable(True)
        control_layout.addWidget(self.log_btn)
        
        save_btn = QPushButton("Save to CSV")
        save_btn.clicked.connect(self.save_log)
        control_layout.addWidget(save_btn)
        
        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self.clear_log)
        control_layout.addWidget(clear_btn)
        
        control_layout.addStretch()
        layout.addLayout(control_layout)
        
        # Data Table
        self.data_table = QTableWidget()
        self.data_table.setColumnCount(5)
        self.data_table.setHorizontalHeaderLabels(["Time", "Type", "Command", "Response", "Note"])
        
        header = self.data_table.horizontalHeader()
        header.setStretchLastSection(True)
        
        layout.addWidget(self.data_table)
        
        self.tabs.addTab(tab, "Data Log")
        
    def setup_connections(self):
        """Setup signal connections"""
        self.serial_worker.data_received.connect(self.handle_data)
        self.serial_worker.error_occurred.connect(self.handle_error)
        self.serial_worker.connection_lost.connect(self.handle_disconnect)
        
    def update_port_list(self):
        """Update available ports"""
        self.port_combo.clear()
        ports = [p.device for p in serial.tools.list_ports.comports()]
        self.port_combo.addItems(ports)
        
    def toggle_connection(self):
        """Toggle serial connection"""
        if self.connect_btn.isChecked():
            port = self.port_combo.currentText()
            baud = int(self.baud_combo.currentText())
            
            if self.serial_worker.connect_port(port, baud):
                self.serial_worker.start()
                self.connect_btn.setText("Disconnect")
                self.status_label.setText("Connected")
                self.status_label.setStyleSheet("color: green; font-weight: bold;")
                self.log_message(f"Connected to {port} at {baud} baud")
            else:
                self.connect_btn.setChecked(False)
        else:
            self.serial_worker.disconnect()
            self.connect_btn.setText("Connect")
            self.status_label.setText("Disconnected")
            self.status_label.setStyleSheet("color: red; font-weight: bold;")
            self.log_message("Disconnected")
            
    def send_command(self, cmd):
        """Send command to device"""
        if self.serial_worker.is_running:
            self.serial_worker.send_command(cmd)
            self.log_message(f"TX: {cmd}", "tx")
            
            # Flash TX LED
            self.tx_led.setState(True)
            QTimer.singleShot(100, lambda: self.tx_led.setState(False))
        else:
            QMessageBox.warning(self, "Not Connected", "Please connect first")
            
    def send_custom_command(self):
        """Send custom command"""
        cmd = self.cmd_input.text().strip()
        if cmd:
            self.send_command(cmd)
            self.cmd_input.clear()
            
    def handle_data(self, data):
        """Handle received data"""
        self.log_message(f"RX: {data}", "rx")
        
        # Flash RX LED
        self.rx_led.setState(True)
        QTimer.singleShot(100, lambda: self.rx_led.setState(False))
        
        # Parse response
        self.parse_response(data)
        
    def handle_error(self, error):
        """Handle errors"""
        self.log_message(f"Error: {error}", "error")
        
    def handle_disconnect(self):
        """Handle disconnection"""
        self.connect_btn.setChecked(False)
        self.toggle_connection()
        
    def log_message(self, msg, msg_type="info"):
        """Log message to communication log"""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        
        colors = {
            "tx": "blue",
            "rx": "green",
            "error": "red",
            "info": "black"
        }
        
        color = colors.get(msg_type, "black")
        self.comm_log.append(f'<span style="color: {color}">[{timestamp}] {msg}</span>')
        
        # Log to data table if logging enabled
        if hasattr(self, 'log_btn') and self.log_btn.isChecked():
            row = self.data_table.rowCount()
            self.data_table.insertRow(row)
            self.data_table.setItem(row, 0, QTableWidgetItem(timestamp))
            self.data_table.setItem(row, 1, QTableWidgetItem(msg_type.upper()))
            
            if msg_type == "tx":
                self.data_table.setItem(row, 2, QTableWidgetItem(msg.replace("TX: ", "")))
            elif msg_type == "rx":
                self.data_table.setItem(row, 3, QTableWidgetItem(msg.replace("RX: ", "")))
            else:
                self.data_table.setItem(row, 4, QTableWidgetItem(msg))
                
    def parse_response(self, data):
        """Parse response data"""
        # Parse analog data
        if "CH1:" in data and "CH2:" in data:
            try:
                parts = data.split(',')
                ch1 = int(parts[0].split(':')[1])
                ch2 = int(parts[1].split(':')[1])
                
                self.analog1_progress.setValue(ch1)
                self.analog1_label.setText(f"{ch1} mV")
                
                self.analog2_progress.setValue(ch2)
                self.analog2_label.setText(f"{ch2} mV")
            except:
                pass
                
        # Parse digital data
        elif "B1:" in data and "B2:" in data:
            try:
                parts = data.split(',')
                values = {}
                for part in parts:
                    key, val = part.split(':')
                    values[key] = int(val)
                
                # Update digital LEDs and labels
                inputs_map = {
                    'B1': 'Button 1',
                    'B2': 'Button 2',
                    'S1': 'Sensor 1',
                    'S2': 'Sensor 2'
                }
                
                for key, name in inputs_map.items():
                    if key in values:
                        state = bool(values[key])
                        led, label = self.digital_labels[name]
                        led.setState(state)
                        label.setText("HIGH" if state else "LOW")
                        label.setStyleSheet(f"color: {'green' if state else 'black'};")
            except:
                pass
                
        # Parse interrupt count
        elif data.isdigit():
            try:
                self.int_lcd.display(int(data))
            except:
                pass
                
    # GPIO Control Functions
    def toggle_led(self, num, state):
        """Toggle LED"""
        self.send_command(f"GPIO:LED{num} {'ON' if state else 'OFF'}")
        self.led_widgets[num-1].setState(state)
        
    def toggle_relay(self, num, state):
        """Toggle relay"""
        self.send_command(f"GPIO:RELAY{num} {'ON' if state else 'OFF'}")
        self.relay_btns[num-1].setText(f"Relay {num}\n{'ON' if state else 'OFF'}")
        
    def all_leds(self, state):
        """Control all LEDs"""
        for i in range(3):
            self.led_checks[i].setChecked(state)
            
    def blink_pattern(self):
        """Blink pattern"""
        for _ in range(3):
            QTimer.singleShot(0, lambda: self.all_leds(True))
            QTimer.singleShot(500, lambda: self.all_leds(False))
            QTimer.singleShot(1000, lambda: None)  # Delay
            
    def wave_pattern(self):
        """Wave pattern"""
        for i in range(3):
            QTimer.singleShot(i * 200, lambda idx=i: self.led_checks[idx].setChecked(True))
            QTimer.singleShot(i * 200 + 500, lambda idx=i: self.led_checks[idx].setChecked(False))
            
    def chase_pattern(self):
        """Chase pattern"""
        for i in range(3):
            QTimer.singleShot(i * 300, lambda idx=i: self.toggle_single_led(idx))
            
    def toggle_single_led(self, idx):
        """Toggle single LED for patterns"""
        for i in range(3):
            self.led_checks[i].setChecked(i == idx)
            
    # PWM Control Functions
    def set_pwm(self, channel, duty):
        """Set PWM duty cycle"""
        self.send_command(f"PWM{channel}:DUTY {duty}")
        
    def set_pwm_freq(self, channel, freq):
        """Set PWM frequency"""
        self.send_command(f"PWM{channel}:FREQ {freq}")
        
    def set_pwm_preset(self, value):
        """Set PWM preset value"""
        self.pwm1_slider.setValue(value)
        self.pwm2_slider.setValue(value)
        
    # Monitoring Functions
    def toggle_monitoring(self):
        """Toggle monitoring"""
        if self.monitor_btn.isChecked():
            self.send_command("MON:START")
            self.monitor_btn.setText("Stop Monitoring")
            
            # Setup timer for periodic updates
            self.monitor_timer = QTimer()
            self.monitor_timer.timeout.connect(self.update_monitoring)
            self.monitor_timer.start(self.monitor_rate.value())
        else:
            self.send_command("MON:STOP")
            self.monitor_btn.setText("Start Monitoring")
            
            if hasattr(self, 'monitor_timer'):
                self.monitor_timer.stop()
                
    def update_monitoring(self):
        """Update monitoring data"""
        self.send_command("DIN:ALL?")
        QTimer.singleShot(50, lambda: self.send_command("AIN:ALL?"))
        
    # Data Logging Functions
    def save_log(self):
        """Save log to CSV"""
        filename, _ = QFileDialog.getSaveFileName(self, "Save Log", "", "CSV Files (*.csv)")
        if filename:
            with open(filename, 'w', newline='') as f:
                writer = csv.writer(f)
                
                # Write headers
                headers = []
                for i in range(self.data_table.columnCount()):
                    headers.append(self.data_table.horizontalHeaderItem(i).text())
                writer.writerow(headers)
                
                # Write data
                for row in range(self.data_table.rowCount()):
                    row_data = []
                    for col in range(self.data_table.columnCount()):
                        item = self.data_table.item(row, col)
                        row_data.append(item.text() if item else "")
                    writer.writerow(row_data)
                    
            QMessageBox.information(self, "Success", f"Log saved to {filename}")
            
    def clear_log(self):
        """Clear data log"""
        self.data_table.setRowCount(0)
        
    def closeEvent(self, event):
        """Handle close event"""
        if self.serial_worker.is_running:
            reply = QMessageBox.question(self, "Exit", "Disconnect and exit?",
                                        QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.serial_worker.disconnect()
                event.accept()
            else:
                event.ignore()

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()