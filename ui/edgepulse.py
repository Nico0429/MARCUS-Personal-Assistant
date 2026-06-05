from PySide6.QtCore import QPropertyAnimation, QEasingCurve, Qt
from PySide6.QtWidgets import QApplication, QWidget
from PySide6.QtGui import QPainter, QColor, QRadialGradient
import math

class EdgePulseOverlay(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.FramelessWindowHint | 
            Qt.WindowStaysOnTopHint | 
            Qt.WindowTransparentForInput | 
            Qt.WindowDoesNotAcceptFocus |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        screen_geo = QApplication.primaryScreen().geometry()
        self.setGeometry(screen_geo)
        
        # Start completely invisible
        self.setWindowOpacity(0.0)

        # THE FIX: We animate Qt's built-in 'windowOpacity' property.
        # This offloads the fade effect directly to the GPU compositor.
        self.anim = QPropertyAnimation(self, b"windowOpacity")
        self.anim.setDuration(3000) 
        
        self.anim.setStartValue(0.0)
        self.anim.setKeyValueAt(0.2, 0.6) # Peak opacity at 20%
        self.anim.setKeyValueAt(0.7, 0.6) # Hold until 70%
        self.anim.setEndValue(0.0)
        
        self.anim.setEasingCurve(QEasingCurve.InOutQuad)

    def start(self):
        self.show()
        self.anim.start()

    def paintEvent(self, event):
        # We only draw this static gradient once. 
        # The GPU handles the fading, so no CPU math is required here.
        painter = QPainter(self)
        
        r = self.rect()
        center = r.center()
        
        dist_x = float(center.x())
        dist_y = float(center.y())
        max_radius = math.sqrt(dist_x**2 + dist_y**2)

        grad = QRadialGradient(float(r.width())/2.0, float(r.height())/2.0, max_radius)

        # --- UPDATED TO RGB(0, 251, 255) ---
        grad.setColorAt(1.0, QColor(0, 251, 255, 255)) 
        grad.setColorAt(0.95, QColor(0, 251, 255, 128)) 
        grad.setColorAt(0.85, Qt.transparent) 
        grad.setColorAt(0.0, Qt.transparent)
        # -----------------------------------

        painter.setBrush(grad)
        painter.setPen(Qt.NoPen)
        painter.drawRect(r)