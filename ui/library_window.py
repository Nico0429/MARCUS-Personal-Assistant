import asyncio
import os
import threading
import time
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTextBrowser, 
                               QLineEdit, QPushButton, QFrame, QLabel)
from PySide6.QtCore import Signal, Qt, QTimer, QMetaObject
from PySide6.QtGui import QFont, QTextCursor, QCloseEvent, QIcon, QMouseEvent, QPixmap
from qasync import asyncSlot 

from event_engine import bus 

class LibraryWindow(QWidget):
    header_signal = Signal(str, str) 
    stream_signal = Signal(str)

    show_news_signal = Signal(str, str)
    hide_news_signal = Signal()

    def __init__(self):
        super().__init__()
        
        self.active_stream_id = 0

        # --- 1. JARVIS AESTHETICS ---
        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowTitle("MARCUS - Neural Terminal")
        self.setWindowIcon(QIcon("marcus_icon.png")) 
        self.setFixedSize(450, 600)

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)

       # HUD Frame and Layout
        self.hud_frame = QFrame()
        self.hud_frame.setObjectName("HudFrame")
        self.hud_layout = QVBoxLayout(self.hud_frame)
        self.hud_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.addWidget(self.hud_frame)

        # Header Buttons
        self.header_layout = QHBoxLayout()
        self.header_layout.setSpacing(5)

        # 1. FOLD BUTTON
        self.fold_btn = QPushButton("[-]")
        self.fold_btn.setFixedSize(30, 25)
        self.fold_btn.setCursor(Qt.PointingHandCursor)
        self.fold_btn.clicked.connect(self.toggle_fold)
        self.fold_btn.setProperty("cssClass", "os_text_icon")
        self.fold_btn.setFont(QFont("Consolas", 10, QFont.Bold))
        self.header_layout.addWidget(self.fold_btn)

        # 2. NATIVE OS MIC BUTTON
        self.mic_btn = QPushButton("\uE720")
        self.mic_btn.setCheckable(True)
        self.mic_btn.setFixedSize(30, 25)
        self.mic_btn.setCursor(Qt.PointingHandCursor)
        self.mic_btn.clicked.connect(self.update_mic_style)
        self.mic_btn.setProperty("cssClass", "os_icon")
        self.header_layout.addWidget(self.mic_btn)

        # 3. NATIVE OS SPEAKER BUTTON
        self.mute_btn = QPushButton("\uE767")
        self.mute_btn.setCheckable(True)
        self.mute_btn.setFixedSize(30, 25)
        self.mute_btn.setCursor(Qt.PointingHandCursor)
        self.mute_btn.clicked.connect(self.update_mute_style)
        self.mute_btn.setProperty("cssClass", "os_icon")
        self.header_layout.addWidget(self.mute_btn)

        self.header_layout.addStretch()
        self.hud_layout.addLayout(self.header_layout)

        # --- NEWS HOLOGRAPHIC DISPLAY (Hidden by default) ---
        self.news_image_label = QLabel()
        self.news_image_label.setAlignment(Qt.AlignCenter)
        self.news_image_label.setStyleSheet("QLabel { background: transparent; border-radius: 8px; }")
        self.news_image_label.hide() # Keep it invisible until needed
        self.hud_layout.addWidget(self.news_image_label)
        # ----------------------------------------------------

        

        # Chat Log
        self.chat_log = QTextBrowser()
        self.hud_layout.addWidget(self.chat_log)

        # --- STATIC SYSTEM BANNER ---
        banner_html = (
            '<span style="color: #00fbff;">:: SYSTEMS OPERATIONAL ::</span><br>'
            '<span style="color: #aaaaaa;">Type <b>/help</b> for system protocols and manual overrides.</span><br><br>'
        )
        self.chat_log.insertHtml(banner_html)
        # -------------------------------------

        # Input Field
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Awaiting input...")

        self.input_field.returnPressed.connect(self._on_text_entered)
        self.hud_layout.addWidget(self.input_field)

        # Core UI Signals
        self.header_signal.connect(self._insert_header)
        self.stream_signal.connect(self._insert_chunk)

        self.show_news_signal.connect(self._render_news_ui)
        self.hide_news_signal.connect(self._hide_news_ui)

        # Subscriptions: Listen to the Async Bus
        bus.subscribe("marcus_speaking", self.on_marcus_speaking)
        bus.subscribe("user_spoken_text", self.on_user_spoken_text)

        bus.subscribe("show_news_ui", self.on_show_news)
        bus.subscribe("close_news_ui", self.on_close_news)

        bus.subscribe("sync_mute_state", self.on_sync_mute_state)
        bus.subscribe("sync_mic_state", self.on_sync_mic_state)

        bus.subscribe("sync_terminal_pos", self._on_sync_pos)

        # State and Positioning
        self.old_pos = None
        self.is_folded = False
        self.normal_height = 600
        self.pre_fold_pos = None
        self.move(10, 10)

        self._drag_active = False
        from PySide6.QtCore import QPoint 
        self._drag_pos = QPoint()

     

    # --- ASYNC EVENT HANDLERS ---
    @asyncSlot(dict)
    async def on_marcus_speaking(self, data):
        """Triggered when the brain/voice module broadcasts speech data."""
        self.stream_message("M.A.R.C.U.S. ", data.get("text", ""))

    @asyncSlot(str)
    async def on_user_spoken_text(self, text):
        """Triggered when the microphone loop transcribes your voice."""
        self.log_message("You", text)

    @asyncSlot(dict)
    async def on_sync_mute_state(self, data):
        """Caught when Marcus mutes himself (e.g., Deep Work macro)."""
        is_muted = data.get("muted", False)
        
        if self.mute_btn.isChecked() != is_muted:
            self.mute_btn.setChecked(is_muted)
            self.mute_btn.setText("\uE74F" if is_muted else "\uE767") 
            
            # Apply the new CSS property and force Qt to refresh the visual state
            self.mute_btn.setProperty("cssClass", "os_icon_alert" if is_muted else "os_icon")
            self.mute_btn.style().unpolish(self.mute_btn)
            self.mute_btn.style().polish(self.mute_btn)


    @asyncSlot(dict)
    async def on_sync_mic_state(self, data):
        """Caught when Marcus is forced to drop the mic feed."""
        is_muted = data.get("muted", False)
        
        if self.mic_btn.isChecked() != is_muted:
            self.mic_btn.setChecked(is_muted)
            self.mic_btn.setText("\uF12E" if is_muted else "\uE720") 
            
            # Apply the red alert class and refresh the UI
            self.mic_btn.setProperty("cssClass", "os_icon_alert" if is_muted else "os_icon")
            self.mic_btn.style().unpolish(self.mic_btn)
            self.mic_btn.style().polish(self.mic_btn)

    # --- NEWS UI ASYNC HANDLERS ---
    @asyncSlot(dict)
    async def on_show_news(self, data):
        """Caught from the event bus when Marcus starts reading a news article."""
        title = data.get("title", "")
        image_path = data.get("image", "")
        self.show_news_signal.emit(title, image_path)

    @asyncSlot()
    async def on_close_news(self):
        """Caught from the event bus when the news is finished."""
        self.hide_news_signal.emit()

    # --- NEWS UI SYNC METHODS (Qt Thread Safe) ---
    def _render_news_ui(self, title, image_path):
        """Renders the image into the HUD."""
        if os.path.exists(image_path):
            pixmap = QPixmap(image_path)
            # Scale the image to fit perfectly inside your 450px wide window
            pixmap = pixmap.scaled(400, 220, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.news_image_label.setPixmap(pixmap)
            
            # <-- Only show the image if the terminal is currently open
            if not self.is_folded:
                self.news_image_label.show()
        else:
            self.news_image_label.hide()

    def _hide_news_ui(self):
        """Clears and hides the news display."""
        self.news_image_label.clear()
        self.news_image_label.hide()

    def _on_text_entered(self):
        text = self.input_field.text().strip()
        if not text:
            return
            
        self.input_field.clear() # Clear the box
        
        # Bridge the UI action to the Async Brain
        bus.emit_sync("manual_text_entered", text)

    # --- UI METHODS (Synchronous) ---


    def _on_sync_pos(self, data):
        """Forces the terminal to follow the face if grabbed by the orb."""
        if self.is_folded:
            self.move(data["x"], data["y"])
            
    def toggle_fold(self):
        self.is_folded = not self.is_folded
        if self.is_folded:
            self.pre_fold_pos = self.pos()
            self.chat_log.hide()
            self.input_field.hide()
            self.news_image_label.hide()
            self.fold_btn.setText("[+]")
            self.setFixedSize(160, 45)
            
            bus.emit_sync("terminal_folded", {"state": True, "pos": {"x": self.pos().x(), "y": self.pos().y()}})
        else:
            self.setMinimumSize(0, 0)
            self.setMaximumSize(16777215, 16777215)
            self.chat_log.show()
            self.input_field.show()
            if self.news_image_label.pixmap() and not self.news_image_label.pixmap().isNull():
                self.news_image_label.show()
            self.fold_btn.setText("[-]")
            self.setFixedSize(450, self.normal_height) 
            
            bus.emit_sync("terminal_folded", {"state": False})

    def log_message(self, sender, text):
        self.header_signal.emit(sender, text + "\n\n")

    def stream_message(self, sender, text):
        # 1. Increment ID to kill any existing typewriter threads
        self.active_stream_id += 1 
        my_id = self.active_stream_id

        # 2. Add a clean break in the UI
        self.header_signal.emit(f"\n[{sender}]", "") 

        def _run():
            time.sleep(0.1) 
            for char in text:
                if my_id != self.active_stream_id:
                    return 
                
                try:
                    self.stream_signal.emit(char)
                except Exception:
                    return 
                
                time.sleep(0.015) 
                
            if my_id == self.active_stream_id:
                try:
                    self.stream_signal.emit("\n")
                except:
                    pass

        threading.Thread(target=_run, daemon=True).start()

    # --- MOUSE DRAG EVENTS ---
    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self._drag_active = True
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._drag_active:
            new_pos = event.globalPosition().toPoint() - self._drag_pos
            self.move(new_pos)
            
            if self.is_folded:
                bus.emit_sync("terminal_dragged", {"x": new_pos.x(), "y": new_pos.y()})
                
            event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self._drag_active = False
            event.accept()

    def update_mute_style(self):
        state = self.mute_btn.isChecked()
        self.mute_btn.setText("\uE74F" if state else "\uE767")
        
        # Dynamic theme refresher protocol
        self.mute_btn.setProperty("cssClass", "os_icon_alert" if state else "os_icon")
        self.mute_btn.style().unpolish(self.mute_btn)
        self.mute_btn.style().polish(self.mute_btn)
        
        bus.emit_sync("sync_mute_state", {"muted": state})

    def update_mic_style(self):
        state = self.mic_btn.isChecked()
        self.mic_btn.setText("\uF12E" if state else "\uE720")
        
        # Dynamic theme refresher protocol
        self.mic_btn.setProperty("cssClass", "os_icon_alert" if state else "os_icon")
        self.mic_btn.style().unpolish(self.mic_btn)
        self.mic_btn.style().polish(self.mic_btn)
        
        bus.emit_sync("mic_mute_control", {"muted": state})

    def _insert_header(self, sender, text):
        cursor = self.chat_log.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.chat_log.setTextCursor(cursor)
        clean_sender = sender.replace("\n", "").replace("[", "").replace("]", "")
        color = "#00fbff" if clean_sender == "M.A.R.C.U.S. " else "#aaaaaa"
        self.chat_log.insertPlainText("\n\n")
        self.chat_log.insertHtml(f'<span style="color: {color};"><b>{clean_sender}:</b></span> ')
        if text: 
            self.chat_log.insertPlainText(text)

    def _insert_chunk(self, chunk):
        cursor = self.chat_log.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.chat_log.setTextCursor(cursor)
        self.chat_log.insertPlainText(chunk)
        self.chat_log.ensureCursorVisible()

    def closeEvent(self, event: QCloseEvent):
        asyncio.create_task(bus.emit("terminal_closed"))
        event.accept()

  