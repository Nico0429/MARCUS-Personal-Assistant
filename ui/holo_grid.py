from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, QPoint, QRect
from PySide6.QtGui import QPainter, QPen, QColor, QGuiApplication, QMouseEvent
from event_engine import bus

# ==========================================
# 1. THE HOLOGRAPHIC VISUAL OVERLAY
# ==========================================
class HoloGridOverlay(QWidget):
    def __init__(self, grid_size=40):
        super().__init__()
        self.grid_size = grid_size
        
        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.WindowTransparentForInput)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # MULTI-MONITOR FIX: Combine all screens into one massive virtual bounding box
        screens = QGuiApplication.screens()
        virtual_rect = screens[0].geometry()
        for s in screens[1:]:
            virtual_rect = virtual_rect.united(s.geometry())
            
        self.setGeometry(virtual_rect)
        self.hide()
        
        bus.subscribe("holo_grid_toggle", self._on_toggle)
        
    def _on_toggle(self, data):
        if data.get("show"): self.show()
        else: self.hide()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        pen = QPen(QColor(0, 255, 255, 30))
        pen.setWidth(1)
        painter.setPen(pen)
        
        for x in range(0, self.width(), self.grid_size):
            painter.drawLine(x, 0, x, self.height())
            
        for y in range(0, self.height(), self.grid_size):
            painter.drawLine(0, y, self.width(), y)

# ==========================================
# 2. THE UNIVERSAL MARCUS WINDOW
# ==========================================
class MarcusBaseWindow(QWidget):
    GRID_SIZE = 40
    _snappable_windows = []

    # GHOST PADDING FIX: Added clamp_margin
    def __init__(self, ignore_collisions=False, clamp_margin=0):
        super().__init__()
        
        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        self._drag_active = False
        self._drag_pos = QPoint()
        self._last_good_pos = QPoint()
        self.ignore_collisions = ignore_collisions
        self.clamp_margin = clamp_margin  # Allows invisible borders to bleed off-screen
        
        if self not in MarcusBaseWindow._snappable_windows:
            MarcusBaseWindow._snappable_windows.append(self)

    def setFixedSize(self, width, height):
        grid_w = round(width / self.GRID_SIZE) * self.GRID_SIZE
        grid_h = round(height / self.GRID_SIZE) * self.GRID_SIZE
        super().setFixedSize(grid_w, grid_h)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self._drag_active = True
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self._last_good_pos = self.pos()
            
            self.setCursor(Qt.ClosedHandCursor)
            bus.emit_sync("holo_grid_toggle", {"show": True})
            event.accept()

    def _get_active_screen_bounds(self, global_pos):
        """Finds which monitor the mouse is currently on."""
        screen = QGuiApplication.screenAt(global_pos)
        if not screen:
            screen = QGuiApplication.primaryScreen()
        return screen.geometry()

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._drag_active:
            raw_pos = event.globalPosition().toPoint() - self._drag_pos
            
            # MULTI-MONITOR FIX: Dynamically track active screen
            screen_geo = self._get_active_screen_bounds(event.globalPosition().toPoint())
            
            # GHOST PADDING FIX: Apply the margin to the edges
            min_x = screen_geo.left() - self.clamp_margin
            min_y = screen_geo.top() - self.clamp_margin
            max_x = screen_geo.right() - self.width() + self.clamp_margin
            max_y = screen_geo.bottom() - self.height() + self.clamp_margin
            
            clamped_x = max(min_x, min(raw_pos.x(), max_x))
            clamped_y = max(min_y, min(raw_pos.y(), max_y))
            
            self.move(clamped_x, clamped_y)
            event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self._drag_active = False
            self.setCursor(Qt.PointingHandCursor)
            bus.emit_sync("holo_grid_toggle", {"show": False})
            
            # 1. Snap to Grid
            current_pos = self.pos()
            snapped_x = round(current_pos.x() / self.GRID_SIZE) * self.GRID_SIZE
            snapped_y = round(current_pos.y() / self.GRID_SIZE) * self.GRID_SIZE
            
            # 2. Strict Screen Bounding on Release (with margins & multi-monitor)
            screen_geo = self._get_active_screen_bounds(event.globalPosition().toPoint())
            min_x = screen_geo.left() - self.clamp_margin
            min_y = screen_geo.top() - self.clamp_margin
            max_x = screen_geo.right() - self.width() + self.clamp_margin
            max_y = screen_geo.bottom() - self.height() + self.clamp_margin
            
            snapped_x = max(min_x, min(snapped_x, max_x))
            snapped_y = max(min_y, min(snapped_y, max_y))
            
            # 3. Intelligent Collision System
            target_rect = QRect(snapped_x, snapped_y, self.width(), self.height())
            collision_detected = False
            
            if not self.ignore_collisions:
                for w in MarcusBaseWindow._snappable_windows:
                    if w is self or not w.isVisible() or w.ignore_collisions or w.windowOpacity() == 0.0:
                        continue
                    if target_rect.intersects(w.geometry()):
                        collision_detected = True
                        break
            
            if collision_detected:
                self.move(self._last_good_pos)
            else:
                self.move(snapped_x, snapped_y)
                
            event.accept()