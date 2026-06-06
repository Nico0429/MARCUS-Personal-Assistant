from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton
from PySide6.QtCore import Qt, QPoint, QTimer
from PySide6.QtGui import QFont, QGuiApplication, QMouseEvent, QCursor
from qasync import asyncSlot
from event_engine import bus
from ui.holo_grid import MarcusBaseWindow

class TimerWindow(MarcusBaseWindow):
    def __init__(self):
        super().__init__()
        self.setFixedSize(300, 140) # Increased height slightly to fit buttons
        self.setCursor(Qt.PointingHandCursor)
        
        screen = QGuiApplication.primaryScreen().geometry()
        self.move((screen.width() - self.width()) // 2, 40)

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

       # MAIN FRAME
        self.frame = QFrame()
        self.frame.setObjectName("HudFrame")
        
        self.frame_layout = QVBoxLayout(self.frame)
        self.frame_layout.setContentsMargins(10, 10, 10, 10)
        self.layout.addWidget(self.frame)

        # Task Name Label
        self.task_label = QLabel("[ POMODORO ACTIVE ]")
        self.task_label.setAlignment(Qt.AlignCenter)
        self.task_label.setObjectName("CyanSub")
        self.frame_layout.addWidget(self.task_label)

        # Time Label
        self.time_label = QLabel("25:00")
        self.time_label.setAlignment(Qt.AlignCenter)
        self.time_label.setObjectName("TimerText")
        self.frame_layout.addWidget(self.time_label)

        # --- THE NEW BUTTONS ---
        self.btn_layout = QHBoxLayout()
        self.btn_layout.setAlignment(Qt.AlignCenter)
        self.btn_layout.setSpacing(15)

        self.pause_btn = QPushButton("PAUSE")
        self.pause_btn.setFixedSize(80, 26)
        self.pause_btn.setCursor(Qt.PointingHandCursor)
        self.pause_btn.clicked.connect(self._on_pause_clicked)
        self.btn_layout.addWidget(self.pause_btn)

        self.stop_btn = QPushButton("CANCEL")
        self.stop_btn.setFixedSize(80, 26)
        self.stop_btn.setCursor(Qt.PointingHandCursor)
        self.stop_btn.setProperty("cssClass", "alert")
        self.stop_btn.clicked.connect(self._on_stop_clicked)
        self.btn_layout.addWidget(self.stop_btn)

        self.frame_layout.addLayout(self.btn_layout)
        # -----------------------

        self.hide()
        self.is_paused = False
        
        bus.subscribe("timer_ui_control", self.on_timer_update)



    # --- BUTTON HANDLERS ---
    def _on_pause_clicked(self):
        self.is_paused = not self.is_paused
        self.pause_btn.setText("RESUME" if self.is_paused else "PAUSE")
        bus.emit_sync("timer_manual_action", {"action": "pause"})

    def _on_stop_clicked(self):
        bus.emit_sync("timer_manual_action", {"action": "stop"})

   

    @asyncSlot(dict)
    async def on_timer_update(self, data):
        action = data.get("action")
        if action == "show":
            self.task_label.setText(f"[ FOCUS: {data.get('task', 'TASK').upper()} ]")
            self.time_label.setText(data.get("time_str", "00:00"))
            self.is_paused = False
            self.pause_btn.setText("PAUSE")
            self.fade_in()
        elif action == "update":
            self.time_label.setText(data.get("time_str", "00:00"))
        elif action == "hide":
            self.fade_out()