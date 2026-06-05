from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton
from PySide6.QtCore import Qt, QPoint, QTimer
from PySide6.QtGui import QGuiApplication, QMouseEvent
from PySide6.QtGui import QFont 
from event_engine import bus
from qasync import asyncSlot

class MediaWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(360, 130) 
        self.setCursor(Qt.PointingHandCursor)
        
        screen = QGuiApplication.primaryScreen().geometry()
        self.move((screen.width() - self.width()) // 2, 200)

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        # MAIN FRAME
        self.frame = QFrame()
        self.frame.setObjectName("HudFrame")
        
       # --- THE NATIVE WINDOWS CLOSE BUTTON ---
        self.close_btn = QPushButton("[X]", self.frame)
        self.close_btn.setGeometry(325, 5, 30, 25) # Shifted slightly left and made wider to fit brackets
        self.close_btn.setCursor(Qt.PointingHandCursor)
        self.close_btn.setProperty("cssClass", "alert")

        self.close_btn.setFont(QFont("Consolas", 9, QFont.Bold))

        self.close_btn.clicked.connect(lambda: bus.emit_sync("media_manual_action", {"action": "close_ui"}))

        # We add extra right margin (25) so the text doesn't overlap the X
        self.frame_layout = QHBoxLayout(self.frame)
        self.frame_layout.setContentsMargins(15, 10, 25, 10) 
        self.frame_layout.setSpacing(15)
        self.layout.addWidget(self.frame)

        # --- LEFT SIDE: ALBUM ART PLACEHOLDER ---
        self.art_label = QLabel("♫")
        self.art_label.setFixedSize(70, 70)
        self.art_label.setAlignment(Qt.AlignCenter)
        self.art_label.setStyleSheet("""
            QLabel {
                background-color: rgba(0, 255, 204, 20);
                color: #00ffcc;
                border: 1px solid rgba(0, 255, 204, 100);
                border-radius: 6px;
                font-size: 36px;
            }
        """)
        self.frame_layout.addWidget(self.art_label)

        # --- RIGHT SIDE: TEXT AND BUTTONS ---
        self.right_layout = QVBoxLayout()
        self.right_layout.setSpacing(2)
        self.right_layout.setAlignment(Qt.AlignVCenter)

        # 1. Track Title
        self.title_label = QLabel("[ SYSTEM MEDIA ]")
        self.title_label.setWordWrap(True)
        self.title_label.setObjectName("WhiteTitle")
        self.right_layout.addWidget(self.title_label)

        # 2. Artist Subtitle
        self.artist_label = QLabel("Unknown Artist")
        self.artist_label.setObjectName("CyanSub")
        self.right_layout.addWidget(self.artist_label)


        # 3. Buttons HBox
        self.btn_layout = QHBoxLayout()
        self.btn_layout.setContentsMargins(0, 5, 0, 0)
        self.btn_layout.setSpacing(10)
        self.btn_layout.setAlignment(Qt.AlignLeft)
        
        self.prev_btn = QPushButton("\uE892")
        self.prev_btn.setProperty("cssClass", "icon_only")
        self.prev_btn.setFixedSize(35, 25)
        self.prev_btn.setCursor(Qt.PointingHandCursor)
        self.prev_btn.clicked.connect(lambda: bus.emit_sync("media_manual_action", {"action": "prev"}))
        
        self.play_btn = QPushButton("\uE768")
        self.play_btn.setProperty("cssClass", "icon_only")
        self.play_btn.setFixedSize(45, 25)
        self.play_btn.setCursor(Qt.PointingHandCursor)
        self.play_btn.clicked.connect(lambda: bus.emit_sync("media_manual_action", {"action": "playpause"}))
        
        self.next_btn = QPushButton("\uE893")
        self.next_btn.setProperty("cssClass", "icon_only")
        self.next_btn.setFixedSize(35, 25)
        self.next_btn.setCursor(Qt.PointingHandCursor)
        self.next_btn.clicked.connect(lambda: bus.emit_sync("media_manual_action", {"action": "next"}))
        
        self.btn_layout.addWidget(self.prev_btn)
        self.btn_layout.addWidget(self.play_btn)
        self.btn_layout.addWidget(self.next_btn)
        
        self.right_layout.addLayout(self.btn_layout)
        self.frame_layout.addLayout(self.right_layout)

        self.hide()
        self._drag_active = False
        self._drag_pos = QPoint()
        
        bus.subscribe("media_ui_control", self.on_media_update)



    # --- DRAG LOGIC ---
    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self._drag_active = True
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._drag_active:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self._drag_active = False
            event.accept()

    # --- UPDATE LOGIC ---
    @asyncSlot(dict)
    async def on_media_update(self, data):
        action = data.get("action")
        track_data = data.get("track", {"title": "[ SYSTEM MEDIA ]", "artist": "Unknown", "is_playing": False})
        
        if action == "show" or action == "update":
            title = track_data.get("title", "Unknown")
            artist = track_data.get("artist", "Unknown")
            is_playing = track_data.get("is_playing", False)
            
            if len(title) > 30: title = title[:27] + "..."
            if len(artist) > 35: artist = artist[:32] + "..."
            
            self.title_label.setText(title.upper())
            self.artist_label.setText(artist.upper())
            
            # --- DYNAMIC ICON TOGGLE ---
            if is_playing:
                self.play_btn.setText("\uE769") # Native Pause Icon
            else:
                self.play_btn.setText("\uE768") # Native Play Icon
            
            if action == "show":
                self.show()
                
        elif action == "hide":
            self.hide()