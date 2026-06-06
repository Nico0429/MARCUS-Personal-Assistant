import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QFrame, QHBoxLayout, 
                               QPushButton, QLabel)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtCore import QUrl, Qt, QPoint, QTimer
from PySide6.QtGui import QMouseEvent, QFont, QGuiApplication
from ui.holo_grid import MarcusBaseWindow

class GraphWindow(MarcusBaseWindow):
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("MARCUS - Neural Matrix")
        self.setFixedSize(850, 650)

        # Ghost Window Setup
        self.setWindowOpacity(0.0)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.show() 

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        self.hud_frame = QFrame()
        self.hud_frame.setObjectName("HudFrame")
        self.hud_layout = QVBoxLayout(self.hud_frame)
        self.hud_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.addWidget(self.hud_frame)

        self.header_layout = QHBoxLayout()
        
        self.title_label = QLabel(":: NEURAL MATRIX UPLINK ::")
        self.title_label.setObjectName("HeaderCyan")
        self.header_layout.addWidget(self.title_label)
        self.header_layout.addStretch()

        self.close_btn = QPushButton("[X]")
        self.close_btn.setFixedSize(30, 25)
        self.close_btn.setProperty("cssClass", "alert")
        self.close_btn.setFont(QFont("Consolas", 9, QFont.Bold))


        self.close_btn.clicked.connect(self.conceal) 
        self.header_layout.addWidget(self.close_btn)
        
        self.hud_layout.addLayout(self.header_layout)

        self.browser = QWebEngineView()
        self.browser.setStyleSheet("background: transparent; border: none;")
        self.browser.page().setBackgroundColor(Qt.transparent)
        self.hud_layout.addWidget(self.browser)

        
        # --- THE FIX: LAZY LOADING FLAG ---
        self._needs_refresh = False

    


    def conceal(self):
        """Fades the window out and lets the user click through it."""
        self.setWindowOpacity(0.0)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.clearFocus()

    def reveal(self):
        """Centers the window, makes it solid, and captures mouse events again."""
        screen = QGuiApplication.primaryScreen().geometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)
        
        # Restore GPU visibility
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self.setWindowOpacity(1.0)
        self.raise_()
        
        # --- THE FIX: Safe Rendering ---
        # Now that the window is solid and the GPU has a mailbox, render the graph
        if self._needs_refresh:
            self.refresh_graph()

    def refresh_graph(self):
        # If the window is a ghost, DO NOT try to use the GPU. Flag it for later.
        if self.windowOpacity() == 0.0:
            self._needs_refresh = True
            return
            
        html_path = os.path.abspath("brain_map.html")
        if os.path.exists(html_path):
            self.browser.setUrl(QUrl.fromLocalFile(html_path))
            self._needs_refresh = False

   