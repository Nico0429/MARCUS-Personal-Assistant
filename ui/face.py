import sys, math, random, time
from PySide6.QtWidgets import QApplication, QWidget
from PySide6.QtGui import QPainter, QColor, QPen, QRadialGradient
from PySide6.QtCore import Qt, QTimer, QPointF, Slot, QPoint

class MarcusFace(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(400, 400)
        
        # Enable mouse tracking to detect hover movements without clicking
        self.setMouseTracking(True)
        
        self.center_point = QPointF(200.0, 200.0)
        self.color_cyan = QColor(0, 255, 255, 180)
        self.color_node_line = QColor(0, 200, 255)
        self.color_bloom = QColor(0, 100, 255, 35)
        self.color_white = QColor(255, 255, 255)
        
        self.angle = 0.0
        self.pulse = 0.0
        self.is_speaking = False 
        self.is_listening = False
        self.is_hovered = False
        self.is_thinking = False
        self.is_folded = False
        self.pre_fold_pos = None  
        self.is_shutting_down = False
        self.hover_glow = 0.0 # Interpolator for brightening
        self.cursor_pos = QPointF(-1000, -1000) # Track cursor for repulsion
        self._audio_level = 0.0 
        
        self.trigger_toggle = False  
        self.stop_toggle = False
        self._drag_active = False
        self._drag_pos = QPoint()
        
        self.current_scale = 1.0
        self.target_scale = 1.0
        
        # Spawn nodes between the two rings (Radius 27 to 46)
        self.nodes = []
        for _ in range(25): 
            a = random.uniform(0, 2 * math.pi)
            r = random.uniform(27, 46) # Increased outer bound from 42 to 46
            self.nodes.append({
                "pos": QPointF(200.0 + r * math.cos(a), 200.0 + r * math.sin(a)),
                "vec": QPointF(random.uniform(-0.4, 0.4), random.uniform(-0.4, 0.4)),
                "phase": random.uniform(0, 10)
            })

        self.launch_top_right()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.process_frame)
        self.timer.start(33) 

        from event_engine import bus
        bus.subscribe("terminal_folded", self.on_terminal_folded)
        bus.subscribe("terminal_dragged", self.on_terminal_dragged)

    def launch_top_right(self):
        screen = QApplication.primaryScreen().availableGeometry()
        
        # We increase the positive X offset and the negative Y offset 
        # to push the 400x400 invisible box further off-screen, 
        # tucking the visible center tightly into the corner.
        self.move(screen.width() - self.width() + 120, -120)

    def set_folded(self, state, terminal_pos=None):
        """Snaps the face into the left side of the terminal pill."""
        self.is_folded = state
        if state and terminal_pos:
            self.pre_fold_pos = self.pos()
            self.update_tether(terminal_pos)
        else:
            if self.pre_fold_pos:
                self.move(self.pre_fold_pos)

    def update_tether(self, terminal_pos):
        """Magnetically locks the orb to the side of the folded terminal."""
        # We keep your exact mathematical offsets (-28 and -177) 
        # but apply them relative to wherever the terminal actually is!
        self.move(terminal_pos.x() - 64, terminal_pos.y() - 177)


   # --- HOVER EVENTS ---
    def enterEvent(self, event):
        # THE FIX: Only glow if the terminal is fully open
        if not self.is_folded:
            self.is_hovered = True
            self.raise_()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.is_hovered = False
        self.cursor_pos = QPointF(-1000, -1000) # Move cursor off-screen
        super().leaveEvent(event)
    # ------------------------

    def showEvent(self, event):
        """Intercepts the window showing up to create a Pop-In animation."""
        self.current_scale = 0.0
        super().showEvent(event)
        


    def trigger_shutdown(self):
        """Creates a Pop-Out animation before killing the program."""
        self.is_shutting_down = True
        

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            pos = event.position()
            dist = math.sqrt((pos.x() - 200)**2 + (pos.y() - 200)**2)
            if dist < 80:
                self.trigger_toggle = True 

    def mousePressEvent(self, event):
        # THE FIX: Removed the 'not self.is_folded' check so you can grab it!
        if event.button() == Qt.LeftButton:
            self._drag_active = True
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
        elif event.button() == Qt.RightButton:
            self.stop_toggle = True

    def mouseMoveEvent(self, event):
        if self._drag_active:
            new_pos = event.globalPosition().toPoint() - self._drag_pos
            self.move(new_pos)
            
            # THE FIX: Tell the terminal to follow the face!
            if self.is_folded:
                from event_engine import bus
                # NOTE: If you changed the 80 or 177 in update_tether, make sure to use the exact opposite numbers here!
                bus.emit_sync("sync_terminal_pos", {"x": new_pos.x() + 64, "y": new_pos.y() + 177})
                
        self.cursor_pos = event.position()

    def mouseReleaseEvent(self, event):
        self._drag_active = False

    @Slot(bool)
    def set_speaking(self, state):
        self.is_speaking = state

    @Slot(bool)
    def set_listening(self, state):
        self.is_listening = state
        self.update()

    @Slot(float)
    def set_audio_level(self, level):
        self._audio_level = level
    
    @Slot(bool)
    def set_thinking(self, state):
        self.is_thinking = state
        self.update()

    @Slot(dict)
    def on_terminal_folded(self, data):
        state = data.get("state")
        self.is_folded = state
        if state:
            self.pre_fold_pos = self.pos()
            # Convert dictionary back to QPoint for tethering
            self.update_tether(QPoint(data["pos"]["x"], data["pos"]["y"]))
        elif self.pre_fold_pos:
            self.move(self.pre_fold_pos)

    @Slot(dict)
    def on_terminal_dragged(self, data):
        if self.is_folded:
            self.update_tether(QPoint(data["x"], data["y"]))

    def process_frame(self):

        # Scale logic
        if self.is_shutting_down:
            self.target_scale = 0.0 # Force it to shrink to nothing
        elif self.is_folded:
            self.target_scale = 0.355 # <---  Shrinks it to a tiny orb
        elif self.is_listening:
            self.target_scale = 1.1
        elif self.is_thinking:
            self.target_scale = 1.05
        elif self.is_speaking:
            self.target_scale = 1.12
        elif self.is_hovered:
            self.target_scale = 1.12 
        else:
            self.target_scale = 1.0



        # Scale interpolation (Shrinks slightly faster when shutting down)
        spd_mult = 0.3 if self.is_shutting_down else 0.2
        self.current_scale += (self.target_scale - self.current_scale) * spd_mult

        render_scale = self.current_scale
        if self.is_speaking:
            render_scale += (self._audio_level * 0.06) 
            render_scale += math.sin(time.time() * 12) * 0.01
        
        # Hover brightness interpolator
        # THE FIX: Force target_glow to 0.0 if folded, no matter where the mouse is
        if self.is_folded:
            target_glow = 0.0
        else:
            target_glow = 1.0 if self.is_hovered else 0.0
            
        self.hover_glow += (target_glow - self.hover_glow) * 0.1
        


       # Speed logic: Make movement reflect the current state
        if self.is_thinking:
            base_spd = 4.0  # Spin the rings fast while processing data
        elif self.is_listening:
            base_spd = 0.3  # Slow down to a gentle drift while waiting for your voice
        else:
            base_spd = 2.5 if self.is_hovered else 0.7 
            
        spd = base_spd + (self._audio_level * 2.5) if self.is_speaking else base_spd


        self.angle += spd
        self.pulse += 0.05 * spd
        
        # Node Physics with Repulsion
        for n in self.nodes:
            # Repulsion from cursor (Scaled down to 30px since the area is tighter)
            dx_c = n["pos"].x() - self.cursor_pos.x()
            dy_c = n["pos"].y() - self.cursor_pos.y()
            dist_c_sq = dx_c**2 + dy_c**2
            
            if dist_c_sq < 900 and dist_c_sq > 0: # 30 pixels repel radius
                dist_c = math.sqrt(dist_c_sq)
                force = (30 - dist_c) * 0.05 # Gentle localized push
                n["pos"] += QPointF((dx_c/dist_c) * force, (dy_c/dist_c) * force)

            # Normal drifting
            n["pos"] += n["vec"]
            dx, dy = n["pos"].x() - 200.0, n["pos"].y() - 200.0
            dist_sq = dx*dx + dy*dy
            
            # Constrain strictly between the inner and outer rings
            # 27^2 = 729 (Inner bound), 46^2 = 2116 (Outer bound)
            if dist_sq > 2116 or dist_sq < 729: 
                # Clean bounce reflection
                n["vec"] = QPointF(-n["vec"].x(), -n["vec"].y())
                n["pos"] += n["vec"] * 2.0
            
        self._final_scale = render_scale
        
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.translate(self.center_point)
        scale = getattr(self, '_final_scale', 1.0)
        painter.scale(scale, scale)
        painter.translate(-self.center_point)

        p_val = (math.sin(self.pulse) + 1.0) / 2.0
        
   # --- STATE COLOR LOGIC (Crisp Light Blue Palette) ---
        if self.is_listening:
            # AZURE CYAN (Original)
            ring_color = QColor(0, 200, 255, 255)
            bloom_color = QColor(0, 150, 255, 70)
            node_base_color = QColor(0, 220, 255)
            core_inner = QColor(150, 240, 255)
            
        elif self.is_thinking:
            # ICE CYAN (Original)
            ring_color = QColor(80, 255, 255, 255)
            bloom_color = QColor(50, 255, 255, 90)
            node_base_color = QColor(150, 255, 255) 
            core_inner = Qt.white
            
        else:
            # IDLE NEON ICE BLUE (0, 251, 255)
            alpha_cyan = int(200 + (self.hover_glow * 55))
            ring_color = QColor(0, 251, 255, alpha_cyan)
            bloom_color = QColor(0, 230, 255, 60) # Kept slightly darker for a better glow contrast
            node_base_color = QColor(0, 251, 255)
            core_inner = Qt.white

        # Background bloom
        b_rad = 110.0 + (p_val * 15.0)
        grad = QRadialGradient(self.center_point, b_rad)
        grad.setColorAt(0, bloom_color)           # <-- Applies the bloom_color!
        grad.setColorAt(1, Qt.transparent)
        painter.setBrush(grad)
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(self.center_point, b_rad, b_rad)

    
        # Web Lines & Nodes
        for i, n in enumerate(self.nodes):
            
            # 1. Draw the explicit Node dot
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(node_base_color.red(), node_base_color.green(), node_base_color.blue(), 200)) # <-- UPDATE
            painter.drawEllipse(n["pos"], 0.5, 0.5) 
            
            # 2. Draw the Firing Edges with Glow Effect
            for other in self.nodes[i+1:]:
                dist_sq = (n["pos"].x()-other["pos"].x())**2 + (n["pos"].y()-other["pos"].y())**2
                
                if dist_sq < 484: 
                    falloff = 1.0 - (dist_sq / 484.0)
                    
                    alpha_core = int(220 * (falloff * falloff)) 
                    alpha_glow = int(120 * falloff) 
                    
                    # --- DRAW GLOW ---
                    glow_color = QColor(node_base_color) # <-- UPDATE
                    glow_color.setAlpha(alpha_glow)
                    painter.setPen(QPen(glow_color, 0.5)) 
                    painter.drawLine(n["pos"], other["pos"])
                    
                    # --- DRAW CORE ---
                    core_color = QColor(node_base_color) # <-- UPDATE
                    core_color.setAlpha(alpha_core)
                    painter.setPen(QPen(core_color, 0.2)) 
                    painter.drawLine(n["pos"], other["pos"])

        # Main Outer Ring (Pushed out to 50px to fit nodes, increased to 14 partitions)
        painter.setPen(QPen(ring_color, 1.5))
        ir = 40.0 + (p_val * 2.0)
        for i in range(14):
            # 360 / 14 = ~25.7 degrees spacing
            painter.drawArc(200-ir, 200-ir, ir*2, ir*2, int((self.angle + i*(360/14))*16), 12*16)

        # Inner Ring (Increased to 10 partitions)
        ir_inner = 22.0 + (p_val * 2.0) 
        painter.setPen(QPen(ring_color, 1.0))
        for i in range(10):
            # 360 / 10 = 36 degrees spacing
            painter.drawArc(200-ir_inner, 200-ir_inner, ir_inner*2, ir_inner*2, int((-self.angle * 1.5 + i*36)*16), 20*16)

        # Core Orb
        cr = 15.0 + (p_val * 5.0)
        c_grad = QRadialGradient(self.center_point, cr)
        core_inner = Qt.white if not self.is_listening else QColor(255, 200, 200)
        c_grad.setColorAt(0, core_inner); c_grad.setColorAt(0.6, ring_color); c_grad.setColorAt(1, Qt.transparent)
        painter.setBrush(c_grad); painter.setPen(Qt.NoPen)
        painter.drawEllipse(self.center_point, cr, cr)