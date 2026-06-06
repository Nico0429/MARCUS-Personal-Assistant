from PySide6.QtCore import QObject, QTimer
from qasync import asyncSlot
from event_engine import bus

class UIManager(QObject):
    def __init__(self, face, library, graph, media, timer, grid):
        super().__init__()
        self.face = face
        self.library = library
        self.graph = graph
        self.media = media
        self.timer = timer
        self.grid = grid
        
        self._is_ghost_mode = False
        self._was_graph_open = False
        self._was_media_open = False
        self._was_timer_open = False

        # The Master Z-Order Dictator (Runs every 1.5 seconds)
        self.master_z_timer = QTimer(self)
        self.master_z_timer.timeout.connect(self.enforce_global_hierarchy)
        self.master_z_timer.start(1500)

        # Master Subscriptions
        bus.subscribe("toggle_ui_visibility", self.on_toggle_visibility)

    def enforce_global_hierarchy(self):
        """Strictly orders windows from bottom to top so they never overlap incorrectly."""
        if self._is_ghost_mode:
            return

        # 1. Bottom Layer: Graph (Only if solid)
        if self.graph and self.graph.windowOpacity() > 0.0:
            self.graph.raise_()
            
        # 2. Middle Layer: Active Utilities
        if self.media and self.media.isVisible():
            self.media.raise_()
        if self.timer and self.timer.isVisible():
            self.timer.raise_()
            
        # 3. Top Layer: Terminal
        if self.library and self.library.isVisible():
            self.library.raise_()
            
        # 4. Absolute Peak: The Face Orb
        if self.face and self.face.isVisible():
            self.face.raise_()

    @asyncSlot(dict)
    async def on_toggle_visibility(self, data):
        self._is_ghost_mode = not self._is_ghost_mode
        
        if self._is_ghost_mode:
            # 1. Hide Core
            if self.face: self.face.hide()
            if self.library: self.library.fade_out()
            
            # --- SAFETY CATCH: Force hide the grid if it was somehow open ---
            if self.grid: self.grid.hide()
            
            # 2. Track & Hide Active Peripherals
            if self.graph and self.graph.windowOpacity() > 0:
                self._was_graph_open = True
                self.graph.fade_out()
            else:
                self._was_graph_open = False

            if self.media and self.media.isVisible():
                self._was_media_open = True
                self.media.fade_out()
            else:
                self._was_media_open = False

            if self.timer and self.timer.isVisible():
                self._was_timer_open = True
                self.timer.fade_out()
            else:
                self._was_timer_open = False
                
        else:
            # 1. Restore Core
            if self.library: self.library.fade_in()
            if self.face: self.face.fade_in()
            
                
            # 2. Restore Peripherals ONLY if they were active
            if self._was_graph_open and self.graph: self.graph.fade_in()
            if self._was_media_open and self.media: self.media.fade_in()
            
            if self._was_timer_open and self.timer: self.timer.fade_in()
            
            # Instantly re-assert the hierarchy
            self.enforce_global_hierarchy()